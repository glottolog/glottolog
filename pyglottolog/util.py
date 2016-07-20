# coding: utf8
from __future__ import unicode_literals
from functools import partial
import itertools
import operator

from clldutils.path import Path
from clldutils.inifile import INI

import pyglottolog


DATA_DIR = Path(pyglottolog.__file__).parent.parent


def subdir_path(subdir, *comps, **kw):
    data_dir = None
    for key in ['data_dir', 'repos']:
        data_dir = kw.pop(key, None)
        if data_dir:
            break
    return Path(data_dir or DATA_DIR).joinpath(subdir, *comps)


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


def intersectall(xs):
    a = set(xs[0])
    for x in xs[1:]:
        a.intersection_update(x)
    return a


def group_first(iterable, groupkey=operator.itemgetter(0)):
    for key, group in itertools.groupby(iterable, groupkey):
        yield key, list(group)


def unique(iterable):
    seen = set()
    for item in iterable:
        if item not in seen:
            seen.add(item)
            yield item
