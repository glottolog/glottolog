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
import argparse
import logging
import logging.config

from clldutils.clilib import ArgumentParser, ParserError
from clldutils.path import copytree, rmtree, remove
import colorlog

from pyglottolog.languoids import Glottocode
from pyglottolog.api import Glottolog
from pyglottolog import commands
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


def classification(args):
    for l in args.repos.languoids():
        if l.classification_comment.family:
            print('{0} family classification: {1}'.format(l.id, l.classification_comment.family))
        if l.classification_comment.sub:
            print('{0} subclassification: {1}'.format(l.id, l.classification_comment.sub))


def main():  # pragma: no cover
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(name)s:%(message)s'))
    log = logging.getLogger('pyglottolog')
    log.propagate = False
    log.addHandler(handler)

    parser = ArgumentParser('pyglottolog')
    parser.add_argument(
        '--repos',
        help="path to glottolog data repository",
        type=Glottolog,
        default=Glottolog())
    parser.add_argument(
        '--log',
        default=log,
        help=argparse.SUPPRESS,
    )
    sys.exit(parser.main())
