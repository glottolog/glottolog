# coding: utf8

from __future__ import unicode_literals

import six

from pyglottolog.references.bibtex_undiacritic import undiacritic

import pytest


@pytest.mark.skipif(six.PY3, reason='PY2 only')
@pytest.mark.parametrize('input_, expected', [
    ("\\cmd{äöüß}", "aouss"),
])
def test_undiacritic(input_, expected):
    assert undiacritic(input_) == expected
