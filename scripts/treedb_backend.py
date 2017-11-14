# treedb_backend.py - ini content as (path, section, option, line, value) rows

from __future__ import unicode_literals

import os
import io
import csv
import sys
import json
import time
import pathlib
import zipfile
import itertools
import contextlib
import subprocess

from treedb_files import iteritems

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative

import treedb_files as _files

REBUILD, ECHO = False, False

DBFILE = pathlib.Path('treedb.sqlite3')

FIELDS = {
    ('core', 'name'): False,
    ('core', 'hid'): False,
    ('core', 'level'): False,
    ('core', 'iso639-3'): False,
    ('core', 'latitude'): False,
    ('core', 'longitude'): False,
    ('core', 'macroareas'): True,
    ('core', 'countries'): True,
    ('core', 'name_comment'): False,
    # FIXME: core hapaxes
    ('core', 'comment'): False,
    ('core', 'comment_type'): False,
    ('core', 'ethnologue_versions'): False,
    ('core', 'isohid'): False,
    ('core', 'location'): False,
    ('core', 'name_pronunciation'): False,
    ('core', 'speakers'): False,

    ('sources', None): True,

    ('altnames', None): True,

    ('triggers', None): True,

    ('identifier', None): False,

    ('classification', 'sub'): False,
    ('classification', 'subrefs'): True,
    ('classification', 'family'): False,
    ('classification', 'familyrefs'): True,

    ('endangerment', 'status'): False,
    ('endangerment', 'source'): False,
    ('endangerment', 'date'): False,
    ('endangerment', 'comment'): False,

    ('hh_ethnologue_comment', 'isohid'): False,
    ('hh_ethnologue_comment', 'comment_type'): False,
    ('hh_ethnologue_comment', 'ethnologue_versions'): False,
    ('hh_ethnologue_comment', 'comment'): False,

    ('iso_retirement', 'change_request'): False,
    ('iso_retirement', 'effective'): False,
    ('iso_retirement', 'supersedes'): True,
    ('iso_retirement', 'code'): False,
    ('iso_retirement', 'name'): False,
    ('iso_retirement', 'remedy'): False,
    ('iso_retirement', 'comment'): False,
    ('iso_retirement', 'reason'): False,
}


def is_lines(section, option, _fields=FIELDS):
    """Return whether the section option is treated as list of lines."""
    result = _fields.get((section, None))
    if result is None:
        # use .get() instead to permit unknown fields as scalar
        return _fields[(section, option)]
    return result


engine = sa.create_engine('sqlite:///%s' % DBFILE, echo=ECHO)


