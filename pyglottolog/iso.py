from __future__ import unicode_literals

import os
import re
import json
import itertools
from datetime import date

import attr
from clldutils import iso_639_3
from csvw import dsv

from .references.bibtex import save

RET_REASON = {  # http://www-01.sil.org/iso639-3/download.asp#retiredDownloads
    'C': 'change',
    'D': 'duplicate',
    'N': 'non-existent',
    'S': 'split',
    'M': 'merge',
}

ISO_CODE_PATTERN = re.compile('[a-z]{3}$')


def read_url(path):
    """
    Delegate scraping to clldutils, since nowadays this requires tweaking the user agent as well.
    """
    with iso_639_3._open(path) as fp:
        return fp.read().decode('utf8')


def valid_iso_code(instance, attr, value):
    if not ISO_CODE_PATTERN.match(value):
        raise ValueError('invalid ISO code in {0}: {1}'.format(attr.name, value))


@attr.s
class Retirement(object):
    Id = attr.ib(validator=valid_iso_code)
    Ref_Name = attr.ib()
    Ret_Reason = attr.ib(convert=lambda v: RET_REASON[v])
    Change_To = attr.ib(
        convert=lambda v: v or None,
        validator=attr.validators.optional(valid_iso_code))
    Ret_Remedy = attr.ib()
    Effective = attr.ib(convert=lambda v: date(*[int(p) for p in v.split('-')]) if v else None)
    cr = attr.ib(default=None)

    @classmethod
    def iter(cls):
        content = read_url('sites/iso639-3/files/downloads/iso-639-3_Retirements.tab')
        for d in dsv.reader(content.splitlines(), dicts=True, delimiter='\t'):
            yield cls(**d)


@attr.s
class ChangeRequest(object):
    Status = attr.ib(
        validator=attr.validators.in_(['Rejected', 'Adopted', 'Pending', 'Partially Adopted', 'NA']))
    Reference_Name = attr.ib()
    Effective_Date = attr.ib(convert=lambda v: date(*[int(p) for p in v.split('-')]) if v else None)
    Change_Type = attr.ib(
        validator=attr.validators.in_(['Create', 'Merge', 'Retire', 'Split', 'Update', 'NA']))
    Change_Request_Number = attr.ib()
    Region_Group = attr.ib()
    Affected_Identifier = attr.ib()
    Language_Family_Group = attr.ib()

    @classmethod
    def empty(cls):
        attrs = {f.name: None for f in attr.fields(cls)}
        attrs.update(Status='NA', Change_Type='NA')
        return cls(**attrs)

    @property
    def url(self):
        return iso_639_3.BASE_URL + 'request/' + self.Change_Request_Number

    @property
    def year(self):
        return self.Change_Request_Number.split('-')[0]

    @property
    def pdf(self):
        return '{0}sites/iso639-3/files/change_requests/{1}/{2}.pdf'.format(
            iso_639_3.BASE_URL, self.year, self.Change_Request_Number)

    @classmethod
    def iter(cls, max_year=None):
        path = "code_changes/change_request_index/data/{0}?" \
               "field_change_request_region_grp_tid=All&field_change_request_lf_group_tid=All&" \
               "field_change_instance_chnge_type_tid=All&field_change_request_act_status_tid=All&" \
               "items_per_page=100&page={1}"
        year, page = 2006, 0
        while year < (max_year or date.today().year):
            while True:
                i = 0
                for i, cr in enumerate(list(_iter_tables(read_url(path.format(year, page))))[0]):
                    yield cls(**{k.replace(' ', '_'): v for k, v in cr.items()})
                if i < 99:
                    break
                page += 1
            year += 1
            page = 0


def change_request_as_source(id_, rows, ref_ids):
    title = "Change Request Number {0}: ".format(id_)
    title += ", ".join(
        "{0} {1} [{2}]".format(r.Status, r.Change_Type.lower(), r.Affected_Identifier) for r in rows
    )
    date = None
    for row in rows:
        if date and row.Effective_Date:
            assert date == row.Effective_Date
        else:
            date = row.Effective_Date
    if date:
        title += ' ({0})'.format(date.isoformat())
    fields = {
        'number': id_,
        'title': title,
        'howpublished': rows[0].url,
        'address': "Dallas",
        'author': "ISO 639-3 Registration Authority",
        'publisher': "SIL International",
        'url': rows[0].pdf,
        'year': rows[0].year,
        'hhtype': "overview",
        'lgcode': ', '.join(
            "{0} [{1}]".format(r.Reference_Name, r.Affected_Identifier) for r in rows),
        'src': "iso6393",
    }
    if id_ in ref_ids and ref_ids[id_]:
        fields['glottolog_ref_id'] = ref_ids[id_]
    return id_, ('misc', fields)


