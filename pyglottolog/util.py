# coding: utf8
from __future__ import unicode_literals

from clldutils.path import Path
from clldutils.inifile import INI

import pyglottolog


DATA_DIR = Path(pyglottolog.__file__).parent.parent


def languoids_path(*comps):
    return DATA_DIR.joinpath('languoids', *comps)


def references_path(*comps):
    return DATA_DIR.joinpath('references', *comps)


def build_path(*comps):
    return DATA_DIR.joinpath('build', *comps)


def read_ini(filename, interpolation=None):
    if isinstance(filename, Path):
        filename = filename.as_posix()
    p = INI(interpolation=interpolation)
    p.read(filename)
    return p


def parse_conjunctions(expr):
    return [
        (False, w[4:].strip()) if w.startswith('NOT ') else (True, w.strip())
        for w in expr.split(' AND ')]
