# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.testing import capture

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_paths(self):
        self.assert_(self.api.ftsindex)

    def test_languoid(self):
        self.assertEqual(self.api.languoid('abc').name, 'language')

    def test_languoids(self):
        from pyglottolog.languoids import Level

        self.assertEqual(len(list(self.api.languoids())), 4)
        self.assertEqual(len(list(self.api.languoids(maxlevel=Level.family))), 1)
        self.assertEqual(len(list(self.api.languoids(maxlevel=Level.language))), 3)
        self.assertEqual(len(self.api.languoids_by_code()), 7)
        self.assertIn('NOCODE_Family-name', self.api.languoids_by_code())

    def test_load_triggers(self):
        self.assertEqual(len(self.api.triggers), 2)

    def test_macroarea_map(self):
        self.assertEqual(self.api.macroarea_map['abc'], 'Eurasia')

    def test_bibfiles(self):
        c = self.api.bibfiles
        with capture(c.roundtrip_all) as out:
            self.assertIn('a.bib', out)
        with capture(c['b.bib'].show_characters) as out:
            self.assertIn('CJK UNIFIED IDEOGRAPH', out)
        abib = c[0]
        self.assertEqual(len(list(abib.iterentries())), 3)
        assert abib.size
        assert abib.mtime
