# coding: utf-8
from __future__ import unicode_literals
import contextlib

from six import BytesIO
import pytest

from pyglottolog import iso


@pytest.fixture
def iso_data(mocker):
    read_url = mocker.patch('pyglottolog.iso.read_url')
    read_url.side_effect = [
        """\
Id	Ref_Name	Ret_Reason	Change_To	Ret_Remedy	Effective
fri	Western Frisian	C	fry		2007-02-01
auv	Auvergnat	M	oci		2007-03-14
gsc	Gascon	M	oci		2007-03-14
lms	Limousin	M	oci		2007-03-14
lnc	Languedocien	M	oci		2007-03-14
bvs	Belgian Sign Language	S		Split into Langue [sfb], and Gebarentaal [vgt]	2007-07-18\
""",
        """\
      <div class="table-responsive">
<table class="views-table cols-8 table table-hover table-striped" >
        <thead>
      <tr>
                  <th class="views-field views-field-title" >
            Change Request Number          </th>
                  <th class="views-field views-field-field-change-request-lf-group" >
            Language Family Group          </th>
                  <th class="views-field views-field-field-change-request-region-grp" >
            Region Group          </th>
                  <th class="views-field views-field-nothing" >
            Affected Identifier          </th>
                  <th class="views-field views-field-nothing-1" >
            Reference Name          </th>
                  <th class="views-field views-field-field-change-instance-chnge-type" >
            Change Type          </th>
                  <th class="views-field views-field-field-change-instance-act-status" >
            Status          </th>
                  <th class="views-field views-field-field-change-request-efctve-date" >
            Effective Date          </th>
              </tr>
    </thead>
    <tbody>
          <tr class="odd views-row-first">
                  <td class="views-field views-field-title" >
            <a href="/request/2006-020"><a href="/request/2006-020">2006-020</a></a>          </td>
                  <td class="views-field views-field-field-change-request-lf-group" >
            Unclassified          </td>
                  <td class="views-field views-field-field-change-request-region-grp" >
            America, South          </td>
                  <td class="views-field views-field-nothing" >
            <a href="/code/xwa">xwa</a>          </td>
                  <td class="views-field views-field-nothing-1" >
            Kwaza          </td>
                  <td class="views-field views-field-field-change-instance-chnge-type" >
            Create          </td>
                  <td class="views-field views-field-field-change-instance-act-status" >
            Adopted          </td>
                  <td class="views-field views-field-field-change-request-efctve-date" >
            <span class="date-display-single">2007-07-18</span>          </td>
              </tr>
          <tr class="even">
                  <td class="views-field views-field-title" >
            <a href="/request/2006-019"><a href="/request/2006-019">2006-019</a></a>          </td>
                  <td class="views-field views-field-field-change-request-lf-group" >
            Macro-Ge          </td>
                  <td class="views-field views-field-field-change-request-region-grp" >
            America, South          </td>
                  <td class="views-field views-field-nothing" >
            <a href="/code/kre">kre</a>          </td>
                  <td class="views-field views-field-nothing-1" >
            Panar          </td>
                  <td class="views-field views-field-field-change-instance-chnge-type" >
            Update          </td>
                  <td class="views-field views-field-field-change-instance-act-status" >
            Adopted          </td>
                  <td class="views-field views-field-field-change-request-efctve-date" >
            <span class="date-display-single">2007-07-18</span>          </td>
              </tr>
</tbody>
</table>              
</div>""",
        """\
<div><table class="views-table cols-7 table table-hover table-striped" >
         <thead>
      <tr>
                  <th class="views-field views-field-title" >
            Identifier          </th>
                  <th class="views-field views-field-field-iso639-language-names" >
            Language Name(s)          </th>
                  <th class="views-field views-field-field-iso639-element-status" >
            Status          </th>
                  <th class="views-field views-field-field-iso639-code-set-membership" >
            Code Sets          </th>
                  <th class="views-field views-field-field-iso639-element-scope" >
            Scope          </th>
                  <th class="views-field views-field-field-iso639-language-type" >
            Language Type          </th>
                  <th class="views-field views-field-field-iso639-denotation-urls" >
            Denotations          </th>
              </tr>
    </thead>
    <tbody>
          <tr class="odd views-row-first views-row-last">
                  <td class="views-field views-field-title" >
            <a href="/code/aam" class="active">aam</a>          </td>
                  <td class="views-field views-field-field-iso639-language-names" >
            Aramanik          </td>
                  <td class="views-field views-field-field-iso639-element-status" >
            Deprecated          </td>
                  <td class="views-field views-field-field-iso639-code-set-membership" >
            639-3          </td>
                  <td class="views-field views-field-field-iso639-element-scope" >
            Individual          </td>
                  <td class="views-field views-field-field-iso639-language-type" >
            Living          </td>
                  <td class="views-field views-field-field-iso639-denotation-urls" >
            <a href="https://www.ethnologue.com/language/aam" target="_blank">Ethnologue</a>, <a href="http://glottolog.org/glottolog?iso=aam" target="_blank">Glottolog</a>, <a href="http://www.multitree.org/codes/aam.html" target="_blank">Multitree</a>, <a href="https://en.wikipedia.org/wiki/ISO_639:aam" target="_blank">Wikipedia</a>          </td>
              </tr>
      </tbody>
</table>
<table class="views-table cols-7 table table-hover table-striped" >
         <thead>
      <tr>
                  <th class="views-field views-field-field-change-instance-req-number" >
            Change Request Number          </th>
                  <th class="views-field views-field-field-change-instance-effctv-dte" >
            Effective Date          </th>
                  <th class="views-field views-field-field-change-instance-chnge-type" >
            Change Type          </th>
                  <th class="views-field views-field-field-change-instance-chg-attr" >
            Change Attribute          </th>
                  <th class="views-field views-field-field-change-instance-old-value" >
            Old Value          </th>
                  <th class="views-field views-field-field-change-instance-new-value" >
            New Value          </th>
                  <th class="views-field views-field-field-change-instance-map-to" >
            Retirement Remedy          </th>
              </tr>
    </thead>
    <tbody>
          <tr class="odd views-row-first">
                  <td class="views-field views-field-field-change-instance-req-number" >
            <a href="/request/2014-042">2014-042</a>          </td>
                  <td class="views-field views-field-field-change-instance-effctv-dte" >
            <span class="date-display-single">2015-01-12</span>          </td>
                  <td class="views-field views-field-field-change-instance-chnge-type" >
            Merge          </td>
                  <td class="views-field views-field-field-change-instance-chg-attr" >
                      </td>
                  <td class="views-field views-field-field-change-instance-old-value" >
            Aramanik          </td>
                  <td class="views-field views-field-field-change-instance-new-value" >
                      </td>
                  <td class="views-field views-field-field-change-instance-map-to" >
            <a href="/code/aas">Merged into Aasax [aas]</a>          </td>
              </tr>
          <tr class="even views-row-last">
                  <td class="views-field views-field-field-change-instance-req-number" >
                      </td>
                  <td class="views-field views-field-field-change-instance-effctv-dte" >
            <span class="date-display-single">2013-02-18</span>          </td>
                  <td class="views-field views-field-field-change-instance-chnge-type" >
            Update          </td>
                  <td class="views-field views-field-field-change-instance-chg-attr" >
            Type          </td>
                  <td class="views-field views-field-field-change-instance-old-value" >
            Type: Living          </td>
                  <td class="views-field views-field-field-change-instance-new-value" >
            Type: Extinct          </td>
                  <td class="views-field views-field-field-change-instance-map-to" >
                      </td>
              </tr>
      </tbody>
</table></div>"""
    ]
    return read_url


