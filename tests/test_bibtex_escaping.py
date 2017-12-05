from __future__ import unicode_literals

import six

import pytest

from pyglottolog.references.bibtex_escaping import ulatex_decode


@pytest.mark.skipif(six.PY3, reason='PY2 only')
@pytest.mark.parametrize('input_, decoded, recoded', [
    ('', '', None),
    ('&#97;', 'a', None),
    ('a\tb', 'a\tb', None),
    ('\\%\\&\\#', '%&#', '\\%\\&\\#'),
    ('a\\^o\=\,b', 'a\u00f4b\u0326\u0304', None),
    ('Luise\\~no', 'Luise\u00f1o', None),
    ('\\textdoublevertline', '\u2016', None),
    ('\\url{abcdefg}', 'abcdefg', None),
    ('\\textdoublegrave{o}', '\u020d', None),
    ("\\textsubu{\\'{v}}a", 'v\u032e\u0301a', None),
    ('ng\\~{\\;u}', 'ng\u1eef', None),
    ('\germ \\"Uber den Wolken', '[deu] \u00dcber den Wolken', None),
    ('P. V\\u{a}n-T\\;u\\;o', 'P. V\u0103n-T\u01b0\u01a1', None),
    ('\\textit{\\"{u}bertext}', '\u00fcbertext', None),
])
def test_ulatex_decode(input_, decoded, recoded):
    assert ulatex_decode(input_) == decoded
    if recoded is not None:
        assert decoded.encode('ulatex+utf-8', errors='keep') == recoded
