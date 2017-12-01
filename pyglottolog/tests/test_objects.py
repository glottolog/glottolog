from __future__ import unicode_literals

import unittest


class Tests(unittest.TestCase):

    def test_legacy_imports(self):
        from pyglottolog.api import Glottolog
        from pyglottolog.objects import Glottocode, Level, Reference
