# fix_autotyp_empty.py - drop fields with empty value from autotyp.bib

import collections

import pyglottolog.api

api = pyglottolog.api.Glottolog()
at = api.bibfiles['autotyp.bib']

def iterfixed(bibfile):
    for e in bibfile.iterentries():
        for key, value in list(e.fields.items()):
            if not value:
                del e.fields[key]
        yield e.key, (e.type, e.fields)

entries = collections.OrderedDict(iterfixed(at))
at.save(entries)
