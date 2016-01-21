# _bibfiles.py - ordered collection of bibfiles with load/save api

import os
import io
import datetime

from clldutils.inifile import INI

from pyglottolog.util import references_path
import _bibtex
from _bibfiles_db import Database

__all__ = ['Collection', 'BibFile', 'Database']

DIR = references_path('bibtex').as_posix()
CONFIG = 'BIBFILES.ini'


class Collection(list):
    """Directory with an INI-file with settings for BibTeX files inside."""

    _encoding = 'utf-8-sig'

    @classmethod
    def _bibfiles(cls, directory, config, endwith):
        """Read the INI-file, yield bibfile instances for sections."""
        cfg = INI(interpolation=None)
        cfg.read(os.path.join(directory, '..', config))
        for s in cfg.sections():
            if not s.endswith(endwith):
                continue
            filepath = os.path.join(directory, s)
            assert os.path.exists(filepath)
            sortkey = cfg.get(s, 'sortkey')
            if sortkey.lower() == 'none':
                sortkey = None
            yield BibFile(
                filepath=filepath,
                encoding=cfg.get(s, 'encoding'), sortkey=sortkey,
                use_pybtex=cfg.getboolean(s, 'use_pybtex'),
                priority=cfg.getint(s, 'priority'),
                name=cfg.get(s, 'name'), title=cfg.get(s, 'title'),
                description=cfg.get(s, 'description'),
                abbr=cfg.get(s, 'abbr'))

    def __init__(self, directory=DIR, config=CONFIG, endwith='.bib'):
        self.directory = directory
        bibfiles = self._bibfiles(directory, config, endwith)
        super(Collection, self).__init__(bibfiles)
        self._map = {b.filename: b for b in self}

    def __getitem__(self, index_or_filename):
        """Retrieve a bibfile by index or filename."""
        if isinstance(index_or_filename, basestring):
            return self._map[index_or_filename]
        return super(Collection, self).__getitem__(index_or_filename)

    def to_sqlite(self, filename=None, rebuild=False):
        """Return a database with the bibfiles loaded."""
        return Database.from_bibfiles(self, filename, rebuild=rebuild)

    def check_all(self):
        """Check the BibTeX syntax of all bibfiles."""
        for b in self:
            b.check()
            
    def roundtrip_all(self):
        """Load and save all bibfiles with the current settings."""
        for b in self:
            b.roundtrip()


class BibFile(object):
    """BibTeX source file with configurable load/save options and meta data."""

    def __init__(self, filepath, encoding, sortkey, use_pybtex=True, priority=0,
                 name=None, title=None, description=None, abbr=None):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.encoding = encoding
        self.sortkey = sortkey
        self.use_pybtex = use_pybtex
        self.priority = priority
        self.name = name
        self.title = title
        self.description = description
        self.abbr = abbr

    @property
    def size(self):
        return os.stat(self.filepath).st_size

    @property
    def mtime(self):
        return datetime.datetime.fromtimestamp(os.stat(self.filepath).st_mtime)

    def iterentries(self):
        """Yield entries as (bibkey, (entrytype, fields)) tuples."""
        return _bibtex.iterentries(filename=self.filepath,
            encoding=self.encoding,
            use_pybtex=self.use_pybtex)

    def load(self):
        """Return entries as bibkey -> (entrytype, fields) dict."""
        return _bibtex.load(filename=self.filepath,
            preserve_order=self.sortkey is None,
            encoding=self.encoding,
            use_pybtex=self.use_pybtex)

    def save(self, entries, verbose=True):
        """Write bibkey -> (entrytype, fields) map to file."""
        _bibtex.save(entries,
            filename=self.filepath,
            sortkey=self.sortkey,
            encoding=self.encoding,
            use_pybtex=self.use_pybtex,
            verbose=verbose)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.filename)

    def check(self):
        print(self)
        entries = self.load()  # bare BibTeX syntax
        invalid = _bibtex.check(filename=self.filepath)  # names/macros etc.
        verdict = ('(%d invalid)' % invalid) if invalid else 'OK'
        print('%d %s' % (len(entries), verdict))

    def roundtrip(self):
        print(self)
        self.save(self.load())

    def show_characters(self, include_plain=False):
        """Display character-frequencies (excluding printable ASCII)."""
        import collections
        from unicodedata import name

        with io.open(self.filepath, encoding=self.encoding) as fd:
            data = fd.read()
        hist = collections.Counter(data)
        table = '\n'.join('%d\t%-9r\t%s\t%s' % (n, c, c, name(c, ''))
            for c, n in hist.most_common()
            if include_plain or not 20 <= ord(c) <= 126)
        print(table)


if __name__ == '__main__':
    c = Collection()
    d = Database()
