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
    assert len(list(api.languoids())) == 5
    assert len(list(api.languoids(maxlevel=languoids.Level.family))) == 1
    assert len(list(api.languoids(maxlevel=languoids.Level.language))) == 3
    assert len(api.languoids_by_code()) == 8
    assert 'NOCODE_Family-name' in api.languoids_by_code()


def test_newick_tree(api):
    assert api.newick_tree(start='abcd1235') == \
           "('dialect [abcd1236]':1)'language [abcd1235][abc]-l-':1;"
    assert api.newick_tree(start='abcd1235', template='{l.id}') == "(abcd1236:1)abcd1235:1;"
    assert set(api.newick_tree().split('\n')) == {
        "(('isolate {dialect} [dial1234]':1)'isolate [isol1234]-l-':1)'isolate [isol1234]':1;",
        "(('dialect [abcd1236]':1)'language [abcd1235][abc]-l-':1)'family [abcd1234][aaa]':1;"
    }


def test_hhtypes(api):
    assert len(api.hhtypes) == 2


def test_load_triggers(api):
    assert len(api.triggers) == 2


def test_macroarea_map(api):
    assert api.macroarea_map['abc'] == 'Eurasia'
