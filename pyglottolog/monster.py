# monster.py - load, combine, annotate, and save bibfiles collection

"""Compiling the monster.

This script read the INI-file in the references/bibtex directory and combines
all .bib files configured there into a file called monster-utf8.bib with some
deduplication and annotation in the process.

1.    The bibfiles are combined in the following manner
1.1   All bibfiles are parsed and loaded into an sqlite3 database
1.2   A hash (keyid) is computed for each bib-entry
1.3.  For each hash, any bib-entries with that hash are merged
1.3.1 The merging takes place such that the priority setting of the file in the
      INI-file (in case of ties, filename and bibkey) decides which value takes
      precedence (hh.bib has the highest priority).
      Some fields (like note) are the concatenation of all original fields.
      The merged entries link back to the original(s) in the added
      src/srctrickle field.

2.    A glottolog_ref_id needs to be assigned to each merged entry
2.1   If a group of entries with the same glottolog_ref_id (last run) is split
      up into different hashes (this run), the new hash group which is most
      similar to the old group retains the glottolog_ref_id
2.2   If entries with different glottolog_ref_ids (last run) are merged into
      a single hash (this run), the old ref_id groups which are not most similar
      to the new group will be marked as being replaced by the most similar one
2.3   Once splitting/merging is resolved, remaining entries get glottolog_ref_ids
2.3.1 New glottolog_ref_id:s (from the private area above 300000) are doled out
      to bib-entries which do not have one

3.    Four steps of annotation are added to the merged entries, but only if
      there isn't already such annotation
3.1   macro_area is added based on the lgcode field if any. The mapping between
      lgcode:s and macro_area:s are taken from "../languoids/lginfo.csv"
3.2   hhtype is added based on a small set of trigger words that may occur in
      the titles of bibentries which are taken from 'alt4hhtype.ini'. A hhtype
      is not inferred if it would change the "descriptive status" of a language
      taken from hh.bib.
3.3   lgcode is added based on a large and dirty set of trigger words that
      may/may not occur in the titles of bibentries which are taken from
      'alt4lgcode.ini'. A lgcode is not inferred if it would change the
      "descriptive status" of a language taken from hh.bib.
3.4   inlg is added based on a small set of trigger words that may occur in the
      titles of bibentries which are specified in "../references/alt4inlg.ini".

4.    The assigned glottolog_ref_id are burned back into the original bib:s

5.    A final monster-utf8.bib is written
"""

import time

from pyglottolog.util import build_path, references_path
from pyglottolog import _bibfiles
from pyglottolog import _libmonster as bib
from pyglottolog import languoids

BIBFILES = _bibfiles.Collection()
PREVIOUS = references_path('monster.csv').as_posix()
REPLACEMENTS = build_path('monster-replacements.json').as_posix()
MONSTER = _bibfiles.BibFile(
    build_path('monster-utf8.bib').as_posix(), encoding='utf-8', sortkey='bibkey')

HHTYPE = references_path('alt4hhtype.ini').as_posix()
MARKHHTYPE = build_path('monstermark-hht.txt').as_posix()
MARKLGCODE = build_path('monstermark-lgc.txt').as_posix()


def intersectall(xs):
    a = set(xs[0])
    for x in xs[1:]:
        a.intersection_update(x)
    return a


def markconservative(m, trigs, ref, outfn="monstermarkrep.txt", blamefield="hhtype"):
    mafter = markall(m, trigs)
    ls = bib.lstat(ref)
    #print bib.fd(ls.values())
    lsafter = bib.lstat_witness(mafter)
    log = []
    for (lg, (stat, wits)) in lsafter.iteritems():
        if not ls.get(lg):
            print lg, "lacks status", [mafter[k][1]['srctrickle'] for k in wits]
            continue
        if bib.hhtype_to_n[stat] > bib.hhtype_to_n.get(ls[lg]):
            log = log + [(lg, [(mafter[k][1].get(blamefield, "No %s" % blamefield), k, mafter[k][1].get('title', 'no title'), mafter[k][1]['srctrickle']) for k in wits], ls[lg])]
            for k in wits:
                (t, f) = mafter[k]
                if f.has_key(blamefield):
                    del f[blamefield]
                mafter[k] = (t, f)
    bib.write_csv_rows(((lg, was) + mis for (lg, miss, was) in log for mis in miss), outfn, dialect='excel-tab')
    return mafter


