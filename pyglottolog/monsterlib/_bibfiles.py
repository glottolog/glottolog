# _bibfiles.py - ordered collection of bibfiles with load/save api

import datetime

from six import string_types

from pyglottolog.util import references_path, read_ini
from pyglottolog.monsterlib import _bibtex
from pyglottolog.monsterlib._bibfiles_db import Database

__all__ = ['Collection', 'BibFile', 'Database']

DIR = references_path('bibtex')


class Collection(list):
    """Directory with an INI-file with settings for BibTeX files inside."""

    _encoding = 'utf-8-sig'

    @classmethod
    def _bibfiles(cls, directory):
        """Read the INI-file, yield bibfile instances for sections."""
        cfg = read_ini(directory.parent.joinpath('BIBFILES.ini'))
        for s in cfg.sections():
            if not s.endswith('.bib'):
                continue
            filepath = directory.joinpath(s)
            assert filepath.exists()
            sortkey = cfg.get(s, 'sortkey')
            if sortkey.lower() == 'none':
                sortkey = None
            yield BibFile(
                filepath=filepath,
                encoding=cfg.get(s, 'encoding'), sortkey=sortkey,
                priority=cfg.getint(s, 'priority'),
                name=cfg.get(s, 'name'), title=cfg.get(s, 'title'),
                description=cfg.get(s, 'description'),
                abbr=cfg.get(s, 'abbr'))

    def __init__(self, directory=DIR):
        self.directory = directory
        bibfiles = self._bibfiles(directory)
        super(Collection, self).__init__(bibfiles)
        self._map = {b.filepath.name: b for b in self}

    def __getitem__(self, index_or_filename):
        """Retrieve a bibfile by index or filename."""
        if isinstance(index_or_filename, string_types):
            return self._map[index_or_filename]
        return super(Collection, self).__getitem__(index_or_filename)

    def to_sqlite(self, filename, rebuild=False):
        """Return a database with the bibfiles loaded."""
        return Database.from_bibfiles(self, filename, rebuild=rebuild)

    def check_all(self):
        """Check the BibTeX syntax of all bibfiles."""
        return [b.check() for b in self]

    def roundtrip_all(self):
        """Load and save all bibfiles with the current settings."""
        return [b.roundtrip() for b in self]


class BibFile(object):
    """BibTeX source file with configurable load/save options and meta data."""

    def __init__(self, filepath, encoding, sortkey, priority=0,
                 name=None, title=None, description=None, abbr=None):
        self.filepath = filepath
        self.filename = filepath.name
        self.encoding = encoding
        self.sortkey = sortkey
        self.priority = priority
        self.name = name
        self.title = title
        self.description = description
        self.abbr = abbr

    @property
    def size(self):
        return self.filepath.stat().st_size

    @property
    def mtime(self):
        return datetime.datetime.fromtimestamp(self.filepath.stat().st_mtime)

    def iterentries(self):
        """Yield entries as (bibkey, (entrytype, fields)) tuples."""
        return _bibtex.iterentries(
            filename=self.filepath.as_posix(),
            encoding=self.encoding)

    def load(self):
        """Return entries as bibkey -> (entrytype, fields) dict."""
        return _bibtex.load(
            filename=self.filepath.as_posix(),
            preserve_order=self.sortkey is None,
            encoding=self.encoding)

    def save(self, entries, verbose=True):
        """Write bibkey -> (entrytype, fields) map to file."""
        _bibtex.save(
            entries,
            filename=self.filepath.as_posix(),
            sortkey=self.sortkey,
            encoding=self.encoding,
            verbose=verbose)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.filepath.name)

    def check(self):
        print(self)
        entries = self.load()  # bare BibTeX syntax
        invalid = _bibtex.check(filename=self.filepath.as_posix())  # names/macros etc.
        verdict = ('(%d invalid)' % invalid) if invalid else 'OK'
        print('%d %s' % (len(entries), verdict))
        return len(entries), verdict

    def roundtrip(self):
        print(self)
        self.save(self.load())

    def show_characters(self, include_plain=False):
        """Display character-frequencies (excluding printable ASCII)."""
        import collections
        from unicodedata import name

        with self.filepath.open(encoding=self.encoding) as fd:
            hist = collections.Counter(fd.read())
        table = '\n'.join(
            '%d\t%-9r\t%s\t%s' % (n, c, c, name(c, ''))
            for c, n in hist.most_common()
            if include_plain or not 20 <= ord(c) <= 126)
        print(table)
