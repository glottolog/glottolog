from __future__ import unicode_literals

import six

import pytest

from pyglottolog.references.bibfiles_db import Database, distance


@pytest.mark.skipif(six.PY3, reason='skip')
def test_Database(capsys, tmpdir, api):
    db = str(tmpdir / 'test.sqlite3')
    api.bibfiles.to_sqlite(db)
    assert 'ENTRYTYPE' in capsys.readouterr()[0]

    api.bibfiles.to_sqlite(db)
    api.bibfiles.to_sqlite(db, rebuild=True)
    capsys.readouterr()

    db = Database(db, api.bibfiles)
    db.recompute(reload_priorities=api.bibfiles)
    assert len(capsys.readouterr()[0].splitlines()) == 34

    db.is_uptodate(api.bibfiles[1:], verbose=True)
    assert len(capsys.readouterr()[0].splitlines()) == 3

    db.to_bibfile(str(tmpdir / 'out.bib'))
    db.to_csvfile(str(tmpdir / 'out.csv'))
    db.to_replacements(str(tmpdir /'out.json'))
    assert db.to_hhmapping() == {'s:Karang:Tati-Harzani': 41999}

    db.trickle()
    assert '2 changed 1 added in a' in capsys.readouterr()[0]

    key, (entrytype, fields) = db[('b.bib', 'arakawa97')]
    assert entrytype == 'article'
    assert fields['volume'] == '16'

    db.stats()

    db.show_splits()

    db.show_merges()

    db.show_identified()

    db.show_combined()


d1 = {
    'ENTRYTYPE':'article',
    'author': 'An Author',
    'year': '1998',
    'title': 'The Title',
}


@pytest.mark.parametrize('left, right, expected', [
    ({}, {}, 0.0),
    (d1, d1, 0.0),
    (d1, {}, 1.0),
    ({}, d1, 1.0),
    (d1, {'author': 'An Author'}, 0.0),
    (d1, {'author': 'Another Author'}, pytest.approx(0.2173, rel=.001)),
    (d1, {'author': 'An Author', 'title': 'Another Title'}, pytest.approx(0.13636, rel=.001)),
])
def test_distance(left, right, expected):
    assert distance(left, right) == expected
