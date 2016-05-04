# coding: utf8
from __future__ import unicode_literals
from functools import partial

from clldutils.path import Path
from clldutils.inifile import INI

import pyglottolog


DATA_DIR = Path(pyglottolog.__file__).parent.parent


def subdir_path(subdir, *comps, **kw):
    data_dir = kw.pop('data_dir', DATA_DIR)
    return data_dir.joinpath(subdir, *comps)


languoids_path = partial(subdir_path, 'languoids')
references_path = partial(subdir_path, 'references')
build_path = partial(subdir_path, 'build')


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