def test_Retirement(iso_data):
    res = list(iso.Retirement.iter())
    assert len(res) == 6

    with pytest.raises(ValueError):
        iso.Retirement('a', 'n', 'C', '', '', '')


def test_ChangeRequest(iso_data):
    iso.read_url(None)
    res = list(iso.ChangeRequest.iter(max_year=2007))
    print(res)
    assert len(res) == 2
    assert res[0].url == 'https://iso639-3.sil.org/request/2006-020'
    assert res[0].pdf == 'https://iso639-3.sil.org/sites/iso639-3/files/change_requests/2006/2006-020.pdf'
    assert res[0].year == '2006'

    _, (_, fields) = iso.change_request_as_source(
        res[0].Change_Request_Number, [res[0]], {'2006-020': '1234567'})
    assert 'title' in fields
    assert 'glottolog_ref_id' in fields


def test_bibtex(api_copy, iso_data, mocker):
    iso.read_url(None)
    assert iso.bibtex(api_copy, mocker.Mock(), max_year=2007) == 2


def test_retirements(api_copy, iso_data, mocker):
    iso.retirements(api_copy, mocker.Mock(), max_year=2007)


def test_code_details(iso_data):
    iso.read_url(None)
    iso.read_url(None)
    details = iso.code_details('')
    assert 'Merged' in details['Retirement Remedy']


def test_get_retirements(iso_data):
    res = iso.get_retirements(max_year=2007)


def test_read_url(mocker, tmpdir):
    isolib = mocker.patch('pyglottolog.iso.iso_639_3')
    isolib._open = lambda p: contextlib.closing(BytesIO(b'abcd'))
    assert iso.read_url(None) == 'abcd'
    assert len(tmpdir.listdir()) == 0
    iso.read_url('p', cache_dir=str(tmpdir))
    assert len(tmpdir.listdir()) == 1
