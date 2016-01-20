# _compare_bibtex - compare regex-based with pybtex bibfile parsing

import _bibfiles, _bibtex

for b in _bibfiles.Collection():
    print(b.filepath)
    d = _bibtex.load(b.filepath, encoding=None, use_pybtex=False)
    e = _bibtex.load(b.filepath, encoding='utf-8', use_pybtex=True)
    if d.keys() != e.keys():
        print sorted(set(d).symmetric_difference(e))
    for k in e:
        x = d[k][1]
        y = e[k][1]
        if x.keys() != y.keys():
            print k
            print repr(x.keys())
            print repr(y.keys())
        for field in x:
            if x[field].decode('utf-8') != y[field]:
                print k
                print field
                print repr(x[field])
                print repr(y[field])
