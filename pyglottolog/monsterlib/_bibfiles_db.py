# _bibfiles_db.py - load bibfiles into sqlite3, hash, assign ids (split/merge)

import sqlite3
import difflib
import operator
import itertools
import contextlib
import collections
import logging

from six import string_types, viewkeys
from clldutils.dsv import UnicodeWriter
from clldutils import jsonlib
from clldutils.path import remove

from pyglottolog.util import unique, group_first
from pyglottolog.monsterlib import _bibtex

log = logging.getLogger('pyglottolog')
UNION_FIELDS = {'fn', 'asjp_name', 'isbn'}
IGNORE_FIELDS = {'crossref', 'numnote', 'glotto_id'}


class Database(object):
    """Bibfile collection parsed into an sqlite3 file."""

    @classmethod
    def from_bibfiles(cls, bibfiles, filename, rebuild=False):
        """If needed, (re)build the db from the bibfiles, hash, split/merge."""
        if filename.exists():
            if not rebuild:
                self = cls(filename, bibfiles)
                if self.is_uptodate():
                    return self
            remove(filename)

        self = cls(filename, bibfiles)
        with self.connect(async=True) as conn:
            create_tables(conn)
            with conn:
                import_bibfiles(conn, bibfiles)
            entrystats(conn)
            fieldstats(conn)

            with conn:
                generate_hashes(conn)
            hashstats(conn)
            hashidstats(conn)

            with conn:
                assign_ids(conn)

        return self

    def __init__(self, filename, bibfiles):
        self.filename = filename.as_posix()
        self._bibfiles = bibfiles

    def is_uptodate(self, bibfiles=None, verbose=False):
        """Does the db have the same filenames, sizes, and mtimes as bibfiles?"""
        with self.connect() as conn:
            return compare_bibfiles(conn, bibfiles or self._bibfiles, verbose=verbose)

    def recompute(self, hashes=True, reload_priorities=True, verbose=True):
        """Call _libmonster.keyid for all entries, splits/merges -> new ids."""
        with self.connect(async=True) as conn:
            if hashes:
                with conn:
                    generate_hashes(conn)
                hashstats(conn)
                hashidstats(conn)
            if reload_priorities:
                with conn:
                    update_priorities(conn, self._bibfiles)
            with conn:
                assign_ids(conn, verbose=verbose)

    def to_bibfile(self, filename, encoding='utf-8', ):
        _bibtex.save(self.merged(), filename.as_posix(), sortkey=None, encoding=encoding)

    def to_csvfile(self, filename):
        """Write a CSV file with one row for each entry in each bibfile."""
        with self.connect() as conn:
            cursor = conn.execute(
                'SELECT filename, bibkey, hash, cast(id AS text) AS id '
                'FROM entry ORDER BY lower(filename), lower(bibkey), hash, id')
            with UnicodeWriter(filename) as writer:
                writer.writerow([col[0] for col in cursor.description])
                for row in cursor:
                    writer.writerow(row)

    def to_replacements(self, filename):
        """Write a JSON file with 301s from merged glottolog_ref_ids."""
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT refid AS id, id AS replacement '
                'FROM entry WHERE id != refid ORDER BY id')
            pairs = map(dict, cursor)
        with jsonlib.update(filename, default=[], indent=4) as repls:
            repls.extend(pairs)

    def to_hhmapping(self):
        with self.connect() as conn:
            assert allid(conn)
            query = 'SELECT bibkey, id FROM entry WHERE filename = ?'
            return dict(conn.execute(query, ('hh.bib',)))

    def trickle(self):
        """Write new/changed glottolog_ref_ids back into the bibfiles."""
        bibfiles = self._bibfiles
        if not self.is_uptodate(verbose=True):
            raise RuntimeError('trickle with an outdated db')  # pragma: no cover
        with self.connect() as conn:
            filenames = conn.execute(
                'SELECT name FROM file WHERE EXISTS '
                '(SELECT 1 FROM entry WHERE filename = name '
                'AND id != coalesce(refid, -1)) ORDER BY name').fetchall()
            for f, in filenames:
                b = bibfiles[f]
                entries = b.load()
                cursor = conn.execute(
                    'SELECT bibkey, cast(refid AS text), cast(id AS text) '
                    'FROM entry WHERE filename = ? AND id != coalesce(refid, -1) '
                    'ORDER BY lower(bibkey)', (f,))
                added = changed = 0
                for bibkey, refid, new in cursor:
                    entrytype, fields = entries[bibkey]
                    old = fields.pop('glottolog_ref_id', None)
                    assert old == refid
                    if old is None:
                        added += 1
                    else:
                        changed += 1
                    fields['glottolog_ref_id'] = new
                print('%d changed %d added in %s' % (changed, added, b.id))
                b.save(entries)

    def merged(self):
        """Yield merged (bibkey, (entrytype, fields)) entries."""
        for (id, hash), grp in self:
            entrytype, fields = self._merged_entry(grp)
            fields['glottolog_ref_id'] = id
            yield hash, (entrytype, fields)

    def connect(self, close=True, async=False):
        conn = sqlite3.connect(self.filename)
        if async:
            conn.execute('PRAGMA synchronous = OFF')
            conn.execute('PRAGMA journal_mode = MEMORY')
        if close:
            conn = contextlib.closing(conn)
        return conn

    def __iter__(self, chunksize=100):
        with self.connect() as conn:
            assert allid(conn)

            allpriority, = conn.execute(
                'SELECT NOT EXISTS '
                '(SELECT 1 FROM entry WHERE NOT EXISTS (SELECT 1 FROM file '
                'WHERE name = filename))').fetchone()
            assert allpriority

            assert onetoone(conn)

            get_id_hash, get_field = operator.itemgetter(0, 1), operator.itemgetter(2)
            for first, last in windowed(conn, 'id', chunksize):
                cursor = conn.execute(
                    'SELECT e.id, e.hash, v.field, v.value, v.filename, v.bibkey '
                    'FROM entry AS e '
                    'JOIN file AS f ON e.filename = f.name '
                    'JOIN value AS v ON e.filename = v.filename AND e.bibkey = v.bibkey '
                    'LEFT JOIN field AS d ON '
                    'v.filename = d.filename AND v.field = d.field '
                    'WHERE e.id BETWEEN ? AND ? '
                    'ORDER BY e.id, v.field, coalesce(d.priority, f.priority) '
                    'DESC, v.filename, v.bibkey',
                    (first, last))
                for id_hash, grp in itertools.groupby(cursor, get_id_hash):
                    yield (
                        id_hash,
                        [
                            (field, [(vl, fn, bk) for id, hs, fd, vl, fn, bk in g])
                            for field, g in itertools.groupby(grp, get_field)])

    def __getitem__(self, key):
        """Entry by (fn, bk) or merged entry by refid (old grouping) or hash (current grouping)."""
        if not isinstance(key, (tuple, int)) and not isinstance(key, string_types):
            raise ValueError  # pragma: no cover
        with self.connect() as conn:
            if isinstance(key, tuple):
                filename, bibkey = key
                entrytype, fields = self._entry(conn, filename, bibkey)
            else:
                grp = self._entrygrp(conn, key)
                entrytype, fields = self._merged_entry(grp)
            return key, (entrytype, fields)

    @staticmethod
    def _entry(conn, filename, bibkey, raw=False):
        cursor = conn.execute(
            'SELECT field, value FROM value '
            'WHERE filename = ? AND bibkey = ? ', (filename, bibkey))
        fields = dict(cursor)
        if not fields:
            raise KeyError((filename, bibkey))
        if raw:
            return fields
        entrytype = fields.pop('ENTRYTYPE')
        return entrytype, fields

    @staticmethod
    def _merged_entry(grp, union=UNION_FIELDS, ignore=IGNORE_FIELDS, raw=False):
        # TODO: consider implementing (a subset of?) onlyifnot logic:
        # {'address': 'publisher', 'lgfamily': 'lgcode', 'publisher': 'school',
        # 'journal': 'booktitle'}
        fields = {
            field: values[0][0] if field not in union
            else ', '.join(unique(vl for vl, fn, bk in values))
            for field, values in grp if field not in ignore}
        fields['src'] = ', '.join(sorted(set(
            fn.partition('.bib')[0] for field, values in grp for vl, fn, bk in values)))
        fields['srctrickle'] = ', '.join(sorted(set(
            '%s#%s' % (fn.partition('.bib')[0], bk)
            for field, values in grp for vl, fn, bk in values)))
        if raw:
            return fields
        entrytype = fields.pop('ENTRYTYPE')
        return entrytype, fields

    @staticmethod
    def _entrygrp(conn, key, get_field=operator.itemgetter(0)):
        col = 'refid' if isinstance(key, int) else 'hash'
        cursor = conn.execute((
            'SELECT v.field, v.value, v.filename, v.bibkey '
            'FROM entry AS e '
            'JOIN file AS f ON e.filename = f.name '
            'JOIN value AS v ON e.filename = v.filename AND e.bibkey = v.bibkey '
            'LEFT JOIN field AS d ON v.filename = d.filename AND v.field = d.field '
            'WHERE %s = ? '
            'ORDER BY v.field, coalesce(d.priority, f.priority) '
            'DESC, v.filename, v.bibkey'
        ) % col, (key,))
        grp = [
            (field, [(vl, fn, bk) for fd, vl, fn, bk in g])
            for field, g in itertools.groupby(cursor, get_field)]
        if not grp:
            raise KeyError(key)
        return grp

    def stats(self, field_files=False):
        with self.connect() as conn:
            entrystats(conn)
            fieldstats(conn, field_files)
            hashstats(conn)
            hashidstats(conn)

    @staticmethod
    def print_group(conn, group):
        for row in group:
            print(row)
        for row in group:
            print('\t%r, %r, %r, %r' % hashfields(conn, row[-2], row[-1]))

    def show_splits(self):
        with self.connect() as conn:
            cursor = conn.execute(
                'SELECT refid, hash, filename, bibkey '
                'FROM entry AS e WHERE EXISTS (SELECT 1 FROM entry '
                'WHERE refid = e.refid AND hash != e.hash) '
                'ORDER BY refid, hash, filename, bibkey')
            for refid, group in group_first(cursor):
                self.print_group(conn, group)
                old = self._merged_entry(self._entrygrp(conn, refid), raw=True)
                cand = [
                    (hs, self._merged_entry(self._entrygrp(conn, hs), raw=True))
                    for hs in unique(hs for ri, hs, fn, bk in group)]
                new = min(cand, key=lambda p: distance(old, p[1]))[0]
                print('-> %s\n' % new)

    def show_merges(self):
        with self.connect() as conn:
            cursor = conn.execute(
                'SELECT hash, refid, filename, bibkey '
                'FROM entry AS e WHERE EXISTS (SELECT 1 FROM entry '
                'WHERE hash = e.hash AND refid != e.refid) '
                'ORDER BY hash, refid DESC, filename, bibkey')
            for hash, group in group_first(cursor):
                self.print_group(conn, group)
                new = self._merged_entry(self._entrygrp(conn, hash), raw=True)
                cand = [
                    (ri, self._merged_entry(self._entrygrp(conn, ri), raw=True))
                    for ri in unique(ri for hs, ri, fn, bk in group)]
                old = min(cand, key=lambda p: distance(new, p[1]))[0]
                print('-> %s\n' % old)

    def _show(self, sql):
        with self.connect() as conn:
            cursor = conn.execute(sql)
            for hash, group in group_first(cursor):
                self.print_group(conn, group)
                print()

    def show_identified(self):
        self._show(
            'SELECT hash, refid, filename, bibkey '
            'FROM entry AS e WHERE EXISTS (SELECT 1 FROM entry '
            'WHERE refid IS NULL AND hash = e.hash) '
            'AND EXISTS (SELECT 1 FROM entry '
            'WHERE refid IS NOT NULL AND hash = e.hash) '
            'ORDER BY hash, refid IS NOT NULL, refid, filename, bibkey')

    def show_combined(self):
        self._show(
            'SELECT hash, filename, bibkey '
            'FROM entry AS e WHERE refid IS NULL AND EXISTS (SELECT 1 FROM entry '
            'WHERE refid IS NULL AND hash = e.hash '
            'AND (filename != e.filename OR bibkey != e.bibkey)) '
            'ORDER BY hash, filename, bibkey')


