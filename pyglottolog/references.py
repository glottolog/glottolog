# coding: utf8
from __future__ import unicode_literals, print_function, division
import re
import functools
from itertools import chain
from collections import Counter, OrderedDict
import unicodedata
import datetime

from six import string_types
import attr
from clldutils.misc import cached_property, UnicodeMixin

from pyglottolog.util import Trigger
from pyglottolog.monsterlib import _bibtex
from pyglottolog.monsterlib._bibfiles_db import Database


class BibFiles(list):
    """Directory with an INI-file with settings for BibTeX files inside."""
    def __init__(self, api, ini):
        res = []
        for sec in ini.sections():
            if sec.endswith('.bib'):
                fname = api.references_path('bibtex', sec)
                if not fname.exists():  # pragma: no cover
                    raise ValueError('invalid bibtex file referenced in BIBFILES.ini')
                res.append(BibFile(fname=fname, **ini[sec]))

        super(BibFiles, self).__init__(res)
        self._map = {b.fname.name: b for b in self}

    def __getitem__(self, index_or_filename):
        """Retrieve a bibfile by index or filename."""
        if isinstance(index_or_filename, string_types):
            return self._map[index_or_filename]
        return super(BibFiles, self).__getitem__(index_or_filename)

    def to_sqlite(self, filename, rebuild=False):
        """Return a database with the bibfiles loaded."""
        return Database.from_bibfiles(self, filename, rebuild=rebuild)

    def roundtrip_all(self):
        """Load and save all bibfiles with the current settings."""
        return [b.roundtrip() for b in self]


def file_if_exists(i, a, value):
    if value.exists() and not value.is_file():
        raise ValueError('invalid path')  # pragma: no cover


@attr.s
class BibFile(UnicodeMixin):
    fname = attr.ib(validator=file_if_exists)
    name = attr.ib(default=None)
    title = attr.ib(default=None)
    description = attr.ib(default=None)
    abbr = attr.ib(default=None)
    encoding = attr.ib(default='utf-8-sig')
    sortkey = attr.ib(default=None, convert=lambda s: None if s.lower() == 'none' else s)
    priority = attr.ib(default=0, convert=int)
    url = attr.ib(default=None)

    @property
    def id(self):
        return self.fname.stem

    @property
    def filepath(self):
        return self.fname

    @property
    def filename(self):
        return self.fname.name

    @property
    def size(self):
        return self.filepath.stat().st_size

    @property
    def mtime(self):
        return datetime.datetime.fromtimestamp(self.filepath.stat().st_mtime)

    def iterentries(self):
        """Yield entries as (bibkey, (entrytype, fields)) tuples."""
        return _bibtex.iterentries(filename=self.fname, encoding=self.encoding)

    def keys(self):
        return ['{0}:{1}'.format(self.id, key) for key, _ in self.iterentries()]

    @property
    def glottolog_ref_id_map(self):
        return {
            k: fields['glottolog_ref_id'] for k, (_, fields) in self.iterentries()
            if 'glottolog_ref_id' in fields}

    def update(self, fname):
        entries = OrderedDict()
        ref_id_map = self.glottolog_ref_id_map
        for key, (type_, fields) in _bibtex.iterentries(fname, self.encoding):
            if key in ref_id_map and 'glottolog_ref_id' not in fields:
                fields['glottolog_ref_id'] = ref_id_map[key]
            entries[key] = (type_, fields)
        self.save(entries)

    def load(self):
        """Return entries as bibkey -> (entrytype, fields) dict."""
        return _bibtex.load(
            self.fname, preserve_order=self.sortkey is None, encoding=self.encoding)

    def save(self, entries):
        """Write bibkey -> (entrytype, fields) map to file."""
        _bibtex.save(
            entries, filename=self.fname, sortkey=self.sortkey, encoding=self.encoding)

    def __unicode__(self):
        return '<%s %s>' % (self.__class__.__name__, self.fname.name)

    def check(self, log):
        entries = self.load()  # bare BibTeX syntax
        invalid = _bibtex.check(filename=self.filepath.as_posix())  # names/macros etc.
        verdict = ('(%d invalid)' % invalid) if invalid else 'OK'
        method = log.warn if invalid else log.info
        method('%s %d %s' % (self, len(entries), verdict))
        return len(entries), verdict

    def roundtrip(self):
        print(self)
        self.save(self.load())

    def show_characters(self, include_plain=False):
        """Display character-frequencies (excluding printable ASCII)."""
        with self.filepath.open(encoding=self.encoding) as fd:
            hist = Counter(fd.read())
        table = '\n'.join(
            '%d\t%-9r\t%s\t%s' % (n, c, c, unicodedata.name(c, ''))
            for c, n in hist.most_common()
            if include_plain or not 20 <= ord(c) <= 126)
        print(table)


@functools.total_ordering
class HHType(object):
    def __init__(self, s, p):
        self.name = s
        self.id = p.get(s, 'id')
        self.rank = p.getint(s, 'rank')
        self.abbv = p.get(s, 'abbv')
        self.bibabbv = p.get(s, 'bibabbv')
        self.triggers = [Trigger('hhtype', self.id, t)
                         for t in p.get(s, 'triggers').strip().splitlines() or []]

    def __repr__(self):
        return '<%s %s rank=%s>' % (self.__class__.__name__, self.id, self.rank)

    def __eq__(self, other):
        return self.rank == other.rank

    def __lt__(self, other):
        return self.rank < other.rank


class HHTypes(object):
    _rekillparen = re.compile(" \([^\)]*\)")
    _respcomsemic = re.compile("[;,]\s?")

    def __init__(self, ini):
        self._types = sorted([HHType(s, ini) for s in ini.sections()], reverse=True)
        self._type_by_id = {t.id: t for t in self._types}

    @classmethod
    def parse(cls, s):
        return cls._respcomsemic.split(cls._rekillparen.sub("", s))

    def __iter__(self):
        return iter(self._types)

    def __len__(self):
        return len(self._types)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._types[0]
        return self._type_by_id.get(item, self._type_by_id.get('unknown'))

    @cached_property()
    def triggers(self):
        return list(chain(*[t.triggers for t in self]))
