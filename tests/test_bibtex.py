from __future__ import unicode_literals

import pytest

from pyglottolog.references.bibtex import names


@pytest.mark.parametrize('name, expected', [
    ('Alfred Meier and Peter von Bohr', ['Meier', 'Bohr']),
])
def test_names(name, expected):
    assert [n.last for n in names(name)] == expected
