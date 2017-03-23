"""
_libmonster.py - mixed support library

# TODO: consider replacing pauthor in keyid with _bibtex.names
# TODO: enusure \emph is dropped from titles in keyid calculation
"""
from __future__ import unicode_literals, print_function
import re
from heapq import nsmallest
from collections import defaultdict
from itertools import groupby
from operator import itemgetter

from clldutils.dsv import UnicodeWriter

from pyglottolog.util import unique, Trigger
from pyglottolog.references import Entry
from pyglottolog.monsterlib._bibtex_undiacritic import undiacritic
from pyglottolog.monsterlib.roman import roman, romanint


lgcodestr = Entry.lgcodes


def opv(d, func, *args):
    """
    Apply func to all values of a dictionary.

    :param d: A dictionary.
    :param func: Callable accepting a value of `d` as first parameter.
    :param args: Additional positional arguments to be passed to `func`.
    :return: `dict` mapping the keys of `d` to the return value of the function call.
    """
    return {i: func(v, *args) for i, v in d.items()}


def grp2(l):
    """
    Turn a list of pairs into a dictionary, mapping first elements to lists of
    co-occurring second elements in pairs.

    :param l:
    :return:
    """
    return {a: [pair[1] for pair in pairs] for a, pairs in
            groupby(sorted(l, key=itemgetter(0)), itemgetter(0))}


def grp2fd(l):
    """
    Turn a list of pairs into a nested dictionary, thus grouping by the first element in
    the pair.

    :param l:
    :return:
    """
    return {k: {vv: 1 for vv in v} for k, v in grp2(l).items()}


reauthor = [re.compile(pattern) for pattern in [
    "(?P<lastname>[^,]+),\s((?P<jr>[JS]r\.|[I]+),\s)?(?P<firstname>[^,]+)$",
    "(?P<firstname>[^{][\S]+(\s[A-Z][\S]+)*)\s"
    "(?P<lastname>([a-z]+\s)*[A-Z\\\\][\S]+)(?P<jr>,\s[JS]r\.|[I]+)?$",
    "(?P<firstname>\\{[\S]+\\}[\S]+(\s[A-Z][\S]+)*)\s"
    "(?P<lastname>([a-z]+\s)*[A-Z\\\\][\S]+)(?P<jr>,\s[JS]r\.|[I]+)?$",
    "(?P<firstname>[\s\S]+?)\s\{(?P<lastname>[\s\S]+)\}(?P<jr>,\s[JS]r\.|[I]+)?$",
    "\{(?P<firstname>[\s\S]+)\}\s(?P<lastname>[\s\S]+?)(?P<jr>,\s[JS]r\.|[I]+)?$",
    "(?P<lastname>[A-Z][\S]+)$",
    "\{(?P<lastname>[\s\S]+)\}$",
    "(?P<lastname>[aA]nonymous)$",
    "(?P<lastname>\?)$",
    "(?P<lastname>[\s\S]+)$",
]]


def psingleauthor(n):
    if not n:
        return

    for pattern in reauthor:
        o = pattern.match(n)
        if o:
            return o.groupdict()
    print("Couldn't parse name:", n)  # pragma: no cover


def pauthor(s):
    pas = [psingleauthor(a) for a in s.split(' and ')]
    if [a for a in pas if not a]:
        if s:
            print(s)
    return [a for a in pas if a]


relu = re.compile("\s+|(d\')(?=[A-Z])")
recapstart = re.compile("\[?[A-Z]")


def lowerupper(s):
    parts, lower, upper = [x for x in relu.split(s) if x], [], []
    for i, x in enumerate(parts):
        if not recapstart.match(undiacritic(x)):
            lower.append(x)
        else:
            upper = parts[i:]
            break
    return lower, upper


def lastnamekey(s):
    _, upper = lowerupper(s)
    return max(upper) if upper else ''


def rangecomplete(incomplete, complete):
    """
    >>> rangecomplete('2', '10')
    '12'
    """
    if len(complete) > len(incomplete):
        # if the second number in a range of pages has less digits than the the first,
        # we assume it's meant as only the last digits of the bigger number,
        # i.e. 10-2 is interpreted as 10-12.
        return complete[:len(complete) - len(incomplete)] + incomplete
    return incomplete


rebracketyear = re.compile("\[([\d\,\-\/]+)\]")
reyl = re.compile("[\,\-\/\s\[\]]+")


def pyear(s):
    if rebracketyear.search(s):
        s = rebracketyear.search(s).group(1)
    my = [x for x in reyl.split(s) if x.strip()]
    if len(my) == 0:
        return "[nd]"
    if len(my) != 1:
        return my[0] + "-" + rangecomplete(my[-1], my[0])
    return my[-1]


