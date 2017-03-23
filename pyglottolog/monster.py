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
      lgcode:s and macro_area:s are taken from "../languoids/tree/**.ini"
3.2   hhtype is added based on a small set of trigger words that may occur in
      the titles of bibentries which are taken from 'hhtype.ini'. A hhtype
      is not inferred if it would change the "descriptive status" of a language
      taken from hh.bib.
3.3   lgcode is added based on a large and dirty set of trigger words that
      may/may not occur in the titles of bibentries which are taken from
      '../languoids/tree/**.ini'. A lgcode is not inferred if it would change the
      "descriptive status" of a language taken from hh.bib.
3.4   inlg is added based on a small set of trigger words that may occur in the
      titles of bibentries which are specified in "../languoids/tree/**.ini".

4.    The assigned glottolog_ref_id are burned back into the original bib:s

5.    A final monster-utf8.bib is written
"""
from __future__ import print_function
import time
from collections import Counter
import logging

from pyglottolog.monsterlib._libmonster import lgcode, add_inlg_e, markconservative
from pyglottolog.references import BibFile


def macro_area_from_lgcode(m, lgd):
    def inject_macro_area(arg):
        typ, fields = arg
        mas = set(lgd[x] for x in lgcode((typ, fields)) if x in lgd and lgd[x])
        if mas:
            fields['macro_area'] = ', '.join(sorted(mas))
        return typ, fields

    return {k: inject_macro_area(tf) for k, tf in m.items()}


def compile(api, log=None, rebuild=False):
    log = log or logging.getLogger('pyglottolog')
    previous = api.references_path('monster.csv')
    replacements = api.references_path('replacements.json')
    monster = BibFile(
        fname=api.build_path('monster-utf8.bib'), encoding='utf-8', sortkey='bibkey')

    log.info('%s open/rebuild bibfiles db' % time.ctime())
    db = api.bibfiles.to_sqlite(api.build_path('_bibfiles.sqlite3'), rebuild=rebuild)

    log.info('%s compile_monster' % time.ctime())
    m = dict(db.merged())

    log.info('%s load hh.bib' % time.ctime())
    hhbib = api.bibfiles['hh.bib'].load()

    # Annotate with macro_area from lgcode when lgcode is assigned manually
    log.info('%s macro_area_from_lgcode' % time.ctime())
    m = macro_area_from_lgcode(m, api.macroarea_map)

    # Annotate with hhtype
    log.info('%s annotate hhtype' % time.ctime())
    m = markconservative(
        m,
        api.hhtypes.triggers,
        hhbib,
        api.hhtypes,
        api.build_path('monstermark-hht.txt'),
        rank=lambda l: api.hhtypes[l])

    # Annotate with lgcode
    log.info('%s annotate lgcode' % time.ctime())
    m = markconservative(
        m,
        api.triggers['lgcode'],
        hhbib,
        api.hhtypes,
        api.build_path('monstermark-lgc.txt'))

    # Annotate with inlg
    log.info('%s add_inlg_e' % time.ctime())
    m = add_inlg_e(m, api.triggers['inlg'])

    # Print some statistics
    stats = Counter()
    log.info(time.ctime())
    for t, f in m.values():
        stats.update(['entry'])
        for field in ['lgcode', 'hhtype', 'macro_area']:
            if field in f:
                stats.update([field])
    log.info("# entries {0}".format(stats['entry']))
    for field in ['lgcode', 'hhtype', 'macro_area']:
        log.info("with {0}: {1}".format(field, stats[field]))

    # Update the CSV with the previous mappings for later reference
    log.info('%s update_previous' % time.ctime())
    db.to_csvfile(previous)

    log.info('%s save_replacements' % time.ctime())
    db.to_replacements(replacements)

    # Trickling back
    log.info('%s trickle' % time.ctime())
    db.trickle()

    # Save
    log.info('%s save as utf8' % time.ctime())
    monster.save(m)

    log.info('%s done.' % time.ctime())
