from __future__ import unicode_literals

from pyglottolog import languoids


def test_paths(api):
    assert api.ftsindex


def test_languoid(api):
    assert api.languoid('abc').name == 'language'


def test_languoids(api):
    assert len(list(api.languoids())) == 4
    assert len(list(api.languoids(maxlevel=languoids.Level.family))) == 1
    assert len(list(api.languoids(maxlevel=languoids.Level.language))) == 3
    assert len(api.languoids_by_code()) == 7
    assert 'NOCODE_Family-name' in api.languoids_by_code()


def test_load_triggers(api):
    assert len(api.triggers) == 2


def test_macroarea_map(api):
    assert api.macroarea_map['abc'] == 'Eurasia'


def test_bibfiles(capsys, api):
    c = api.bibfiles
    c.roundtrip_all()
    assert 'a.bib' in capsys.readouterr()[0]

    c['b.bib'].show_characters()
    assert 'CJK UNIFIED IDEOGRAPH' in capsys.readouterr()[0]

    abib = c[0]
    assert len(list(abib.iterentries())) == 3
    assert abib.size
    assert abib.mtime
