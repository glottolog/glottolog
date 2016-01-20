"""

from lff to directory tree:
- get mapping glottocode -> Languoid from old tree
- assemble new directory tree
  - for each path component in lff:
    - create new dir
      - copy info file from old tree (possibly updating the name) or
      - create new info file
  - for each language in lff:
    - copy subtree rooted in language from old tree or
    - create new dir + info file
- rm old tree
- copy new tree
"""
from __future__ import unicode_literals
import io
from collections import defaultdict
import re
from itertools import takewhile

from clldutils.misc import slug
from clldutils.path import Path, walk
from clldutils.inifile import INI


class Languoid(object):
    section_core = 'core'
    id_pattern = re.compile('[a-z0-9]{4}[0-9]{4}$')

    def __init__(self, cfg, lineage=None):
        """

        :param cfg:
        :param lineage: list of ancestors, given as (id, name) pairs.
        """
        lineage = lineage or []
        assert all([self.id_pattern.match(id) for name, id, level in lineage])
        self.lineage = lineage
        self.cfg = cfg

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
        cfg = INI()
        cfg.read(ini.as_posix(), encoding='utf8')

        lineage = []
        for parent in directory.parents:
            id_ = parent.name.split('.')[-1]
            assert id_ != directory.name.split('.')[-1]
            if not cls.id_pattern.match(id_):
                # we ignore leading non-languoid-dir path components.
                break

            if id_ not in nodes:
                l = Languoid.from_dir(parent, nodes=nodes)
                nodes[id_] = (l.name, l.id, l.level)
            lineage.append(nodes[id_])

        res = cls(cfg, list(reversed(lineage)))
        nodes[res.id] = (res.name, res.id, res.level)
        return res

    @classmethod
    def from_lff(cls, path, name_and_codes, level):
        lname, codes = name_and_codes.split('[', 1)
        lname = lname.strip()
        glottocode, isocode = codes[:-1].split('][')

        lineage = []
        for i, comp in enumerate(path.split('], ')):
            if comp.endswith(']'):
                comp = comp[:-1]
            name, id_ = comp.split(' [', 1)
            if id_ != '-isolate-':
                _level = 'family'
                if level == 'dialect':
                    _level = 'language' if i == 0 else 'dialect'
                lineage.append((name, id_, _level))

        cfg = INI()
        cfg.read_dict(dict(core=dict(name=lname, glottocode=glottocode, level=level)))
        res = cls(cfg, lineage)
        if isocode:
            res.iso = isocode
        return res

    def _set(self, key, value):
        self.cfg.set(self.section_core, key, value)

    def _get(self, key):
        return self.cfg.get(self.section_core, key, fallback=None)

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
    def classification_status(self):
        return self._get('classification_status')

    @classification_status.setter
    def classification_status(self, value):
        self._set('classification_status', value)

    def fname(self, suffix=''):
        return '%s.%s%s' % (slug(self.name), self.id, suffix)

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


def languoids_from_tree(tree, **kw):
    for fname in walk(tree, mode='files'):
        if fname.suffix == '.ini':
            yield Languoid.from_ini(fname, **kw)


def read_lff(p, level):
    path = None
    with io.open(p, encoding='utf8') as fp:
        for line in fp:
            if line.startswith('#'):
                continue
            if line.startswith('    '):
                assert path
                #
                # TODO: handle these errors, or fix them in glottolog before switching!
                #
                if path != 'ERROR [-unclassified-]':
                    yield Languoid.from_lff(path, line.strip(), level)
            else:
                path = line.strip()


def lff2tree(lff, tree=None, outdir='fromlff'):
    out = Path(outdir)
    out.mkdir()
    old_tree = {l.id: l for l in languoids_from_tree(tree)} if tree else {}

    nodes = set()
    languages = {}
    for lang in read_lff(lff, 'language'):
        groupdir = out
        languages[lang.id] = lang

        for name, id_, level in lang.lineage:
            groupdir = groupdir.joinpath('%s.%s' % (slug(name), id_))
            if not groupdir.exists():
                groupdir.mkdir()
                if id_ in old_tree:
                    group = old_tree[id_]
                    assert group.level == level
                    if name != group.name:
                        # rename a subgroup!
                        group.name = name
                    group.write_info(groupdir)
                else:
                    # TODO: create Languoid, write info file!
                    pass

            assert id_ in old_tree
            nodes.add(id_)

        assert lang.id in old_tree
        nodes.add(lang.id)
        old_lang = old_tree[lang.id]
        assert old_lang.level == lang.level
        if old_lang.name != lang.name:
            old_lang.name = lang.name
        langdir = groupdir.joinpath(lang.fname())
        langdir.mkdir()
        old_lang.write_info(langdir)

    for lang in read_lff(lff.replace('lff', 'dff'), 'dialect'):
        groupdir = out

        if not lang.lineage:
            # TODO: handle error of un-attached dialects!
            continue

        for name, id_, level in languages[lang.lineage[0][1]].lineage + lang.lineage:
            groupdir = groupdir.joinpath('%s.%s' % (slug(name), id_))
            if not groupdir.exists():
                groupdir.mkdir()
                if id_ in old_tree:
                    group = old_tree[id_]
                    assert group.level == level
                    if name != group.name:
                        # rename a subgroup!
                        group.name = name
                    group.write_info(groupdir)
                else:
                    # TODO: create Languoid, write info file!
                    pass

            assert id_ in old_tree
            nodes.add(id_)

        assert lang.id in old_tree
        nodes.add(lang.id)
        old_lang = old_tree[lang.id]
        assert old_lang.level == lang.level
        if old_lang.name != lang.name:
            old_lang.name = lang.name
        langdir = groupdir.joinpath(lang.fname())
        langdir.mkdir()
        old_lang.write_info(langdir)

    print len(nodes)


def tree2lff(tree):
    languoids = dict(dialect=defaultdict(list), language=defaultdict(list))
    nodes = {}

    for l in languoids_from_tree(tree, nodes=nodes):
        if l.level in languoids:
            languoids[l.level][l.lff_group()].append(l.lff_language())

    for level, languages in languoids.items():
        with io.open('%sff.txt' % level[0], 'w', encoding='utf8') as fp:
            fp.write('# -*- coding: utf-8 -*-\n')
            for path in sorted(languages):
                fp.write(path + '\n')
                for l in sorted(languages[path]):
                    fp.write(l + '\n')


if __name__ == "__main__":
    import sys
    tree2lff(sys.argv[1])
