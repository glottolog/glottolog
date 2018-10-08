# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict, Counter
from itertools import chain
import os
import sys
import re
import argparse
import subprocess
from json import dumps
from string import Template

from termcolor import colored
from clldutils.clilib import command, ParserError
from clldutils.misc import slug
from clldutils.markup import Table
from clldutils.path import Path, write_text, read_text, git_describe

import pyglottolog
import pyglottolog.iso
from .languoids import Languoid, Level, Reference
from . import fts
from . import lff
from .monster import compile
from .references import evobib
from .util import message, sprint


@command()
def htmlmap(args, min_langs_for_legend_item=10):
    """
    glottolog htmlmap [OUTDIR]
    """
    nodes = {n.id: n for n in args.repos.languoids()}
    legend = Counter()

    langs = []
    for n in nodes.values():
        if n.level == Level.language and n.latitude != None:
            fid = n.lineage[0][1] if n.lineage else n.id
            if (not nodes[fid].category.startswith('Pseudo')) or fid == n.id:
                langs.append((n, fid))
                legend.update([fid])

    color_map = {fid: "{0:0{1}X}".format((i + 1) * 10, 3)
                 for i, fid in enumerate(sorted(legend.keys()))}

    def l2f(t):
        n, fid = t
        lon, lat = n.longitude, n.latitude
        if lon <= -26:
            lon += 360  # make the map pacific-centered.

        return {
            "geometry": {"coordinates": [lon, lat], "type": "Point"},
            "id": n.id,
            "properties": {
                "name": n.name,
                "color": color_map[fid],
                "family": nodes[fid].name,
                "family_id": fid,
            },
            "type": "Feature"
        }

    def legend_item(fid, c):
        return \
            '<span style="background-color: #{0}; border: 1px solid black;">'\
            '&nbsp;&nbsp;&nbsp;</span> '\
            '<a href="http://glottolog.org/resource/languoid/id/{1}">{2}</a> ({3})'.format(
                color_map[fid], fid, nodes[fid].name, c)

    geojson = {
        "features": list(map(l2f, langs)),
        "properties": {
            "legend": {
                fid: legend_item(fid, c) for fid, c in legend.most_common() if
                c >= min_langs_for_legend_item},
        },
        "type": "FeatureCollection"
    }

    def rendered_template(name, **kw):
        return Template(read_text(
            Path(pyglottolog.__file__).parent.joinpath('templates', 'htmlmap', name))
        ).substitute(**kw)

    jsname = 'glottolog_map.json'
    outdir = Path('.') if not args.args else Path(args.args[0])
    write_text(
        outdir.joinpath(jsname),
        rendered_template('htmlmap.js', geojson=dumps(geojson, indent=4)))
    html = outdir.joinpath('glottolog_map.html')
    write_text(
        html,
        rendered_template(
            'htmlmap.html',
            version=git_describe(args.repos.repos),
            jsname=jsname,
            nlangs=len(langs)))
    print(html.resolve().as_uri())


@command()
def iso2codes(args):
    """
    Map ISO codes to the list of all Glottolog languages and dialects subsumed "under" it.
    """
    from clldutils.dsv import UnicodeWriter

    nodes = list(args.repos.languoids())

    res = {}
    for node in nodes:
        if node.iso:
            res[node.id] = (node.iso, set())

    for node in nodes:
        if node.level == Level.family or node.id in res:
            continue
        for nid in res:
            matched = False
            for l in node.lineage:
                if l[1] == nid:
                    res[nid][1].add(node.id)
                    matched = True
                    break
            if matched:
                break

    outdir = Path('.') if not args.args else Path(args.args[0])
    with UnicodeWriter(outdir / 'iso2glottocodes.csv') as writer:
        writer.writerow(['iso', 'glottocodes'])
        for gc, (iso, gcs) in res.items():
            writer.writerow([iso, ';'.join([gc] + list(gcs))])


@command('evobib')
def _evobib(args):
    evobib.download(args.repos.bibfiles['evobib.bib'], args.log)


@command()
def roundtrip(args):
    """Load/save the bibfile with the given name."""
    args.repos.bibfiles[args.args[0]].roundtrip()


@command()
def bibfiles_db(args):
    """(Re-)create bibfiles sqlite3 database in the current directory."""
    args.repos.bibfiles.to_sqlite(rebuild=True)


