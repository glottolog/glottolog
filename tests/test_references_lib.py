# coding: utf8
from __future__ import unicode_literals

import pytest

from six import PY2


def test_roman():
    from pyglottolog.references.roman import introman, romanint

    assert introman(5) == 'v'
    assert introman(8) == 'viii'
    for i in range(1, 2000):
        assert romanint(introman(i)) == i


def test_Database(capsys, tmpdir, api):
    from pyglottolog.references.bibfiles_db import Database

    if not PY2:  # pragma: no cover
        return

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


def test_markconcservative(tmpdir, sapi):
    from pyglottolog.references.libmonster import markconservative

    res = markconservative(
        {1: ('article', {'title': 'Grammar'})},
        sapi.hhtypes.triggers,
        {1: ('article', {'title': 'Grammar'})},
        sapi.hhtypes,
        str(tmpdir /'marks.txt'),
        verbose=False)
    assert res[1][1]['hhtype'].split()[0] == 'grammar'

    # If a higher hhtype is computed, this cancels out previous computations.
    res = markconservative(
        {1: ('article', {'title': 'grammar', 'lgcode': 'abc'})},
        sapi.hhtypes.triggers,
        {1: ('article', {'title': 'other', 'hhtype': 'other', 'lgcode': 'abc'})},
        sapi.hhtypes,
        str(tmpdir /'marks.txt'),
        verbose=False)
    assert 'hhtype' not in res[1][1]


def test_markall(sapi):
    from pyglottolog.references.libmonster import markall

    bib = {
        1: ('article', {'title': "other grammar of lang"}),
        2: ('article', {'title': "grammar of lang and dial"}),
        3: ('article', {'title': "other"}),
        4: ('article', {'title': "grammar and phonologie and morphologie"})
    }
    hht = sapi.hhtypes
    markall(bib, hht.triggers, verbose=False, rank=lambda l: hht[l].rank)
    assert 'grammar' in bib[1][1]['hhtype']
    assert 'morphologie and phonologie;grammar' in bib[4][1]['hhtype']

    markall(bib, sapi.triggers['lgcode'], verbose=False)
    assert 'language' in bib[1][1]['lgcode']


def test_add_inlg_e(sapi):
    from pyglottolog.references.libmonster import add_inlg_e, INLG

    res = add_inlg_e(
        {1: ('article', {'title': 'Grammar of language'})},
        sapi.triggers[INLG],
        verbose=False)
    assert res[1][1][INLG] == 'language [abc]'


def test_names():
    from pyglottolog.references.bibtex import names

    assert [n.last for n in names('Alfred Meier and Peter von Bohr')] == \
           ['Meier', 'Bohr']


@pytest.mark.parametrize('input_, expected', [
        ("\\cmd{äöüß}", "aouss"),
])
def test_undiacritic(input_, expected):
    from pyglottolog.references.bibtex_undiacritic import undiacritic

    if not PY2:
        return  # pragma: no cover

    assert undiacritic(input_) == expected


@pytest.mark.parametrize('input_, decoded, recoded', [
    ("", "", None),
    ("&#97;", "a", None),
    ("a\tb", "a\tb", None),
    ("\\%\\&\\#", "%&#", "\\%\\&\\#"),
    ("a\\^o\=\,b", "aôb̦̄", None),
    ("Luise\\~no", "Luiseño", None),
    ("\\textdoublevertline", "‖", None),
    ("\\url{abcdefg}", "abcdefg", None),
    ("\\textdoublegrave{o}", "\u020d", None),
    ("\\textsubu{\\'{v}}a", "v\u032e\u0301a", None),
    ("ng\\~{\\;u}", "ngữ", None),
    ('\germ \\"Uber den Wolken', "[deu] Über den Wolken", None),
    ('P. V\\u{a}n-T\\;u\\;o', 'P. Văn-Tươ', None),
    ('\\textit{\\"{u}bertext}', 'übertext', None),
])
def test_ulatex_decode(input_, decoded, recoded):
    from pyglottolog.references.bibtex_escaping import ulatex_decode

    if not PY2:
        return  # pragma: no cover

    assert ulatex_decode(input_) == decoded
    assert recoded is None or decoded.encode('ulatex+utf8', errors='keep') == recoded


def test_distance():
    from pyglottolog.references.bibfiles_db import distance

    assert distance({}, {}) == pytest.approx(0)
    d1 = dict(author='An Author', year='1998', title='The Title', ENTRYTYPE='article')
    for d2, dist in [
        ({}, 1.0),
        (d1, 0.0),
        (dict(author='An Author'), 0.0),
        (dict(author='Another Author'), 0.2173),
        (dict(author='An Author', title='Another Title'), 0.13636),
    ]:
        assert distance(d1, d2) == pytest.approx(dist, rel=0.001)


@pytest.mark.parametrize('fields, expected', [
    ({}, '__missingcontrib__'),
    (dict(author='An Author'), 'author_no-titlend'),
    (dict(editor='An Author'), 'author_no-titlend'),
    (dict(author='An Author', title='A rather long title'), 'author_rather-longnd'),
    (dict(author='An Author', title='Title', year='2014'), 'author_title2014'),
    (dict(author='An Author', volume='IV'), 'author_no-titleivnd'),
    (dict(author='An Author', extra_hash='a'), 'author_no-titlenda'),
])
def test_keyid(fields, expected):
    from pyglottolog.references.libmonster import keyid

    assert keyid(fields, {}) == expected


def test_keyid_invalid(capsys):
    from pyglottolog.references.libmonster import keyid

    keyid(dict(author='An Author and '), {})
    assert 'Unparsed' in capsys.readouterr()[0]


@pytest.mark.parametrize('year, expected', [
    ('', '[nd]'),
    ('1931', '1931'),
    ('1931-32', '1931-1932'),
])
def test_pyear(year, expected):
    from pyglottolog.references.libmonster import pyear

    assert pyear(year) == expected


@pytest.mark.parametrize('pages, expected', [
    ('', ''),
    ('1', '1'),
    ('10-20', '11'),
    ('10-20,v-viii', '4+11'),
    ('20,viii', '8+20'),
    ('10-2', '3'),  # interpreted as 10-12
])
def test_pagecount(pages, expected):
    from pyglottolog.references.libmonster import pagecount

    assert pagecount(pages) == expected


@pytest.mark.parametrize('lgcode_, expected', [
    ('', []),
    ('[abc]', ['abc']),
    ('abc,NOCODE_Abc', ['abc', 'NOCODE_Abc']),
])
def test_lgcode(lgcode_, expected):
    from pyglottolog.references.libmonster import lgcode

    assert lgcode((None, {'lgcode': lgcode_})) == expected


def test_grp2fd():
    from pyglottolog.references.libmonster import grp2fd

    assert grp2fd([(1, 2), (1, 3), (2, 4), (1, 5)]) == \
           {1: {2: 1, 3: 1, 5: 1}, 2: {4: 1}}
