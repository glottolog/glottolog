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


def test_bibfiles(capsys, api):
    api.bibfiles.roundtrip_all()
    assert 'a.bib' in capsys.readouterr()[0]

    api.bibfiles['b.bib'].show_characters()
    assert 'CJK UNIFIED IDEOGRAPH' in capsys.readouterr()[0]

    bf = api.bibfiles[0]
    assert len(list(bf.iterentries())) == 3
    assert bf.size
    assert bf.mtime
