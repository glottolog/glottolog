# coding: utf8
from __future__ import unicode_literals

import pytest

from six import PY2
from clldutils.testing import capture


def test_roman(api):
    from pyglottolog.references.roman import introman, romanint

    assert introman(5) == 'v'
    assert introman(8) == 'viii'
    for i in range(1, 2000):
        assert i == romanint(introman(i))


def test_Database(tmpdir, api):
    from pyglottolog.references.bibfiles_db import Database

    if not PY2:  # pragma: no cover
        return

    db = str(tmpdir / 'test.sqlite3')
    with capture(api.bibfiles.to_sqlite, db) as out:
        assert 'ENTRYTYPE' in out
    with capture(api.bibfiles.to_sqlite, db) as out:
        pass
    with capture(api.bibfiles.to_sqlite, db, rebuild=True) as out:
        pass

    db = Database(db, api.bibfiles)
    with capture(db.recompute, reload_priorities=api.bibfiles) as out:
        assert len(out.splitlines()) == 34
    with capture(db.is_uptodate, api.bibfiles[1:], verbose=True) as out:
        assert len(out.splitlines()) == 3
    db.to_bibfile(str(tmpdir / 'out.bib'))
    db.to_csvfile(str(tmpdir / 'out.csv'))
    db.to_replacements(str(tmpdir /'out.json'))
    assert db.to_hhmapping() == {'s:Karang:Tati-Harzani': 41999}
    with capture(db.trickle) as out:
        assert '2 changed 1 added in a' in out
    key, (entrytype, fields) = db[('b.bib', 'arakawa97')]
    assert entrytype == 'article'
    assert fields['volume'] == '16'
    with capture(db.stats) as out:
        pass

    for attr in ['splits', 'merges', 'identified', 'combined']:
        with capture(getattr(db, 'show_' + attr)) as out:
            pass


def test_markconcservative(tmpdir, api):
    from pyglottolog.references.libmonster import markconservative

    res = markconservative(
        {1: ('article', {'title': 'Grammar'})},
        api.hhtypes.triggers,
        {1: ('article', {'title': 'Grammar'})},
        api.hhtypes,
        str(tmpdir /'marks.txt'),
        verbose=False)
    assert res[1][1]['hhtype'].split()[0] == 'grammar'

    # If a higher hhtype is computed, this cancels out previous computations.
    res = markconservative(
        {1: ('article', {'title': 'grammar', 'lgcode': 'abc'})},
        api.hhtypes.triggers,
        {1: ('article', {'title': 'other', 'hhtype': 'other', 'lgcode': 'abc'})},
        api.hhtypes,
        str(tmpdir /'marks.txt'),
        verbose=False)
    assert 'hhtype' not in res[1][1]


def test_markall(api):
    from pyglottolog.references.libmonster import markall

    bib = {
        1: ('article', {'title': "other grammar of lang"}),
        2: ('article', {'title': "grammar of lang and dial"}),
        3: ('article', {'title': "other"}),
        4: ('article', {'title': "grammar and phonologie and morphologie"})
    }
    hht = api.hhtypes
    markall(bib, hht.triggers, verbose=False, rank=lambda l: hht[l].rank)
    assert 'grammar' in bib[1][1]['hhtype']
    assert 'morphologie and phonologie;grammar' in bib[4][1]['hhtype']

    markall(bib, api.triggers['lgcode'], verbose=False)
    assert 'language' in bib[1][1]['lgcode']


def test_add_inlg_e(api):
    from pyglottolog.references.libmonster import add_inlg_e, INLG

    res = add_inlg_e(
        {1: ('article', {'title': 'Grammar of language'})},
        api.triggers[INLG],
        verbose=False)
    assert res[1][1][INLG] == 'language [abc]'


def test_names():
    from pyglottolog.references.bibtex import names

    assert [n.last for n in names('Alfred Meier and Peter von Bohr')] == \
           ['Meier', 'Bohr']


def test_undiacritic():
    from pyglottolog.references.bibtex_undiacritic import undiacritic

    if not PY2:
        return  # pragma: no cover

    for i, o in [
        ("\\cmd{äöüß}", "aouss"),
    ]:
        assert undiacritic(i) == o


def test_ulatex_decode():
    from pyglottolog.references.bibtex_escaping import ulatex_decode

    if not PY2:
        return  # pragma: no cover

    for i, o, r in [
        ("", "", ""),
        ("&#97;", "a", ""),
        ("a\tb", "a\tb", ""),
        ("\\%\\&\\#", "%&#", "\\%\\&\\#"),
        ("a\\^o\=\,b", "aôb̦̄", ""),
        ("Luise\\~no", "Luiseño", ""),
        ("\\textdoublevertline", "‖", ""),
        ("\\url{abcdefg}", "abcdefg", ""),
        ("\\textdoublegrave{o}", "\u020d", ""),
        ("\\textsubu{\\'{v}}a", "v\u032e\u0301a", ""),
        ("ng\\~{\\;u}", "ngữ", ""),
        ('\germ \\"Uber den Wolken', "[deu] Über den Wolken", ""),
        ('P. V\\u{a}n-T\\;u\\;o', 'P. Văn-Tươ', ""),
        ('\\textit{\\"{u}bertext}', 'übertext', ""),
    ]:
        assert ulatex_decode(i) == o
        if r:
            assert o.encode('ulatex+utf8', errors='keep') == r


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


def test_keyid():
    from pyglottolog.references.libmonster import keyid

    for fields, res in [
        ({}, '__missingcontrib__'),
        (dict(author='An Author'), 'author_no-titlend'),
        (dict(editor='An Author'), 'author_no-titlend'),
        (dict(author='An Author', title='A rather long title'), 'author_rather-longnd'),
        (dict(author='An Author', title='Title', year='2014'), 'author_title2014'),
        (dict(author='An Author', volume='IV'), 'author_no-titleivnd'),
        (dict(author='An Author', extra_hash='a'), 'author_no-titlenda'),
    ]:
        assert keyid(fields, {}) == res

    with capture(keyid, dict(author='An Author and '), {}) as out:
        assert 'Unparsed' in out


def test_pyear():
    from pyglottolog.references.libmonster import pyear

    for year, res in [
        ('', '[nd]'),
        ('1931', '1931'),
        ('1931-32', '1931-1932'),
    ]:
        assert pyear(year) == res


def test_pagecount():
    from pyglottolog.references.libmonster import pagecount

    for pages, res in [
        ('', ''),
        ('1', '1'),
        ('10-20', '11'),
        ('10-20,v-viii', '4+11'),
        ('20,viii', '8+20'),
        ('10-2', '3'),  # interpreted as 10-12
    ]:
        assert pagecount(pages) == res


def test_lgcode():
    from pyglottolog.references.libmonster import lgcode

    for lgcode_, codes in [
        ('', []),
        ('[abc]', ['abc']),
        ('abc,NOCODE_Abc', ['abc', 'NOCODE_Abc']),
    ]:
        assert lgcode((None, dict(lgcode=lgcode_))) == codes


def test_grp2fd():
    from pyglottolog.references.libmonster import grp2fd

    assert grp2fd([(1, 2), (1, 3), (2, 4), (1, 5)]) == \
           {1: {2: 1, 3: 1, 5: 1}, 2: {4: 1}}
