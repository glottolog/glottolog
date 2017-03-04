from __future__ import unicode_literals, print_function, division
from collections import defaultdict, Counter
from operator import itemgetter
import re
import os
import logging

from clldutils.path import as_posix, move, readlines

from pyglottolog.languoids import Languoid
from pyglottolog.objects import Level, Glottocode

ISOLATE_ID = '-isolate-'
LINEAGE_SEP = ';'
NAME_AND_ID_PATTERN = re.compile(
    '(?P<name>[^\[;]+)'
    '(\[(?P<gc>(' + Glottocode.regex + ')|' + ISOLATE_ID + ')?\])\s*'
    '(?P<hid>[a-z]{3}|NOCODE_[^;]+)?$')


def parse_languoid(s, log):
    match = NAME_AND_ID_PATTERN.match(s.strip())
    if not match or not match.group('name').strip():
        log.error('Invalid languoid spec: {0}'.format(s))
        raise ValueError()
    return match.group('name').strip(), match.group('gc'), match.group('hid')


def rmtree(d, **kw):
    """More performant way to remove large directory structures."""
    d = as_posix(d)
    for path in (os.path.join(d, f) for f in os.listdir(d)):
        if os.path.isdir(path):
            rmtree(path)
        else:
            os.unlink(path)
    os.rmdir(d)


def languoid(api, log, new, path, lname, glottocode, isocode, level):
    if not glottocode:
        glottocode = new.get((lname, level))
    if not glottocode:
        new[lname, level] = glottocode = api.glottocodes.new(lname)

    lineage = []
    if path:
        for i, (name, id_, hid) in enumerate(path):
            if id_ == ISOLATE_ID:
                if i != 0 or len(path) != 1:
                    log.error(
                        'invalid classification line for languoid: {0} [{1}]'.format(
                            lname, glottocode))
                    raise ValueError('invalid isolate line')
                break
            _level = Level.family
            if level == Level.dialect:
                _level = Level.language if i == 0 else Level.dialect

            if not id_:
                id_ = new.get((name, _level))
            if not id_:
                new[name, _level] = id_ = api.glottocodes.new(name)

            lineage.append((name, id_, _level, hid))

    lang = Languoid.from_name_id_level(
        api.tree, lname, glottocode, level, lineage=[(r[0], r[1], r[2]) for r in lineage])
    if (isocode in api.iso) or (isocode is None):
        lang.iso = isocode
    lang.hid = isocode
    return lang, lineage


def read_lff(api, log, new, level, fname=None):
    assert level in [Level.language, Level.dialect]
    log.info('reading {0}s from {1}'.format(level.name, fname))

    path = None
    for line in fname if isinstance(fname, list) \
            else readlines(fname or api.build_path('%sff.txt' % level.name[0])):
        line = line.rstrip()
        if line.startswith('#') or not line.strip():
            # ignore comments or empty lines
            continue

        if re.match('\s', line):
            # leading whitespace => a language/dialect spec.
            if path is None:
                raise ValueError('language line without classification line')
            name, id_, hid = parse_languoid(line.strip(), log)
            yield languoid(api, log, new, path, name, id_, hid, level)
        else:
            path = [parse_languoid(s.strip(), log) for s in line.split(LINEAGE_SEP)]