def markall(e, trigs, labelab=lambda x: x):
    clss = set(cls for (cls, _) in trigs.iterkeys())
    ei = dict((k, (typ, fields)) for (k, (typ, fields)) in e.iteritems() if [c for c in clss if not fields.has_key(c)])

    wk = {}
    for (k, (typ, fields)) in ei.iteritems():
        for w in bib.wrds(fields.get('title', '')):
            bib.setd(wk, w, k)

    u = {}
    it = bib.indextrigs(trigs)
    for (dj, clslabs) in it.iteritems():
        mkst = [wk.get(w, {}).iterkeys() for (stat, w) in dj if stat]
        mksf = [set(ei.iterkeys()).difference(wk.get(w, [])) for (stat, w) in dj if not stat]
        mks = intersectall(mkst + mksf)
        for k in mks:
            for cl in clslabs:
                bib.setd3(u, k, cl, dj)

    for (k, cd) in u.iteritems():
        (t, f) = e[k]
        f2 = dict((a, b) for (a, b) in f.iteritems())
        for ((cls, lab), ms) in cd.iteritems():
            a = ';'.join(' and '.join(('' if stat else 'not ') + w for (stat, w) in m) for m in ms)
            f2[cls] = labelab(lab) + ' (computerized assignment from "' + a + '")'
            e[k] = (t, f2)
    print "trigs", len(trigs)
    print "trigger-disjuncts", len(it)
    print "label classes", len(clss)
    print "unlabeled refs", len(ei)
    print "updates", len(u)
    return e


def macro_area_from_lgcode(m):
    lgd = languoids.macro_area_from_hid()

    def inject_macro_area((typ, fields)):
        mas = set(lgd[x] for x in bib.lgcode((typ, fields)) if x in lgd and lgd[x])
        if mas:
            fields['macro_area'] = ', '.join(sorted(mas))
        return (typ, fields)
    
    return dict((k, inject_macro_area(tf)) for k, tf in m.iteritems())


def main(bibfiles=BIBFILES, previous=PREVIOUS, replacements=REPLACEMENTS, monster=MONSTER):
    print '%s open/rebuild bibfiles db' % time.ctime()
    db = bibfiles.to_sqlite()

    print '%s compile_monster' % time.ctime()
    m = dict(db.merged())

    print '%s load hh.bib' % time.ctime()
    hhbib = bibfiles['hh.bib'].load()

    # Annotate with macro_area from lgcode when lgcode is assigned manually
    print '%s macro_area_from_lgcode' % time.ctime()
    m = macro_area_from_lgcode(m)

    # Annotate with hhtype
    print '%s annotate hhtype' % time.ctime()
    hht = dict(((cls, bib.expl_to_hhtype[lab]), v) for ((cls, lab), v) in bib.load_triggers(HHTYPE).iteritems())
    m = markconservative(m, hht, hhbib, outfn=MARKHHTYPE, blamefield="hhtype")

    # Annotate with lgcode
    print '%s annotate lgcode' % time.ctime()
    lgc = languoids.load_triggers()
    m = markconservative(m, lgc, hhbib, outfn=MARKLGCODE, blamefield="hhtype")

    # Annotate with inlg
    print '%s add_inlg_e' % time.ctime()
    m = bib.add_inlg_e(m)

    # Print some statistics
    print time.ctime()
    print "# entries", len(m)
    print "with lgcode", sum(1 for t, f in m.itervalues() if 'lgcode' in f)
    print "with hhtype", sum(1 for t, f in m.itervalues() if 'hhtype' in f)
    print "with macro_area", sum(1 for t, f in m.itervalues() if 'macro_area' in f)

    # Update the CSV with the previous mappings for later reference
    print '%s update_previous' % time.ctime()
    db.to_csvfile(previous)

    print '%s save_replacements' % time.ctime()
    db.to_replacements(replacements)

    # Trickling back
    print '%s trickle' % time.ctime()
    db.trickle()

    # Save
    print '%s save as utf8' % time.ctime()
    monster.save(m, verbose=False)

    print '%s done.' % time.ctime()


if __name__ == '__main__':
    main()
