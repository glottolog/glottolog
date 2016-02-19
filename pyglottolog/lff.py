from __future__ import unicode_literals, print_function, division
from collections import defaultdict
import re
import os

from clldutils.path import Path, copytree, as_posix

from pyglottolog.util import build_path
from pyglottolog.languoids import Languoid, walk_tree, TREE, ID_REGEX


NAME_AND_ID_REGEX = '([^\[]+)(\[' + ID_REGEX + '\])'


def rmtree(d, **kw):
    d = as_posix(d)
    for path in (os.path.join(d, f) for f in os.listdir(d)):
        if os.path.isdir(path):
            rmtree(path)
        else:
            os.unlink(path)
    os.rmdir(d)


def read_lff(level, fp=None):
    lang_line = re.compile('\s+' + NAME_AND_ID_REGEX + '(\[([a-z]{3})?\])$')
    class_line = re.compile(NAME_AND_ID_REGEX + '(,\s*' + NAME_AND_ID_REGEX + ')*$')
    isolate_line = re.compile('([^\[]+)(\[-isolate-\])$')

    path = None
    with fp or build_path('%sff.txt' % level[0]).open(encoding='utf8') as fp:
        for line in fp:
            line = line.rstrip()
            if line.startswith('#') or not line.strip():
                # ignore comments or empty lines
                continue
            match = lang_line.match(line)
            if match:
                assert path
                yield Languoid.from_lff(
                    None if path == 'isolate' else path, line.strip(), level)
            else:
                match = isolate_line.match(line)
                if match:
                    path = 'isolate'
                else:
                    # assert it matches a classification line!
                    if not class_line.match(line):
                        raise ValueError(line)
                    path = line.strip()


def lang2tree(lang, lineage, out, old_tree):
    groupdir = out

    for name, id_, level in lineage:
        groupdir = groupdir.joinpath(id_)
        if not groupdir.exists():
            groupdir.mkdir()
            if id_ in old_tree:
                group = old_tree[id_]
                assert group.level == level
                if name != group.name:
                    # rename a subgroup!
                    group.name = name
            else:
                assert id_.startswith('NOCODE')
                group = Languoid.from_name_id_level(name, id_, level)
            group.write_info(groupdir)

    langdir = groupdir.joinpath(lang.fname())
    langdir.mkdir()

    if lang.id in old_tree:
        old_lang = old_tree[lang.id]
        assert old_lang.level == lang.level
        if old_lang.name != lang.name:
            old_lang.name = lang.name
        old_lang.write_info(langdir)
    else:
        assert lang.id.startswith('NOCODE')
        lang.write_info(langdir)


def lff2tree(tree=TREE, outdir=None, test=False):
    """
    - get mapping glottocode -> Languoid from old tree
    - assemble new directory tree
      - for each path component in lff/dff:
        - create new dir
        - copy info file from old tree (possibly updating the name) or
        - create info file
      - for each language/dialect in lff/dff:
        - create new dir
        - copy info file from old tree (possibly updating the name) or
        - create info file
    - rm old tree
    - copy new tree
    """
    out = Path(outdir or build_path('tree'))
    if not out.parent.exists():
        out.parent.mkdir()
    if out.exists():
        rmtree(out)
    out.mkdir()
    old_tree = {l.id: l for l in walk_tree(tree)} if tree else {}

    languages = {}
    for lang in read_lff('language'):
        languages[lang.id] = lang
        lang2tree(lang, lang.lineage, out, old_tree)

    for lang in read_lff('dialect'):
        if not lang.lineage or lang.lineage[0][1] not in languages:
            raise ValueError('unattached dialect')

        lang2tree(
            lang, languages[lang.lineage[0][1]].lineage + lang.lineage, out, old_tree)

    if not test:
        rmtree(TREE, ignore_errors=True)
        copytree(out, TREE)


def tree2lff(tree=TREE):
    languoids = dict(dialect=defaultdict(list), language=defaultdict(list))
    nodes = {}

    for l in walk_tree(tree=tree, nodes=nodes):
        if l.level in languoids:
            languoids[l.level][l.lff_group()].append(l.lff_language())

    for level, languages in languoids.items():
        with build_path('%sff.txt' % level[0]).open('w', encoding='utf8') as fp:
            fp.write('# -*- coding: utf-8 -*-\n')
            for path in sorted(languages):
                fp.write(path + '\n')
                for l in sorted(languages[path]):
                    fp.write(l + '\n')
