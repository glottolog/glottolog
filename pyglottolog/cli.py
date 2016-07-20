# coding: utf8
"""
Main command line interface of the pyglottolog package.

Like programs such as git, this cli splits its functionality into sub-commands
(see e.g. https://docs.python.org/2/library/argparse.html#sub-commands).
The rationale behind this is that while a lot of different tasks may be triggered using
this cli, most of them require common configuration.

The basic invocation looks like

    glottolog [OPTIONS] <command> [args]

"""
from __future__ import unicode_literals, print_function
import sys
from collections import Counter
import logging

from clldutils.clilib import ArgumentParser, ParserError
from clldutils.path import copytree, rmtree, remove

from pyglottolog.monster import main as compile_monster
from pyglottolog.languoids import (
    make_index, Languoid, find_languoid, Glottocode, Glottocodes, walk_tree, TREE, Level,
)
from pyglottolog.util import DATA_DIR, languoids_path
from pyglottolog import lff


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def monster(args):
    """Compile the monster bibfile from the BibTeX files listed in references/BIBFILES.ini

    glottolog monster
    """
    compile_monster()


def index(args):
    """Create an index page listing and linking to all languoids of a specified level.

    glottolog index (family|language|dialect|all)
    """
    for level in Level:
        if args.args[0] in [level.value, 'all']:
            make_index(level, repos=args.repos)


def check_tree(args):
    tree = languoids_path('tree', repos=args.repos)
    glottocodes = Glottocodes()
    log.info('checking tree at %s' % tree)
    stats = Counter()
    for lang in walk_tree(tree=tree):
        stats.update([lang.level])
        if lang.id not in glottocodes:
            log.error('unregistered glottocode %s' % lang.id)
        for attr in ['level', 'name', 'glottocode']:
            if not getattr(lang, attr):
                log.error('missing %s: %s' % (attr, lang.id))
        if not Glottocode.pattern.match(lang.dir.name):
            log.error('invalid directory name: %s' % lang.dir.name)
        if lang.level == Level.language:
            if lang.parent and lang.parent.level != Level.family:
                log.error('invalid nesting of language under {0}: {1}'.format(
                    lang.parent.level, lang.id))
            for child in lang.children:
                if child.level != Level.dialect:
                    log.error('invalid nesting of {0} under language: {1}'.format(
                        child.level, child.id))
    log.info(stats)
    return stats


def recode(args):
    """Assign a new glottocode to an existing languoid.

    glottolog recode <code>
    """
    lang = find_languoid(glottocode=args.args[0])
    if not lang:
        raise ParserError('languoid not found')
    lang.id = Glottocode.from_name(lang.name)
    new_dir = lang.dir.parent.joinpath(lang.id)
    copytree(lang.dir, new_dir)
    lang.write_info(new_dir)
    remove(new_dir.joinpath('%s.ini' % args.args[0]))
    rmtree(lang.dir)
    print("%s -> %s" % (args.args[0], lang.id))


def new_languoid(args):
    """Create a new languoid directory for a languoid specified by name and level.

    glottolog new_languoid <name> <level>
    """
    assert args.args[1] in ['family', 'language', 'dialect']
    lang = Languoid.from_name_id_level(
        args.args[0],
        Glottocode.from_name(args.args[0]),
        args.args[1],
        **dict(prop.split('=') for prop in args.args[2:]))
    #
    # FIXME: how to specify parent? Just mv there?
    #
    print("Info written to %s" % lang.write_info())


def tree2lff(args):
    """Create lff.txt and dff.txt from the current languoid tree.

    glottolog tree2lff
    """
    lff.tree2lff()


def lff2tree(args):
    """Recreate tree from lff.txt and dff.txt

    glottolog lff2tree [test]
    """
    lff.lff2tree()
    if args.args and args.args[0] == 'test':
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

    git add languoids/tree/...

  for any newly created nodes listed under

# Untracked files:
#   (use "git add <file>..." to include in what will be committed)
#
#	languoids/tree/...

  followed by

    git commit -a -m"reason for change of classification"
    git push origin
""")


def main():  # praga: no cover
    parser = ArgumentParser(
        'pyglottolog',
        monster,
        index,
        tree2lff,
        lff2tree,
        new_languoid,
        recode,
        check_tree)
    parser.add_argument(
        '--repos', help="path to glottolog data repository", default=DATA_DIR)
    sys.exit(parser.main())
