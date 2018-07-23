from __future__ import unicode_literals

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
            Panará          </td>
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
        """
        """
    ]
    return read_url


def test_Retirement(iso_data):
    res = list(iso.Retirement.iter())
    assert len(res) == 6


def test_ChangeRequest(iso_data):
    iso.read_url(None)
    res = list(iso.ChangeRequest.iter(max_year=2007))
    print(res)
    assert len(res) == 2
    assert res[0].url == 'https://iso639-3.sil.org/request/2006-020'
    assert res[0].pdf == 'https://iso639-3.sil.org/sites/iso639-3/files/change_requests/2006/2006-020.pdf'
    assert res[0].year == '2006'

    _, (_, fields) = iso.change_request_as_source(res[0].Change_Request_Number, [res[0]], {})
    assert 'title' in fields


def test_bibtex(api_copy, iso_data, mocker):
    iso.read_url(None)
    assert iso.bibtex(api_copy, mocker.Mock(), max_year=2007) == 2


def test_get_retirements(iso_data):
    res = iso.get_retirements(max_year=2007)