def create_tables(conn, page_size=32768):
    if page_size is not None:
        conn.execute('PRAGMA page_size = %d' % page_size)
    conn.execute(
        'CREATE TABLE file ('
        'name TEXT NOT NULL, '
        'size INTEGER NOT NULL, '
        'mtime DATETIME NOT NULL, '
        'priority INTEGER NOT NULL, '
        'PRIMARY KEY (name))')
    conn.execute(
        'CREATE TABLE field ('
        'filename TEXT NOT NULL, '
        'field TEXT NOT NULL, '
        'priority INTEGER NOT NULL, '
        'PRIMARY KEY (filename, field), '
        'FOREIGN KEY (filename) REFERENCES file(name))')
    conn.execute(
        'CREATE TABLE entry ('
        'filename TEXT NOT NULL, '
        'bibkey TEXT NOT NULL, '
        'refid INTEGER, '  # old glottolog_ref_id from bibfiles (previous hash groupings)
        'hash TEXT, '      # current groupings, m:n with refid (splits/merges)
        'srefid INTEGER, '  # split-resolved refid (every srefid maps to exactly one hash)
        'id INTEGER, '    # new glottolog_ref_id save to bibfiles (current hash groupings)
        'PRIMARY KEY (filename, bibkey), '
        'FOREIGN KEY (filename) REFERENCES file(name))')
    conn.execute('CREATE INDEX ix_refid ON entry(refid)')
    conn.execute('CREATE INDEX ix_hash ON entry(hash)')
    conn.execute('CREATE INDEX ix_srefid ON entry(srefid)')
    conn.execute('CREATE INDEX ix_id ON entry(id)')
    conn.execute(
        'CREATE TABLE value ('
        'filename TEXT NOT NULL, '
        'bibkey TEXT NOT NULL, '
        'field TEXT NOT NULL, '
        'value TEXT NOT NULL, '
        'PRIMARY KEY (filename, bibkey, field), '
        'FOREIGN KEY (filename, bibkey) REFERENCES entry(filename, bibkey))')


