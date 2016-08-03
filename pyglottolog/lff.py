from __future__ import unicode_literals, print_function, division
from collections import defaultdict
import re
import os
import shutil

from clldutils.path import Path, as_posix

from pyglottolog.util import build_path
from pyglottolog.languoids import Languoid, walk_tree, TREE, Level, Glottocode


NAME_AND_ID_REGEX = '([^\[]+)(\[(' + Glottocode.regex + ')?\])'


def rmtree(d, **kw):
    """More performant way to remove large directory structures."""
    d = as_posix(d)
    for path in (os.path.join(d, f) for f in os.listdir(d)):
        if os.path.isdir(path):
            rmtree(path)
        else:
            os.unlink(path)
    os.rmdir(d)


def read_lff(level, fp=None, dry_run=False):
    assert isinstance(level, Level)
    lang_line = re.compile('\s+' + NAME_AND_ID_REGEX + '(\[([a-z]{3}|NOCODE\_[^\]]+)?\])$')
    class_line = re.compile(NAME_AND_ID_REGEX + '(,\s*' + NAME_AND_ID_REGEX + ')*$')
    isolate_line = re.compile('([^\[]+)(\[-isolate-\])$')

    path = None
    with fp or build_path('%sff.txt' % level.name[0]).open(encoding='utf8') as fp:
        for line in fp:
            line = line.rstrip()
            if line.startswith('#') or not line.strip():
                # ignore comments or empty lines
                continue
            match = lang_line.match(line)
            if match:
                assert path
                yield Languoid.from_lff(
                    None if path == 'isolate' else path,
                    line.strip(),
                    level,
                    dry_run=dry_run)
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
                group = Languoid.from_name_id_level(name, id_, level)
            group.write_info(groupdir)

    langdir = groupdir.joinpath(lang.fname())
    langdir.mkdir()

    if lang.id in old_tree:
        old_lang = old_tree[lang.id]
        assert old_lang.level == lang.level
        if old_lang.name != lang.name:
            old_lang.name = lang.name
        if old_lang.iso != lang.iso:
            old_lang.iso = lang.iso
        old_lang.write_info(langdir)
    else:
        lang.write_info(langdir)


def lff2tree(tree=TREE, outdir=None, builddir=None, lffs=None):
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
    # FIXME: instead of removing trees, we should just move the current one
    # from outdir to build, and then recreate in outdir.
    builddir = Path(builddir) if builddir else build_path('tree')
    old_tree = {l.id: l for l in walk_tree(tree)} if tree else {}
    out = Path(outdir or tree)
    if not out.parent.exists():
        out.parent.mkdir()

    if out.exists():
        if builddir.exists():
            try:
                rmtree(builddir)
            except:  # pragma: no cover
                pass
            if builddir.exists():  # pragma: no cover
                raise ValueError('please remove %s before proceeding' % builddir)
        # move the old tree out of the way
        shutil.move(out.as_posix(), builddir.as_posix())
    out.mkdir()

    lffs = lffs or {}
    languages = {}
    for lang in read_lff(Level.language, fp=lffs.get(Level.language)):
        languages[lang.id] = lang
        lang2tree(lang, lang.lineage, out, old_tree)

    for lang in read_lff(Level.dialect, fp=lffs.get(Level.dialect)):
        if not lang.lineage or lang.lineage[0][1] not in languages:
            raise ValueError('unattached dialect')  # pragma: no cover

        lang2tree(
            lang, languages[lang.lineage[0][1]].lineage + lang.lineage, out, old_tree)


def tree2lff(tree=TREE, out_paths=None):
    out_paths = out_paths or {}
    languoids = {Level.dialect: defaultdict(list), Level.language: defaultdict(list)}
    nodes = {}

    for l in walk_tree(tree=tree, nodes=nodes):
        if l.level in languoids:
            languoids[l.level][l.lff_group()].append(l.lff_language())

    for level, languages in languoids.items():
        out_path = out_paths.get(level, build_path('%sff.txt' % level.name[0]))
        with out_path.open('w', encoding='utf8') as fp:
            fp.write('# -*- coding: utf-8 -*-\n')
            for path in sorted(languages):
                fp.write(path + '\n')
                for l in sorted(languages[path]):
                    fp.write(l + '\n')
