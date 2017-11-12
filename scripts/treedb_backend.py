# treedb_backend.py

from __future__ import unicode_literals

import os
import io
import csv
import sys
import json
import time
import pathlib
import datetime
import functools
import itertools
import contextlib
import subprocess
import configparser

if sys.version_info < (3,):
    from scandir import scandir
    iteritems = lambda x: x.iteritems()
else:
    from os import scandir
    iteritems = lambda x: iter(x.items())

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative

REBUILD = False

ECHO = False

ROOT, BASENAME = pathlib.Path('../languoids/tree'), 'md.ini'

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

    ('classification', 'family'): False,
    ('classification', 'familyrefs'): True,
    ('classification', 'sub'): False,
    ('classification', 'subrefs'): True,

    ('endangerment', 'status'): False,
    ('endangerment', 'source'): False,
    ('endangerment', 'date'): False,
    ('endangerment', 'comment'): False,

    ('hh_ethnologue_comment', 'isohid'): False,
    ('hh_ethnologue_comment', 'comment_type'): False,
    ('hh_ethnologue_comment', 'comment'): False,
    ('hh_ethnologue_comment', 'ethnologue_versions'): False,

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


def iterfiles(top=ROOT, verbose=False):
    """Yield DirEntry objects for all files under top."""
    if isinstance(top, pathlib.Path):
        top = str(top)
    stack = [top]
    while stack:
        root = stack.pop()
        if verbose:
            print(root)
        direntries = scandir(root)
        dirs = []
        for d in direntries:
            if d.is_dir():
                dirs.append(d.path)
            else:
                yield d
        stack.extend(dirs[::-1])


class ConfigParser(configparser.ConfigParser):

    _header =  '# -*- coding: %s -*-\n'
    _encoding = 'utf-8'
    _newline = '\r\n'
    _init_defaults = {
        'delimiters': ('=',),
        'comment_prefixes': ('#',),
        'interpolation': None,
    }

    @classmethod
    def from_file(cls, filename, encoding=_encoding, newline=_newline, **kwargs):
        inst = cls(**kwargs)
        with io.open(filename, encoding=encoding) as f:
            inst.read_file(f)
        return inst

    def __init__(self, defaults=None, **kwargs):
        for k, v in iteritems(self._init_defaults):
            kwargs.setdefault(k, v)
        super(ConfigParser, self).__init__(defaults=defaults, **kwargs)

    def to_file(self, filename, encoding=_encoding, newline=_newline):
        with io.open(filename, 'w', encoding=encoding, newline=newline) as f:
            f.write(self._header % encoding)
            self.write(f)

    def getlines(self, section, option):
        if not self.has_option(section, option):
            return []
        return self.get(section, option).strip().splitlines()

    def getdatetime(self, section, option, format_='%Y-%m-%dT%H:%M:%S'):
        return datetime.datetime.strptime(self.get(section, option), format_)


def iterconfig(root=ROOT, assert_name=BASENAME, load=ConfigParser.from_file):
    if not isinstance(root, pathlib.Path):
        root = pathlib.Path(root)
    root_len = len(root.parts)
    for d in iterfiles(root):
        assert d.name == assert_name
        path_tuple = pathlib.Path(d.path).parts[root_len:-1]
        yield path_tuple, load(d.path)


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

    __tablename__ = 'path'

    id = sa.Column(sa.Integer, primary_key=True)
    path = sa.Column(sa.Text, nullable=False, unique=True)


class Option(Model):

    __tablename__ = 'option'

    id = sa.Column(sa.Integer, primary_key=True)
    section = sa.Column(sa.Text, nullable=False)
    option = sa.Column(sa.Text, nullable=False)
    lines = sa.Column(sa.Boolean, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(section, option),
    )


class Statement(Model):

    __tablename__ = 'statement'

    path_id = sa.Column(sa.ForeignKey('path.id'), primary_key=True)
    option_id = sa.Column(sa.ForeignKey('option.id'), primary_key=True)
    line = sa.Column(sa.Integer, primary_key=True)
    # TODO: consider adding version for selective updates 
    value = sa.Column(sa.Text, nullable=False)


