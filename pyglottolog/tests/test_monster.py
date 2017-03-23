# coding: utf8
from __future__ import unicode_literals, print_function, division

from six import PY2
from clldutils.testing import capture
from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_main(self):
        from pyglottolog.monster import compile

        if not PY2:  # pragma: no cover
            return

        with capture(compile, self.api) as out:
            self.assertEqual(len(out.splitlines()), 43)
            self.assertIn('2 splitted', out)
            self.assertIn('2 merged', out)
