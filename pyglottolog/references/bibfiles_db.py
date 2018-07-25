# bibfiles_db.py - load bibfiles into sqlite3, hash, assign ids (split/merge)

from __future__ import print_function

import logging
import difflib
import operator
import functools
import itertools
import contextlib
import collections

from six import string_types, iteritems, itervalues, viewkeys
from six.moves import map

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative  # noqa: F401
from clldutils import path, dsv, jsonlib

from . import bibtex
from ..util import unique, group_first

__all__ = ['Database']

UNION_FIELDS = {'fn', 'asjp_name', 'isbn'}

IGNORE_FIELDS = {'crossref', 'numnote', 'glotto_id'}

log = logging.getLogger('pyglottolog')


class Database(object):
    """Bibfile collection parsed into an sqlite3 database."""

    @classmethod
    def from_bibfiles(cls, bibfiles, filepath, rebuild=False, page_size=32768):
        """If needed, (re)build the db from the bibfiles, hash, split/merge."""
        self = cls(filepath)

        if self.filepath.exists():
            if not rebuild and self.is_uptodate(bibfiles):
                return self
            path.remove(self.filepath)

        with self.engine.connect() as conn:
            if page_size is not None:
                conn.execute('PRAGMA page_size = %d' % page_size)
            Model.metadata.create_all(conn)

        with self.engine.connect() as conn:
            conn.execute('PRAGMA synchronous = OFF')
            conn.execute('PRAGMA journal_mode = MEMORY')
            conn = conn.execution_options(compiled_cache={})

            with conn.begin():
                import_bibfiles(conn, bibfiles)

            Entry.stats(conn)
            Value.fieldstats(conn)

            with conn.begin():
                generate_hashes(conn)

            Entry.hashstats(conn)
            Entry.hashidstats(conn)

            with conn.begin():
                assign_ids(conn)

        return self

    def __init__(self, filepath):
        if not isinstance(filepath, path.Path):
            filepath = path.Path(filepath)
        self.filepath = filepath
        self.engine = sa.create_engine('sqlite:///%s' % filepath, paramstyle='qmark')

    def is_uptodate(self, bibfiles, verbose=False):
        """Does the db have the same filenames, sizes, and mtimes as the given bibfiles?"""
        return File.same_as(self.engine, bibfiles, verbose=verbose)

    def stats(self, field_files=False):
        Entry.stats(self.engine)
        Value.fieldstats(self.engine, field_files)
        Entry.hashstats(self.engine)
        Entry.hashidstats(self.engine)

    def execute(self, statement, closing=True):
        cursor = self.engine.execute(statement)
        if closing:
            cursor = contextlib.closing(cursor)
        return cursor

    def to_bibfile(self, filepath, encoding='utf-8'):
        bibtex.save(self.merged(), str(filepath), sortkey=None, encoding=encoding)

    def to_csvfile(self, filename, encoding='utf-8', dialect='excel'):
        """Write a CSV file with one row for each entry in each bibfile."""
        select_rows = sa.select(
            [
                File.name.label('filename'), Entry.bibkey, Entry.hash,
                sa.cast(Entry.id, sa.Text).label('id'),
            ]).select_from(sa.join(File, Entry))\
            .order_by(sa.func.lower(File.name), sa.func.lower(Entry.bibkey), Entry.hash, Entry.id)
        with self.execute(select_rows) as cursor:
            with dsv.UnicodeWriter(filename, encoding=encoding, dialect=dialect) as writer:
                writer.writerow(cursor.keys())
                for row in cursor:
                    writer.writerow(row)

    def to_replacements(self, filename):
        """Write a JSON file with 301s from merged glottolog_ref_ids."""
        select_pairs = sa.select([Entry.refid.label('id'), Entry.id.label('replacement')])\
            .where(Entry.id != Entry.refid)\
            .order_by(Entry.id)
        with self.execute(select_pairs) as cursor:
            pairs = list(map(dict, cursor))
        with jsonlib.update(filename, default=[], indent=4) as repls:
            repls.extend(pairs)

    def trickle(self, bibfiles):
        """Write new/changed glottolog_ref_ids back into the given bibfiles."""
        assert Entry.allid(self.engine)
        if not self.is_uptodate(bibfiles, verbose=True):
            raise RuntimeError('trickle with an outdated db')  # pragma: no cover
        changed = (Entry.id != sa.func.coalesce(Entry.refid, -1))
        select_files = sa.select([File.pk, File.name])\
            .where(sa.exists().where(Entry.file_pk == File.pk).where(changed))\
            .order_by(File.name)
        select_changed = sa.select(
            [
                Entry.bibkey,
                sa.cast(Entry.refid, sa.Text).label('refid'),
                sa.cast(Entry.id, sa.Text).label('id'),
            ]).where(Entry.file_pk == sa.bindparam('file_pk')).where(changed)\
            .order_by(sa.func.lower(Entry.bibkey))
        with self.engine.connect() as conn:
            for file_pk, filename in conn.execute(select_files).fetchall():
                b = bibfiles[filename]
                entries = b.load()
                added = changed = 0
                for bibkey, refid, new in conn.execute(select_changed, file_pk=file_pk):
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
            fields['glottolog_ref_id'] = u'%d' % id
            yield hash, (entrytype, fields)

    def __iter__(self, chunksize=100):
        assert Entry.allid(self.engine)
        assert Entry.onetoone(self.engine)
        select_values = sa.select(
            [
                Entry.id, Entry.hash, Value.field, Value.value, File.name, Entry.bibkey,
            ]).select_from(sa.join(Entry, File).join(Value))\
            .where(sa.between(Entry.id, sa.bindparam('first'), sa.bindparam('last')))\
            .order_by(Entry.id, Value.field, File.priority.desc(), File.name, Entry.bibkey)
        get_id_hash, get_field = operator.itemgetter(0, 1), operator.itemgetter(2)
        with self.engine.connect() as conn:
            for first, last in Entry.windowed(conn, 'id', chunksize):
                cursor = conn.execute(select_values, first=first, last=last)
                for id_hash, grp in itertools.groupby(cursor, get_id_hash):
                    yield (
                        id_hash,
                        [
                            (field, [(vl, fn, bk) for _, _, _, vl, fn, bk in g])
                            for field, g in itertools.groupby(grp, get_field)])

    def __getitem__(self, key, _types=(tuple, int) + string_types):
        """Entry by (fn, bk) or merged entry by refid (old grouping) or hash (current grouping)."""
        if not isinstance(key, _types):
            raise ValueError  # pragma: no cover
        if isinstance(key, tuple):
            filename, bibkey = key
            entrytype, fields = self._entry(self.engine, filename, bibkey)
        else:
            grp = self._entrygrp(self.engine, key)
            entrytype, fields = self._merged_entry(grp)
        return key, (entrytype, fields)

    @staticmethod
    def _entry(bind, filename, bibkey):
        select_items = sa.select([Value.field, Value.value], bind=bind)\
            .select_from(sa.join(Value, Entry).join(File))\
            .where(File.name == filename)\
            .where(Entry.bibkey == bibkey)
        fields = dict(iter(select_items.execute()))
        if not fields:
            raise KeyError((filename, bibkey))
        return fields.pop('ENTRYTYPE'), fields

    @staticmethod
    def _merged_entry(grp, union=UNION_FIELDS, ignore=IGNORE_FIELDS, raw=False):
        # TODO: consider implementing (a subset of?) onlyifnot logic:
        # {'address': 'publisher', 'lgfamily': 'lgcode', 'publisher': 'school',
        # 'journal': 'booktitle'}
        fields = {
            field: values[0][0] if field not in union
            else ', '.join(unique(vl for vl, _, _ in values))
            for field, values in grp if field not in ignore}
        fields['src'] = ', '.join(sorted(set(
            fn.rpartition('.bib')[0] or fn for _, values in grp for _, fn, _ in values)))
        fields['srctrickle'] = ', '.join(sorted(set(
            '%s#%s' % (fn.rpartition('.bib')[0] or fn, bk)
            for _, values in grp for _, fn, bk in values)))
        if raw:
            return fields
        entrytype = fields.pop('ENTRYTYPE')
        return entrytype, fields

    @staticmethod
    def _entrygrp(bind, key, get_field=operator.itemgetter(0)):
        select_values = sa.select(
            [
                Value.field, Value.value, File.name, Entry.bibkey
            ],
            bind=bind).select_from(sa.join(Entry, File).join(Value))\
            .where((Entry.refid if isinstance(key, int) else Entry.hash) == key)\
            .order_by(Value.field, File.priority.desc(), File.name, Entry.bibkey)
        grouped = itertools.groupby(select_values.execute(), get_field)
        grp = [(field, [(vl, fn, bk) for _, vl, fn, bk in g]) for field, g in grouped]
        if not grp:
            raise KeyError(key)
        return grp

    def show_splits(self):
        other = sa.orm.aliased(Entry)
        select_entries = sa.select(
            [
                Entry.refid, Entry.hash, File.name.label('filename'), Entry.bibkey,
            ]).select_from(sa.join(Entry, File))\
            .order_by(Entry.refid, Entry.hash, File.name, Entry.bibkey)\
            .where(sa.exists().where(other.refid == Entry.refid).where(other.hash != Entry.hash))
        with self.engine.connect() as conn:
            for refid, group in group_first(conn.execute(select_entries)):
                self._print_group(conn, group)
                old = self._merged_entry(self._entrygrp(conn, refid), raw=True)
                cand = [
                    (hs, self._merged_entry(self._entrygrp(conn, hs), raw=True))
                    for hs in unique(hs for _, hs, _, _ in group)]
                new = min(cand, key=lambda p: distance(old, p[1]))[0]
                print('-> %s\n' % new)

    def show_merges(self):
        other = sa.orm.aliased(Entry)
        select_entries = sa.select(
            [
                Entry.hash, Entry.refid, File.name.label('filename'), Entry.bibkey,
            ]).select_from(sa.join(Entry, File))\
            .order_by(Entry.hash, Entry.refid.desc(), File.name, Entry.bibkey)\
            .where(sa.exists().where(other.hash == Entry.hash).where(other.refid != Entry.refid))
        with self.engine.connect() as conn:
            for hash, group in group_first(conn.execute(select_entries)):
                self._print_group(conn, group)
                new = self._merged_entry(self._entrygrp(conn, hash), raw=True)
                cand = [
                    (ri, self._merged_entry(self._entrygrp(conn, ri), raw=True))
                    for ri in unique(ri for _, ri, _, _ in group)]
                old = min(cand, key=lambda p: distance(new, p[1]))[0]
                print('-> %s\n' % old)

    @staticmethod
    def _print_group(conn, group, out=print):
        for row in group:
            out(row)
        for row in group:
            out('\t%r, %r, %r, %r' % Value.hashfields(conn, row['filename'], row['bibkey']))

    def _show(self, sql):
        with self.engine.connect() as conn:
            cursor = conn.execute(sql)
            for hash, group in group_first(cursor):
                self._print_group(conn, group)
                print()

    def show_identified(self):
        other = sa.orm.aliased(Entry)
        select_entries = sa.select(
            [
                Entry.hash, Entry.refid, File.name.label('filename'), Entry.bibkey,
            ]).select_from(sa.join(Entry, File))\
            .order_by(Entry.hash, Entry.refid != sa.null(), Entry.refid, File.name, Entry.bibkey)\
            .where(sa.exists().where(other.refid == sa.null()).where(other.hash == Entry.hash))\
            .where(sa.exists().where(other.refid != sa.null()).where(other.hash == Entry.hash))
        self._show(select_entries)

    def show_combined(self):
        other = sa.orm.aliased(Entry)
        select_entries = sa.select(
            [
                Entry.hash, File.name.label('filename'), Entry.bibkey,
            ]).select_from(sa.join(Entry, File))\
            .order_by(Entry.hash, File.name, Entry.bibkey)\
            .where(Entry.refid == sa.null())\
            .where(sa.exists().where(other.refid == sa.null()).where(other.hash == Entry.hash))
        self._show(select_entries)


