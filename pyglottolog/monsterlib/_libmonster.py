# _libmonster.py - mixed support library

# TODO: consider replacing pauthor in keyid with _bibtex.names
# TODO: enusure \emph is dropped from titles in keyid calculation

import re
from heapq import nsmallest
from collections import defaultdict

from clldutils.dsv import UnicodeWriter

from pyglottolog import languoids
from pyglottolog.util import references_path, parse_conjunctions, read_ini, intersectall
from pyglottolog.monsterlib._bibtex_undiacritic import undiacritic

__all__ = [
    'add_inlg_e',
    'keyid',
    'wrds',
    'lstat', 'lstat_witness', 
    'hhtype_to_n', 'expl_to_hhtype', 'lgcode',
    'load_triggers',
    'pitems',
]

HHTYPE = references_path('alt4hhtype.ini')


def load_triggers(filename=HHTYPE):
    p = read_ini(filename)
    result = {}
    for s in p.sections():
        cls, lab = s.split(', ', 1)
        triggers = p.get(s, 'triggers').strip().splitlines()
        if not triggers:  # hhtype, unknown
            continue
        result[(cls, lab)] = [parse_conjunctions(t) for t in triggers]
    return result


def load_hhtypes(filename=HHTYPE):
    p = read_ini(filename)
    result = {}
    for s in p.sections():
        _, _, expl = s.partition(', ')
        hht = p.get(s, 'id')
        rank = p.getint(s, 'rank')
        abbv = p.get(s, 'abbv')
        bibabbv = p.get(s, 'bibabbv')
        result[hht] = (rank, expl, abbv, bibabbv)
    return result


def opv(d, func):
    return {i: func(v) for i, v in d.iteritems()}


def grp2fd(l):
    r = defaultdict(dict)
    for (a, b) in l:
        r[a][b] = 1
    return r


def grp2(l):
    r = defaultdict(dict)
    for (a, b) in l:
        r[a][b] = None
    return opv(r, lambda x: list(x.keys()))


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


def psingleauthor(n, vonlastname=True):
    for pattern in reauthor:
        o = pattern.match(n)
        if o:
            if vonlastname:
                return lastvon(o.groupdict())
            return o.groupdict()
    if n:
        print "Couldn't parse name:", n
    return None


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
    parts = [x for x in relu.split(s) if x]
    lower = []
    upper = []
    for (i, x) in enumerate(parts):
        if not recapstart.match(undiacritic(x)):
            lower.append(x)
        else:
            upper = parts[i:]
            break
    return (lower, upper)


def lastvon(author):
    if not author.has_key('firstname'):
        return author
    r = {}
    (lower, upper) = lowerupper(author['firstname'])
    r['lastname'] = (' '.join(lower).strip() + ' ' + author['lastname']).strip()
    r['firstname'] = ' '.join(upper)
    if author.has_key('jr') and author['jr']:
        r['jr'] = author['jr']

    return r


def lastnamekey(s):
    (_, upper) = lowerupper(s)
    if not upper:
        return ''
    return max(upper)


def rangecomplete(incomplete, complete):
    if len(complete) > len(incomplete):
        return complete[:len(complete)-len(incomplete)] + incomplete
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


refields = re.compile('\s*(?P<field>[a-zA-Z\_]+)\s*=\s*[{"](?P<data>.*)[}"],\r?\n')
refieldsnum = re.compile('\s*(?P<field>[a-zA-Z\_]+)\s*=\s*(?P<data>\d+),\r?\n')
refieldsacronym = re.compile('\s*(?P<field>[a-zA-Z\_]+)\s*=\s*(?P<data>[A-Za-z]+),\r?\n')
#refieldslast = re.compile('\s*(?P<field>[a-zA-Z\_]+)\s*=\s*[{"]*(?P<data>.+?)[}"]*\r?\n}')
refieldslast = re.compile('\s*(?P<field>[a-zA-Z\_]+)\s*=\s*[\{\"]?(?P<data>[^\r\n]+?)[\}\"]?(?<!\,)(?:$|\r?\n)')
retypekey = re.compile("@(?P<type>[a-zA-Z]+){(?P<key>[^,\s]*)[,\r\n]")
reitem = re.compile("@[a-zA-Z]+{[^@]+}")

