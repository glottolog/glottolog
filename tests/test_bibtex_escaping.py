# coding: utf8
from __future__ import unicode_literals

import pytest

import six

from pyglottolog.references.bibtex_escaping import ulatex_decode


@pytest.mark.skipif(six.PY3, reason='skip')
@pytest.mark.parametrize('input_, decoded, recoded', [
    ("", "", None),
    ("&#97;", "a", None),
    ("a\tb", "a\tb", None),
    ("\\%\\&\\#", "%&#", "\\%\\&\\#"),
    ("a\\^o\=\,b", "aôb̦̄", None),
    ("Luise\\~no", "Luiseño", None),
    ("\\textdoublevertline", "‖", None),
    ("\\url{abcdefg}", "abcdefg", None),
    ("\\textdoublegrave{o}", "\u020d", None),
    ("\\textsubu{\\'{v}}a", "v\u032e\u0301a", None),
    ("ng\\~{\\;u}", "ngữ", None),
    ('\germ \\"Uber den Wolken', "[deu] Über den Wolken", None),
    ('P. V\\u{a}n-T\\;u\\;o', 'P. Văn-Tươ', None),
    ('\\textit{\\"{u}bertext}', 'übertext', None),
])
def test_ulatex_decode(input_, decoded, recoded):
    assert ulatex_decode(input_) == decoded
    if recoded is not None:
        assert decoded.encode('ulatex+utf8', errors='keep') == recoded