Model = sa.ext.declarative.declarative_base()


class File(Model):

    __tablename__ = 'file'

    pk = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.Text, nullable=False, unique=True)
    size = sa.Column(sa.Integer, nullable=False)
    mtime = sa.Column(sa.DateTime, nullable=False)
    priority = sa.Column(sa.Integer, nullable=False)

    @classmethod
    def same_as(cls, bind, bibfiles, verbose=False):
        ondisk = collections.OrderedDict(
            (b.fname.name, (b.size, b.mtime)) for b in bibfiles)
        select_files = sa.select([cls.name, cls.size, cls.mtime], bind=bind).order_by(cls.name)
        indb = collections.OrderedDict(
            (name, (size, mtime)) for name, size, mtime in select_files.execute())
        if dict(ondisk) == dict(indb):
            return True
        if verbose:
            ondisk_names, indb_names = (viewkeys(d) for d in (ondisk, indb))
            print('missing in db: %s' % list(ondisk_names - indb_names))
            print('missing on disk: %s' % list(indb_names - ondisk_names))
            print('differing in size/mtime: %s' % [
                o for o in (ondisk_names & indb_names) if ondisk[o] != indb[o]])
        return False


class Entry(Model):

    __tablename__ = 'entry'

    pk = sa.Column(sa.Integer, primary_key=True)
    file_pk = sa.Column(sa.ForeignKey('file.pk'), nullable=False)
    bibkey = sa.Column(sa.Text, nullable=False)
    # old glottolog_ref_id from bibfiles (previous hash groupings)
    refid = sa.Column(sa.Integer, index=True)
    # current groupings, m:n with refid (splits/merges):
    hash = sa.Column(sa.Text, index=True)
    # split-resolved refid (every srefid maps to exactly one hash):
    srefid = sa.Column(sa.Integer, index=True)
    # new glottolog_ref_id save to bibfiles (current hash groupings):
    id = sa.Column(sa.Integer, index=True)

    __table_args__ = (
        sa.UniqueConstraint(file_pk, bibkey),
    )

    @classmethod
    def allhash(cls, bind):
        return sa.select([~sa.exists().where(cls.hash == sa.null())], bind=bind).scalar()

    @classmethod
    def allid(cls, bind):
        return sa.select([~sa.exists().where(cls.id == sa.null())], bind=bind).scalar()

    @classmethod
    def onetoone(cls, bind):
        other = sa.orm.aliased(cls)
        return sa.select([~sa.exists().select_from(cls).where(sa.exists().where(sa.or_(
            sa.and_(other.hash == cls.hash, other.id != cls.id),
            sa.and_(other.id == cls.hash, other.hash != cls.hash))))], bind=bind).scalar()

    @classmethod
    def stats(cls, bind, out=log.info):
        out('entry stats:')
        select_n = sa.select([File.name.label('filename'), sa.func.count().label('n')], bind=bind)\
            .select_from(sa.join(cls, File)).group_by(cls.file_pk)
        out('\n'.join('%(filename)s %(n)d' % r for r in select_n.execute()))
        select_total = sa.select([sa.func.count()], bind=bind).select_from(cls)
        out('%d entries total' % select_total.scalar())

    @classmethod
    def hashstats(cls, bind, out=print):
        select_total = sa.select(
            [
                sa.func.count(cls.hash.distinct()).label('distinct'),
                sa.func.count(cls.hash).label('total'),
            ],
            bind=bind)
        tmpl = '%(distinct)d\tdistinct keyids (from %(total)d total)'
        out(tmpl % select_total.execute().first())

        sq1 = sa.select(
            [
                File.name.label('filename'),
                sa.func.count(cls.hash.distinct()).label('distinct'),
                sa.func.count(cls.hash).label('total'),
            ]).select_from(sa.join(cls, File))\
            .group_by(cls.file_pk).alias()
        other = sa.orm.aliased(cls)
        sq2 = sa.select(
            [
                File.name.label('filename'),
                sa.func.count(cls.hash.distinct()).label('unique'),
            ]).select_from(sa.join(cls, File))\
            .where(
                ~sa.exists()
                .where(other.hash == cls.hash)
                .where(other.file_pk != cls.file_pk))\
            .group_by(cls.file_pk).alias()
        select_files = sa.select(
            [
                sa.func.coalesce(sq2.c.unique, 0).label('unique'),
                sq1.c.filename, sq1.c.distinct, sq1.c.total,
            ],
            bind=bind)\
            .select_from(sq1.outerjoin(sq2, sq1.c.filename == sq2.c.filename))\
            .order_by(sq1.c.filename)
        tmpl = '%(unique)d\t%(filename)s (from %(distinct)d distinct of %(total)d total)'
        out('\n'.join(tmpl % r for r in select_files.execute()))

        select_multiple = sa.select([sa.func.count()], bind=bind)\
            .select_from(
                sa.select([1])
                .select_from(cls)
                .group_by(cls.hash)
                .having(sa.func.count(cls.file_pk.distinct()) > 1))
        out('%d\tin multiple files' % select_multiple.scalar())

    @classmethod
    def hashidstats(cls, bind, out=print):
        sq = sa.select([sa.func.count(cls.refid.distinct()).label('hash_nid')])\
            .where(cls.hash != sa.null())\
            .group_by(cls.hash)\
            .having(sa.func.count(cls.refid.distinct()) > 1).alias()
        select_nid = sa.select([sq.c.hash_nid, sa.func.count().label('n')], bind=bind)\
            .group_by(sq.c.hash_nid).order_by(sa.desc('n'))
        tmpl = '1 keyid %(hash_nid)d glottolog_ref_ids: %(n)d'
        out('\n'.join(tmpl % r for r in select_nid.execute()))

        sq = sa.select([sa.func.count(cls.hash.distinct()).label('id_nhash')])\
            .where(cls.refid != sa.null())\
            .group_by(cls.refid)\
            .having(sa.func.count(cls.hash.distinct()) > 1).alias()
        select_nhash = sa.select([sq.c.id_nhash, sa.func.count().label('n')], bind=bind)\
            .group_by(sq.c.id_nhash).order_by(sa.desc('n'))
        tmpl = '1 glottolog_ref_id %(id_nhash)d keyids: %(n)d'
        out('\n'.join(tmpl % r for r in select_nhash.execute()))

    @classmethod
    def windowed(cls, bind, colname, chunksize):
        col = cls.__table__.c[colname]
        select_col = sa.select([col.distinct()], bind=bind).order_by(col)
        with contextlib.closing(select_col.execute()) as cursor:
            for rows in iter(functools.partial(cursor.fetchmany, chunksize), []):
                (first,), (last,) = rows[0], rows[-1]
                yield first, last


