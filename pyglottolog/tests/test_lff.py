# coding: utf8
from __future__ import unicode_literals

from clldutils.testing import capture
from clldutils.path import walk

from pyglottolog.lff import read_lff, rmtree, lff2tree, tree2lff
from pyglottolog.languoids import Level
from pyglottolog.tests.util import WithApi


class TestsWithFiles(WithApi):
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

    def _set_lff(self, content, name):
        with self.api.build_path(name).open('w', encoding='utf8') as fp:
            fp.write(content)
        return content

    def test_lff2tree(self):
        lfftext = self._set_lff("""# -*- coding: utf-8 -*-
Abkhaz-Adyge [abkh1242]
    Ubykh [ubyk1235][uby]
Abkhaz-Adyge [abkh1242], Abkhaz-Abaza [abkh1243]
    Abaza [abaz1241][abq]
    Abkhazian [abkh1244][abk]
Abkhaz-Adyge [abkh1242], Circassian [circ1239]
    Adyghe [adyg1241][ady]
    Kabardian [kaba1278][kbd]
""", 'lff.txt')

        dfftext = self._set_lff("""# -*- coding: utf-8 -*-
Abaza [abaz1241]
    Ashkaraua [ashk1247][]
    Bezshagh [bezs1238][]
    Tapanta [tapa1256][]
Abkhazian [abkh1244]
    Abzhui [abzh1238][]
    Bzyb [bzyb1238][]
    Samurzakan [samu1242][]
""", 'dff.txt')

        lff2tree(self.api)
        self.assertEqual(self.api.languoid('ashk1247').level, Level.dialect)
        self.assertEqual(self.api.languoid('abaz1241').level, Level.language)
        self.assertEqual(self.api.languoid('abaz1241').hid, 'abq')

        self._set_lff(lfftext.replace('Abkhaz-Abaza', 'Abkhaz-Abazzza'), 'lff.txt')
        lff2tree(self.api)
        glottocodes = [d.name for d in walk(self.api.tree, mode='dirs')]
        self.assertEqual(len(glottocodes), len(set(glottocodes)))
        self.assertEqual(self.api.languoid('abkh1243').name, 'Abkhaz-Abazzza')

        lfftext = self._set_lff("""# -*- coding: utf-8 -*-
Abkhaz-Adyge [abkh1242]
    Ubykh [ubyk1235][uby]
Abkhaz-Adyge [abkh1242], Abkhaz-Abaza [abkh1243], Abaza [abaz1241]
    Ashkaraua [ashk1247][xyz]
    Abkhazian [abkh1244][abk]
Abkhaz-Adyge [abkh1242], Circassian [circ1239]
    Adyghe [adyg1241][ady]
    Kabardian [kaba1278][kbd]
Abkhaz-Adyge [abkh1242], Circassian [circ1239], New Group []
    New name [][NOCODE_New-name]
    Another one [][aaa]
""", 'lff.txt')

        dfftext = self._set_lff("""# -*- coding: utf-8 -*-
Abaza [abaz1241]
    Bezshagh [bezs1238][]
    Tapanta [tapa1256][]
Abkhazian [abkh1244]
    Abzhui [abzh1238][]
    Bzyb [bzyb1238][]
    Samurzakan [samu1242][]
None [xyzz1234]
    Dia [][]
""", 'dff.txt')

        with capture(lff2tree, self.api) as out:
            self.assertIn('missing language referenced', out)
        self.assertEqual(self.api.languoid('abaz1241').level, Level.family)
        self.assertEqual(self.api.languoid('aaa').name, 'Another one')
        langs = list(self.api.languoids())
        self.assertIn('newg1234', self.api.glottocodes)
        self.assertEqual(len([l for l in langs if l.name == 'New Group']), 1)
        self.assertEqual(len([l for l in langs if l.hid == 'NOCODE_New-name']), 1)
        tree2lff(self.api)

    def test_read_lff_error(self):
        _lff = """
Name [ac1234], Name2 [abcd1235]
   Lang [abcd1236][abc]
"""
        with self.assertRaises(ValueError):
            list(read_lff(self.api, {}, Level.language, _lff.split('\n')))
