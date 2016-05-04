# coding: utf8
from __future__ import unicode_literals
import re
from itertools import takewhile
from collections import defaultdict

from clldutils.misc import slug
from clldutils.path import Path, walk
from clldutils.inifile import INI

from pyglottolog.util import languoids_path, parse_conjunctions


TREE = languoids_path('tree')
ID_REGEX = '([a-z0-9]{4}[0-9]{4}|NOCODE(_[A-Za-z0-9\-]+)?)'


class Languoid(object):
    section_core = 'core'
    id_pattern = re.compile(ID_REGEX + '$')

    def __init__(self, cfg, lineage=None, directory=None):
        """

        :param cfg:
        :param lineage: list of ancestors, given as (id, name) pairs.
        """
        lineage = lineage or []
        assert all([self.id_pattern.match(id) for name, id, level in lineage])
        self.lineage = lineage
        self.cfg = cfg
        self.dir = directory or TREE.joinpath(*[id for name, id, _ in self.lineage])

    @classmethod
    def from_dir(cls, directory, **kw):
        for p in directory.iterdir():
            if p.is_file():
                assert p.suffix == '.ini'
                return cls.from_ini(p, **kw)

    @classmethod
    def from_ini(cls, ini, nodes={}):
        if not isinstance(ini, Path):
            ini = Path(ini)

        directory = ini.parent
        cfg = INI(interpolation=None)
        cfg.read(ini.as_posix(), encoding='utf8')

        lineage = []
        for parent in directory.parents:
            id_ = parent.name
            assert id_ != directory.name
            if not cls.id_pattern.match(id_):
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
    def from_name_id_level(cls, name, id, level):
        cfg = INI(interpolation=None)
        cfg.read_dict(dict(core=dict(name=name, glottocode=id, level=level)))
        return cls(cfg, [])

    @classmethod
    def from_lff(cls, path, name_and_codes, level):
        lname, codes = name_and_codes.split('[', 1)
        lname = lname.strip()
        glottocode, isocode = codes[:-1].split('][')

        lineage = []
        if path:
            for i, comp in enumerate(path.split('], ')):
                if comp.endswith(']'):
                    comp = comp[:-1]
                name, id_ = comp.split(' [', 1)
                _level = 'family'
                if level == 'dialect':
                    _level = 'language' if i == 0 else 'dialect'
                lineage.append((name, id_, _level))

        cfg = INI(interpolation=None)
        cfg.read_dict(dict(core=dict(name=lname, glottocode=glottocode, level=level)))
        res = cls(cfg, lineage)
        if isocode:
            res.iso = isocode
        return res

    @property
    def children(self):
        return [Languoid.from_dir(d) for d in self.dir.iterdir() if d.is_dir()]

    @property
    def ancestors(self):
        res = []
        for parent in self.dir.parents:
            id_ = parent.name
            if self.id_pattern.match(id_):
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
        return self._get('glottocode')

    @id.setter
    def id(self, value):
        self._set('glottocode', value)

    @property
    def glottocode(self):
        return self._get('glottocode')

    @glottocode.setter
    def glottocode(self, value):
        self._set('glottocode', value)

    @property
    def latitude(self):
        return self._get('latitude', float)

    @latitude.setter
    def latitude(self, value):
        self._set('latitude', value)

    @property
    def longitude(self):
        return self._get('longitude', float)

    @longitude.setter
    def longitude(self, value):
        self._set('longitude', value)

    @property
    def hid(self):
        return self._get('hid')

    @property
    def level(self):
        return self._get('level')

    @level.setter
    def level(self, value):
        self._set('level', value)

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
    def classification_status(self):
        return self._get('classification_status')

    @classification_status.setter
    def classification_status(self, value):
        self._set('classification_status', value)

    def fname(self, suffix=''):
        return '%s%s' % (self.id, suffix)

    def write_info(self, outdir):
        if not isinstance(outdir, Path):
            outdir = Path(outdir)
        self.cfg.write(outdir.joinpath(self.fname('.ini')))

    def lff_group(self):
        if self.level == 'dialect':
            lineage = reversed(
                list(takewhile(lambda x: x[2] != 'family', reversed(self.lineage))))
        else:
            lineage = self.lineage
        if not self.lineage:
            return '%s [-isolate-]' % self.name
        res = ', '.join('%s [%s]' % (name, id) for name, id, level in lineage)
        return res or 'ERROR [-unclassified-]'

    def lff_language(self):
        res = '    %s [%s][%s]' % (self.name, self.id, self.iso or '')
        if self.classification_status:
            res = '%s %s' % (res, self.classification_status)
        return res


def walk_tree(tree=TREE, **kw):
    for fname in walk(tree, mode='files', followlinks=True):
        if fname.suffix == '.ini':
            yield Languoid.from_ini(fname, **kw)


def make_index(level):
    fname = dict(language='languages', family='families', dialect='dialects')[level]
    links = defaultdict(dict)
    for lang in walk_tree():
        if lang.level == level:
            label = '{0.name} [{0.id}]'.format(lang)
            if lang.iso:
                label += '[%s]' % lang.iso
            links[slug(lang.name)[0]][label] = \
                lang.dir.joinpath(lang.fname('.ini')).relative_to(languoids_path())

    with languoids_path(fname + '.md').open('w', encoding='utf8') as fp:
        fp.write('## %s\n\n' % fname.capitalize())
        fp.write(' '.join(
            '[-%s-](%s_%s.md)' % (i.upper(), fname, i) for i in sorted(links.keys())))
        fp.write('\n')

    for i, langs in links.items():
        with languoids_path('%s_%s.md' % (fname, i)).open('w', encoding='utf8') as fp:
            for label in sorted(langs.keys()):
                fp.write('- [%s](%s)\n' % (label, langs[label]))


#
# The following two functions are necessary to make the compilation of the monster bib
# compatible with the new way of storing languoid data.
#
def macro_area_from_hid(tree=TREE):
    res = {}
    for lang in walk_tree(tree):
        if lang.hid:
            macroareas = lang.cfg.getlist('core', 'macroareas')
            res[lang.hid] = macroareas[0] if macroareas else ''
    return res


def load_triggers(tree=TREE, type_='lgcode'):
    res = {}
    for lang in walk_tree(tree):
        if lang.hid and lang.cfg.has_option('triggers', type_):
            triggers = lang.cfg.getlist('triggers', type_)
            if not triggers:
                continue
            res[(type_, '%s [%s]' % (lang.name, lang.hid))] = [
                parse_conjunctions(t) for t in triggers]
    return res