def import_bibfiles(conn, bibfiles):
    log.info('importing bibfiles into a new db')
    for b in bibfiles:
        conn.execute(
            'INSERT INTO file (name, size, mtime, priority)'
            'VALUES (?, ?, ?, ?)', (b.fname.name, b.size, b.mtime, b.priority))
        for e in b.iterentries():
            bibkey, entrytype, fields = e.key, e.type, e.fields
            conn.execute(
                'INSERT INTO entry (filename, bibkey, refid) VALUES (?, ?, ?)',
                (b.fname.name, bibkey, fields.get('glottolog_ref_id')))
            fields = itertools.chain([('ENTRYTYPE', entrytype)], fields.items())
            conn.executemany(
                'INSERT INTO value (filename, bibkey, field, value) VALUES (?, ?, ?, ?)',
                ((b.fname.name, bibkey, field, value) for field, value in fields))


def update_priorities(conn, bibfiles):
    inini = {b.fname.name for b in bibfiles}
    indb = {filename for filename, in conn.execute('SELECT name FROM file')}
    assert inini == indb
    for b in bibfiles:
        conn.execute(
            'UPDATE file SET priority = ? WHERE NAME = ?',
            (b.priority, b.fname.name))
    print('\n'.join('%d\t%s' % pn for pn in conn.execute(
        'SELECT priority, name FROM file ORDER BY priority DESC, name')))


