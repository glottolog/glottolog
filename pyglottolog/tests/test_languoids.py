# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase

from clldutils.testing import WithTempDir
from clldutils import jsonlib

from pyglottolog.tests.util import WithApi
from pyglottolog.languoids import Languoid, EndangermentStatus
from pyglottolog.objects import Glottocodes, Glottocode, Level, Country, Macroarea


class TestGlottocodes(WithTempDir):
    def test_Glottocodes(self):
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
        self.assertEqual(len(list(Glottocodes(gcjson))), 1)


class Tests(TestCase):
    def test_es(self):
        self.assertEqual(
            EndangermentStatus.critical,
            EndangermentStatus.get('Critically endangered'))

    def test_pattern(self):
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

    def test_Country(self):
        self.assertEqual(Country.from_text('Germany').id, 'DE')
        self.assertIsNone(Country.from_name('abcdefg'))
        self.assertIsNone(Country.from_id('abcdefg'))

    def test_init(self):
        with self.assertRaises(ValueError):
            Glottocode('a2')


class TestLanguoid(WithApi):
    def test_Level(self):
        self.assertGreater(Level.dialect, Level.language)
        self.assertEqual(Level.language, self.api.languoid('abcd1235').level)
        with self.assertRaises(ValueError):
            Level.get('abcde')

    def test_factory(self):
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

        self.assertEqual(len(l.macroareas), 2)
        l.macroareas = [Macroarea.africa]
        self.assertEqual(l.macroareas, [Macroarea.africa])

        l.countries = self.api.countries[:2]
        self.assertEqual(len(l.countries), 2)

        self.assertEqual(l.parent, f)
        self.assertEqual(f.children[0], l)
        self.assertEqual(l.children[0].family, f)
        l.write_info(self.tmp_path().as_posix())
        self.assertTrue(self.tmp_path('abcd1235').exists())
        self.assertIsInstance(
            self.api.languoid('abcd1235').iso_retirement.asdict(), dict)
        self.assertIsNone(l.classification_comment)
        l.endangerment = 'Critically endangered'
        self.assertEqual(l.endangerment, EndangermentStatus.critical)
        self.assertEqual(l.names, {})
        l.cfg['altnames'] = {'glottolog': 'xyz'}
        self.assertIn('glottolog', l.names)
        self.assertEqual(l.identifier, {})
        l.cfg['identifier'] = {'multitree': 'xyz'}
        self.assertIn('multitree', l.identifier)

    def test_isolate(self):
        l = Languoid.from_dir(self.api.tree.joinpath('isol1234'))
        self.assertTrue(l.isolate)
        self.assertIsNone(l.parent)
        self.assertIsNone(l.family)

    def test_attrs(self):
        l = Languoid.from_name_id_level(
            self.api.tree, 'name', 'abcd1235', Level.language, hid='NOCODE')
        l.name = 'other'
        self.assertEqual(l.name, 'other')
        with self.assertRaises(AttributeError):
            l.glottocode = 'x'
        with self.assertRaises(AttributeError):
            l.id = 'x'
        self.assertEqual(l.id, l.glottocode)
        self.assertEqual(l.hid, 'NOCODE')
