# coding: utf8
from __future__ import unicode_literals
import os
import re
from itertools import takewhile
from collections import defaultdict, OrderedDict

from enum import IntEnum
from six import text_type
from clldutils.misc import slug, UnicodeMixin
from clldutils import jsonlib
from clldutils.path import Path
from clldutils.inifile import INI
import attr

from pyglottolog.util import languoids_path


TREE = languoids_path('tree')


class Level(IntEnum):
    family = 1
    language = 2
    dialect = 3


@attr.s
class ClassificationComment(object):
    sub = attr.ib(default=None)
    family = attr.ib(default=None)


@attr.s
class ISORetirement(object):
    code = attr.ib()
    comment = attr.ib()
    name = attr.ib()
    effective = attr.ib()
    reason = attr.ib(default=None)
    remedy = attr.ib(default=None)
    change_request = attr.ib(default=None)

    def asdict(self):
        return attr.asdict(self)


class EndangermentStatus(IntEnum):
    """
    http://www.unesco.org/new/en/culture/themes/endangered-languages/atlas-of-languages-in-danger/
    """
    # language is spoken by all generations;
    # intergenerational transmission is uninterrupted:
    safe = 0

    # most children speak the language, but it may be restricted to certain domains
    # (e.g., home):
    vulnerable = 1

    # children no longer learn the language as mother tongue in the home:
    definite = 2

    # language is spoken by grandparents and older generations; while the parent
    # generation may understand it, they do not speak it to children or among themselves:
    severe = 3

    # the youngest speakers are grandparents and older, and they speak the language
    # partially and infrequently:
    critical = 4

    # there are no speakers left since the 1950s:
    extinct = 5

    @classmethod
    def from_name(cls, value):
        value = value.lower().split()[0]
        if value.endswith('ly'):
            value = value[:-2]
        return getattr(cls, value)


class Glottocodes(object):
    def __init__(self, fname):
        self._fname = fname
        self._store = jsonlib.load(self._fname)

    def __contains__(self, item):
        alpha, num = Glottocode(item).split()
        return alpha in self._store and num <= self._store[alpha]

    def new(self, name, dry_run=False):
        alpha = slug(text_type(name))[:4]
        assert alpha
        while len(alpha) < 4:
            alpha += alpha[-1]
        num = self._store.get(alpha, 1233) + 1
        if not dry_run:
            self._store[alpha] = num
            # Store the updated dictionary of glottocodes back.
            ordered = OrderedDict()
            for k in sorted(self._store.keys()):
                ordered[k] = self._store[k]
            jsonlib.dump(ordered, self._fname, indent=4)
        return Glottocode('%s%s' % (alpha, num))


class Glottocode(text_type):
    regex = '[a-z0-9]{4}[0-9]{4}'
    pattern = re.compile(regex + '$')

    def __new__(cls, content):
        if not cls.pattern.match(content):
            raise ValueError(content)
        return text_type.__new__(cls, content)

    def split(self):
        return self[:4], int(self[4:])


class Languoid(UnicodeMixin):
    section_core = 'core'

    def __init__(self, cfg, lineage=None, directory=None):
        """

        :param cfg:
        :param lineage: list of ancestors, given as (id, name) pairs.
        """
        lineage = lineage or []
        assert all([
            Glottocode.pattern.match(id) and Level(level) for name, id, level in lineage])
        self.lineage = [(name, id, Level(level)) for name, id, level in lineage]
        self.cfg = cfg
        self.dir = directory or TREE.joinpath(*[id for name, id, _ in self.lineage])

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return '<%s %s>' % (self.level.name.capitalize(), self.id)

    def __unicode__(self):
        return '%s [%s]' % (self.name, self.id)

    @classmethod
    def from_dir(cls, directory, nodes=None, **kw):
        assert Glottocode.pattern.match(directory.name)
        ini = directory.joinpath(directory.name + '.ini')
        if nodes is None:
            nodes = {}
        ini = Path(ini)
        directory = ini.parent
        cfg = INI(interpolation=None)
        cfg.read(ini.as_posix(), encoding='utf8')

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
    def from_name_id_level(cls, name, id, level, **kw):
        cfg = INI(interpolation=None)
        cfg.read_dict(dict(core=dict(name=name, glottocode=id)))
        res = cls(cfg, kw.pop('lineage', []))
        res.level = Level(level)
        for k, v in kw.items():
            setattr(res, k, v)
        return res

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

    @property
    def children(self):
        return [Languoid.from_dir(d) for d in self.dir.iterdir() if d.is_dir()]

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

    def _set(self, key, value):
        self.cfg.set(self.section_core, key, value)

    def _get(self, key, type_=None):
        res = self.cfg.get(self.section_core, key, fallback=None)
        if type_ and res:
            return type_(res)
        return res

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
    def endangerment(self):
        if 'status' in self.cfg[self.section_core]:
            res = self.cfg.get(self.section_core, 'status')
            if res:
                return EndangermentStatus.from_name(res)

    @endangerment.setter
    def endangerment(self, value):
        self._set('status', EndangermentStatus.from_name(value).name)

    @property
    def classification_comment(self):
        cfg = self.cfg['classification'] if 'classification' in self.cfg else {}
        return ClassificationComment(**cfg)

    @property
    def macroareas(self):
        return self.cfg.getlist(self.section_core, 'macroareas')

    @macroareas.setter
    def macroareas(self, value):
        assert isinstance(value, (list, tuple))
        self._set('macroareas', value)

    @property
    def name(self):
        return self._get('name')

    @name.setter
    def name(self, value):
        self._set('name', value)

    @property
    def id(self):
        return self._get('glottocode', Glottocode)

    @id.setter
    def id(self, value):
        self._set('glottocode', Glottocode(value))

    @property
    def glottocode(self):
        return self._get('glottocode', Glottocode)

    @glottocode.setter
    def glottocode(self, value):
        self._set('glottocode', Glottocode(value))

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
        return self._get('level', lambda v: getattr(Level, v))

    @level.setter
    def level(self, value):
        self._set('level', value.name)

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
            try:
                return ISORetirement(**self.cfg['iso_retirement'])
            except:
                print(self.cfg['iso_retirement'].keys())
                raise

    def fname(self, suffix=''):
        return '%s%s' % (self.id, suffix)

    def write_info(self, outdir=None):
        outdir = outdir or self.id
        if not isinstance(outdir, Path):
            outdir = Path(outdir)
        if not outdir.exists():
            outdir.mkdir()
        fname = outdir.joinpath(self.fname('.ini'))
        self.cfg.write(fname)
        if os.linesep == '\n':
            with fname.open(encoding='utf8') as fp:
                text = fp.read()
            with fname.open('w', encoding='utf8') as fp:
                fp.write(text.replace('\n', '\r\n'))
        return fname

    def lff_group(self):
        if self.level == Level.dialect:
            lineage = reversed(
                list(takewhile(lambda x: x[2] != Level.family, reversed(self.lineage))))
        else:
            lineage = self.lineage
        if not self.lineage:
            return '%s [-isolate-]' % self.name
        res = ', '.join('%s [%s]' % (name, id) for name, id, level in lineage)
        return res or 'ERROR [-unclassified-]'

    def lff_language(self):
        return '    %s [%s][%s]' % (self.name, self.id, self.iso or self.hid or '')