def lang2tree(api, log, lang, lineage, out, old_tree):
    groupdir = out

    for spec in lineage:
        hid = -1
        name, id_, level = spec[:3]
        if len(spec) == 4:
            hid = spec[3]

        groupdir = groupdir.joinpath(id_)
        if not groupdir.exists():
            groupdir.mkdir()
            if id_ in old_tree:
                group = old_tree[id_]
                if group.level != level:
                    log.info('{0} from {1} to {2}'.format(group, group.level, level))
                    group.level = level
                if name != group.name:
                    # rename a subgroup!
                    group.name = name
            else:
                group = Languoid.from_name_id_level(api.tree, name, id_, level)

            if hid != -1:
                if (hid in api.iso or hid is None) and group.iso != hid:
                    group.iso = hid
                if hid != group.hid:
                    group.hid = hid
            group.write_info(groupdir)

    langdir = groupdir.joinpath(lang.id)
    langdir.mkdir()

    if lang.id in old_tree:
        old_lang = old_tree[lang.id]
        if old_lang.level != lang.level:
            log.info('{0} from {1} to {2}'.format(old_lang, old_lang.level, lang.level))
            old_lang.level = lang.level
        if old_lang.name != lang.name:
            old_lang.name = lang.name
        if old_lang.iso != lang.iso:
            old_lang.iso = lang.iso
        old_lang.write_info(langdir)
    else:
        lang.write_info(langdir)


def lff2tree(api, log=logging.getLogger(__name__)):
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
    languoids = {}

    def checked(l, lin):
        if l.id in languoids:
            print(l.id, lin, l)
        assert l.id not in languoids
        for n, gc, _level, hid in lin:
            if gc in languoids:
                if languoids[gc] != (n, _level, hid):
                    log.error(
                        '{0}: {1} vs {2}'.format(gc, languoids[gc], (n, _level, hid)))
                    raise ValueError('inconsistent languoid data')
            else:
                languoids[gc] = (n, _level, hid)
        languoids[l.id] = (l.name, l.level, l.iso or l.hid)
        return l

    for lang, lineage in read_lff(api, log, new, Level.language, api.build_path('lff.txt')):
        languages[lang.id] = checked(lang, lineage)
        lang2tree(api, log, lang, lineage, out, old_tree)

    for lang, lineage in read_lff(api, log, new, Level.dialect, api.build_path('dff.txt')):
        lang = checked(lang, lineage)
        if not lang.lineage or lang.lineage[0][1] not in languages:
            log.error('missing language in dff: {0[0]} [{0[1]}]'.format(lang.lineage[0]))
            raise ValueError('invalid language referenced')

        lin = languages[lang.lineage[0][1]].lineage + lang.lineage
        lang2tree(api, log, lang, lin, out, old_tree)

    duplicates = False
    for name, getter in [('name', itemgetter(0)), ('hid', itemgetter(2))]:
        count = Counter(getter(spec) for spec in languoids.values())
        for thing, n in count.most_common():
            if thing is None:
                continue
            if n < 2:
                break
            log.error('duplicate {0}: {1} ({2})'.format(name, thing, n))
            duplicates = True
    if duplicates:
        raise ValueError('duplicates found')


def format_comp(l, gc=None):
    res = '{0} [{1}]'.format(l.name, gc or l.id)
    if l.iso:
        res += ' {0}'.format(l.iso)
    elif l.hid:
        res += ' {0}'.format(l.hid)
    return res


def format_language(l):
    return '    {0}'.format(format_comp(l))


def format_classification(l, agg):
    if not l.lineage:
        return format_comp(l, gc=ISOLATE_ID)
    comps = []
    for _, gc, _ in l.lineage:
        a = agg[gc]
        if l.level == Level.language or \
                (l.level == Level.dialect and a.level != Level.family):
            comps.append(format_comp(a))
    return (LINEAGE_SEP + ' ').join(comps)


def tree2lff(api, log=logging.getLogger(__name__)):
    languoids = {Level.dialect: defaultdict(list), Level.language: defaultdict(list)}

    agg = {}
    for l in api.languoids():
        agg[l.id] = l
        if l.level in languoids:
            languoids[l.level][format_classification(l, agg)].append(format_language(l))

    for level, languages in languoids.items():
        ff = api.build_path('%sff.txt' % level.name[0])
        with ff.open('w', encoding='utf8') as fp:
            fp.write('# -*- coding: utf-8 -*-\n')
            for path in sorted(languages):
                fp.write(path + '\n')
                for l in sorted(languages[path]):
                    fp.write(l + '\n')
        log.info('{0}s written to {1}'.format(level.name, ff.as_posix()))
