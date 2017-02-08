# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict, Counter
from itertools import chain

from termcolor import cprint
from clldutils.clilib import command, ParserError
from clldutils.misc import slug
from clldutils.markup import Table

from pyglottolog.languoids import Level, Glottocode, Languoid
from pyglottolog import fts
from pyglottolog import lff
from pyglottolog.monster import compile


@command()
def show(args):
    lang = args.repos.languoid(args.args[0])
    print()
    cprint('Glottolog languoid {0}'.format(lang.id), None, attrs=['bold', 'underline'])
    print()
    cprint('Classification:', None, attrs=['bold', 'underline'])
    args.repos.ascii_tree(lang, maxlevel=1)
    print()
    cprint('Info:', None, attrs=['bold', 'underline'])
    cprint('Path: {0}'.format(lang.fname), 'green', attrs=['bold'])
    for line in lang.cfg.write_string().split('\n'):
        if not line.startswith('#'):
            cprint(line, None, attrs=['bold'] if line.startswith('[') else [])


@command()
def create(args):
    """Create a new languoid directory for a languoid specified by name and level.

    glottolog create <parent> <name> <level>
    """
    assert args.args[2] in ['family', 'language', 'dialect']
    parent = args.repos.languoid(args.args[0]) or None
    lang = Languoid.from_name_id_level(
        args.args[1],
        args.repos.glottocodes.new(args.args[1]),
        getattr(Level, args.args[2]),
        **dict(prop.split('=') for prop in args.args[3:]))

    outdir = parent.dir if parent else args.repos.languoids_path('tree')
    print("Info written to %s" % lang.write_info(outdir=outdir))


@command()
def bib(args):
    """Compile the monster bibfile from the BibTeX files listed in references/BIBFILES.ini

    glottolog monster
    """
    compile(args.repos, args.log, rebuild=bool(args.args))


@command()
def tree(args):
    """Print the classification tree starting at a specific Glottocode

    glottolog tree GLOTTOCODE
    """
    if not args.args:
        raise ParserError('No root glottocode specified')
    start = args.repos.languoid(args.args[0])
    if not start:
        raise ParserError('Start glottocode does not exist')
    maxlevel = None
    if len(args.args) > 1:
        try:
            maxlevel = int(args.args[1])
        except:
            maxlevel = getattr(Level, args.args[1], None)
    args.repos.ascii_tree(start, maxlevel=maxlevel)


@command()
def newick(args):
    print(args.repos.newick_tree(args.args[0]))


@command()
def index(args):
    """Create an index page listing and linking to all languoids of a specified level.

    glottolog index (family|language|dialect|all)
    """
    def make_index(level, languoids, repos):
        fname = dict(
            language='languages', family='families', dialect='dialects')[level.name]
        links = defaultdict(dict)
        for lang in languoids:
            label = '{0.name} [{0.id}]'.format(lang)
            if lang.iso:
                label += '[%s]' % lang.iso
            links[slug(lang.name)[0]][label] = \
                lang.fname.relative_to(repos.languoids_path())

        with repos.languoids_path(fname + '.md').open('w', encoding='utf8') as fp:
            fp.write('## %s\n\n' % fname.capitalize())
            fp.write(' '.join(
                '[-%s-](%s_%s.md)' % (i.upper(), fname, i) for i in sorted(links.keys())))
            fp.write('\n')

        for i, langs in links.items():
            with repos.languoids_path(
                    '%s_%s.md' % (fname, i)).open('w', encoding='utf8') as fp:
                for label in sorted(langs.keys()):
                    fp.write('- [%s](%s)\n' % (label, langs[label]))

    langs = list(args.repos.languoids())
    for level in Level:
        if not args.args or args.args[0] == level.name:
            make_index(level, [l for l in langs if l.level == level], args.repos)