@command()
def copy_benjamins(args, name='benjamins.bib'):  # pragma: no cover
    """
    glottolog copy_benjamins /path/to/benjamins/benjamins.bib
    """
    args.repos.bibfiles[name].update(args.args[0], log=args.log)


@command()
def isobib(args):  # pragma: no cover
    """Update iso6393.bib - the file of references for ISO 639-3 change requests."""
    pyglottolog.iso.bibtex(args.repos, args.log)


@command()
def isoretirements(args):  # pragma: no cover
    """Update retirement info in language info files."""
    pyglottolog.iso.retirements(args.repos, args.log)


def existing_lang(args):
    if not args.args:
        raise ParserError('No languoid specified')
    lang = args.repos.languoid(args.args[0])
    if not lang:
        raise ParserError('Invalid languoid spec')
    return lang


@command()
def show(args):
    """Display details of a Glottolog object.

    glottolog show <GLOTTOCODE>|<ISO-CODE>|<BIBTEXKEY>
    """
    if args.args and ':' in args.args[0]:
        if args.args[0].startswith('**'):
            ref = Reference.from_string(args.args[0])
        else:
            ref = Reference(key=args.args[0])
        sprint('Glottolog reference {0}'.format(ref), attrs=['bold', 'underline'])
        print()
        src = ref.get_source(args.repos)
        sprint(src.text())
        print()
        sprint(src)
        return
    lang = existing_lang(args)
    print()
    sprint('Glottolog languoid {0}'.format(lang.id), attrs=['bold', 'underline'])
    print()
    sprint('Classification:', attrs=['bold', 'underline'])
    args.repos.ascii_tree(lang, maxlevel=1)
    print()
    sprint('Info:', attrs=['bold', 'underline'])
    sprint('Path: {0}'.format(lang.fname), 'green', attrs=['bold'])
    sources = lang.sources
    if sources:
        del lang.cfg['sources']['glottolog']
        del lang.cfg['sources']
    for line in lang.cfg.write_string().split('\n'):
        if not line.startswith('#'):
            sprint(line, None, attrs=['bold'] if line.startswith('[') else [])
    sprint('Sources:', attrs=['bold', 'underline'])
    for src in sources:
        src = src.get_source(args.repos)
        sprint(src.id, color='green')
        sprint(src.text())
        print()


@command()
def edit(args):
    """Open a languoid's INI file in a text editor.

    glottolog edit <GLOTTOCODE>|<ISO-CODE>
    """
    lang = existing_lang(args)
    if sys.platform.startswith('os2'):  # pragma: no cover
        cmd = ['open']
    elif sys.platform.startswith('linux'):
        cmd = ['xdg-open']
    elif sys.platform.startswith('win'):  # pragma: no cover
        cmd = []
    else:  # pragma: no cover
        print(lang.fname)
        return
    cmd.append(lang.fname.as_posix())
    subprocess.call(cmd)


@command()
def create(args):
    """Create a new languoid directory for a languoid specified by name and level.

    glottolog create <parent> <name> <level>
    """
    assert args.args[2] in ['family', 'language', 'dialect']
    parent = args.repos.languoid(args.args[0]) or None
    outdir = parent.dir if parent else args.repos.tree
    lang = Languoid.from_name_id_level(
        outdir,
        args.args[1],
        args.repos.glottocodes.new(args.args[1]),
        getattr(Level, args.args[2]),
        **dict(prop.split('=') for prop in args.args[3:]))

    print("Info written to %s" % lang.write_info(outdir=outdir))


@command()
def bib(args):
    """Compile the monster bibfile from the BibTeX files listed in references/BIBFILES.ini

    glottolog bib [rebuild]
    """
    compile(args.repos, args.log, rebuild=bool(args.args))


@command()
def tree(args):
    """Print the classification tree starting at a specific languoid.

    glottolog tree <GLOTTOCODE>|<ISO-CODE> [MAXLEVEL]

    MAXLEVEL [family|language|dialect] will limit the displayed children.
    """
    start = existing_lang(args)
    maxlevel = None
    if len(args.args) > 1:
        try:
            maxlevel = int(args.args[1])
        except Exception:
            maxlevel = getattr(Level, args.args[1], None)
    args.repos.ascii_tree(start, maxlevel=maxlevel)


