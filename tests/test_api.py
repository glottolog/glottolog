from __future__ import unicode_literals

from pyglottolog import languoids


def test_paths(sapi):
    assert sapi.ftsindex


def test_languoid(sapi):
    assert sapi.languoid('abc').name == 'language'


def test_languoids(sapi):
    assert len(list(sapi.languoids())) == 4
    assert len(list(sapi.languoids(maxlevel=languoids.Level.family))) == 1
    assert len(list(sapi.languoids(maxlevel=languoids.Level.language))) == 3
    assert len(sapi.languoids_by_code()) == 7
    assert 'NOCODE_Family-name' in sapi.languoids_by_code()


def test_load_triggers(sapi):
    assert len(sapi.triggers) == 2


def test_macroarea_map(sapi):
    assert sapi.macroarea_map['abc'] == 'Eurasia'