def compare_bibfiles(conn, bibfiles, verbose=False):
    ondisk = collections.OrderedDict(
        (b.fname.name, (b.size, str(b.mtime))) for b in bibfiles)
    indb = collections.OrderedDict(
        (name, (size, mtime)) for name, size, mtime in
        conn.execute('SELECT name, size, mtime FROM file ORDER BY name'))
    if dict(ondisk) == dict(indb):
        return True
    if verbose:
        print('missing in db: %s' % [o for o in ondisk if o not in indb])
        print('missing on disk: %s' % [i for i in indb if i not in ondisk])
        print('differing in size/mtime: %s' % [
            o for o in ondisk if o in indb and ondisk[o] != indb[o]])
    return False


def allid(conn):
    result, = conn.execute(
        'SELECT NOT EXISTS (SELECT 1 FROM entry '
        'WHERE id IS NULL)').fetchone()
    return result


def onetoone(conn):
    result, = conn.execute(
        'SELECT NOT EXISTS '
        '(SELECT 1 FROM entry AS e WHERE EXISTS (SELECT 1 FROM entry '
        'WHERE hash = e.hash AND id != e.id '
        'OR id = e.id AND hash != e.hash))').fetchone()
    return result


def entrystats(conn):
    log.info('entry stats:\n' + '\n'.join('%s %d' % (f, n) for f, n in conn.execute(
        'SELECT filename, count(*) FROM entry GROUP BY filename')))
    log.info('%d entries total' % conn.execute('SELECT count(*) FROM entry').fetchone())