@command()
def check(args):
    what = args.args[0] if args.args else 'all'

    if what in ['all', 'refs']:
        for bibfile in args.repos.bibfiles:
            bibfile.check(args.log)

    if what not in ['all', 'tree']:
        return

    iso = args.repos.iso
    args.log.info('Checking ISO codes against %s' % iso)

    args.log.info('checking tree at %s' % args.repos)
    by_level = Counter()
    by_category = Counter()
    iso_in_gl, languoids = {}, {}
    for lang in args.repos.languoids():
        if lang.id in languoids:
            args.log.error('duplicate glottocode {0}:\n{1}\n{2}'.format(
                lang.id, languoids[lang.id].dir, lang.dir))
        languoids[lang.id] = lang
        by_level.update([lang.level.name])
        if lang.level == Level.language:
            by_category.update([lang.category])

        if iso and lang.iso:
            if lang.iso not in iso:
                args.log.warn('invalid ISO-639-3 code: %s [%s]' % (lang.id, lang.iso))
            else:
                isocode = iso[lang.iso]
                if lang.iso in iso_in_gl:
                    args.log.error('duplicate ISO code {0}: {1}, {2}'.format(
                        isocode, iso_in_gl[lang.iso].id, lang.id))
                iso_in_gl[lang.iso] = lang
                if isocode.is_retired and lang.category != 'Bookkeeping':
                    msg = '%s %s' % (lang.id, repr(isocode))
                    level = args.log.info
                    if len(isocode.change_to) == 1:
                        level = args.log.warn
                        msg += ' changed to %s' % repr(isocode.change_to[0])
                    level(msg)

        if not lang.id.startswith('unun9') and lang.id not in args.repos.glottocodes:
            args.log.error('unregistered glottocode %s' % lang.id)
        for attr in ['level', 'name', 'glottocode']:
            if not getattr(lang, attr):
                args.log.error('missing %s: %s' % (attr, lang.id))
        if not Glottocode.pattern.match(lang.dir.name):
            args.log.error('invalid directory name: %s' % lang.dir.name)
        if lang.level == Level.language:
            if lang.parent and lang.parent.level != Level.family:
                args.log.error('invalid nesting of language under {0}: {1}'.format(
                    lang.parent.level, lang.id))
            for child in lang.children:
                if child.level != Level.dialect:
                    args.log.error('invalid nesting of {0} under language: {1}'.format(
                        child.level, child.id))
        elif lang.level == Level.family:
            for d in lang.dir.iterdir():
                if d.is_dir():
                    break
            else:
                args.log.error('family without children: {0}'.format(lang.id))

    if iso:
        changed_to = set(chain(*[code.change_to for code in iso.retirements]))
        for code in sorted(iso.languages):
            if code.type == 'Individual/Living':
                if code not in changed_to:
                    if code.code not in iso_in_gl:
                        args.log.info('missing ISO code {0}'.format(code))

    def log_counter(counter, name):
        msg = [name + ':']
        maxl = max([len(k) for k in counter.keys()]) + 1
        for k, l in counter.most_common():
            msg.append(('{0:<%s} {1:>8,}' % maxl).format(k + ':', l))
        msg.append(('{0:<%s} {1:>8,}' % maxl).format('', sum(list(counter.values()))))
        print('\n'.join(msg))

    log_counter(by_level, 'Languoids by level')
    log_counter(by_category, 'Languages by category')
    return by_level


@command()
def metadata(args):
    ops = defaultdict(Counter)

    for l in args.repos.languoids():
        for sec in l.cfg:
            for opt in l.cfg[sec]:
                if l.cfg.get(sec, opt):
                    ops[sec].update([opt])

    t = Table('section', 'option', 'count')
    for section, options in ops.items():
        t.append([section, '', 0.0])
        for k, n in options.most_common():
            t.append(['', k, float(n)])
    print(t.render(condensed=False, floatfmt=',.0f'))


@command()
def ftssearch(args):
    """
    Search Glottolog references

    glottolog ftssearch QUERY

    E.g.:
    - glottolog ftssearch "Izi provider:hh"
    - glottolog ftssearch "author:Haspelmath provider:wals"
    """
    count, results = fts.search(args.repos, args.args[0])
    table = Table('ID', 'Author', 'Year', 'Title')
    for res in results:
        table.append([res.id, res.author, res.year, res.title])
    print(table.render(tablefmt='simple'))
    print('({} matches)'.format(count))


@command()
def ftsindex(args):
    """
    Index all bib files for use with the whoosh search engine.
    """
    return fts.build_index(args.repos, args.log)


@command()
def tree2lff(args):
    """Create lff.txt and dff.txt from the current languoid tree.

    glottolog tree2lff
    """
    lff.tree2lff(args.repos)


@command()
def lff2tree(args):
    """Recreate tree from lff.txt and dff.txt

    glottolog lff2tree [test]
    """
    lff.lff2tree(args.repos)
    if args.args and args.args[0] == 'test':  # pragma: no cover
        print("""
You can run

    diff -rbB build/tree/ languoids/tree/

to inspect the changes in the directory tree.
""")
    else:
        print("""
Run

    git status

to inspect changes in the directory tree.
You can run

    diff -rbB build/tree/ languoids/tree/

to inspect the changes in detail.

- To discard changes run

    git checkout languoids/tree

- To commit and push changes, run

    git add -A languoids/tree/...

  for any newly created nodes listed under

# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	languoids/tree/...

  followed by

    git commit -a -m"reason for change of classification"
    git push origin
""")
