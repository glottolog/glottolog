# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import read_text, write_text

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_Entry(self):
        from pyglottolog.references import Entry

        self.assertEqual(Entry.lgcodes(None), [])
        e = Entry(
            'x', 'misc', {'hhtype': 'grammar (computerized assignment from "xyz")'}, None)
        self.assertEqual(e.doctypes({'grammar': 1}), ([1], 'xyz'))

    def test_HHTypes(self):
        hht = self.api.hhtypes
        self.assertEqual(hht['grammar'].rank, 17)
        self.assertIn('grammar', hht)

        prev = None
        for t in hht:
            if prev:
                self.assertGreater(prev, t)
            prev = t

        self.assertEqual(len(hht), 2)
        self.assertIn('rank', repr(hht[0]))
        self.assertEqual(hht.parse('grammar'), ['grammar'])

    def test_BibFile(self):
        bibfile = self.api.bibfiles['a.bib']
        self.assertEqual(bibfile['a:key'].type, 'misc')
        self.assertEqual(bibfile['s:Andalusi:Turk'].key, 's:Andalusi:Turk')

        for entry in bibfile.iterentries():
            if entry.key == 'key':
                self.assertEqual(len(list(entry.languoids({'abc': 1})[0])), 1)

        with self.assertRaises(KeyError):
            bibfile['xyz']

        self.assertEqual(len(list(bibfile.iterentries())), 3)

        lines = [line for line in read_text(bibfile.fname).split('\n')
                 if not line.strip().startswith('glottolog_ref_id')]
        write_text(self.tmp_path('a.bib'), '\n'.join(lines))
        bibfile.update(self.tmp_path('a.bib'))
        self.assertEqual(len(list(bibfile.iterentries())), 3)

        bibfile.update(self.api.bibfiles['b.bib'].fname)
        self.assertEqual(len(list(bibfile.iterentries())), 1)

        def visitor(entry):
            entry.fields['new_field'] = 'a'

        bibfile.visit(visitor=visitor)
        for entry in bibfile.iterentries():
            self.assertIn('new_field', entry.fields)

        bibfile.visit(visitor=lambda e: True)
        self.assertEqual(len(bibfile.keys()), 0)

    def test_Isbns(self):
        from pyglottolog.references import Isbns, Isbn

        self.assertEqual(Isbns.from_field('9783866801929, 3866801920'),
                         [Isbn('9783866801929')])

        self.assertEqual(Isbns.from_field('978-3-86680-192-9 3-86680-192-0'),
                         [Isbn('9783866801929')])

        with self.assertRaisesRegexp(ValueError, 'pattern'):
            Isbns.from_field('9783866801929 spam, 3866801920')

        with self.assertRaisesRegexp(ValueError, 'delimiter'):
            Isbns.from_field('9783866801929: 3866801920')

        self.assertEqual(Isbns.from_field('9780199593569, 9780191739385').to_string(),
                         '9780199593569, 9780191739385')
        
    def test_Isbn(self):
        from pyglottolog.references import Isbn

        with self.assertRaisesRegexp(ValueError, 'length'):
            Isbn('978-3-86680-192-9')

        with self.assertRaisesRegexp(ValueError, 'length'):
            Isbn('03-86680-192-0')

        with self.assertRaisesRegexp(ValueError, '0 instead of 9'):
            Isbn('9783866801920')

        with self.assertRaisesRegexp(ValueError, '9 instead of 0'):
            Isbn('3866801929')

        self.assertEqual(Isbn('9783866801929').digits, '9783866801929')
        self.assertEqual(Isbn('3866801920').digits, '9783866801929')

        twins = Isbn('9783866801929'), Isbn('9783866801929')
        self.assertEqual(*twins)
        self.assertEqual(len(set(twins)), 1)
        self.assertFalse(twins[0] != twins[1])

        self.assertIn(repr(Isbn('9783866801929')),
                      ["Isbn(u'9783866801929')", "Isbn('9783866801929')"])
