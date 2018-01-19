import pyglottolog

COMMON = ['author', 'editor', 'title', 'publisher', 'year', 'address']

FIELDS = {
    'incollection': COMMON + ['booktitle'],
    'inproceedings': COMMON + ['booktitle'],
    'inbook': COMMON,
}

FIELDS['unpublished'] = [f for f in FIELDS['incollection'] if f != 'publisher']


bf = pyglottolog.Glottolog().bibfiles


def fixed(entries, copy_fields=FIELDS):
    changed = set()
    for bibkey, (entrytype, fields) in entries.iteritems():
        crossref = fields.get('crossref')
        if crossref is not None:
            if crossref in entries:
                _, pfields = entries[crossref]
                if 'title' in fields and 'booktitle' not in fields and \
                   'title' in pfields and 'booktitle' not in pfields:
                    fields['booktitle'] = pfields['title']
                for f in copy_fields[entrytype]:
                    vparent, vchild = (x.get(f) for x in (pfields, fields))
                    if vparent and not vchild:
                        fields[f] = vparent
            del fields['crossref']
            changed.add(bibkey)
    return entries, changed


for b in bf:
    entries, changed = fixed(b.load())
    if changed:
        print('%s changed %d entries' % (b, len(changed)))
        b.save(entries)
