from __future__ import unicode_literals

import re

__all__ = ['introman', 'romanint']

ROMAN_MAP = {'m': 1000, 'd': 500, 'c': 100, 'l': 50, 'x': 10, 'v': 5, 'i': 1}

REROM = re.compile("(\d+)")


def introman(i):
    iz = {v: k for k, v in ROMAN_MAP.items()}
    x = ""
    for v, c in sorted(iz.items(), reverse=True):
        q, r = divmod(i, v)
        if q == 4 and c != 'm':
            x = x + c + iz[5 * v]
        else:
            x += ''.join(c for _ in range(q))
        i = r
    return x


def romanint(r):
    i = 0
    prev = 10000
    for c in r:
        zc = ROMAN_MAP[c]
        if zc > prev:
            i = i - 2 * prev + zc
        else:
            i += zc
        prev = zc
    return i


def roman(x):
    return REROM.sub(lambda o: introman(int(o.group(1))), x).upper()
