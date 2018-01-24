from __future__ import unicode_literals

import pytest

from pyglottolog import languoids


def test_legacy_import():
    from pyglottolog import api
    from pyglottolog import Glottolog
    assert api.Glottolog is Glottolog


def test_glottolog_invalid_repos(tmpdir):
    from pyglottolog import Glottolog
    with pytest.raises(ValueError, match=r'missing tree dir'):
        Glottolog(str(tmpdir))


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