trf = '@Book{g:Fourie:Mbalanhu,\n  author =   {David J. Fourie},\n  title =    {Mbalanhu},\n  publisher =    LINCOM,\n  series =       LWM,\n  volume =       03,\n  year = 1993\n}'


def pitems(txt):
    for m in reitem.finditer(txt):
        item = m.group()
        o = retypekey.search(item)
        if o is None:
            continue
        key = o.group("key")
        typ = o.group("type")
        fields = refields.findall(item) + refieldsacronym.findall(item) + refieldsnum.findall(item) + refieldslast.findall(item)
        fieldslower = ((x.lower(), y) for x, y in fields)
        yield key, typ.lower(), dict(fieldslower)


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
    for (k, field, newvalue) in ups:
        (typ, fields) = e[k]
        #fields['mpifn'] = fields['fn']
        fields[field] = newvalue
        e[k] = (typ, fields)
    return e


def add_inlg_e(e):
    inlg = languoids.load_triggers(type_='inlg')
    # FIXME: does not honor 'NOT' for now
    dh = {word: label  for (cls, label), triggers in inlg.iteritems()
        for t in triggers for flag, word in t}  
    ts = [(k, wrds(fields['title']) + wrds(fields.get('booktitle', ''))) for (k, (typ, fields)) in e.iteritems() if fields.has_key('title') and not fields.has_key('inlg')]
    print len(ts), "without", 'inlg'
    ann = [(k, set(dh[w] for w in tit if dh.has_key(w))) for (k, tit) in ts]
    unique = [(k, lgs.pop()) for (k, lgs) in ann if len(lgs) == 1]
    print len(unique), "cases of unique hits"
    fnups = [(k, 'inlg', v) for (k, v) in unique]
    t2 = renfn(e, fnups)
    #print len(unique), "updates"

    newtrain = grp2fd([(lgcodestr(fields['inlg'])[0], w) for (k, (typ, fields)) in t2.iteritems() if fields.has_key('title') and fields.has_key('inlg') if len(lgcodestr(fields['inlg'])) == 1 for w in wrds(fields['title'])])
    #newtrain = grp2fd([(cname(lgc), w) for (lgcs, w) in alc if len(lgcs) == 1 for lgc in lgcs])
    for (lg, wf) in sorted(newtrain.iteritems(), key=lambda x: len(x[1])):
        cm = [(1+f, float(1-f+sum(owf.get(w, 0) for owf in newtrain.itervalues())), w) for (w, f) in wf.iteritems() if f > 9]
        cms = [(f/fn, f, fn, w) for (f, fn, w) in cm]
        cms.sort(reverse=True)
        ##print lg, cms[:10]
        ##print ("h['%s'] = " % lg) + str([x[3] for x in cms[:10]])
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
    return str(rsump + sump)


def introman(i):
    z = {'m': 1000, 'd': 500, 'c': 100, 'l': 50, 'x': 10, 'v': 5, 'i': 1}
    iz = dict((v, k) for (k, v) in z.iteritems())
    x = ""
    for (v, c) in sorted(iz.items(), reverse=True):
        (q, r) = divmod(i, v)
        if q == 4 and c != 'm':
            x = x + c + iz[5*v]
        else:
            x = x + ''.join(c for i in range(q))
        i = r
    return x


def romanint(r):
    z = {'m': 1000, 'd': 500, 'c': 100, 'l': 50, 'x': 10, 'v': 5, 'i': 1}
    i = 0
    prev = 10000
    for c in r:
        zc = z[c]
        if zc > prev:
            i = i - 2*prev + zc
        else:
            i = i + zc
        prev = zc
    return i


rerom = re.compile("(\d+)")


