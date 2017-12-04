from __future__ import unicode_literals

from clldutils.testing import capture  # FIXME


def test_paths(api):
    assert api.ftsindex


def test_languoid(api):
    assert api.languoid('abc').name == 'language'


def test_languoids(api):
    from pyglottolog.languoids import Level

    assert len(list(api.languoids())) == 4
    assert len(list(api.languoids(maxlevel=Level.family))) == 1
    assert len(list(api.languoids(maxlevel=Level.language))) == 3
    assert len(api.languoids_by_code()) == 7
    assert 'NOCODE_Family-name' in api.languoids_by_code()


def test_load_triggers(api):
    assert len(api.triggers) == 2


def test_macroarea_map(api):
    assert api.macroarea_map['abc'] == 'Eurasia'


def test_bibfiles(api):
    c = api.bibfiles
    with capture(c.roundtrip_all) as out:
        assert 'a.bib' in out
    with capture(c['b.bib'].show_characters) as out:
        assert 'CJK UNIFIED IDEOGRAPH' in out
    abib = c[0]
    assert len(list(abib.iterentries())) == 3
    assert abib.size
    assert abib.mtime
