# treedb_backend.py - sqlite3 database engine

from __future__ import unicode_literals

import io
import csv
import sys
import time
import pathlib
import zipfile
import contextlib

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative

PY2 = sys.version_info < (3,)

if PY2:
    iteritems = lambda x: x.iteritems()
else:
    iteritems = lambda x: iter(x.items())

__all__ = [
    'engine', 'Session', 'Model',
    'load', 'export',
    'print_rows',
    'iteritems',
]

DBFILE = pathlib.Path('treedb.sqlite3')


engine = sa.create_engine('sqlite:///%s' % DBFILE, echo=False)


@sa.event.listens_for(sa.engine.Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Activate sqlite3 forein key checks."""
    with contextlib.closing(dbapi_connection.cursor()) as cursor:
        cursor.execute('PRAGMA foreign_keys = ON')


Session = sa.orm.sessionmaker(bind=engine)


Model = sa.ext.declarative.declarative_base()


def create_tables(bind=engine):
    Model.metadata.create_all(bind)


def load(load_func, rebuild=False, engine=engine):
    assert engine.url.drivername == 'sqlite'
    dbfile = pathlib.Path(engine.url.database)
    if dbfile.exists():
        if rebuild:
            dbfile.unlink()
        else:
            return

    start = time.time()
    with engine.begin() as conn:
        create_tables(conn)
    with engine.begin() as conn:
        conn.execute('PRAGMA synchronous = OFF')
        conn.execute('PRAGMA journal_mode = MEMORY')
        load_func(conn.execution_options(compiled_cache={}))
    print(time.time() - start)


def export(metadata=Model.metadata, engine=engine, encoding='utf-8'):
    """Write all tables to <tablename>.csv in <databasename>.zip."""
    filename = '%s.zip' % pathlib.Path(engine.url.database).stem
    with engine.connect() as conn, zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as z:
        for table in metadata.sorted_tables:
            rows = table.select(bind=conn).execute()
            with _csv_io() as f:
                _csv_write(f, encoding, header=rows.keys(), rows=rows)
                data = f.getvalue()
            if not PY2:
                data = data.encode(encoding)
            z.writestr('%s.csv' % table.name, data)


def _csv_io():
    if PY2:
        return io.BytesIO()
    return io.StringIO()


def _csv_open(filename, mode, encoding):
    if PY2:
        if not mode.endswith('b'):
            mode = mode + 'b'
        return io.open(filename, mode)
    return io.open(filename, mode, newline='', encoding=encoding)


def _csv_write(f, encoding, header, rows):
    writer = csv.writer(f)
    if PY2:
        writer.writerow([h.encode(encoding) for h in header])
        for r in rows:
            writer.writerow([unicode(col).encode(encoding) if col else col for col in r])
        return
    writer.writerow(header)
    writer.writerows(rows)


def print_rows(query, format_=None, engine=engine):
    rows = engine.execute(query)
    if format_ is None:
        for r in rows:
            print(r)
    else:
        for r in rows:
            print(format_.format(**r))


def pd_read_sql(query, engine=engine, **kwargs):
    import pandas as pd
    return pd.read_sql_query(query, engine, **kwargs)