@command(usage="""
Print the classification tree starting at a specific languoid in Newick format.

    glottolog newick [--template="{{l.id}}"] [<GLOTTOCODE>|<ISO-CODE>]

The --template option can be used to control the node labels in the Newick string.
Values for this option must be valid python format strings expecting a single
template variable `l` which points to the Languoid instance.
In addition to Languoid attributes and properties specified as "{{l.<attr>}}",
e.g. "{{l.id}}" for the Glottocode of a Languoid, the following custom format specs
can be used:
{0}""".format(
    '\n'.join('    l:{0}\t{1[1]}'.format(k, v) for k, v in Languoid._format_specs.items())))
def newick(args):
    parser = argparse.ArgumentParser(prog='newick')
    parser.add_argument('root', nargs='?', default=None, help='root node')
    parser.add_argument('--template', help='node label template', default=None)
    xargs = parser.parse_args(args.args)
    sprint(args.repos.newick_tree(xargs.root, template=xargs.template))


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
    """Check the glottolog data for consistency.

    glottolog check [tree|refs]
    """
    def error(obj, msg):
        args.log.error(message(obj, msg))

    def warn(obj, msg):
        args.log.warn(message(obj, msg))

    def info(obj, msg):
        args.log.info(message(obj, msg))

    what = args.args[0] if args.args else 'all'

    if what in ['all', 'refs']:
        for bibfile in args.repos.bibfiles:
            bibfile.check(args.log)

    if what not in ['all', 'tree']:
        return

    hhkeys = args.repos.bibfiles['hh.bib'].keys()
    iso = args.repos.iso
    args.log.info('checking ISO codes against %s' % iso)
    args.log.info('checking tree at %s' % args.repos)
    by_level = Counter()
    by_category = Counter()
    iso_in_gl, languoids, iso_splits, hid = {}, {}, [], {}
    names = defaultdict(set)

    for lang in args.repos.languoids():
        # duplicate glottocodes:
        if lang.id in languoids:
            error(
                lang.id,
                'duplicate glottocode\n{0}\n{1}'.format(languoids[lang.id].dir, lang.dir))
        languoids[lang.id] = lang

    for lang in languoids.values():
        ancestors = lang.ancestors_from_nodemap(languoids)
        children = lang.children_from_nodemap(languoids)

        if lang.latitude and not (-90 <= lang.latitude <= 90):
            error(lang, 'invalid latitude: {0}'.format(lang.latitude))
        if lang.longitude and not (-180 <= lang.longitude <= 180):
            error(lang, 'invalid longitude: {0}'.format(lang.longitude))

        assert isinstance(lang.countries, list)
        assert isinstance(lang.macroareas, list)

        if 'sources' in lang.cfg:
            for ref in Reference.from_list(lang.cfg.getlist('sources', 'glottolog')):
                if ref.provider == 'hh' and ref.key not in hhkeys:
                    error(lang, 'missing source: {0}'.format(ref))

        for attr in ['classification_comment', 'ethnologue_comment']:
            obj = getattr(lang, attr)
            if obj:
                obj.check(lang, hhkeys, args.log)

        names[lang.name].add(lang)
        by_level.update([lang.level.name])
        if lang.level == Level.language:
            by_category.update([lang.category])

        if iso and lang.iso:
            if lang.iso not in iso:
                warn(lang, 'invalid ISO-639-3 code [%s]' % lang.iso)
            else:
                isocode = iso[lang.iso]
                if lang.iso in iso_in_gl:
                    error(isocode,
                          'duplicate: {0}, {1}'.format(iso_in_gl[lang.iso].id, lang.id))
                iso_in_gl[lang.iso] = lang
                if isocode.is_retired and lang.category != 'Bookkeeping':
                    if isocode.type == 'Retirement/split':
                        iso_splits.append(lang)
                    else:
                        msg = repr(isocode)
                        level = info
                        if len(isocode.change_to) == 1:
                            level = warn
                            msg += ' changed to [%s]' % isocode.change_to[0].code
                        level(lang, msg)

        if lang.hid is not None:
            if lang.hid in hid:
                error(
                    lang.hid,
                    'duplicate hid\n{0}\n{1}'.format(languoids[hid[lang.hid]].dir, lang.dir))
            else:
                hid[lang.hid] = lang.id

        if not lang.id.startswith('unun9') and lang.id not in args.repos.glottocodes:
            error(lang, 'unregistered glottocode')
        for attr in ['level', 'name']:
            if not getattr(lang, attr):
                error(lang, 'missing %s' % attr)
        if lang.level == Level.language:
            parent = ancestors[-1] if ancestors else None
            if parent and parent.level != Level.family:
                error(lang, 'invalid nesting of language under {0}'.format(parent.level))
            for child in children:
                if child.level != Level.dialect:
                    error(child,
                          'invalid nesting of {0} under language'.format(child.level))
        elif lang.level == Level.family:
            for d in lang.dir.iterdir():
                if d.is_dir():
                    break
            else:
                error(lang, 'family without children')

    if iso:
        changed_to = set(chain(*[code.change_to for code in iso.retirements]))
        for code in sorted(iso.languages):
            if code.type == 'Individual/Living':
                if code not in changed_to:
                    if code.code not in iso_in_gl:
                        info(repr(code), 'missing')
        for lang in iso_splits:
            isocode = iso[lang.iso]
            missing = [s.code for s in isocode.change_to if s.code not in iso_in_gl]
            if missing:
                warn(lang, '{0} missing new codes: {1}'.format(
                    repr(isocode), ', '.join(missing)))

    for name, gcs in sorted(names.items()):
        if len(gcs) > 1:
            # duplicate names:
            method = error
            if len([1 for n in gcs if n.level != Level.dialect]) <= 1:
                # at most one of the languoids is not a dialect, just warn
                method = warn
            if len([1 for n in gcs
                    if (not n.lineage) or (n.lineage[0][1] != 'book1242')]) <= 1:
                # at most one of the languoids is not in bookkeping, just warn
                method = warn
            method(name, 'duplicate name: {0}'.format(', '.join(sorted(
                ['{0} <{1}>'.format(n.id, n.level.name[0]) for n in gcs]))))

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
    """List all metadata fields used in languoid INI files and their frequency.

    glottolog metadata
    """
    ops = defaultdict(Counter)

    for l in args.repos.languoids():
        for secname, sec in l.cfg.items():
            ops[secname].update(opt for opt, val in sec.items() if val)

    ops.pop('DEFAULT', None)

    t = Table('section', 'option', 'count')
    for section, options in ops.items():
        t.append([section, '', float(sum(options.values()))])
        for k, n in options.most_common():
            t.append(['', k, float(n)])
    print(t.render(condensed=False, floatfmt=',.0f'))


