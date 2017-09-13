# coding: utf8
"""
Create a BibTeX file listing records for each past ISO 639-3 change request.

http://www-01.sil.org/iso639-3/chg_requests.asp?order=CR_Number&chg_status=past
"""
from __future__ import unicode_literals, print_function, division
from itertools import groupby

import requests
from bs4 import BeautifulSoup as bs

from pyglottolog.monsterlib._bibtex import save


BASE_URL = "http://www-01.sil.org/iso639-3"


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
        'howpublished': BASE_URL + "/chg_detail.asp?id=" + id_,
        'address': "Dallas",
        'author': "ISO 639-3 Registration Authority",
        'publisher': "SIL International",
        'url': BASE_URL + "/cr_files/{0}.pdf".format(id_),
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

    url = BASE_URL + "/chg_requests.asp"
    log.info('downloading {0} ...'.format(url))
    res = requests.get(url, params=dict(order='CR_Number', chg_status='past'))
    log.info('HTTP {0}'.format(res.status_code))
    table = bs(res.content, 'html.parser').find('table')
    cols = None
    for i, tr in enumerate(table.find_all('tr')):
        if i == 0:
            cols = parse_row(tr, 'th')
        else:
            yield dict(zip(cols, parse_row(tr, 'td')))


def bibtex(api, log):
    bib = api.bibfiles['iso6393.bib']
    glottolog_ref_ids = bib.glottolog_ref_id_map

    entries = []
    for id_, rows in groupby(iter_change_requests(log), lambda c: c['CR Number']):
        entries.append(change_request_as_source(id_, list(rows), glottolog_ref_ids))
    save(entries, bib.fname, None)
    log.info('bibtex written to {0}'.format(bib.fname))
    return len(entries)


def retirements(api, log):
    retired = []
    for id_, rows in groupby(iter_change_requests(log), lambda c: c['CR Number']):
        #
        # Merge -> Update
        # Split -> Create
        #
        crs = list(rows)
        if crs[0]['Outcome/Effective date'].startswith('Adopted'):
            ret = [t for t in crs if t['Change Type'] == 'Split' and t['Outcome/Effective date'].startswith('Adopted')]
            if ret:
                assert len(ret) == 1
                instead = [t for t in crs if t['Change Type'] == 'Create' and t['Outcome/Effective date'].startswith('Adopted')]
            else:
                ret = [t for t in crs if t['Change Type'] == 'Merge' and t['Outcome/Effective date'].startswith('Adopted')]
                if ret:
                    instead = [t for t in crs if t['Change Type'] == 'Update' and t['Outcome/Effective date'].startswith('Adopted')]
                else:
                    ret, instead = [t for t in crs if t['Change Type'] == 'Retire' and t['Outcome/Effective date'].startswith('Adopted')], []
                    if ret:
                        assert len(ret) == 1
            if ret:
                retired.append((ret, instead))

    iso2lang = {l.iso: l for l in api.languoids() if l.iso}
    for ret, instead in retired:
        for cr in ret:
            if cr['Affected Identifier'] not in iso2lang:
                print('--- Missing retired ISO code: {0}'.format(cr['Affected Identifier']))
                print(cr)
                continue
            lang = iso2lang[cr['Affected Identifier']]
            if lang.iso_retirement:
                assert lang.iso_retirement.code == cr['Affected Identifier']
            else:
                lang.cfg['iso_retirement'] = {
                    'code': cr['Affected Identifier'],
                    'name': cr['Language Name'].strip(),
                    'effective': cr['Outcome/Effective date'].replace('Adopted', ''),
                    'remedy': cr['Change Type'],
                    'change_request': cr['CR Number'],
                }
                lang.write_info()
        for cr in instead:
            if cr['Affected Identifier'] not in iso2lang:
                print('+++ Missing active ISO code: {0}'.format(cr['Affected Identifier']))
                print(cr)
                continue
            lang = iso2lang[cr['Affected Identifier']]
            lang.cfg.set('iso_retirement', 'change_request', cr['CR Number'])
            lang.cfg.set('iso_retirement', 'effective', cr['Outcome/Effective date'].replace('Adopted', ''))
            lang.cfg.set('iso_retirement', 'supersedes', [c['Affected Identifier'] for c in ret])
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
