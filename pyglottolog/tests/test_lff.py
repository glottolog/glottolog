# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase
from contextlib import contextmanager

from clldutils.testing import WithTempDir

from pyglottolog.lff import read_lff, rmtree, lang2tree, lff2tree, tree2lff
from pyglottolog.languoids import Level, Languoid, walk_tree


@contextmanager
def lff(text):
    yield text.split('\n')


class TestsWithFiles(WithTempDir):
    def test_rmtree(self):
        comps = []
        for i in range(100):
            comps.append('a')
            d = self.tmp_path(*comps)
            d.mkdir()
            f = d.joinpath('a.ini')
            with f.open('w', encoding='utf8') as fp:
                fp.write('a')
        assert self.tmp_path('a').exists()
        rmtree(self.tmp_path('a'))
        assert not self.tmp_path('a').exists()

    def test_lang2tree(self):
        old, new = self.tmp_path('old'), self.tmp_path('new')
        old.mkdir()
        new.mkdir()

        lang2tree(
            Languoid.from_name_id_level('name', 'abcd1234', Level.language),
            [('parent', 'abcd1233', Level.family)],
            old,
            {})
        assert old.joinpath('abcd1233', 'abcd1234', 'abcd1234.ini').exists()
        lang2tree(
            Languoid.from_name_id_level('name', 'abcd1234', Level.language),
            [('parent', 'abcd1233', Level.family)],
            new,
            {l.id: l for l in walk_tree(old)})
        assert new.joinpath('abcd1233', 'abcd1234', 'abcd1234.ini').exists()

    def test_lff2tree(self):
        old, new = self.tmp_path('old'), self.tmp_path('new')
        old.mkdir()
        new.mkdir()

        _l = """# -*- coding: utf-8 -*-
Abkhaz-Adyge [abkh1242]
    Ubykh [ubyk1235][uby]
Abkhaz-Adyge [abkh1242], Abkhaz-Abaza [abkh1243]
    Abaza [abaz1241][abq]
    Abkhazian [abkh1244][abk]
Abkhaz-Adyge [abkh1242], Circassian [circ1239]
    Adyghe [adyg1241][ady]
    Kabardian [kaba1278][kbd]
"""

        _d = """# -*- coding: utf-8 -*-
Abaza [abaz1241]
    Ashkaraua [ashk1247][]
    Bezshagh [bezs1238][]
    Tapanta [tapa1256][]
Abkhazian [abkh1244]
    Abzhui [abzh1238][]
    Bzyb [bzyb1238][]
    Samurzakan [samu1242][]
"""

        def lffs():
            return {Level.language: lff(_l), Level.dialect: lff(_d)}

        lff2tree(old, builddir=self.tmp_path('build1'), lffs=lffs())
        lff2tree(old, new, builddir=self.tmp_path('build2'), lffs=lffs())
        tree2lff(
            new,
            out_paths={
                Level.language: self.tmp_path('lff'),
                Level.dialect: self.tmp_path('dff')
            }
        )
        with self.tmp_path('lff').open() as fp:
            self.assertEqual(fp.read(), _l)

        with self.tmp_path('dff').open() as fp:
            self.assertEqual(fp.read(), _d)

        lffs_ = {Level.language: lff(_l.replace('Abaza', 'Abazul')),
                 Level.dialect: lff(_d)}
        lff2tree(old, new, builddir=self.tmp_path('build2'), lffs=lffs_)
        l = Languoid.from_dir(new.joinpath('abkh1242', 'abkh1243', 'abaz1241'))
        self.assertEqual(l.name, 'Abazul')
        self.assertEqual(l.parent.name, 'Abkhaz-Abazul')


class Tests(TestCase):
    def test_read_lff(self):
        _lff = lff("""
Name [abcd1234], Name2 [abcd1235]
   Lang [abcd1236][abc]
""")
        res = list(read_lff(Level.language, fp=_lff))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, 'Lang')
        self.assertEqual(len(res[0].lineage), 2)
        self.assertEqual(res[0].lineage[0], ('Name', 'abcd1234', Level.family))

    def test_read_lff_error(self):
        _lff = lff("""
Name [acd1234], Name2 [abcd1235]
   Lang [abcd1236][abc]
""")
        with self.assertRaises(ValueError):
            list(read_lff(Level.language, fp=_lff))
