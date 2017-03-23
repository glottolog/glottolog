# bibtex.py - bibtex file parsing/serialization

# TODO: make check fail on non-whitespace between entries (bibtex 'comments')

import io
import collections

from six import PY2, text_type
from pybtex.database.input.bibtex import BibTeXEntryIterator, Parser, UndefinedMacro
from pybtex.scanner import PybtexSyntaxError
from pybtex.exceptions import PybtexError
from pybtex.textutils import whitespace_re
from pybtex.bibtex.utils import split_name_list
from pybtex.database import Person

from clldutils.path import as_posix, memorymapped


FIELDORDER = [
    'author', 'editor', 'title', 'booktitle', 'journal',
    'school', 'publisher', 'address',
    'series', 'volume', 'number', 'pages', 'year', 'issn', 'url',
]


def load(filename, preserve_order=False, encoding=None):
    cls = collections.OrderedDict if preserve_order else dict
    return cls(iterentries(filename, encoding))


def py2_decode(text, encoding):
    return text.decode(encoding) if PY2 else text


def iterentries_from_text(text, encoding='utf8'):
    if not PY2:  # pragma: no cover
        if hasattr(text, 'read'):
            text = text.read()
        if not isinstance(text, text_type):
            text = text.decode(encoding)
    for entrytype, (bibkey, fields) in BibTeXEntryIterator(text):
        fields = {
            py2_decode(name, encoding).lower():
                whitespace_re.sub(' ', py2_decode(''.join(values), encoding).strip())
            for name, values in fields}
        yield py2_decode(bibkey, encoding), (py2_decode(entrytype, encoding), fields)


def iterentries(filename, encoding=None):
    encoding = encoding or 'utf8'
    with memorymapped(as_posix(filename)) as source:
        try:
            for entrytype, (bibkey, fields) in iterentries_from_text(source, encoding):
                yield entrytype, (bibkey, fields)
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
        except PybtexError as e:  # pragma: no cover
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


def save(entries, filename, sortkey, encoding='utf8'):
    with io.open(as_posix(filename), 'w', encoding=encoding, errors='strict') as fd:
        dump(entries, fd, sortkey, encoding, None)


def dump(entries, fd, sortkey=None, encoding=None, errors='strict'):
    assert sortkey in [None, 'bibkey']
    if sortkey is None:
        if isinstance(entries, collections.OrderedDict):  # pragma: no cover
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
    parser.parse_file(as_posix(filename))
    return parser.error_count


class CheckParser(Parser):
    """Unline BibTeXEntryIterator also parses names, macros, etc."""

    def __init__(self, *args, **kwargs):
        super(CheckParser, self).__init__(*args, **kwargs)
        self.error_count = 0

    def handle_error(self, error):  # pragma: no cover
        print('%r' % error)
        self.error_count += 1
        if not isinstance(error, UndefinedMacro):
            raise error

    def process_entry(self, *args, **kwargs):
        try:
            super(CheckParser, self).process_entry(*args, **kwargs)
        except PybtexError as e:  # pragma: no cover
            print(e)
            self.error_count += 1