bibord = {k: i for i, k in enumerate([
    'author',
    'editor',
    'title',
    'booktitle',
    'journal',
    'school',
    'publisher',
    'address',
    'series',
    'volume',
    'number',
    'pages',
    'year',
    'issn',
    'url',
])}


def bibord_iteritems(fields, sortkey=lambda f, inf=float('inf'): (bibord.get(f, inf), f)):
    for f in sorted(fields, key=sortkey):
        yield f, fields[f]


resplittit = re.compile("[\(\)\[\]\:\,\.\s\-\?\!\;\/\~\=]+")


def wrds(txt):
    txt = undiacritic(txt.lower())
    txt = txt.replace("'", "").replace('"', "")
    return [x for x in resplittit.split(txt) if x]


def renfn(e, ups):
    for k, field, newvalue in ups:
        typ, fields = e[k]
        fields[field] = newvalue
        e[k] = (typ, fields)
    return e


INLG = 'inlg'


def add_inlg_e(e, trigs, verbose=True, return_newtrain=False):
    # FIXME: does not honor 'NOT' for now, only maps words to iso codes.
    dh = {word: t.type for t in trigs for _, word in t.clauses}

    # map record keys to lists of words in titles:
    ts = [(k, wrds(fields['title']) + wrds(fields.get('booktitle', '')))
          for (k, (typ, fields)) in e.items()
          if 'title' in fields and INLG not in fields]

    if verbose:
        print(len(ts), "without", INLG)

    # map record keys to sets of assigned iso codes, based on words in the title
    ann = [(k, set(dh[w] for w in tit if w in dh)) for k, tit in ts]

    # list of record keys which have been assigned exactly one iso code
    unique_ = [(k, lgs.pop()) for (k, lgs) in ann if len(lgs) == 1]
    if verbose:
        print(len(unique_), "cases of unique hits")

    t2 = renfn(e, [(k, INLG, v) for (k, v) in unique_])

    if return_newtrain:  # pragma: no cover
        newtrain = grp2fd([
            (lgcodestr(fields[INLG])[0], w) for (k, (typ, fields)) in t2.items()
            if 'title' in fields and INLG in fields
            if len(lgcodestr(fields[INLG])) == 1 for w in wrds(fields['title'])])
        for (lg, wf) in sorted(newtrain.items(), key=lambda x: len(x[1])):
            cm = [(1 + f,
                   float(1 - f + sum(owf.get(w, 0) for owf in newtrain.values())),
                   w) for (w, f) in wf.items() if f > 9]
            cms = [(f / fn, f, fn, w) for (f, fn, w) in cm]
            cms.sort(reverse=True)
        return t2, newtrain, cms

    return t2


rerpgs = re.compile("([xivmcl]+)\-?([xivmcl]*)")
repgs = re.compile("([\d]+)\-?([\d]*)")


def pagecount(pgstr):
    rpgs = rerpgs.findall(pgstr)
    pgs = repgs.findall(pgstr)
    rsump = sum(romanint(b) - romanint(a) + 1 if b else romanint(a) for (a, b) in rpgs)
    sump = sum(int(rangecomplete(b, a)) - int(a) + 1 if b else int(a) for (a, b) in pgs)
    if rsump != 0 and sump != 0:
        return "%s+%s" % (rsump, sump)
    if rsump == 0 and sump == 0:
        return ''
    return '%s' % (rsump + sump)


rewrdtok = re.compile("[a-zA-Z].+")
reokkey = re.compile("[^a-z\d\-\_\[\]]")


def keyid(fields, fd, ti=2, infinity=float('inf')):
    if 'author' not in fields:
        if 'editor' not in fields:
            values = ''.join(
                v for f, v in bibord_iteritems(fields) if f != 'glottolog_ref_id')
            return '__missingcontrib__' + reokkey.sub('_', values.lower())
        else:
            astring = fields['editor']
    else:
        astring = fields['author']

    authors = pauthor(astring)
    if len(authors) != len(astring.split(' and ')):
        print("Unparsed author in", authors)
        print("   ", astring, astring.split(' and '))
        print(fields.get('title'))

    ak = [undiacritic(x) for x in sorted(lastnamekey(a['lastname']) for a in authors)]
    yk = pyear(fields.get('year', '[nd]'))[:4]
    tks = wrds(fields.get("title", "no.title"))  # takeuntil :
    # select the (leftmost) two least frequent words from the title
    types = list(unique(w for w in tks if rewrdtok.match(w)))
    tk = nsmallest(ti, types, key=lambda w: fd.get(w, infinity))
    # put them back into the title order (i.e. 'spam eggs' != 'eggs spam')
    order = {w: i for i, w in enumerate(types)}
    tk.sort(key=lambda w: order[w])
    if 'volume' in fields and all(
            f not in fields for f in ['journal', 'booktitle', 'series']):
        vk = roman(fields['volume'])
    else:
        vk = ''

    if 'extra_hash' in fields:
        yk = yk + fields['extra_hash']

    key = '-'.join(ak) + "_" + '-'.join(tk) + vk + yk
    return reokkey.sub("", key.lower())


