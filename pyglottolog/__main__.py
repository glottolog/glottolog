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

from clldutils.clilib import ArgumentParserWithLogging, ParserError
from clldutils.path import copytree, rmtree, remove

from .languoids import Glottocode
from .api import Glottolog
from . import commands
assert commands


def recode(args):
    """Assign a new glottocode to an existing languoid.

    glottolog recode <code>
    """
    lang = args.repos.languoid(args.args[0])
    if not lang:
        raise ParserError('languoid not found')
    lang.id = Glottocode.from_name(lang.name)
    new_dir = lang.dir.parent.joinpath(lang.id)
    copytree(lang.dir, new_dir)
    lang.write_info(new_dir)
    remove(new_dir.joinpath('%s.ini' % args.args[0]))
    rmtree(lang.dir)
    print("%s -> %s" % (args.args[0], lang.id))


def main():  # pragma: no cover
    parser = ArgumentParserWithLogging('pyglottolog')
    parser.add_argument(
        '--repos',
        help="path to glottolog data repository",
        type=Glottolog,
        default=Glottolog())
    sys.exit(parser.main())


if __name__ == '__main__':
    main()