class Value(Model):

    __tablename__ = 'value'

    entry_pk = sa.Column(sa.ForeignKey('entry.pk'), primary_key=True)
    field = sa.Column(sa.Text, primary_key=True)
    value = sa.Column(sa.Text, nullable=False)

    @classmethod
    def hashfields(cls, bind, filename, bibkey, _fields=('author', 'editor', 'year', 'title')):
        # also: extra_hash, volume (if not journal, booktitle, or series)
        select_items = sa.select([cls.field, cls.value], bind=bind)\
            .select_from(sa.join(Value, Entry).join(File))\
            .where(File.name == filename)\
            .where(Entry.bibkey == bibkey)\
            .where(cls.field.in_(_fields))
        fields = dict(iter(select_items.execute()))
        return tuple(fields.get(f) for f in _fields)

    @classmethod
    def fieldstats(cls, bind, with_files=False, out=print):
        select_n = sa.select([cls.field, sa.func.count().label('n')], bind=bind)\
            .group_by(cls.field).order_by(sa.desc('n'), cls.field)
        tmpl = '%(n)d\t%(field)s'
        if with_files:
            select_n = select_n.select_from(sa.join(Value, Entry).join(File))
            files = sa.func.replace(sa.func.group_concat(File.name.distinct()), ',', ', ')
            select_n.append_column(files.label('files'))
            tmpl += '\t%(files)s'
        out('\n'.join(tmpl % r for r in select_n.execute()))