def lgcode(arg):
    fields = arg[1]
    return lgcodestr(fields['lgcode']) if 'lgcode' in fields else []


def sd(es, hht):
    # most signficant piece of descriptive material
    # hhtype, pages, year
    mi = [(k,
           (hht.parse(fields.get('hhtype', 'unknown')),
            fields.get('pages', ''),
            fields.get('year', ''))) for (k, (typ, fields)) in es.items()]
    d = accd(mi)
    return [sorted(((p, y, k, t.id) for (k, (p, y)) in d[t.id].items()), reverse=True)
            for t in hht if t.id in d]


def pcy(pagecountstr):
    if not pagecountstr:
        return 0
    return eval(pagecountstr)  # int(takeafter(pagecountstr, "+"))


def accd(mi):
    r = defaultdict(dict)
    for (k, (hhts, pgs, year)) in mi:
        pci = pcy(pagecount(pgs))
        for t in hhts:
            r[t][k] = (pci / float(len(hhts)), year)
    return r


def byid(es):
    return grp2([(cfn, k) for (k, tf) in es.items() for cfn in lgcode(tf)])


def sdlgs(e, hht):
    eindex = byid(e)
    fes = opv(eindex, lambda ks: {k: e[k] for k in ks})
    fsd = opv(fes, sd, hht)
    return fsd, fes


def lstat(e, hht):
    (lsd, lse) = sdlgs(e, hht)
    return opv(lsd, lambda xs: (xs + [[[None]]])[0][0][-1])


def lstat_witness(e, hht):
    def statwit(xs):
        if len(xs) == 0:
            return None, []
        [(typ, ks)] = grp2([(t, k) for [p, y, k, t] in xs[0]]).items()
        return typ, ks
    (lsd, lse) = sdlgs(e, hht)
    return opv(lsd, statwit)


def markconservative(m, trigs, ref, hht, outfn, verbose=True, rank=None):
    blamefield = "hhtype"
    mafter = markall(m, trigs, verbose=verbose, rank=rank)
    ls = lstat(ref, hht)
    lsafter = lstat_witness(mafter, hht)
    log = []
    no_status = defaultdict(set)
    for (lg, (stat, wits)) in lsafter.items():
        if not ls.get(lg):
            srctrickles = [mafter[k][1]['srctrickle'] for k in wits]
            for t in srctrickles:
                if not t.startswith('iso6393'):
                    no_status[lg].add(t)
            continue
        if hht[stat] > hht[ls[lg]]:
            log = log + [
                (lg, [(mafter[k][1].get(blamefield, "No %s" % blamefield),
                       k,
                       mafter[k][1].get('title', 'no title'),
                       mafter[k][1].get('srctrickle', 'no srctrickle')) for k in wits], ls[lg])]
            for k in wits:
                (t, f) = mafter[k]
                if blamefield in f:
                    del f[blamefield]
                mafter[k] = (t, f)
    for lg in no_status:
        print('{0} lacks status'.format(lg))
    with UnicodeWriter(outfn, dialect='excel-tab') as writer:
        writer.writerows(((lg, was) + mis for (lg, miss, was) in log for mis in miss))
    return mafter


def markall(e, trigs, verbose=True, rank=None):
    # the set of fields triggers relate to:
    clss = set(t.field for t in trigs)

    # all bibitems lacking any of the potential triggered fields:
    ei = {k: (typ, fields) for k, (typ, fields) in e.items()
          if any(c not in fields for c in clss)}
    eikeys = set(list(ei.keys()))

    # map words in titles to lists of bibitem keys having the word in the title:
    wk = defaultdict(set)
    for k, (typ, fields) in ei.items():
        for w in wrds(fields.get('title', '')):
            wk[w].add(k)

    u = defaultdict(lambda: defaultdict(list))
    for clauses, triggers in Trigger.group(trigs):
        for k in triggers[0](eikeys, wk):
            for t in triggers:
                u[k][t.cls].append(t)

    for k, t_by_c in u.items():
        t, f = e[k]
        f2 = {a: b for a, b in f.items()}
        for (field, type_), triggers in sorted(t_by_c.items(), key=lambda i: len(i[1])):
            # Make sure we handle the trigger class with the biggest number of matching
            # triggers last.
            if rank and field in f2:
                # only update the assigned hhtype if something better comes along:
                if rank(f2[field].split(' (comp')[0]) >= rank(type_):
                    continue
            f2[field] = Trigger.format(type_, triggers)
        e[k] = (t, f2)

    if verbose:
        print("trigs", len(trigs))
        print("label classes", len(clss))
        print("unlabeled refs", len(ei))
        print("updates", len(u))
    return e