def load(root=ROOT, rebuild=False):
    if not DBFILE.exists():
        create_tables(engine)
    elif rebuild:
        DBFILE.unlink()
        create_tables(engine)
    else:
        return

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
    
    insert_path = sa.insert(Path, bind=conn)\
        .values(path=sa.bindparam('path'))\
        .execute
    insert_statement = sa.insert(Statement, bind=conn)\
        .values({c.name: sa.bindparam(c.name) for c in Statement.__table__.columns})\
        .execute

    class Options(dict):

        _insert = sa.insert(Option, bind=conn)\
            .values({c: sa.bindparam(c) for c in ['section', 'option', 'lines']})\
            .execute

        def __missing__(self, key):
            section, option = key
            lines = is_lines(section, option)
            id_, = self._insert(section=section, option=option, lines=lines).inserted_primary_key
            self[key] = result = (id_, lines)
            return result

    options = Options()

    for path_tuple, cfg in iterconfig():
        path_id, = insert_path(path='/'.join(path_tuple)).inserted_primary_key
        for section, sec in cfg.items():
            for option, value in sec.items():
                option_id, lines = options[(section, option)]
                if lines:
                    for i, v in enumerate(value.strip().splitlines(), 1):
                        insert_statement(path_id=path_id, option_id=option_id,
                                         line=i, value=v)
                else:
                    insert_statement(path_id=path_id, option_id=option_id,
                                     line=0, value=value)


def stats(bind=engine):
    return sa.select([
            Option.section, Option.option, sa.func.count().label('n'),
        ], bind=bind)\
        .select_from(sa.join(Option, Statement))\
        .group_by(Option.section, Option.option)\
        .order_by(Option.section, sa.desc('n'))


def iterlanguoids(bind=engine, _groupby=itertools.groupby):
    select_paths = sa.select([Path.path], bind=bind).order_by(Path.path)
    select_statements = sa.select([
            Option.section, Option.option, Option.lines, Statement.line,
            Statement.value,
        ], bind=bind)\
        .select_from(sa.join(Path, Statement).join(Option))\
        .where(Path.path == sa.bindparam('path'))\
        .order_by(Option.section, Option.option, Statement.line)
    for p, in select_paths.execute():
        statements = select_statements.execute(path=p)
        languoid = {
            s: {o: [l.value for l in lines] if islines else next(lines).value
               for (o, islines), lines in _groupby(sections, lambda r: (r.option, r.lines))}
            for s, sections in _groupby(statements, lambda r: r.section)}
        yield p, languoid


def to_csv(filename=None, bind=engine, encoding='utf-8'):
    if filename is None:
        filename = '%s-json.csv' % os.path.splitext(bind.url.database)[0]
    with io.open(filename, 'w', newline='', encoding=encoding) as f:
        # FIXME: PY3 only, use backport
        csvwriter = csv.writer(f)
        csvwriter.writerow(['path', 'json'])
        for path, data in iterlanguoids(bind=bind):
            csvwriter.writerow([path, json.dumps(data)])


def to_files(root=ROOT, basename=BASENAME, bind=engine, load=ConfigParser.from_file):
    for p, l in iterlanguoids(bind=bind):
        path = str(root / p / basename)
        cfg = load(path)
        for section, s in iteritems(l):
            for option, value in iteritems(s):
                if is_lines(section, option):
                    value = '\n'.join([''] + value)
                cfg.set(section, option, value)
        cfg.to_file(path)


def print_fields(bind=engine):
    has_scalar = sa.func.min(Statement.line) == 0
    has_lines = sa.func.max(Statement.line) != 0
    query = sa.select([
            Option.section, Option.option, has_scalar.label('scalar'), has_lines.label('lines'),
        ], bind=bind)\
        .select_from(sa.join(Option, Statement))\
        .group_by(Option.section, Option.option)\
        .order_by(Option.section, Option.option)
    print('FIELDS_LIST = {')
    print_rows(query, '    ({section!r}, {option!r}): {lines},  # 0x{scalar:d}{lines:d}')
    print('}')


if __name__ == '__main__':
    load(rebuild=REBUILD)
    print_rows(stats(), '{section:<22} {option:<22} {n:,}')
    print_fields()
    #to_csv()
    #to_files()