@command()
def refsearch(args):
    """Search Glottolog references

    glottolog refsearch "QUERY"

    E.g.:
    - glottolog refsearch "Izi provider:hh"
    - glottolog refsearch "author:Haspelmath provider:wals"
    """
    count, results = fts.search(args.repos, args.args[0])
    table = Table('ID', 'Author', 'Year', 'Title')
    for res in results:
        table.append([res.id, res.author, res.year, res.title])
    sprint(table.render(tablefmt='simple'))
    print('({} matches)'.format(count))


@command()
def refindex(args):
    """Index all bib files for use with `glottolog refsearch`.

    glottolog refindex

    This will take about 15 minutes and create an index of about 450 MB.
    """
    return fts.build_index(args.repos, args.log)


@command()
def langsearch(args):
    """Search Glottolog languoids

    glottolog langsearch "QUERY"
    """
    def highlight(text):
        res, i = '', 0
        for m in re.finditer('\[\[(?P<m>[^\]]+)\]\]', text):
            res += text[i:m.start()]
            res += colored(m.group('m'), 'red', attrs=['bold'])
            i = m.end()
        res += text[i:]
        return res + '\n'

    count, results = fts.search_langs(args.repos, args.args[0])
    cwd = os.getcwd()
    print('{} matches'.format(count))
    for res in results:
        try:
            p = Path(res.fname).relative_to(Path(cwd))
        except ValueError:
            p = res.fname
        sprint('{0.name} [{0.id}] {0.level}'.format(res), color=None, attrs=['bold'])
        sprint(p, color='green')
        sprint(highlight(res.highlights) if res.highlights else '')
    print('{} matches'.format(count))


@command()
def langindex(args):
    """Index all bib files for use with `glottolog langsearch`.

    glottolog langindex

    This will take a couple of minutes and create an index of about 60 MB.
    """
    return fts.build_langs_index(args.repos, args.log)


@command()
def tree2lff(args):
    """Create lff.txt and dff.txt from the current languoid tree.

    glottolog tree2lff
    """
    lff.tree2lff(args.repos, args.log)


@command()
def lff2tree(args):
    """Recreate tree from lff.txt and dff.txt

    glottolog lff2tree [test]
    """
    try:
        lff.lff2tree(args.repos, args.log)
    except ValueError:  # pragma: no cover
        print("""
Something went wrong! Roll back inconsistent state running

    rm -rf languoids
    git checkout languoids
""")
        raise

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
