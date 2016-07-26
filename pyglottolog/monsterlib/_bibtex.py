# bibtex.py - bibtex file parsing/serialization

# TODO: make check fail on non-whitespace between entries (bibtex 'comments')

import io
import mmap
import contextlib
import collections

from pybtex.database.input.bibtex import BibTeXEntryIterator, Parser, UndefinedMacro
from pybtex.scanner import PybtexSyntaxError
from pybtex.exceptions import PybtexError
from pybtex.textutils import whitespace_re
from pybtex.bibtex.utils import split_name_list
from pybtex.database import Person


FIELDORDER = [
    'author', 'editor', 'title', 'booktitle', 'journal',
    'school', 'publisher', 'address',
    'series', 'volume', 'number', 'pages', 'year', 'issn', 'url',
]


@contextlib.contextmanager
def memorymapped(filename, access=mmap.ACCESS_READ):
    fd = open(filename)
    try:
        m = mmap.mmap(fd.fileno(), 0, access=access)
    except:  # pragma: no cover
        fd.close()
        raise
    try:
        yield m
    finally:
        m.close()
        fd.close()


def load(filename, preserve_order=False, encoding=None):
    cls = collections.OrderedDict if preserve_order else dict
    return cls(iterentries(filename, encoding))


def iterentries(filename, encoding=None):
    encoding = encoding or 'utf8'
    with memorymapped(filename) as source:
        try:
            for entrytype, (bibkey, fields) in BibTeXEntryIterator(source):
                fields = {
                    name.decode(encoding).lower():
                    whitespace_re.sub(' ', ''.join(values).decode(encoding).strip())
                    for name, values in fields}
                yield bibkey.decode(encoding), (entrytype.decode(encoding), fields)
        except PybtexSyntaxError as e:  # pragma: no cover
            debug_pybtex(source, e)


def debug_pybtex(source, e):  # pragma: no cover
    start, line, pos = e.error_context_info
    print('BIBTEX ERROR on line %d, last parsed lines:' % line)
    print(source[start:start + 500] + '...')
    raise e


def names(s):
    for name in split_name_list(s):
        try:
            yield Name.from_string(name)
        except PybtexError as e:
            print(repr(e))


class Name(collections.namedtuple('Name', 'prelast last given lineage')):

    __slots__ = ()

    @classmethod
    def from_string(cls, name):
        person = Person(name)
        prelast, last, first, middle, lineage = (
            ' '.join(getattr(person, part)())
            for part in ('prelast', 'last', 'first', 'middle', 'lineage'))
        given = ' '.join(n for n in (first, middle) if n)
        return cls(prelast, last, given, lineage)


def save(entries, filename, sortkey, encoding=None, verbose=True):
    with io.open(filename, 'w', encoding=encoding or 'utf8', errors='strict') as fd:
        dump(entries, fd, sortkey, encoding, None, verbose)


def dump(entries, fd, sortkey=None, encoding=None, errors='strict', verbose=True):
    assert sortkey in [None, 'bibkey']
    if sortkey is None:
        if isinstance(entries, collections.OrderedDict):
            items = entries.items()
        elif isinstance(entries, dict):  # pragma: no cover
            raise ValueError('dump needs sortkey or ordered entries')
        else:
            items = entries
    else:  # elif sortkey == 'bibkey':
        items = (
            (bibkey, entries[bibkey])
            for bibkey in sorted(entries, key=lambda bibkey: bibkey.lower()))
    """Reserved characters (* -> en-/decoded by latexcodec)
    * #: \#
      $: \$
      %: \%
      ^: \^{} \textasciicircum
    * &: \&
    * _: \_
      {: \{
      }: \}
      ~: \~{} \textasciitilde
      \: \textbackslash{}
      <: \textless
      >: \textgreater
    """
    assert encoding
    assert errors is None
    fd.write(u'# -*- coding: utf-8 -*-\n')
    for bibkey, (entrytype, fields) in items:
        fd.write(u'@%s{%s' % (entrytype, bibkey))
        for k, v in fieldorder.itersorted(fields):
            fd.write(u',\n    %s = {%s}' % (k, v.strip() if hasattr(v, 'strip') else v))
        fd.write(u'\n}\n' if fields else u',\n}\n')


class Ordering(dict):
    """Key order for iterating over dicts (unknown keys last alphabetic)."""

    _missing = float('inf')

    @classmethod
    def fromlist(cls, keys):
        """Define the order of keys as given."""
        return cls((k, i) for i, k in enumerate(keys))

    def itersorted(self, dct):
        """Iterate over dct (key, value) pairs in the defined order."""
        for key in sorted(dct, key=self._itersorted_key):
            yield key, dct[key]

    def _itersorted_key(self, key):
         return self[key], key

    def __missing__(self, key):
        return self._missing


fieldorder = Ordering.fromlist(FIELDORDER)


def check(filename, encoding=None):
    parser = CheckParser(encoding=encoding)
    parser.parse_file(filename)
    return parser.error_count
    

class CheckParser(Parser):
    """Unline BibTeXEntryIterator also parses names, macros, etc."""

    def __init__(self, *args, **kwargs):
        super(CheckParser, self).__init__(*args, **kwargs)
        self.error_count = 0

    def handle_error(self, error):
        print('%r' % error)
        self.error_count += 1
        if not isinstance(error, UndefinedMacro):
            raise error

    def process_entry(self, *args, **kwargs):
        try:
            super(CheckParser, self).process_entry(*args, **kwargs)
        except PybtexError as e:
            print(e)
            self.error_count += 1


def _test_load():
    import _bibfiles
    _bibfiles.Collection().check_all()


if __name__ == '__main__':
    _test_load()
