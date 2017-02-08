# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase

from clldutils.testing import WithTempDir
from clldutils import jsonlib

from pyglottolog.tests.util import WithApi


class TestGlottocodes(WithTempDir):
    def test_Glottocodes(self):
        from pyglottolog.languoids import Glottocodes

        gcjson = self.tmp_path('glottocodes.json')
        jsonlib.dump({}, gcjson)

        glottocodes = Glottocodes(gcjson)
        gc = glottocodes.new('a', dry_run=True)
        self.assertTrue(gc.startswith('aaaa'))
        self.assertNotIn(gc, glottocodes)
        gc = glottocodes.new('a')
        self.assertIn(gc, glottocodes)
        # make sure it's also written to file:
        self.assertIn(gc, Glottocodes(gcjson))


class Tests(TestCase):
    def test_es(self):
        from pyglottolog.languoids import EndangermentStatus

        self.assertEqual(
            EndangermentStatus.critical,
            EndangermentStatus.from_name('Critically endangered'))

    def test_pattern(self):
        from pyglottolog.languoids import Glottocode

        pattern = Glottocode.pattern
        for valid in [
            'abcd1234',
            'a12d3456',
        ]:
            self.assertIsNotNone(pattern.match(valid))

        for invalid in [
            'abcd123',
            '12d3456',
            'aNOCODE',
            'NOCODE_abd',
            'nocode',
        ]:
            self.assertIsNone(pattern.match(invalid))

    def test_init(self):
        from pyglottolog.languoids import Glottocode

        with self.assertRaises(ValueError):
            Glottocode('a2')


class TestLanguoid(WithApi):
    def test_factory(self):
        from pyglottolog.languoids import Languoid, Level

        f = Languoid.from_dir(self.api.tree.joinpath('abcd1234'))
        self.assertEqual(f.category, 'Family')
        l = Languoid.from_dir(self.api.tree.joinpath(f.id, 'abcd1235'))
        self.assertEqual(l.name, 'language')
        self.assertIn('abcd1235', repr(l))
        self.assertIn('language', '%s' % l)
        self.assertEqual(l.level, Level.language)
        self.assertAlmostEqual(l.latitude, 0.5)
        self.assertAlmostEqual(l.longitude, 0.5)
        l.latitude, l.longitude = 1.0, 1.0
        self.assertAlmostEqual(l.latitude, 1.0)
        self.assertAlmostEqual(l.longitude, 1.0)
        self.assertEqual(l.iso_code, 'abc')
        l.iso_code = 'cde'
        self.assertEqual(l.iso, 'cde')
        self.assertEqual(l.hid, 'abc')
        l.hid = 'abo'
        self.assertEqual(l.hid, 'abo')
        self.assertEqual(l.id, 'abcd1235')
        self.assertEqual(l.macroareas, ['a', 'b'])
        l.macroareas = ['a']
        self.assertEqual(l.macroareas, ['a'])
        self.assertEqual(l.parent, f)
        self.assertEqual(f.children[0], l)
        self.assertEqual(l.children[0].family, f)
        l.write_info(self.tmp_path('new').as_posix())

    def test_isolate(self):
        from pyglottolog.languoids import Languoid

        l = Languoid.from_dir(self.api.tree.joinpath('isol1234'))
        self.assertTrue(l.isolate)
        self.assertIsNone(l.parent)
        self.assertIsNone(l.family)

    def test_attrs(self):
        from pyglottolog.languoids import Languoid, Level

        l = Languoid.from_name_id_level('name', 'abcd1235', Level.language, hid='NOCODE')
        l.name = 'other'
        self.assertEqual(l.name, 'other')
        with self.assertRaises(ValueError):
            l.glottocode = 'x'
        with self.assertRaises(ValueError):
            l.id = 'x'
        self.assertEqual(l.id, l.glottocode)
        self.assertEqual(l.hid, 'NOCODE')
