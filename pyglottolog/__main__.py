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

from clldutils.clilib import ArgumentParserWithLogging

from .api import Glottolog
from . import commands
assert commands


def main():  # pragma: no cover
    parser = ArgumentParserWithLogging('pyglottolog')
    parser.add_argument(
        '--repos',
        help="path to glottolog data repository",
        type=Glottolog,
        default=Glottolog())
    sys.exit(parser.main())


if __name__ == '__main__':  # pragma: no cover
    main()
