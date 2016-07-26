"""
_libmonster.py - mixed support library

# TODO: consider replacing pauthor in keyid with _bibtex.names
# TODO: enusure \emph is dropped from titles in keyid calculation
"""
from __future__ import unicode_literals
import re
from heapq import nsmallest
from collections import defaultdict

from clldutils.dsv import UnicodeWriter

from pyglottolog.util import unique, Trigger
from pyglottolog.monsterlib._bibtex_undiacritic import undiacritic


def opv(d, func, *args):
    return {i: func(v, *args) for i, v in d.items()}


def grp2fd(l):
    r = defaultdict(dict)
    for (a, b) in l:
        r[a][b] = 1
    return r


def grp2(l):
    return opv(grp2fd(l), lambda x: list(x.keys()))


reauthor = [re.compile(pattern) for pattern in [
    "(?P<lastname>[^,]+),\s((?P<jr>[JS]r\.|[I]+),\s)?(?P<firstname>[^,]+)$",
    "(?P<firstname>[^{][\S]+(\s[A-Z][\S]+)*)\s(?P<lastname>([a-z]+\s)*[A-Z\\\\][\S]+)(?P<jr>,\s[JS]r\.|[I]+)?$",
    "(?P<firstname>\\{[\S]+\\}[\S]+(\s[A-Z][\S]+)*)\s(?P<lastname>([a-z]+\s)*[A-Z\\\\][\S]+)(?P<jr>,\s[JS]r\.|[I]+)?$",
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
    else:
        print "Couldn't parse name:", n


def pauthor(s):
    pas = [psingleauthor(a) for a in s.split(' and ')]
    if [a for a in pas if not a]:
        if s:
            print s
    return [a for a in pas if a]


#"Adam, A., W.B. Wood, C.P. Symons, I.G. Ord & J. Smith"
#"Karen Adams, Linda Lauck, J. Miedema, F.I. Welling, W.A.L. Stokhof, Don A.L. Flassy, Hiroko Oguri, Kenneth Collier, Kenneth Gregerson, Thomas R. Phinnemore, David Scorza, John Davies, Bernard Comrie & Stan Abbott"


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
    if not upper:
        return ''
    return max(upper)


def rangecomplete(incomplete, complete):
    if len(complete) > len(incomplete):
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


#	Author = ac # { and Howard Coate},
#	Author = ad,


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
        print len(ts), "without", INLG

    # map record keys to sets of assigned iso codes, based on words in the title
    ann = [(k, set(dh[w] for w in tit if w in dh)) for k, tit in ts]

    # list of record keys which have been assigned exactly one iso code
    unique_ = [(k, lgs.pop()) for (k, lgs) in ann if len(lgs) == 1]
    if verbose:
        print len(unique_), "cases of unique hits"

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
    rsump = sum([romanint(b) - romanint(a) + 1 for (a, b) in rpgs if b] + [romanint(a) for (a, b) in rpgs if not b])
    sump = sum([int(rangecomplete(b, a)) - int(a) + 1 for (a, b) in pgs if b] + [int(a) for (a, b) in pgs if not b])
    if rsump != 0 and sump != 0:
        return "%s+%s" % (rsump, sump)
    if rsump == 0 and sump == 0:
        return ''
    return '%s' % (rsump + sump)


roman_map = {'m': 1000, 'd': 500, 'c': 100, 'l': 50, 'x': 10, 'v': 5, 'i': 1}


def introman(i):
    iz = {v: k for k, v in roman_map.items()}
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
        zc = roman_map[c]
        if zc > prev:
            i = i - 2 * prev + zc
        else:
            i += zc
        prev = zc
    return i


rerom = re.compile("(\d+)")


def roman(x):
    return rerom.sub(lambda o: introman(int(o.group(1))), x).upper()


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
        print "Unparsed author in", authors
        print "   ", astring, astring.split(' and ')
        print fields.get('title')

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


isoregex = '[a-z]{3}|NOCODE_[A-Z][^\s\]]+'
reisobrack = re.compile("\[(" + isoregex + ")\]")
recomma = re.compile("[,/]\s?")
reiso = re.compile(isoregex + "$")


def lgcode((_, fields)):
    return lgcodestr(fields['lgcode']) if 'lgcode' in fields else []


def lgcodestr(lgcstr):
    lgs = reisobrack.findall(lgcstr)
    if lgs:
        return lgs

    parts = [p.strip() for p in recomma.split(lgcstr)]
    codes = [p for p in parts if reiso.match(p)]
    if len(codes) == len(parts):
        return codes
    return []


def sd(es, hht):
    # most signficant piece of descriptive material
    # hhtype, pages, year
    mi = [(k,
           (hht.parse(fields.get('hhtype', 'unknown')),
            fields.get('pages', ''),
            fields.get('year', ''))) for (k, (typ, fields)) in es.items()]
    d = accd(mi)
    return [sorted(((p, y, k, t.id) for (k, (p, y)) in d[t.id].iteritems()), reverse=True)
            for t in hht if t.id in d]


def pcy(pagecountstr):
    if not pagecountstr:
        return 0
    return eval(pagecountstr) #int(takeafter(pagecountstr, "+"))


def accd(mi):
    r = defaultdict(dict)
    for (k, (hhts, pgs, year)) in mi:
        pci = pcy(pagecount(pgs))
        for t in hhts:
            r[t][k] = (pci / float(len(hhts)), year)
    return r


def byid(es):
    return grp2([(cfn, k) for (k, tf) in es.iteritems() for cfn in lgcode(tf)])


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
    for (lg, (stat, wits)) in lsafter.items():
        if not ls.get(lg):
            if verbose:
                print lg, "lacks status", [mafter[k][1]['srctrickle'] for k in wits]
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
        print "trigs", len(trigs)
        print "label classes", len(clss)
        print "unlabeled refs", len(ei)
        print "updates", len(u)
    return e