def roman(x):
    return rerom.sub(lambda o: introman(int(o.group(1))), x).upper()


rewrdtok = re.compile("[a-zA-Z].+")
reokkey = re.compile("[^a-z\d\-\_\[\]]")


def keyid(fields, fd={}, ti=2, infinity=float('inf')):
    if not fields.has_key('author'):
        if not fields.has_key('editor'):
            values = ''.join(v for f, v in bibord_iteritems(fields)
                if f != 'glottolog_ref_id')
            return '__missingcontrib__' + reokkey.sub('_', values.lower())
        else:
            astring = fields['editor']
    else:
        astring = fields['author']

    authors = pauthor(astring)
    if len(authors) != len(astring.split(' and ')):
        print "Unparsed author in", authors
        print "   ", astring, astring.split(' and ')
        print fields['title']

    ak = [undiacritic(x) for x in sorted(lastnamekey(a['lastname']) for a in authors)]
    yk = pyear(fields.get('year', '[nd]'))[:4]
    tks = wrds(fields.get("title", "no.title")) #takeuntil :
    # select the (leftmost) two least frequent words from the title
    types = uniqued(w for w in tks if rewrdtok.match(w))
    tk = nsmallest(ti, types, key=lambda w: fd.get(w, infinity))
    # put them back into the title order (i.e. 'spam eggs' != 'eggs spam')
    order = {w: i for i, w in enumerate(types)}
    tk.sort(key=lambda w: order[w])
    if fields.has_key('volume') and not fields.has_key('journal') and not fields.has_key('booktitle') and not fields.has_key('series'):
        vk = roman(fields['volume'])
    else:
        vk = ''

    if fields.has_key('extra_hash'):
        yk = yk + fields['extra_hash']

    key = '-'.join(ak) + "_" + '-'.join(tk) + vk + yk
    return reokkey.sub("", key.lower())


def uniqued(items):
    seen = set()
    return [i for i in items if i not in seen and not seen.add(i)]


reisobrack = re.compile("\[([a-z][a-z][a-z]|NOCODE\_[A-Z][^\s\]]+)\]")
recomma = re.compile("[\,\/]\s?")
reiso = re.compile("[a-z][a-z][a-z]$|NOCODE\_[A-Z][^\s\]]+$")


def lgcode((typ, fields)):
    if not fields.has_key('lgcode'):
        return []
    return lgcodestr(fields['lgcode'])


def lgcodestr(lgcstr):
    lgs = reisobrack.findall(lgcstr)
    if lgs:
        return lgs

    parts = [p.strip() for p in recomma.split(lgcstr)]
    codes = [p for p in parts if reiso.match(p)]
    if len(codes) == len(parts):
        return codes
    return []


rekillparen = re.compile(" \([^\)]*\)")
respcomsemic = re.compile("[;,]\s?")


def hhtypestr(s):
    return respcomsemic.split(rekillparen.sub("", s))


def sd(es):
    #most signficant piece of descriptive material
    #hhtype, pages, year
    mi = [(k, (hhtypestr(fields.get('hhtype', 'unknown')), fields.get('pages', ''), fields.get('year', ''))) for (k, (typ, fields)) in es.iteritems()]
    d = accd(mi)
    ordd = [sorted(((p, y, k, t) for (k, (p, y)) in d[t].iteritems()), reverse=True) for t in hhtyperank if d.has_key(t)]
    return ordd


def pcy(pagecountstr):
    #print pagecountstr
    if not pagecountstr:
        return 0
    return eval(pagecountstr) #int(takeafter(pagecountstr, "+"))


def accd(mi):
    r = defaultdict(dict)
    for (k, (hhts, pgs, year)) in mi:
        pci = pcy(pagecount(pgs))
        for t in hhts:
            r[t][k] = (pci/float(len(hhts)), year)
    return r


def byid(es, idf=lgcode, unsorted=False):
    def tftoids(tf):
        z = idf(tf)
        if unsorted and not z:
            return ['!Unsorted']
        return z
    return grp2([(cfn, k) for (k, tf) in es.iteritems() for cfn in tftoids(tf)])


