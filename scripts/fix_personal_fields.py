# fix_personal_fields.py - Drop personal usage fields from non-hh.bib bibfiles

from __future__ import print_function

import collections

import pyglottolog

FIELDS = ('last_changed', 'owner', 'timestamp', 'modified', 'added', 'rating')

api = pyglottolog.Glottolog()

def iterfixed(bibfile, infos, fields=FIELDS):
    for e in bibfile.iterentries():
        for f in fields:
            if f in e.fields:
                del e.fields[f]
                infos['deleted'] += 1
        yield e.key, (e.type, e.fields)

for bf in api.bibfiles:
    print(bf, end='\t')
    if bf.fname.name != 'hh.bib':
        infos = {'deleted': 0}
        entries = collections.OrderedDict(iterfixed(bf, infos))
        n = infos['deleted']
        print(n)
        if n:
            bf.save(entries)