def fieldstats(conn, with_files=False):
    if with_files:
        print('\n'.join('%d\t%s\t%s' % (n, f, b) for f, n, b in conn.execute(
            'SELECT field, count(*) AS n, replace(group_concat(DISTINCT filename), ",", ", ") '
            'FROM value GROUP BY field ORDER BY n DESC, field')))
    else:
        print('\n'.join('%d\t%s' % (n, f) for f, n in conn.execute(
            'SELECT field, count(*) AS n '
            'FROM value GROUP BY field ORDER BY n DESC, field')))


def windowed_entries(conn, chunksize):
    for filename, in conn.execute('SELECT name FROM file ORDER BY name'):
        cursor = conn.execute(
            'SELECT bibkey FROM entry WHERE filename = ? '
            'ORDER BY bibkey', (filename,))
        while True:
            bibkeys = cursor.fetchmany(chunksize)
            if not bibkeys:
                cursor.close()
                break
            (first,), (last,) = bibkeys[0], bibkeys[-1]
            yield filename, first, last


def hashfields(conn, filename, bibkey):
    # also: extra_hash, volume (if not journal, booktitle, or series)
    cursor = conn.execute(
        'SELECT field, value FROM value '
        "WHERE field IN ('author', 'editor', 'year', 'title') "
        'AND filename = ? AND bibkey = ? ', (filename, bibkey))
    fields = dict(cursor)
    return tuple(fields.get(f) for f in ('author', 'editor', 'year', 'title'))


def generate_hashes(conn):
    from _libmonster import wrds, keyid

    words = collections.Counter()
    cursor = conn.execute('SELECT value FROM value WHERE field = ?', ('title',))
    while True:
        rows = cursor.fetchmany(10000)
        if not rows:
            break
        for title, in rows:
            words.update(wrds(title))
    # TODO: consider dropping stop words/hapaxes from freq. distribution
    print('%d title words (from %d tokens)' % (len(words), sum(words.values())))

    get_bibkey = operator.itemgetter(0)
    for filename, first, last in windowed_entries(conn, 500):
        rows = conn.execute(
            'SELECT bibkey, field, value FROM value '
            'WHERE filename = ? AND bibkey BETWEEN ? AND ? '
            'AND field != ? ORDER BY bibkey', (filename, first, last, 'ENTRYTYPE'))
        conn.executemany(
            'UPDATE entry SET hash = ? WHERE filename = ? AND bibkey = ?',
            ((keyid({k: v for b, k, v in grp}, words), filename, bibkey)
             for bibkey, grp in itertools.groupby(rows, get_bibkey)))


def hashstats(conn):
    print('%d\tdistinct keyids (from %d total)' % conn.execute(
        'SELECT count(DISTINCT hash), count(hash) FROM entry').fetchone())
    print('\n'.join(
        '%d\t%s (from %d distinct of %d total)' % row
        for row in conn.execute(
            'SELECT coalesce(c2.unq, 0), '
            'c1.filename, c1.dst, c1.tot FROM (SELECT filename, '
            'count(hash) AS tot, count(DISTINCT hash) AS dst  '
            'FROM entry GROUP BY filename) AS c1 LEFT JOIN '
            '(SELECT filename, count(DISTINCT hash) AS unq '
            'FROM entry AS e WHERE NOT EXISTS (SELECT 1 FROM entry '
            'WHERE hash = e.hash AND filename != e.filename) '
            'GROUP BY filename) AS c2 ON c1.filename = c2.filename '
            'ORDER BY c1.filename')))
    print('%d\tin multiple files' % conn.execute(
        'SELECT count(*) FROM '
        '(SELECT 1 FROM entry GROUP BY hash '
        'HAVING COUNT(DISTINCT filename) > 1)').fetchone())


