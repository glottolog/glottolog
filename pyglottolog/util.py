# coding: utf8
from __future__ import unicode_literals
from functools import partial
import itertools
import operator
import functools
from copy import copy

from clldutils.path import Path
from clldutils.iso_639_3 import ISO, download_tables
from clldutils.misc import UnicodeMixin

import pyglottolog


DATA_DIR = Path(pyglottolog.__file__).parent.parent


class DatedISO(ISO, UnicodeMixin):
    def __init__(self, zip):
        self.name = zip.stem
        ISO.__init__(self, zip)

    def __unicode__(self):
        return self.name


def get_iso(d):
    zips = sorted(
        list(Path(d).glob('iso-639-3_Code_Tables_*.zip')),
        key=lambda p: p.name)
    if zips:
        return DatedISO(zips[-1])

    return DatedISO(download_tables(d))


@functools.total_ordering
class Trigger(object):
    def __init__(self, field, type_, string):
        self.field = field
        self.type = type_
        self._string = string
        self.clauses = tuple(sorted([
            (False, w[4:].strip()) if w.startswith('NOT ') else (True, w.strip())
            for w in string.split(' AND ')]))

    def __eq__(self, other):
        # make triggers sortable so that we can easily group them by clauses.
        return self.clauses == other.clauses and self.cls == other.cls

    def __lt__(self, other):
        # make triggers sortable so that we can easily group them by clauses.
        return (self.clauses, self.cls) < (other.clauses, other.cls)

    @property
    def cls(self):
        return self.field, self.type

    def __call__(self, allkeys, keys_by_word):
        allkeys = set(allkeys)
        matching = copy(allkeys)
        for isin, word in self.clauses:
            matching_for_clause = copy(keys_by_word[word])
            if not isin:
                matching_for_clause = allkeys.difference(matching_for_clause)
            matching.intersection_update(matching_for_clause)
        return matching

    @staticmethod
    def format(label, triggers):
        trigs = [triggers] if isinstance(triggers, Trigger) else reversed(triggers)
        from_ = ';'.join(
            [' and '.join(
                [('' if c else 'not ') + w for c, w in t.clauses]) for t in trigs])
        return '%s (computerized assignment from "%s")' % (label, from_)

    @staticmethod
    def group(triggers):
        return [(clauses, list(triggers)) for clauses, triggers
                in itertools.groupby(sorted(triggers), lambda t: t.clauses)]


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


def group_first(iterable, groupkey=operator.itemgetter(0)):
    for key, group in itertools.groupby(iterable, groupkey):
        yield key, list(group)


def unique(iterable):
    seen = set()
    for item in iterable:
        if item not in seen:
            seen.add(item)
            yield item
