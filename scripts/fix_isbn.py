# fix_isbn.py - clean up mix of different delimiters in hh.bib

import re

import pyglottolog.api

FIELD = 'isbn'

FIXES = {
# other delimiters, extra text
    '9780884323747 : PAP 0884323749 : PAP': '9780884323747 0884323749',
    '978-0-87081901-8, 0-87081901-1': '978-0-87081901-8, 0870819011',
    '9630481-881-1': '9634818811', 
    '9780520077003; 9780520912182': '9780520077003, 9780520912182',
    '0195136241 9780195136241 0195152468 9780195152463, ISBN-0-19-513624-1': '0195136241 9780195136241 0195152468 9780195152463, ISBN-10 0-19-513624-1',
    '978-0521808613': '9780521808613',
    'ISBN 978-0-86848-878-3 pb, ISBN-10 0-86848-878-X pb': 'ISBN 978-0-86848-878-3, ISBN-10 0-86848-878-X',
    '9780198724742; 9780191792281': '9780198724742, 9780191792281',
    'ISBN 978-91-7346-364-5 pb, ISBN-10 91-7346-364-7 pb, 9789173463645': 'ISBN 978-91-7346-364-5, ISBN-10 91-7346-364-7, 9789173463645',
    '039100946X 9780391009462 0391009486 pbk. 9780391009486 pbk 0855750766 9780855750763 0855750820 9780855750824': '039100946X 9780391009462 0391009486 9780391009486 0855750766 9780855750763 0855750820 9780855750824',
    'ISBN-10 0-415-10011-9 set, 0-415-10009-7 book, 0-415-10010-0 cassette': 'ISBN-10 0-415-10011-9  0-415-10009-7, 0-415-10010-0',
    'ISBN-0-8108-3032-9, 0810830329 9780810830325': 'ISBN-10 0-8108-3032-9, 0810830329 9780810830325',
    'ISBN-10 1-55876-087-3 pb, 1-55876-088-1 pb': 'ISBN-10 1-55876-087-3, 1-55876-088-1',
    '9197016500 ; 9789197016506': '9197016500, 9789197016506',
    '9780195139778; 9780195307450': '9780195139778, 9780195307450',
    '9582100052 : donacion 9789582100056 : donacion, 9582100036 9789582100032 9582100044 9789582100049 9582100052 9789582100056': '9582100052, 9789582100056, 9582100036 9789582100032 9582100044 9789582100049 9582100052 9789582100056',
# not 10 or 13 digits, broken checksum
    '9990-58-75-0, ISBN-10 99908-58-75-0': None,
    '5-87232-0320-9': None,
# wrong checksum
    '2-86538-126-0': '2-86538-126-9',
    '0-85883-456-0': '0-85883-456-1',
    '0-87168-155-8': '0-87168-155-2',
    '0-85883-456-0': '0-85883-456-1',
    'ISBN-10 3-933943-02-6': 'ISBN-10 3-933943-02-7',
    '978-3-7420-2106-0': '978-3-7420-2106-9',
    '84-249-0957-X': '84-249-0957-7',
}


class Parser(object):

    @staticmethod
    def parse(ma):
        return ''.join(g for g in ma.groups() if g is not None)


class Numeric(Parser):

    pattern = re.compile(r'(97[89])?(\d{9})([\dXx])')


class Hyphened(Parser):

    pattern = re.compile(r'''
        (?:
          (?:ISBN[- ])? (97[89])-
          |
          ISBN-10[ ]
        )?
        (\d{1,5})- (\d+)- (\d+)- ([\dXx])''', flags=re.VERBOSE)


class Ten99(Parser):

    pattern = re.compile(r'(99)-(\d{7})-([\dXx])')


def iterparse(s, pos=0, parsers=[Hyphened, Numeric, Ten99],
              delimiters=[', ', '  ', ' : ', ' ']):
    while True:
        for p in parsers:
            ma = p.pattern.match(s, pos)
            if ma is not None:
                yield p.parse(ma)
                pos += len(ma.group())
                break
        else:
            raise RuntimeError(s, pos)
        if pos == len(s):
            return
        for delim in delimiters:
            if s.startswith(delim, pos):
                pos += len(delim)
                break
        else:
            raise RuntimeError(s, pos)    


class Isbn(object):

    @staticmethod
    def _check13(digits):
        halfes = digits[0:12:2], digits[1:12:2]
        odd, even = (sum(map(int, h)) for h in halfes)
        return str((10 - (odd + 3 * even) % 10) % 10)

    @staticmethod
    def _check10(digits):
        result = sum(i * int(d) for i, d in enumerate(digits[:9], 1)) % 11
        return 'X' if result == 10 else str(result) 

    def __init__(self, digits):
        if len(digits) == 13:
            calculated = self._check13(digits)
        elif len(digits) == 10:
            digits = digits.upper()
            calculated = self._check10(digits)
        else:
            raise ValueError(digits)

        if digits[-1] != calculated:
            raise ValueError(digits)

        if len(digits) == 10:
            digits = '978' + digits[:9]
            digits += self._check13(digits)
        self.digits = digits


def uniqued(items):
    seen = set()
    return [i for i in items if i not in seen and not seen.add(i)]


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
                    isbns = uniqued(Isbn(v).digits for v in iterparse(value))
                    e.fields[FIELD] = ', '.join(isbns)
            yield e.key, (e.type, e.fields)

    hh.save(list(iterfixed(hh)))
