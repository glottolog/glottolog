from __future__ import unicode_literals

import pytest

from pyglottolog.references.roman import introman, romanint


def test_legacy_import():
    from pyglottolog.monsterlib import roman
    assert roman.romanint is romanint


@pytest.mark.parametrize('input_, expected', [
    (5, 'v',),
    (8, 'viii'),
])
def test_introman(input_, expected):
    assert introman(input_) == expected


def test_roundtrip(n=2000):
    for i in range(1, n + 1):
        assert romanint(introman(i)) == i