def hashidstats(conn):
    print('\n'.join(
        '1 keyid %d glottolog_ref_ids: %d' % (hash_nid, n)
        for (hash_nid, n) in conn.execute(
            'SELECT hash_nid, count(*) AS n FROM '
            '(SELECT count(DISTINCT refid) AS hash_nid FROM entry WHERE hash IS NOT NULL '
            'GROUP BY hash HAVING count(DISTINCT refid) > 1) '
            'GROUP BY hash_nid ORDER BY n desc')))
    print('\n'.join(
        '1 glottolog_ref_id %d keyids: %d' % (id_nhash, n)
        for (id_nhash, n) in conn.execute(
            'SELECT id_nhash, count(*) AS n FROM '
            '(SELECT count(DISTINCT hash) AS id_nhash FROM entry WHERE refid IS NOT NULL '
            'GROUP BY refid HAVING count(DISTINCT hash) > 1) '
            'GROUP BY id_nhash ORDER BY n desc')))


def windowed(conn, col, chunksize):
    query = 'SELECT DISTINCT %(col)s FROM entry ORDER BY %(col)s' % {'col': col}
    cursor = conn.execute(query)
    while True:
        rows = cursor.fetchmany(chunksize)
        if not rows:
            cursor.close()
            break
        (first,), (last,) = rows[0], rows[-1]
        yield first, last


def assign_ids(conn, verbose=False):
    merged_entry, entrygrp = Database._merged_entry, Database._entrygrp

    allhash, = conn.execute(
        'SELECT NOT EXISTS (SELECT 1 FROM entry WHERE hash IS NULL)').fetchone()
    assert allhash

    print('%d entries' % conn.execute(
        'UPDATE entry SET id = NULL, srefid = refid').rowcount)

    # resolve splits: srefid = refid only for entries from the most similar hash group
    nsplit = 0
    cursor = conn.execute(
        'SELECT refid, hash, filename, bibkey FROM entry AS e '
        'WHERE EXISTS (SELECT 1 FROM entry WHERE refid = e.refid AND hash != e.hash) '
        'ORDER BY refid, hash, filename, bibkey')
    for refid, group in group_first(cursor):
        old = merged_entry(entrygrp(conn, refid), raw=True)
        nsplit += len(group)
        cand = [
            (hs, merged_entry(entrygrp(conn, hs), raw=True))
            for hs in unique(hs for ri, hs, fn, bk in group)]
        new = min(cand, key=lambda p: distance(old, p[1]))[0]
        separated = conn.execute(
            'UPDATE entry SET srefid = NULL WHERE refid = ? AND hash != ?',
            (refid, new)).rowcount
        if verbose:
            for row in group:
                print(row)
            for ri, hs, fn, bk in group:
                print('\t%r, %r, %r, %r' % hashfields(conn, fn, bk))
            print('-> %s' % new)
            print('%d: %d separated from %s\n' % (refid, separated, new))
    print('%d splitted' % nsplit)

    nosplits, = conn.execute(
        'SELECT NOT EXISTS (SELECT 1 FROM entry AS e '
        'WHERE EXISTS (SELECT 1 FROM entry WHERE srefid = e.srefid AND hash != e.hash))')\
        .fetchone()
    assert nosplits

    # resolve merges: id = srefid of the most similar srefid group
    nmerge = 0
    cursor = conn.execute(
        'SELECT hash, srefid, filename, bibkey FROM entry AS e '
        'WHERE EXISTS (SELECT 1 FROM entry WHERE hash = e.hash AND srefid != e.srefid) '
        'ORDER BY hash, srefid DESC, filename, bibkey')
    for hash, group in group_first(cursor):
        new = merged_entry(entrygrp(conn, hash), raw=True)
        nmerge += len(group)
        cand = [
            (ri, merged_entry(entrygrp(conn, ri), raw=True))
            for ri in unique(ri for hs, ri, fn, bk in group)]
        old = min(cand, key=lambda p: distance(new, p[1]))[0]
        merged = conn.execute(
            'UPDATE entry SET id = ? WHERE hash = ? AND srefid != ?',
            (old, hash, old)).rowcount
        if verbose:
            for row in group:
                print(row)
            for hs, ri, fn, bk in group:
                print('\t%r, %r, %r, %r' % hashfields(conn, fn, bk))
            print('-> %s' % old)
            print('%s: %d merged into %d\n' % (hash, merged, old))
    print('%d merged' % nmerge)

    # unchanged entries
    print('%d unchanged' % conn.execute(
        'UPDATE entry SET id = srefid '
        'WHERE id IS NULL AND srefid IS NOT NULL').rowcount)

    nomerges, = conn.execute(
        'SELECT NOT EXISTS (SELECT 1 FROM entry AS e '
        'WHERE EXISTS (SELECT 1 FROM entry WHERE hash = e.hash AND id != e.id))')\
        .fetchone()
    assert nomerges

    # identified
    print('%d identified (new/separated)' % conn.execute(
        'UPDATE entry '
        'SET id = '
        '(SELECT id FROM entry AS e WHERE e.hash = entry.hash AND e.id IS NOT NULL) '
        'WHERE refid IS NULL AND id IS NULL AND EXISTS '
        '(SELECT 1 FROM entry AS e WHERE e.hash = entry.hash AND e.id IS NOT NULL)')
        .rowcount)

    # assign new ids to hash groups of separated/new entries
    nextid, = conn.execute('SELECT coalesce(max(refid), 0) + 1 FROM entry').fetchone()
    cursor = conn.execute(
        'SELECT hash FROM entry WHERE id IS NULL GROUP BY hash ORDER BY hash')
    print(
        '%d new ids (new/separated)' % conn.executemany(
            'UPDATE entry SET id = ? WHERE hash = ?',
            ((id, hash) for id, (hash,) in enumerate(cursor, nextid))).rowcount)

    assert allid(conn)
    assert onetoone(conn)

    # supersede relation
    superseded, = conn.execute('SELECT count(*) FROM entry WHERE id != srefid').fetchone()
    print('%d supersede pairs' % superseded)


