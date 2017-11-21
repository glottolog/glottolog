from __future__ import unicode_literals

import io
import os
import re
import sys
import csv
import json
import itertools
import contextlib
import collections

PY2 = sys.version_info < (3,)

if PY2:
    from urlparse import urljoin
    from urllib2 import urlopen
else:
    from urllib.parse import urljoin
    from urllib.request import urlopen

import bs4
import requests

from pyglottolog.monsterlib._bibtex import save

BASE_URL = 'http://www-01.sil.org/iso639-3/'

RET_REASON = {  # http://www-01.sil.org/iso639-3/download.asp#retiredDownloads
    'C': 'change',
    'D': 'duplicate',
    'N': 'non-existent',
    'S': 'split',
    'M': 'merge',
}

OUTCOME_DATE = r'(?P<Outcome>Adopted|Rejected)(?P<Effective_date>2\d\d\d-[01]\d-[0-3]\d)?$'

REMEDY = (r'<td valign="top">Retirement remedy:</td>'
          r'\s*<td>\s*'
          r'(?:<a href="documentation\.asp\?id=[a-z]{3}">)?'
          r'([^<]+)'
          r'(?:</a>)?\s*</td>')


def change_request_as_source(id_, rows, ref_ids):
    title = "Change Request Number {0}: ".format(id_)
    title += ", ".join(
        "{0} {1} [{2}]".format(
            r['Outcome/Effective date'].split('20')[0].strip().lower(),
            r['Change Type'].lower(),
            r['Affected Identifier'])
        for r in rows)
    date = None
    for row in rows:
        parts = row['Outcome/Effective date'].split('20')
        if len(parts) > 1:
            if date:
                assert date == parts[1].strip()
            else:
                date = parts[1].strip()
    if date:
        title += ' ({0})'.format(date)
    fields = {
        'number': id_,
        'title': title,
        'howpublished': BASE_URL + "chg_detail.asp?id=" + id_,
        'address': "Dallas",
        'author': "ISO 639-3 Registration Authority",
        'publisher': "SIL International",
        'url': BASE_URL + "cr_files/{0}.pdf".format(id_),
        'year': id_.split('-')[0],
        'hhtype': "overview",
        'lgcode': ', '.join(
            "{0} [{1}]".format(r['Language Name'].strip(), r['Affected Identifier'])
            for r in rows),
        'src': "iso6393",
    }
    if id_ in ref_ids and ref_ids[id_]:
        fields['glottolog_ref_id'] = ref_ids[id_]
    return id_, ('misc', fields)


def iter_change_requests(log):
    def parse_row(tr, coltag):
        return [td.get_text() for td in tr.find_all(coltag)]

    url = BASE_URL + "chg_requests.asp"
    log.info('downloading {0} ...'.format(url))
    res = requests.get(url, params=dict(order='CR_Number', chg_status='past'))
    log.info('HTTP {0}'.format(res.status_code))
    table = bs4.BeautifulSoup(res.content, 'html.parser').find('table')
    cols = None
    for i, tr in enumerate(table.find_all('tr')):
        if i == 0:
            cols = parse_row(tr, 'th')
        else:
            yield dict(zip(cols, parse_row(tr, 'td')))


def bibtex(api, log):
    """Create a BibTeX file listing records for each past ISO 639-3 change request.

    http://www-01.sil.org/iso639-3/chg_requests.asp?order=CR_Number&chg_status=past
    """
    bib = api.bibfiles['iso6393.bib']
    glottolog_ref_ids = bib.glottolog_ref_id_map

    entries = []
    grouped = itertools.groupby(iter_change_requests(log), lambda c: c['CR Number'])
    for id_, rows in grouped:
        entries.append(change_request_as_source(id_, list(rows), glottolog_ref_ids))
    save(entries, bib.fname, None)
    log.info('bibtex written to {0}'.format(bib.fname))
    return len(entries)


def url_open(path, base=BASE_URL, encoding=None, verbose=True):
    url = urljoin(base, path) if base is not None else path
    result = urlopen(url)
    if encoding is not None:
        result = io.TextIOWrapper(result, encoding=encoding)
    if verbose:
        print(url)
    return contextlib.closing(result)


