# fix_gbid.py - normalize mix of full urls and ids in bibfiles gbid

import re
import collections

import pyglottolog

FIELD = 'gbid'

GBID = re.compile(
    r'(?:'
        r'http://books\.google\.com/books\?id='
    r'|'
        r'http://www\.google\.com/books/feeds/volumes/'
    r')?'
    r'([a-zA-Z0-9_-]{12})$')


if __name__ == '__main__':
    api = pyglottolog.Glottolog()

    def iterfixed(bibfile, field='gbid', pattern=GBID):
        for e in bibfile.iterentries():
            value = e.fields.get(field)
            if value is not None:
                e.fields[field] = pattern.match(value).group(1)
            yield e.key, (e.type, e.fields)

    for bf in api.bibfiles:
        entries = collections.OrderedDict(iterfixed(bf))
        bf.save(entries)
