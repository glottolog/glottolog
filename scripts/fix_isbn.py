# fix_isbn.py - clean up mix of different delimiters in hh.bib

import pyglottolog.api
from pyglottolog.references import Isbns

FIELD = 'isbn'

FIXES = {}

if __name__ == '__main__':
    api = pyglottolog.api.Glottolog()
    hh = api.bibfiles['hh.bib']

    def iterfixed(bibfile):
        for e in bibfile.iterentries():
            value = e.fields.get(FIELD)
            if value is not None:
                value = FIXES.get(value, value)
                if value is None:
                    del e.fields[FIELD]
                else:
                    isbns = Isbns.from_field(value)
                    e.fields[FIELD] = isbns.to_string()
            yield e.key, (e.type, e.fields)

    hh.save(list(iterfixed(hh)))