@sa.event.listens_for(sa.engine.Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    with contextlib.closing(dbapi_connection.cursor()) as cursor:
        cursor.execute('PRAGMA foreign_keys = ON')


def create_tables(bind=engine):
    Model.metadata.create_all(bind)


def print_rows(query, format_):
    for r in query.execute():
        print(format_.format(**r))


Model = sa.ext.declarative.declarative_base()


class Dataset(Model):

    __tablename__ = 'dataset'

    id = sa.Column(sa.Boolean, sa.CheckConstraint('id'),
                   primary_key=True, server_default=sa.true())
    git_commit = sa.Column(sa.String(40), nullable=False, unique=True)


class Path(Model):

    __tablename__ = '_path'

    id = sa.Column(sa.Integer, primary_key=True)
    path = sa.Column(sa.Text, nullable=False, unique=True)


class Option(Model):

    __tablename__ = '_option'

    id = sa.Column(sa.Integer, primary_key=True)
    section = sa.Column(sa.Text, nullable=False)
    option = sa.Column(sa.Text, nullable=False)
    lines = sa.Column(sa.Boolean, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(section, option),
    )


class Data(Model):

    __tablename__ = '_data'

    path_id = sa.Column(sa.ForeignKey('_path.id'), primary_key=True)
    option_id = sa.Column(sa.ForeignKey('_option.id'), primary_key=True)
    line = sa.Column(sa.Integer, primary_key=True)
    # TODO: consider adding version for selective updates
    value = sa.Column(sa.Text, nullable=False)


def load(rebuild=False, root=_files.ROOT):
    if DBFILE.exists():
        if rebuild:
            DBFILE.unlink()
        else:
            return

    create_tables(engine)

    start = time.time()
    with engine.begin() as conn:
        conn.execute('PRAGMA synchronous = OFF')
        conn.execute('PRAGMA journal_mode = MEMORY')
        conn = conn.execution_options(compiled_cache={})
        _load(conn, root)
    print(time.time() - start)


def _load(conn, root):
    git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip()
    sa.insert(Dataset, bind=conn).execute(git_commit=git_commit)

    insert_path = sa.insert(Path, bind=conn).execute
    insert_data = sa.insert(Data, bind=conn).execute

    class Options(dict):

        _insert = sa.insert(Option, bind=conn).execute

        def __missing__(self, key):
            section, option = key
            lines = is_lines(section, option)
            id_, = self._insert(section=section, option=option, lines=lines).inserted_primary_key
            self[key] = result = (id_, lines)
            return result

    options = Options()

    for path_tuple, cfg in _files.iterconfig(root):
        path_id, = insert_path(path='/'.join(path_tuple)).inserted_primary_key
        for section, sec in cfg.items():
            for option, value in sec.items():
                option_id, lines = options[(section, option)]
                if lines:
                    for i, v in enumerate(value.strip().splitlines(), 1):
                        insert_data(path_id=path_id, option_id=option_id,
                                    line=i, value=v)
                else:
                    insert_data(path_id=path_id, option_id=option_id,
                                line=0, value=value)


def stats(bind=engine):
    return sa.select([
            Option.section, Option.option, sa.func.count().label('n'),
        ], bind=bind)\
        .select_from(sa.join(Option, Data))\
        .group_by(Option.section, Option.option)\
        .order_by(Option.section, sa.desc('n'))


def iterrecords(bind=engine, _groupby=itertools.groupby):
    select_paths = sa.select([Path.path], bind=bind).order_by(Path.path)
    select_data = sa.select([
            Option.section, Option.option, Option.lines, Data.line,
            Data.value,
        ], bind=bind)\
        .select_from(sa.join(Path, Data).join(Option))\
        .where(Path.path == sa.bindparam('path'))\
        .order_by(Option.section, Option.option, Data.line)
    for p, in select_paths.execute():
        data = select_data.execute(path=p)
        record = {
            s: {o: [l.value for l in lines] if islines else next(lines).value
               for (o, islines), lines in _groupby(sections, lambda r: (r.option, r.lines))}
            for s, sections in _groupby(data, lambda r: r.section)}
        yield p, record


def to_csv(filename=None, bind=engine, encoding='utf-8'):
    if filename is None:
        filename = '%s-json.csv' % os.path.splitext(bind.url.database)[0]
    with io.open(filename, 'w', newline='', encoding=encoding) as f:
        # FIXME: PY3 only, use backport
        csvwriter = csv.writer(f)
        csvwriter.writerow(['path', 'json'])
        for path, data in iterrecords(bind=bind):
            csvwriter.writerow([path, json.dumps(data)])


def to_files(bind=engine, is_lines=is_lines):
    def iterpairs(records=iterrecords(bind=bind)):
        for p, r in records:
            path_tuple = pathlib.Path(p).parts
            for section, s in iteritems(r):
                for option in s:
                    if is_lines(section, option):
                        s[option] = '\n'.join([''] + s[option])
            yield path_tuple, r

    _files.to_files(iterpairs())


def export_csv(metadata=Model.metadata, engine=engine, encoding='utf-8'):
    filename = '%s.zip' % os.path.splitext(engine.url.database)[0]
    with engine.connect() as conn,\
         zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as z:
        get_fd = io.BytesIO if sys.version_info < (3,) else io.StringIO
        for table in metadata.sorted_tables:
            with contextlib.closing(get_fd()) as f:
                writer = csv.writer(f)
                result = conn.execute(table.select())
                writer.writerow(result.keys())
                if sys.version_info < (3,):
                    for row in result:
                        writer.writerow([unicode(col).encode(encoding) if col else col for col in row])
                    data = f.getvalue()
                else:
                    writer.writerows(result)
                    data = f.getvalue().encode(encoding)
                z.writestr('%s.csv' % table.name, data)


def print_fields(bind=engine):
    has_scalar = (sa.func.min(Data.line) == 0).label('scalar')
    has_lines = (sa.func.max(Data.line) != 0).label('lines')
    query = sa.select([
            Option.section, Option.option, has_scalar, has_lines,
        ], bind=bind)\
        .select_from(sa.join(Option, Data))\
        .group_by(Option.section, Option.option)\
        .order_by(Option.section, Option.option)
    print('FIELDS_LIST = {')
    print_rows(query, '    ({section!r}, {option!r}): {lines},  # 0x{scalar:d}{lines:d}')
    print('}')


def dump_data(filename='data.csv', bind=engine, encoding='utf-8'):
    query = sa.select([
            Path.path, Option.section, Option.option, Data.line, Data.value,
        ], bind=engine).select_from(sa.join(Path, Data).join(Option))\
        .order_by(Path.path, Option.section, Option.option, Data.line)
    with io.open(filename, 'w', newline='', encoding=encoding) as f:
        csvwriter = csv.writer(f)
        csvwriter.writerows(iter(query.execute()))


if __name__ == '__main__':
    load(rebuild=REBUILD)
    print_rows(stats(), '{section:<22} {option:<22} {n:,}')
    print_fields()
    #to_csv()
    #to_files()
    #export_csv()