def import_bibfiles(conn, bibfiles):
    log.info('importing bibfiles into a new db')
    assert conn.dialect.paramstyle == 'qmark'
    insert_file = sa.insert(File, bind=conn)\
        .compile(column_keys=['name', 'size', 'mtime', 'priority']).string
    insert_entry = sa.insert(Entry, bind=conn)\
        .compile(column_keys=['file_pk', 'bibkey', 'refid']).string
    insert_value = sa.insert(Value, bind=conn)\
        .compile(column_keys=['entry_pk', 'field', 'value']).string

    insert_file = functools.partial(conn.connection.execute, insert_file)
    insert_entry = functools.partial(conn.connection.execute, insert_entry)
    insert_values = functools.partial(conn.connection.executemany, insert_value)
    for b in bibfiles:
        file_pk = insert_file((b.fname.name, b.size, b.mtime, b.priority)).lastrowid
        for e in b.iterentries():
            bibkey = e.key
            entry_pk = insert_entry((file_pk, bibkey, e.fields.get('glottolog_ref_id'))).lastrowid
            fields = itertools.chain([('ENTRYTYPE', e.type)], iteritems(e.fields))
            insert_values(((entry_pk, field, value) for field, value in fields))


def generate_hashes(conn):
    from .libmonster import wrds, keyid

    words = collections.Counter()
    cursor = sa.select([Value.value], bind=conn).where(Value.field == 'title').execute()
    for rows in iter(functools.partial(cursor.fetchmany, 10000), []):
        for title, in rows:
            words.update(wrds(title))
    # TODO: consider dropping stop words/hapaxes from freq. distribution
    print('%d title words (from %d tokens)' % (len(words), sum(itervalues(words))))

    def windowed_entries(chunksize=500):
        select_files = sa.select([File.pk], bind=conn).order_by(File.name)
        select_bibkeys = sa.select([Entry.pk], bind=conn)\
            .where(Entry.file_pk == sa.bindparam('file_pk'))\
            .order_by(Entry.pk).execute
        for file_pk, in select_files.execute().fetchall():
            with contextlib.closing(select_bibkeys(file_pk=file_pk)) as cursor:
                for entry_pks in iter(functools.partial(cursor.fetchmany, chunksize), []):
                    (first,), (last,) = entry_pks[0], entry_pks[-1]
                    yield first, last

    select_bfv = sa.select([Entry.pk, Value.field, Value.value], bind=conn)\
        .select_from(sa.join(Value, Entry))\
        .where(Entry.pk.between(sa.bindparam('first'), sa.bindparam('last')))\
        .where(Value.field != 'ENTRYTYPE')\
        .order_by(Entry.pk).execute
    assert conn.dialect.paramstyle == 'qmark'
    update_entry = sa.update(Entry, bind=conn)\
        .values(hash=sa.bindparam('hash'))\
        .where(Entry.pk == sa.bindparam('entry_pk')).compile().string
    update_entry = functools.partial(conn.connection.executemany, update_entry)
    get_entry_pk = operator.itemgetter(0)
    for first, last in windowed_entries():
        rows = select_bfv(first=first, last=last)
        update_entry(
            ((keyid({k: v for _, k, v in grp}, words), entry_pk)
             for entry_pk, grp in itertools.groupby(rows, get_entry_pk)))


