# coding: utf8
from __future__ import unicode_literals, print_function, division

from six import PY2
from nose.tools import assert_almost_equal, assert_equal
from clldutils.testing import capture

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_roman(self):
        from pyglottolog.monsterlib.roman import introman, romanint

        self.assertEqual(introman(5), 'v')
        self.assertEqual(introman(8), 'viii')
        for i in range(1, 2000):
            self.assertEqual(i, romanint(introman(i)))

    def test_Collection(self):
        from pyglottolog.monsterlib._bibfiles_db import Database

        if not PY2:  # pragma: no cover
            return

        db = self.tmp_path('test.sqlite')
        with capture(self.api.bibfiles.to_sqlite, db) as out:
            self.assertIn('ENTRYTYPE', out)
        with capture(self.api.bibfiles.to_sqlite, db) as out:
            pass
        with capture(self.api.bibfiles.to_sqlite, db, rebuild=True) as out:
            pass

        db = Database(db, self.api.bibfiles)
        with capture(db.recompute, reload_priorities=self.api.bibfiles) as out:
            self.assertEqual(len(out.splitlines()), 34)
        with capture(db.is_uptodate, self.api.bibfiles[1:], verbose=True) as out:
            self.assertEqual(len(out.splitlines()), 3)
        db.to_bibfile(self.tmp_path('out.bib'))
        db.to_csvfile(self.tmp_path('out.csv'))
        db.to_replacements(self.tmp_path('out.json'))
        self.assertEqual(db.to_hhmapping(), {'s:Karang:Tati-Harzani': 41999})
        with capture(db.trickle) as out:
            self.assertIn('2 changed 1 added in a', out)
        key, (entrytype, fields) = db[('b.bib', 'arakawa97')]
        self.assertEqual(entrytype, 'article')
        self.assertEqual(fields['volume'], '16')
        with capture(db.stats) as out:
            pass

        for attr in ['splits', 'merges', 'identified', 'combined']:
            with capture(getattr(db, 'show_' + attr)) as out:
                pass

    def test_markconcservative(self):
        from pyglottolog.monsterlib._libmonster import markconservative

        res = markconservative(
            {1: ('article', {'title': 'Grammar'})},
            self.api.hhtypes.triggers,
            {1: ('article', {'title': 'Grammar'})},
            self.api.hhtypes,
            self.tmp_path('marks.txt'),
            verbose=False)
        self.assertEqual(res[1][1]['hhtype'].split()[0], 'grammar')

        # If a higher hhtype is computed, this cancels out previous computations.
        res = markconservative(
            {1: ('article', {'title': 'grammar', 'lgcode': 'abc'})},
            self.api.hhtypes.triggers,
            {1: ('article', {'title': 'other', 'hhtype': 'other', 'lgcode': 'abc'})},
            self.api.hhtypes,
            self.tmp_path('marks.txt'),
            verbose=False)
        self.assertNotIn('hhtype', res[1][1])

    def test_markall(self):
        from pyglottolog.monsterlib._libmonster import markall

        bib = {
            1: ('article', {'title': "other grammar of lang"}),
            2: ('article', {'title': "grammar of lang and dial"}),
            3: ('article', {'title': "other"}),
            4: ('article', {'title': "grammar and phonologie and morphologie"})
        }
        hht = self.api.hhtypes
        markall(bib, hht.triggers, verbose=False, rank=lambda l: hht[l].rank)
        self.assertIn('grammar', bib[1][1]['hhtype'])
        self.assertIn('morphologie and phonologie;grammar', bib[4][1]['hhtype'])

        markall(bib, self.api.triggers['lgcode'], verbose=False)
        self.assertIn('language', bib[1][1]['lgcode'])

    def test_add_inlg_e(self):
        from pyglottolog.monsterlib._libmonster import add_inlg_e, INLG

        res = add_inlg_e(
            {1: ('article', {'title': 'Grammar of language'})},
            self.api.triggers[INLG],
            verbose=False)
        assert_equal(res[1][1][INLG], 'language [abc]')


def test_names():
    from pyglottolog.monsterlib._bibtex import names

    assert_equal(
        [n.last for n in names('Alfred Meier and Peter von Bohr')],
        ['Meier', 'Bohr'])


def test_undiacritic():
    from pyglottolog.monsterlib._bibtex_undiacritic import undiacritic

    if not PY2:
        return  # pragma: no cover

    for i, o in [
        ("\\cmd{äöüß}", "aouss"),
    ]:
        assert_equal(undiacritic(i), o)


def test_ulatex_decode():
    from pyglottolog.monsterlib._bibtex_escaping import ulatex_decode

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
        assert_equal(ulatex_decode(i), o)
        if r:
            assert_equal(o.encode('ulatex+utf8', errors='keep'), r)


def test_distance():
    from pyglottolog.monsterlib._bibfiles_db import distance

    assert_almost_equal(distance({}, {}), 0)
    d1 = dict(author='An Author', year='1998', title='The Title', ENTRYTYPE='article')
    for d2, dist in [
        ({}, 1.0),
        (d1, 0),
        (dict(author='An Author'), 0),
        (dict(author='Another Author'), 0.2173),
        (dict(author='An Author', title='Another Title'), 0.13636),
    ]:
        assert_almost_equal(distance(d1, d2), dist, places=3)


def test_keyid():
    from pyglottolog.monsterlib._libmonster import keyid

    for fields, res in [
        ({}, '__missingcontrib__'),
        (dict(author='An Author'), 'author_no-titlend'),
        (dict(editor='An Author'), 'author_no-titlend'),
        (dict(author='An Author', title='A rather long title'), 'author_rather-longnd'),
        (dict(author='An Author', title='Title', year='2014'), 'author_title2014'),
        (dict(author='An Author', volume='IV'), 'author_no-titleivnd'),
        (dict(author='An Author', extra_hash='a'), 'author_no-titlenda'),
    ]:
        assert_equal(keyid(fields, {}), res)

    with capture(keyid, dict(author='An Author and '), {}) as out:
        assert 'Unparsed' in out


def test_pyear():
    from pyglottolog.monsterlib._libmonster import pyear

    for year, res in [
        ('', '[nd]'),
        ('1931', '1931'),
        ('1931-32', '1931-1932'),
    ]:
        assert_equal(pyear(year), res)


def test_pagecount():
    from pyglottolog.monsterlib._libmonster import pagecount

    for pages, res in [
        ('', ''),
        ('1', '1'),
        ('10-20', '11'),
        ('10-20,v-viii', '4+11'),
        ('20,viii', '8+20'),
        ('10-2', '3'),  # interpreted as 10-12
    ]:
        assert_equal(pagecount(pages), res)


def test_lgcode():
    from pyglottolog.monsterlib._libmonster import lgcode

    for lgcode_, codes in [
        ('', []),
        ('[abc]', ['abc']),
        ('abc,NOCODE_Abc', ['abc', 'NOCODE_Abc']),
    ]:
        assert_equal(lgcode((None, dict(lgcode=lgcode_))), codes)


def test_grp2fd():
    from pyglottolog.monsterlib._libmonster import grp2fd

    l = [(1, 2), (1, 3), (2, 4), (1, 5)]
    assert_equal(grp2fd(l), {1: {2: 1, 3: 1, 5: 1}, 2: {4: 1}})