hhtypes = load_hhtypes()
hhtyperank = [hht for (n, expl, abbv, bibabbv, hht) in sorted((info + (hht,) for (hht, info) in hhtypes.iteritems()), reverse=True)]
hhtype_to_n = dict((x, len(hhtyperank)-i) for (i, x) in enumerate(hhtyperank))
expl_to_hhtype = dict((expl, hht) for (hht, (n, expl, abbv, bibabbv)) in hhtypes.iteritems())


def sdlgs(e, unsorted=False):
    eindex = byid(e, unsorted=unsorted)
    fes = opv(eindex, lambda ks: dict((k, e[k]) for k in ks))
    fsd = opv(fes, sd)
    return (fsd, fes)


def lstat(e, unsorted=False):
    (lsd, lse) = sdlgs(e, unsorted=unsorted)
    return opv(lsd, lambda xs: (xs + [[[None]]])[0][0][-1])


def lstat_witness(e, unsorted=False):
    def statwit(xs):
        if len(xs) == 0:
            return (None, [])
        [(typ, ks)] = grp2([(t, k) for [p, y, k, t] in xs[0]]).items()
        return (typ, ks)
    (lsd, lse) = sdlgs(e, unsorted=unsorted)
    return opv(lsd, statwit)


def markconservative(m, trigs, ref, outfn="monstermarkrep.txt", blamefield="hhtype"):
    mafter = markall(m, trigs)
    ls = lstat(ref)
    lsafter = lstat_witness(mafter)
    log = []
    for (lg, (stat, wits)) in lsafter.items():
        if not ls.get(lg):
            print lg, "lacks status", [mafter[k][1]['srctrickle'] for k in wits]
            continue
        if hhtype_to_n[stat] > hhtype_to_n.get(ls[lg]):
            log = log + [
                (lg, [(mafter[k][1].get(blamefield, "No %s" % blamefield),
                       k,
                       mafter[k][1].get('title', 'no title'),
                       mafter[k][1]['srctrickle']) for k in wits], ls[lg])]
            for k in wits:
                (t, f) = mafter[k]
                if blamefield in f:
                    del f[blamefield]
                mafter[k] = (t, f)
    with UnicodeWriter(outfn, dialect='excel-tab') as writer:
        writer.writerows(((lg, was) + mis for (lg, miss, was) in log for mis in miss))
    return mafter


def markall(e, trigs, labelab=lambda x: x, verbose=True):
    clss = set(cls for (cls, _) in trigs.keys())
    ei = {k: (typ, fields) for k, (typ, fields) in e.items()
          if [c for c in clss if c not in fields]}

    wk = defaultdict(dict)
    for (k, (typ, fields)) in ei.items():
        for w in wrds(fields.get('title', '')):
            wk[w][k] = None

    u = defaultdict(lambda: defaultdict(dict))
    it = grp2([(tuple(sorted(disj)), clslab) for (clslab, t) in trigs.items() for disj in t])
    for (dj, clslabs) in it.items():
        mkst = [wk.get(w, {}).keys() for (stat, w) in dj if stat]
        mksf = [set(ei.keys()).difference(wk.get(w, [])) for (stat, w) in dj if not stat]
        mks = intersectall(mkst + mksf)
        for k in mks:
            for cl in clslabs:
                u[k][cl][dj] = None

    for (k, cd) in u.items():
        (t, f) = e[k]
        f2 = {a: b for a, b in f.items()}
        for (cls, lab), ms in cd.items():
            a = ';'.join(' and '.join(('' if stat else 'not ') + w for (stat, w) in m) for m in ms)
            f2[cls] = labelab(lab) + ' (computerized assignment from "' + a + '")'
            e[k] = (t, f2)
    if verbose:
        print "trigs", len(trigs)
        print "trigger-disjuncts", len(it)
        print "label classes", len(clss)
        print "unlabeled refs", len(ei)
        print "updates", len(u)
    return e
