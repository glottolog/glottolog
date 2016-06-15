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
from __future__ import unicode_literals
import sys
import argparse

from pyglottolog.monster import main as compile_monster
from pyglottolog.languoids import make_index, glottocode_for_name, Languoid
from pyglottolog import lff


def monster(args):
    """Compile the monster bibfile from the BibTeX files listed in references/BIBFILES.ini

    glottolog monster
    """
    compile_monster()


def index(args):
    """Create an index page listing and linking to all languoids of a specified level.

    glottolog index (family|language|dialect|all)
    """
    for level in ['family', 'language', 'dialect']:
        if args.args[0] in [level, 'all']:
            make_index(level)


def new_languoid(args):
    """Create a new languoid directory for a languoid specified by name and level.

    glottolog new_languoid <name> <level>
    """
    assert args.args[1] in ['family', 'language', 'dialect']
    lang = Languoid.from_name_id_level(
        args.args[0],
        glottocode_for_name(args.args[0]),
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


COMMANDS = {f.__name__: f for f in [monster, index, tree2lff, lff2tree, new_languoid]}


def main():
    parser = argparse.ArgumentParser(
        description="""Main command line interface of the pyglottolog package.""",
        epilog="Use '%(prog)s help <cmd>' to get help about individual commands.")
    parser.add_argument("--verbosity", help="increase output verbosity")
    parser.add_argument('command', help='|'.join(COMMANDS))
    parser.add_argument('args', nargs=argparse.REMAINDER)

    args = parser.parse_args()
    if args.command == 'help':
        # As help text for individual commands we simply re-use the docstrings of the
        # callables registered for the command:
        print(COMMANDS[args.args[0]].__doc__)
        sys.exit(0)

    COMMANDS[args.command](args)
    sys.exit(0)
