# _compare_names.py - compare regex-based with pybtex name parsing
from __future__ import print_function

import _bibfiles
import _bibtex
import _libmonster


def names1(s):  # pragma: no cover
    return [
        (debr(n.get('firstname', '')), debr(n.get('lastname', '')), debr(n.get('jr', '')))
        for n in _libmonster.pauthor(s)]


def names2(s):  # pragma: no cover
    return [
        (debr(first), debr(' '.join(n for n in (prelast, last) if n)), debr(lineage))
        for prelast, last, first, lineage in _bibtex.names(s)]


def debr(s):  # pragma: no cover
    if s.startswith('{') and s.endswith('}'):
        return s[1:-1]
    return s


if __name__ == '__main__':  # pragma: no cover
    from collections import Counter

    counts = Counter()
    for b in _bibfiles.Collection():
        print(b.filename.center(80, '#'))
        for bibkey, (entrytype, fields) in b.iterentries():
            for role in ('author', 'editor'):
                names = fields.get(role, '')
                n1, n2 = names1(names), names2(names)
                if n1 != n2:
                    counts.update([b.filename])
                    print(b.filename, bibkey, role)
                    print(repr(names))
                    print(n1)
                    print(n2)
                    print()

    print('\n'.join('%d\t%s' % (n, f) for f, n in sorted(counts.most_common())))
