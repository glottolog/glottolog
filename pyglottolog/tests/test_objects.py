# coding: utf8
from __future__ import unicode_literals, print_function, division
from unittest import TestCase

from mock import Mock


class Tests(TestCase):
    def test_Reference(self):
        from pyglottolog.objects import Reference

        ref = Reference('bib:key', '12-34', 'German')
        self.assertEqual('{0}'.format(ref), '**bib:key**:12-34<trigger "German">')
        Reference.from_list(['{0}'.format(ref)])

        with self.assertRaises(ValueError):
            Reference.from_list(['abc'])

    def test_ClassificationComment(self):
        from pyglottolog.objects import ClassificationComment

        cc = ClassificationComment(family='**bib:key**')
        log = Mock()
        cc.check(Mock(), [], log)
        self.assertTrue(log.error.called)
        log = Mock()
        cc.check(Mock(), ['bib:key'], log)
        self.assertFalse(log.error.called)

    def test_EndangermentStatus(self):
        from pyglottolog.objects import EndangermentStatus

        c = EndangermentStatus.critical
        self.assertEqual(EndangermentStatus.get(c), c)

        with self.assertRaises(ValueError):
            EndangermentStatus.get(123)

    def test_EthnologueComment(self):
        from pyglottolog.objects import EthnologueComment

        with self.assertRaises(ValueError):
            EthnologueComment('abc', 't')

        with self.assertRaises(ValueError):
            EthnologueComment('abc', 'missing', 'E15')

        with self.assertRaises(ValueError):
            EthnologueComment('abc', 'missing', 'E16')

        with self.assertRaises(ValueError):
            EthnologueComment('abc', 'missing', 'E16', 'äöü'.encode('utf8'))

        log = Mock()
        ec = EthnologueComment('abc', 'missing', 'E16', 'abc')
        ec.check(Mock(), [], log)
        self.assertFalse(log.error.called)

        log = Mock()
        ec = EthnologueComment('abc', 'missing', 'E16', '**bib:key**')
        ec.check(Mock(), [], log)
        self.assertTrue(log.error.called)
