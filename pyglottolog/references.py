# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import OrderedDict
import re
import functools

from clldutils.misc import cached_property

from pyglottolog.util import references_path, parse_conjunctions, read_ini


@functools.total_ordering
class HHType(object):
    def __init__(self, s, p):
        self.name = s
        self.id = p.get(s, 'id')
        self.rank = p.getint(s, 'rank')
        self.abbv = p.get(s, 'abbv')
        self.bibabbv = p.get(s, 'bibabbv')
        self.triggers = p.get(s, 'triggers').strip().splitlines() or []

    def __repr__(self):
        return '<%s %s rank=%s>' % (self.__class__.__name__, self.id, self.rank)

    def __eq__(self, other):
        return self.rank == other.rank

    def __lt__(self, other):
        return self.rank < other.rank


class HHTypes(object):
    _rekillparen = re.compile(" \([^\)]*\)")
    _respcomsemic = re.compile("[;,]\s?")

    def __init__(self, repos=None):
        ini = read_ini(references_path('hhtype.ini', repos=repos))
        self._types = sorted([HHType(s, ini) for s in ini.sections()], reverse=True)
        self._type_by_id = {t.id: t for t in self._types}

    @classmethod
    def parse(cls, s):
        return cls._respcomsemic.split(cls._rekillparen.sub("", s))

    def __iter__(self):
        return iter(self._types)

    def __getitem__(self, item):
        return self._type_by_id.get(item, self._type_by_id.get('unknown'))

    @cached_property()
    def triggers(self):
        return OrderedDict(
            [(('hhtype', t.id), [parse_conjunctions(trig) for trig in t.triggers])
             for t in self if t.triggers])

    @cached_property()
    def hhtypes(self):
        return OrderedDict([(t.id, (t.rank, t.name, t.abbv, t.bibabbv)) for t in self])