def iterretirements(path='iso-639-3_Retirements.tab', encoding='utf-8', delimiter=b'\t'):
    if PY2:
        open_encoding, decode_row = None, lambda r: [c.decode(encoding) for c in r]
    else:
        open_encoding, decode_row = encoding, lambda r: r
    with url_open(path, encoding=open_encoding) as u:
        reader = csv.reader(u, delimiter=delimiter)
        header = decode_row(next(reader))
        make_row = collections.namedtuple('Retirement', header)._make
        for row in reader:
            r = make_row(decode_row(row))
            yield r._replace(Ret_Reason=RET_REASON[r.Ret_Reason])


def iterchangerequests(path='chg_requests.asp?order=CR_Number&chg_status=past',
                       outcome_date=re.compile(OUTCOME_DATE)):
    with url_open(path) as u:
        soup = bs4.BeautifulSoup(u, features='html.parser')
    rows = soup.find('table').find_all('tr')
    header = [h.get_text() for h in rows[0].find_all('th')[:-1]]
    assert header[-1] == 'Outcome/Effective date'
    fields = [h.replace(' ', '_') for h in header[:-1] + ['Outcome', 'Effective date']]
    make_row = collections.namedtuple('Changerequest', fields)._make
    for r in rows[1:]:
        row = [d.get_text().strip() for d in r.find_all('td')[:-1]]
        outcome, date = outcome_date.match(row[-1]).groups()
        yield make_row(row[:-1] + [outcome, date])


def get_retirements(scrape_missing_remedies=True):
    # retired iso_codes
    rets = {r.Id: r for r in iterretirements()}

    # latest adopted change request affecting each iso_code
    crs = (r for r in iterchangerequests() if r.Outcome == 'Adopted')
    crs = sorted(crs, key=lambda r: (r.Affected_Identifier, r.Effective_date or ''))
    crs = itertools.groupby(crs, lambda r: r.Affected_Identifier)
    crs = {id_: list(grp)[-1] for id_, grp in crs}

    # left join
    types = [next(iter(d.values())).__class__ for d in (rets, crs)]
    empty_cr = types[1]._make(None for _ in types[1]._fields)
    make_row = collections.namedtuple('Row', [f for cls in types for f in cls._fields])._make
    res = [make_row(rets[id_] + crs.get(id_, empty_cr)) for id_ in sorted(rets)]

    # fill Change_To from Ret_Remedy for splits and make it a list for others
    assert all(bool(r.Change_To) == (r.Ret_Reason not in ('split', 'non-existent')) for r in res)
    assert all(bool(r.Ret_Remedy) == (r.Ret_Reason == 'split') for r in res)
    iso = re.compile(r'\[([a-z]{3})\]')
    res = [r._replace(Change_To=iso.findall(r.Ret_Remedy))
           if r.Ret_Reason == 'split' else
           r._replace(Change_To=[r.Change_To] if r.Change_To else [])
           for r in res]
    
    if scrape_missing_remedies:  # get remedies for non-splits

        def get_detail_pages(iso_codes, rebuild=True, encoding='utf-8', cache='iso_detail_pages.json'):
            if rebuild or not os.path.exists(cache):
                if PY2:
                    open_encoding, decode = None, lambda s: s.decode(encoding)
                else:
                    open_encoding, decode_row = encoding, lambda r: r
                def iterpairs():
                    for i in iso_codes:
                        with url_open('documentation.asp?id=%s' % i, encoding=open_encoding) as u:
                            yield i, decode(u.read())
                result = dict(iterpairs())
                with open(cache, 'w') as f:
                    json.dump(result, f)
            with open(cache) as f:
                return json.load(f)

        def get_remedy(detail_page, pattern=re.compile(REMEDY)):
            ma = pattern.search(detail_page)
            if ma is None:
                return None
            return ma.group(1).replace('\t', '').strip()
        
        iso_codes = [r.Id for r in res if r.Ret_Reason != 'split']
        pages = get_detail_pages(iso_codes)
        res = [r._replace(Ret_Remedy=get_remedy(pages[r.Id])) if r.Id in pages else r for r in res]

    return res


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
