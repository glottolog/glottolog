from __future__ import unicode_literals, print_function, division
from collections import defaultdict
import re
import os

from clldutils.path import as_posix, move, readlines

from pyglottolog.util import build_path
from pyglottolog.languoids import Languoid, TREE, Level, Glottocode
from pyglottolog.api import Glottolog


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


def languoid(api, new, path, name_and_codes, level):
    lname, codes = name_and_codes.split('[', 1)
    lname = lname.strip()
    glottocode, isocode = codes[:-1].split('][')
    if not glottocode:
        glottocode = new.get((lname, level))
    if not glottocode:
        new[lname, level] = glottocode = api.glottocodes.new(lname)
        #print('+++ {0} {1}: {2}'.format(level, lname, glottocode))

    lineage = []
    if path:
        for i, comp in enumerate(path.split('], ')):
            if comp.endswith(']'):
                comp = comp[:-1]
            name, id_ = comp.split(' [', 1)

            _level = Level.family
            if level == Level.dialect:
                _level = Level.language if i == 0 else Level.dialect

            if not id_:
                id_ = new.get((name, _level))
            if not id_:
                new[name, _level] = id_ = api.glottocodes.new(name)
                #print('+++ {0} {1}: {2}'.format(_level, name, id_))

            lineage.append((name, id_, _level))

    lang = Languoid.from_name_id_level(lname, glottocode, level, lineage=lineage)
    if isocode:
        if len(isocode) == 3:
            lang.iso = isocode
        else:
            lang.hid = isocode
    return lang


def read_lff(api, new, level, fname=None):
    assert isinstance(level, Level)
    lang_line = re.compile('\s+' + NAME_AND_ID_REGEX + '(\[([a-z]{3}|NOCODE\_[^\]]+)?\])$')
    class_line = re.compile(NAME_AND_ID_REGEX + '(,\s*' + NAME_AND_ID_REGEX + ')*$')
    isolate_line = re.compile('([^\[]+)(\[-isolate-\])$')

    path = None
    for line in fname if isinstance(fname, list) \
            else readlines(fname or api.build_path('%sff.txt' % level.name[0])):
        line = line.rstrip()
        if line.startswith('#') or not line.strip():
            # ignore comments or empty lines
            continue
        match = lang_line.match(line)
        if match:
            assert path
            yield languoid(
                api,
                new,
                None if path == 'isolate' else path,
                line.strip(),
                level)
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

    langdir = groupdir.joinpath(lang.id)
    langdir.mkdir()

    if lang.id in old_tree:
        old_lang = old_tree[lang.id]
        if old_lang.level != lang.level:
            old_lang.level = lang.level
        if old_lang.name != lang.name:
            old_lang.name = lang.name
        if old_lang.iso != lang.iso:
            old_lang.iso = lang.iso
        old_lang.write_info(langdir)
    else:
        lang.write_info(langdir)


def lff2tree(api):
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
    builddir = api.build_path('tree')
    old_tree = {l.id: l for l in api.languoids()}
    out = api.tree

    if out.exists():
        if builddir.exists():
            try:
                rmtree(builddir)
            except:  # pragma: no cover
                pass
            if builddir.exists():  # pragma: no cover
                raise ValueError('please remove %s before proceeding' % builddir)
        # move the old tree out of the way
        move(out, builddir)
    out.mkdir()

    new = {}
    languages = {}
    for lang in read_lff(api, new, Level.language, api.build_path('lff.txt')):
        languages[lang.id] = lang
        lang2tree(lang, lang.lineage, out, old_tree)

    missing = set()
    for lang in read_lff(api, new, Level.dialect, api.build_path('dff.txt')):
        if not lang.lineage or lang.lineage[0][1] not in languages:
            #raise ValueError('unattached dialect')  # pragma: no cover
            missing.add(lang.lineage[0])
            continue

        lang2tree(
            lang, languages[lang.lineage[0][1]].lineage + lang.lineage, out, old_tree)

    for m in missing:
        print('--- missing language referenced from dff.txt: {0[0]} [{0[1]}]'.format(m))


def tree2lff(api):
    languoids = {Level.dialect: defaultdict(list), Level.language: defaultdict(list)}

    for l in api.languoids():
        if l.level in languoids:
            languoids[l.level][l.lff_group()].append(l.lff_language())

    for level, languages in languoids.items():
        with api.build_path('%sff.txt' % level.name[0]).open('w', encoding='utf8') as fp:
            fp.write('# -*- coding: utf-8 -*-\n')
            for path in sorted(languages):
                fp.write(path + '\n')
                for l in sorted(languages[path]):
                    fp.write(l + '\n')
