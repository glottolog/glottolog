# _compare_names.py - compare regex-based with pybtex name parsing

import _bibfiles, _bibtex, _libmonster


def names1(s):
    return [(debr(n.get('firstname', '')), debr(n.get('lastname', '')), debr(n.get('jr', '')))
        for n in _libmonster.pauthor(s)]


def names2(s):
    return [(debr(first), debr(' '.join(n for n in (prelast, last) if n)), debr(lineage))
        for prelast, last, first, lineage in _bibtex.names(s)]


def debr(s):
    if s.startswith('{') and s.endswith('}'):
        return s[1:-1]
    return s


counts = {}

for b in _bibfiles.Collection():
    print b.filename.center(80, '#')
    count = 0
    for bibkey, (entrytype, fields) in b.iterentries():
        for role in ('author', 'editor'):
            names = fields.get(role, '')
            n1, n2 = names1(names), names2(names)
            if n1 != n2:
                count += 1
                print b.filename, bibkey, role
                print repr(names)
                print n1
                print n2
                print
    counts[b.filename] = count

print '\n'.join('%d\t%s' % (n, f) for f, n in sorted(counts.iteritems()))
