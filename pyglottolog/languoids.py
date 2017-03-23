# coding: utf8
from __future__ import unicode_literals
import os
from collections import defaultdict

from clldutils.misc import UnicodeMixin
from clldutils.path import Path
from clldutils.inifile import INI
from newick import Node

from pyglottolog.objects import (
    Glottocode, EthnologueComment, Reference, Level, Country, Macroarea,
    EndangermentStatus, ClassificationComment, ISORetirement,
)

INFO_FILENAME = 'md.ini'


class Languoid(UnicodeMixin):
    """
    Info on languoids is encoded in the ini files and in the directory hierarchy.
    This class provides access to all of it.
    """
    section_core = 'core'

    def __init__(self, cfg, lineage=None, id_=None, directory=None, tree=None):
        """

        :param cfg:
        :param lineage: list of ancestors, given as (id, name) pairs.
        """
        assert (id_ and tree) or directory
        if id_ is None:
            id_ = Glottocode(directory.name)
        lineage = lineage or []
        assert all([
            Glottocode.pattern.match(id) and
            Level.get(level) for name, id, level in lineage])
        self.lineage = [(name, id, Level.get(level)) for name, id, level in lineage]
        self.cfg = cfg
        self.dir = directory or tree.joinpath(*[id for name, id, _ in self.lineage])
        self._id = id_

    @classmethod
    def from_dir(cls, directory, nodes=None, **kw):
        if nodes is None:
            nodes = {}
        cfg = INI.from_file(directory.joinpath(INFO_FILENAME), interpolation=None)

        lineage = []
        for parent in directory.parents:
            id_ = parent.name
            assert id_ != directory.name
            if not Glottocode.pattern.match(id_):
                # we ignore leading non-languoid-dir path components.
                break

            if id_ not in nodes:
                l = Languoid.from_dir(parent, nodes=nodes)
                nodes[id_] = (l.name, l.id, l.level)
            lineage.append(nodes[id_])

        res = cls(cfg, list(reversed(lineage)), directory=directory)
        nodes[res.id] = (res.name, res.id, res.level)
        return res

    @classmethod
    def from_name_id_level(cls, tree, name, id, level, **kw):
        cfg = INI(interpolation=None)
        cfg.read_dict(dict(core=dict(name=name)))
        res = cls(cfg, kw.pop('lineage', []), id_=Glottocode(id), tree=tree)
        res.level = Level.get(level)
        for k, v in kw.items():
            setattr(res, k, v)
        return res

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return '<%s %s>' % (self.level.name.capitalize(), self.id)

    def __unicode__(self):
        return '%s [%s]' % (self.name, self.id)

    def _set(self, key, value):
        if value is None and key in self.cfg[self.section_core]:
            del self.cfg[self.section_core][key]
        else:
            self.cfg.set(self.section_core, key, value)

    def _get(self, key, type_=None):
        res = self.cfg.get(self.section_core, key, fallback=None)
        if type_ and res:
            return type_(res)
        return res

    def newick_node(self, nodes=None):
        label = '{0} [{1}]'.format(
            self.name.replace(',', '/').replace('(', '{').replace(')', '}'), self.id)
        if self.iso:
            label += '[%s]' % self.iso
        if self.level == Level.language:
            label += '-l-'
        n = Node(name="'{0}'".format(label))
        children = self.children if nodes is None else self.children_from_nodemap(nodes)
        for nn in sorted(children, key=lambda nn: nn.name):
            n.add_descendant(nn.newick_node(nodes=nodes))
        return n

    def write_info(self, outdir=None):
        outdir = outdir or self.dir
        if not isinstance(outdir, Path):
            outdir = Path(outdir)
        if outdir.name != self.id:
            outdir = outdir.joinpath(self.id)
        if not outdir.exists():
            outdir.mkdir()
        fname = outdir.joinpath(INFO_FILENAME)
        self.cfg.write(fname)
        if os.linesep == '\n':
            with fname.open(encoding='utf8') as fp:
                text = fp.read()
            with fname.open('w', encoding='utf8') as fp:
                fp.write(text.replace('\n', '\r\n'))
        return fname

    # -------------------------------------------------------------------------
    # Accessing info of a languoid
    # -------------------------------------------------------------------------
    @property
    def glottocode(self):
        return self._id

    @property
    def id(self):
        return self._id

    @property
    def category(self):
        fid = self.lineage[0][1] if self.lineage else None
        category_map = defaultdict(
            lambda: 'Spoken L1 Language',
            **{
                'book1242': 'Bookkeeping',
                'unat1236': 'Unattested',
                'uncl1493': 'Unclassifiable',
                'sign1238': 'Sign Language',
                'arti1236': 'Artificial Language',
                'spee1234': 'Speech Register',
                'pidg1258': 'Pidgin',
                'mixe1287': 'Mixed Language',
            })
        if self.level == Level.language:
            return category_map[fid]
        cat = self.level.name.capitalize()
        if self.level == Level.family:
            if self.id.startswith('unun9') or \
                    self.id in category_map or fid in category_map:
                cat = 'Pseudo ' + cat
        return cat

    @property
    def isolate(self):
        return self.level == Level.language and not self.lineage

    def children_from_nodemap(self, nodes):
        # A faster alternative to `children` when the relevant languoids have already been
        # read from disc.
        return [nodes[d.name] for d in self.dir.iterdir() if d.is_dir()]

    @property
    def children(self):
        return [Languoid.from_dir(d) for d in self.dir.iterdir() if d.is_dir()]

    def ancestors_from_nodemap(self, nodes):
        # A faster alternative to `ancestors` when the relevant languoids have already
        # been read from disc.
        return [nodes[l[1]] for l in self.lineage]

    @property
    def ancestors(self):
        res = []
        for parent in self.dir.parents:
            id_ = parent.name
            if Glottocode.pattern.match(id_):
                res.append(Languoid.from_dir(parent))
            else:
                # we ignore leading non-languoid-dir path components.
                break
        return list(reversed(res))

    @property
    def parent(self):
        ancestors = self.ancestors
        return ancestors[-1] if ancestors else None

    @property
    def family(self):
        ancestors = self.ancestors
        return ancestors[0] if ancestors else None

    @property
    def names(self):
        if 'altnames' in self.cfg:
            return {k: self.cfg.getlist('altnames', k) for k in self.cfg['altnames']}
        return {}

    @property
    def identifier(self):
        if 'identifier' in self.cfg:
            return self.cfg['identifier']
        return {}

    @property
    def sources(self):
        if self.cfg.has_option('sources', 'glottolog'):
            return Reference.from_list(self.cfg.getlist('sources', 'glottolog'))
        return []

    @sources.setter
    def sources(self, refs):
        assert all(isinstance(r, Reference) for r in refs)
        self.cfg.set('sources', 'glottolog', ['{0}'.format(ref) for ref in refs])

    @property
    def endangerment(self):
        if 'status' in self.cfg[self.section_core]:
            res = self.cfg.get(self.section_core, 'status')
            if res:
                return EndangermentStatus.get(res.lower())

    @endangerment.setter
    def endangerment(self, value):
        value = value.lower() if hasattr(value, 'lower') else value
        self._set('status', EndangermentStatus.get(value).name)

    @property
    def classification_comment(self):
        if 'classification' in self.cfg:
            cfg = self.cfg['classification']
            return ClassificationComment(
                family=cfg.get('family'),
                familyrefs=self.cfg.getlist('classification', 'familyrefs'),
                sub=cfg.get('sub'),
                subrefs=self.cfg.getlist('classification', 'subrefs'))

    @property
    def ethnologue_comment(self):
        section = 'hh_ethnologue_comment'
        if section in self.cfg:
            return EthnologueComment(**self.cfg[section])

    @property
    def macroareas(self):
        return [Macroarea.get(n)
                for n in self.cfg.getlist(self.section_core, 'macroareas')]

    @macroareas.setter
    def macroareas(self, value):
        assert isinstance(value, (list, tuple)) \
            and all(o in list(Macroarea) for o in value)
        self._set('macroareas', ['{0}'.format(ma) for ma in value])

    @property
    def countries(self):
        return [Country.from_text(n)
                for n in self.cfg.getlist(self.section_core, 'countries')]

    @countries.setter
    def countries(self, value):
        assert isinstance(value, (list, tuple)) \
            and all(isinstance(o, Country) for o in value)
        self._set('countries', ['{0}'.format(c) for c in value])

    @property
    def name(self):
        return self._get('name')

    @name.setter
    def name(self, value):
        self._set('name', value)

    @property
    def latitude(self):
        return self._get('latitude', float)

    @latitude.setter
    def latitude(self, value):
        self._set('latitude', float(value))

    @property
    def longitude(self):
        return self._get('longitude', float)

    @longitude.setter
    def longitude(self, value):
        self._set('longitude', float(value))

    @property
    def hid(self):
        return self._get('hid')

    @hid.setter
    def hid(self, value):
        self._set('hid', value)

    @property
    def level(self):
        return self._get('level', Level.get)

    @level.setter
    def level(self, value):
        self._set('level', Level.get(value).name)

    @property
    def iso(self):
        return self._get('iso639-3')

    @iso.setter
    def iso(self, value):
        self._set('iso639-3', value)

    @property
    def iso_code(self):
        return self._get('iso639-3')

    @iso_code.setter
    def iso_code(self, value):
        self._set('iso639-3', value)

    @property
    def iso_retirement(self):
        if 'iso_retirement' in self.cfg:
            kw = self.cfg['iso_retirement']
            if 'comment' in kw:
                kw['comment'] = self.cfg.gettext('iso_retirement', 'comment')
            return ISORetirement(**self.cfg['iso_retirement'])

    @property
    def fname(self):
        return self.dir.joinpath(INFO_FILENAME)
