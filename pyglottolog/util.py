# coding: utf8
from __future__ import unicode_literals
import itertools
import operator
import functools
from copy import copy
import textwrap

from six import PY2, text_type
from termcolor import colored
from clldutils.path import Path
from clldutils.iso_639_3 import ISO, download_tables


def sprint(text, *args, **kw):
    if not isinstance(text, text_type):
        text = '{0}'.format(text)
    if args:
        text = text.format(*args)
    color = kw.pop('color', None)
    attrs = kw.pop('attrs', None)
    if color or attrs:
        text = colored(text, color=color, attrs=attrs)
    if PY2:
        text = text.encode('utf8')
    print(text)


def wrap(text,
         line_as_paragraph=False,
         width=80,
         break_long_words=False,
         break_on_hyphens=False,
         **kw):
    kw.update(
        width=width, break_long_words=break_long_words, break_on_hyphens=break_on_hyphens)
    lines = []
    for line in text.split('\n'):
        if not line:
            lines.append('')
        else:
            lines.extend(textwrap.wrap(line, **kw))
            if line_as_paragraph:
                lines.append('')
    return '\n'.join(lines).strip()


def message(obj, msg):
    return '{0}: {1}'.format(colored('{0}'.format(obj), 'blue', attrs=['bold']), msg)


def get_iso(d):
    zips = sorted(
        list(Path(d).glob('iso-639-3_Code_Tables_*.zip')),
        key=lambda p: p.name)
    if zips:
        return ISO(zips[-1])

    return ISO(download_tables(d))  # pragma: no cover


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
        return [(clauses, list(trigs)) for clauses, trigs
                in itertools.groupby(sorted(triggers), lambda t: t.clauses)]


def group_first(iterable, groupkey=operator.itemgetter(0)):
    for key, group in itertools.groupby(iterable, groupkey):
        yield key, list(group)


def unique(iterable):
    seen = set()
    for item in iterable:
        if item not in seen:
            seen.add(item)
            yield item
