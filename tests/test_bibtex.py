from __future__ import unicode_literals

from pyglottolog.references.bibtex import names


def test_names():
    assert [n.last for n in names('Alfred Meier and Peter von Bohr')] == \
           ['Meier', 'Bohr']