def distance(left, right, weight={'author': 3, 'year': 3, 'title': 3, 'ENTRYTYPE': 2}):
    """Simple measure of the difference between two bibtex-field dicts."""
    if not (left or right):
        return 0.0

    keys = viewkeys(left) & viewkeys(right)
    if not keys:
        return 1.0

    weights = {k: weight.get(k, 1) for k in keys}
    ratios = (
        w * difflib.SequenceMatcher(None, left[k], right[k]).ratio()
        for k, w in weights.items())
    return 1 - (sum(ratios) / sum(weights.values()))


def _test_merge():  # pragma: no cover
    import sqlalchemy as sa

    engine = sa.create_engine('postgresql://postgres@/overrides')
    metadata = sa.MetaData()
    overrides = sa.Table(
        'overrides', metadata,
        sa.Column('hash', sa.Text, primary_key=True),
        sa.Column('field', sa.Text, primary_key=True),
        sa.Column('file1', sa.Text, primary_key=True),
        sa.Column('bibkey1', sa.Text, primary_key=True),
        sa.Column('file2', sa.Text, primary_key=True),
        sa.Column('bibkey2', sa.Text, primary_key=True),
        sa.Column('value1', sa.Text),
        sa.Column('value2', sa.Text))
    metadata.drop_all(engine)
    metadata.create_all(engine)
    insert_ov = overrides.insert(bind=engine).execute

    for hash, grp in Database():
        for field, values in grp:
            if field in UNION_FIELDS:
                continue
            value1, file1, bibkey1 = values[0]
            for value2, file2, bibkey2 in values[1:]:
                if value1.lower() != value2.lower():
                    insert_ov(
                        hash=hash, field=field, value1=value1, value2=value2,
                        file1=file1, bibkey1=bibkey1, file2=file2, bibkey2=bibkey2)

    query = sa.select([
        overrides.c.file1, overrides.c.file2, sa.func.count().label('n')
    ])\
        .where(overrides.c.file1 != overrides.c.file2)\
        .group_by(overrides.c.file1, overrides.c.file2)\
        .order_by(sa.literal_column('n'), overrides.c.file1, overrides.c.file2)

    print(
        '\n'.join('%d\t%s\t%s' % (n, f1, f2) for f1, f2, n in engine.execute(query)))
