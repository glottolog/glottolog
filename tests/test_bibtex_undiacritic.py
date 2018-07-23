from __future__ import unicode_literals

import six

from pyglottolog.references.bibtex_undiacritic import undiacritic

import pytest


@pytest.mark.parametrize('input_, expected', [
    ('\\cmd{\u00e4\u00f6\u00fc\u00df}', 'aouss'),
])
def test_undiacritic(input_, expected):
    assert undiacritic(input_) == expected