def assign_ids(conn, verbose=False):
    merged_entry, entrygrp = Database._merged_entry, Database._entrygrp
    other = sa.orm.aliased(Entry)

    assert Entry.allhash(conn)

    reset_entries = sa.update(Entry, bind=conn).values(id=sa.null(), srefid=Entry.refid)
    print('%d entries' % reset_entries.execute().rowcount)

    # resolve splits: srefid = refid only for entries from the most similar hash group
    nsplit = 0
    select_split = sa.select([Entry.refid, Entry.hash, File.name, Entry.bibkey], bind=conn)\
        .select_from(sa.join(Entry, File))\
        .order_by(Entry.refid, Entry.hash, File.name, Entry.bibkey)\
        .where(sa.exists().where(other.refid == Entry.refid).where(other.hash != Entry.hash))
    update_split = sa.update(Entry, bind=conn)\
        .where(Entry.refid == sa.bindparam('eq_refid'))\
        .where(Entry.hash != sa.bindparam('ne_hash'))\
        .values(srefid=sa.null()).execute
    for refid, group in group_first(select_split.execute()):
        old = merged_entry(entrygrp(conn, refid), raw=True)
        nsplit += len(group)
        cand = [
            (hs, merged_entry(entrygrp(conn, hs), raw=True))
            for hs in unique(hs for _, hs, _, _ in group)]
        new = min(cand, key=lambda p: distance(old, p[1]))[0]
        separated = update_split(eq_refid=refid, ne_hash=new).rowcount
        if verbose:
            for row in group:
                print(row)
            for _, _, fn, bk in group:
                print('\t%r, %r, %r, %r' % Value.hashfields(conn, fn, bk))
            print('-> %s' % new)
            print('%d: %d separated from %s\n' % (refid, separated, new))
    print('%d splitted' % nsplit)

    nosplits = sa.select(
        [
            ~sa.exists().select_from(Entry)
            .where(sa.exists().where(other.srefid == Entry.srefid).where(other.hash != Entry.hash))
        ],
        bind=conn)
    assert nosplits.scalar()

    # resolve merges: id = srefid of the most similar srefid group
    nmerge = 0
    select_merge = sa.select([Entry.hash, Entry.srefid, File.name, Entry.bibkey], bind=conn)\
        .select_from(sa.join(Entry, File))\
        .order_by(Entry.hash, Entry.srefid.desc(), File.name, Entry.bibkey)\
        .where(sa.exists().where(other.hash == Entry.hash).where(other.srefid != Entry.srefid))
    update_merge = sa.update(Entry, bind=conn)\
        .where(Entry.hash == sa.bindparam('eq_hash'))\
        .where(Entry.srefid != sa.bindparam('ne_srefid'))\
        .values(id=sa.bindparam('new_id')).execute
    for hash, group in group_first(select_merge.execute()):
        new = merged_entry(entrygrp(conn, hash), raw=True)
        nmerge += len(group)
        cand = [
            (ri, merged_entry(entrygrp(conn, ri), raw=True))
            for ri in unique(ri for _, ri, _, _ in group)]
        old = min(cand, key=lambda p: distance(new, p[1]))[0]
        merged = update_merge(eq_hash=hash, ne_srefid=old, new_id=old).rowcount
        if verbose:
            for row in group:
                print(row)
            for _, _, fn, bk in group:
                print('\t%r, %r, %r, %r' % Value.hashfields(conn, fn, bk))
            print('-> %s' % old)
            print('%s: %d merged into %d\n' % (hash, merged, old))
    print('%d merged' % nmerge)

    # unchanged entries
    update_unchanged = sa.update(Entry, bind=conn)\
        .where(Entry.id == sa.null())\
        .where(Entry.srefid != sa.null())\
        .values(id=Entry.srefid)
    print('%d unchanged' % update_unchanged.execute().rowcount)

    nomerges = sa.select(
        [
            ~sa.exists().select_from(Entry)
            .where(sa.exists().where(other.hash == Entry.hash).where(other.id != Entry.id))],
        bind=conn)
    assert nomerges.scalar()

    # identified
    update_identified = sa.update(Entry, bind=conn)\
        .where(Entry.refid == sa.null())\
        .where(
            sa.exists()
            .where(other.hash == Entry.hash)
            .where(other.id != sa.null()))\
        .values(
            id=sa.select([other.id]).where(other.hash == Entry.hash).where(other.id != sa.null()))
    print('%d identified (new/separated)' % update_identified.execute().rowcount)

    # assign new ids to hash groups of separated/new entries
    nextid = sa.select([sa.func.coalesce(sa.func.max(Entry.refid), 0) + 1], bind=conn).scalar()
    select_new = sa.select([Entry.hash], bind=conn)\
        .where(Entry.id == sa.null())\
        .group_by(Entry.hash)\
        .order_by(Entry.hash)
    assert conn.dialect.paramstyle == 'qmark'
    update_new = sa.update(Entry, bind=conn)\
        .values(id=sa.bindparam('new_id'))\
        .where(Entry.hash == sa.bindparam('eq_hash')).compile().string
    params = ((id, hash) for id, (hash,) in enumerate(select_new.execute(), nextid))
    dbapi_rowcount = conn.connection.executemany(update_new, params).rowcount
    # https://docs.python.org/2/library/sqlite3.html#sqlite3.Cursor.rowcount
    print('%d new ids (new/separated)' % (0 if dbapi_rowcount == -1 else dbapi_rowcount))

    assert Entry.allid(conn)
    assert Entry.onetoone(conn)

    # supersede relation
    select_superseded = sa.select([sa.func.count()], bind=conn).where(Entry.id != Entry.srefid)
    print('%d supersede pairs' % select_superseded.scalar())


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
        for k, w in iteritems(weights))
    return 1 - (sum(ratios) / sum(itervalues(weights)))