def bibtex(api, log, max_year=None):
    """Create a BibTeX file listing records for each past ISO 639-3 change request.

    http://www-01.sil.org/iso639-3/chg_requests.asp?order=CR_Number&chg_status=past
    """
    bib = api.bibfiles['iso6393.bib']
    glottolog_ref_ids = bib.glottolog_ref_id_map

    entries = []
    grouped = itertools.groupby(
        sorted(ChangeRequest.iter(max_year=max_year), key=lambda cr: cr.Change_Request_Number),
        lambda cr: cr.Change_Request_Number)
    for id_, rows in grouped:
        entries.append(change_request_as_source(id_, list(rows), glottolog_ref_ids))
    save(entries, bib.fname, None)
    log.info('bibtex written to {0}'.format(bib.fname))
    return len(entries)


def _read_table(table):
    def _text(e):
        if e.find('span') is not None:
            return _text(e.find('span'))
        if e.find('a') is not None:
            return _text(e.find('a'))
        return e.text or ''

    from xml.etree import ElementTree as et

    d = et.fromstring(table)
    header = [e.text.strip() for e in d.findall('.//th')]
    for tr in d.find('tbody').findall('.//tr'):
        yield dict(zip(header, [_text(e).strip() for e in tr.findall('.//td')]))



def _iter_tables(html):
    start, end = '<table ', '</table>'
    while start in html:
        html = html.split(start, 1)[1]
        table, html = html.split(end, 1)
        yield _read_table(start + table + end)


def code_details(code):
    res = {}
    try:
        for md in _iter_tables(read_url('code/{0}'.format(code))):
            res.update(list(md)[0])
    except:
        pass
    return res


def get_retirements(scrape_missing_remedies=True, max_year=None):
    # retired iso_codes
    rets = list(Retirement.iter())

    # latest adopted change request affecting each iso_code
    crs = (r for r in ChangeRequest.iter(max_year=max_year) if r.Status == 'Adopted')
    crs = sorted(crs, key=lambda r: (r.Affected_Identifier, r.Effective_Date or date.today()))
    crs = itertools.groupby(crs, lambda r: r.Affected_Identifier)
    crs = {id_: list(grp)[-1] for id_, grp in crs}

    # left join
    for ret in rets:
        ret.cr = crs.get(ret.Id, ChangeRequest.empty())

    # fill Change_To from Ret_Remedy for splits and make it a list for others
    assert all(bool(r.Change_To) == (r.Ret_Reason not in ('split', 'non-existent')) for r in rets)
    assert all(bool(r.Ret_Remedy) == (r.Ret_Reason == 'split') for r in rets)
    iso = re.compile(r'\[([a-z]{3})\]')
    for r in rets:
        if r.Ret_Reason == 'split':
            r.Change_To = iso.findall(r.Ret_Remedy)
        else:
            r.Change_To = [r.Change_To] if r.Change_To else []

    if scrape_missing_remedies:  # get remedies for non-splits

        def get_detail_pages(iso_codes, rebuild=True, cache='iso_detail_pages.json'):
            if rebuild or not os.path.exists(cache):
                result = {code: code_details(code) for code in iso_codes}
                with open(cache, 'w') as f:
                    json.dump(result, f)
            with open(cache) as f:
                return json.load(f)

        iso_codes = [r.Id for r in rets if r.Ret_Reason != 'split']
        pages = get_detail_pages(iso_codes)
        for r in rets:
            if not r.Ret_Remedy and r.Id in pages:
                r.Ret_Remedy = pages[r.Id].get('Retirement Remedy')

    return rets


def retirements(api, log):
    fields = [
        ('Id', 'code'), ('Ref_Name', 'name'),
        ('CR_Number', 'change_request'), ('Effective', 'effective'),
        ('Ret_Reason', 'reason'), ('Change_To', 'change_to'),
        ('Ret_Remedy', 'remedy'),
    ]
    iso2lang = {l.iso: l for l in api.languoids() if l.iso}
    for r in get_retirements():
        lang = iso2lang.get(r.Id)
        if lang is None:
            print('--- Missing retired ISO code: {}'.format(r.Id))
            print(r)
            continue
        for iso in r.Change_To:
            if iso not in iso2lang:
                print('+++ Missing change_to ISO code: {}'.format(iso))
                print(r)
                #continue
        for f, option in fields:
            lang.cfg.set('iso_retirement', option, getattr(r, f))
        lang.write_info()
    """
    [iso_retirement]
    comment = Interlingue is the later name (currently in use) for this language, created by
        Edgar de Wahl. The [ile] identifier is in ISO 639-2 (as well as ISO 639-3).
        Occidental should be added as another name associated with [ile].
    code = occ
    name = Occidental
    effective = 2007-07-18
    reason = duplicate
    remedy = Merge into Interlingue [ile] as Duplicate
    change_request = 2006-090
    """
