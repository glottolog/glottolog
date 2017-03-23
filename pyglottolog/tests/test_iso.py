# coding: utf8
from __future__ import unicode_literals, print_function, division

from mock import patch, Mock

from pyglottolog.tests.util import WithApi


class Tests(WithApi):
    def test_bibtex(self):
        from pyglottolog.iso import bibtex

        with patch(
                'pyglottolog.iso.requests',
                Mock(get=Mock(return_value=Mock(content=HTML)))):
            self.assertEqual(bibtex(self.api, Mock()), 2)


HTML = """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<body>
<div id="main">
<h1>ISO 639-3 Index of All Past Change Requests</h1>
<table  width="100%" class="stripeMe">
<tr VALIGN="TOP">
   <th ALIGN="LEFT">CR Number</th>
   <th ALIGN="LEFT">Region</th>
   <th ALIGN="LEFT">Language Family</th>
   <th ALIGN="LEFT">Affected Identifier</th>
   <th ALIGN="LEFT">Language Name</th>
   <th ALIGN="LEFT">Change Type</th>
        <th ALIGN="LEFT">Outcome/<br>Effective date</th>
   <th ALIGN="LEFT" WIDTH="10%"></th>
</tr>
    <tr VALIGN="TOP">
        <td>2006-001</td>
        <td>Europe, Western</td>
        <td>Deaf sign language</td>
        <td>bvs</td>
        <td>
            Belgian Sign Language
        </td>
        <td>Split</td>
        <td>Adopted<br>2007-07-18 </td>
        <td><a HREF="chg_detail.asp?id=2006-001&lang=bvs">more ...</a></td>
    </tr>
    <tr VALIGN="TOP">
        <td>2006-001</td>
        <td>Europe, Western</td>
        <td>Deaf sign language</td>
        <td>sfb</td>
        <td>
            Langue des signes de Belgique Francophone
        </td>
        <td>Create</td>
        <td>Adopted<br>2007-07-18 </td>
        <td><a HREF="chg_detail.asp?id=2006-001&lang=sfb">more ...</a></td>
    </tr>
    <tr VALIGN="TOP">
        <td>2006-023</td>
        <td>Asia, South</td>
        <td>Kuki-Chin-Naga</td>
        <td>flm</td>
        <td>
            Falam Chin
        </td>
        <td>Split</td>
        <td>Adopted<br>2007-07-18 </td>
        <td><a HREF="chg_detail.asp?id=2006-023&lang=flm">more ...</a></td>
    </tr>
</table>
</div>
</body>
</html>
"""
