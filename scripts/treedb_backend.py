# treedb_backend.py

import io
import time
import pathlib
import datetime
import functools
import itertools
import contextlib
import collections  # FIXME: ChainMap is PY3
import configparser

try:
    from os import scandir
except ImportError:
    from scandir import scandir

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative

REBUILD = False

ROOT = pathlib.Path('../languoids/tree')

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
    result = _fields.get((section, None))
    if result is None:
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

    @classmethod
    def from_file(cls, filename, encoding='utf-8', **kwargs):
        inst = cls(**kwargs)
        with io.open(filename, encoding=encoding) as f:
            inst.read_file(f)
        return inst

    def __init__(self, defaults=None, **kwargs):
        super(ConfigParser, self).__init__(defaults=defaults, interpolation=None, **kwargs)

    def getlist(self, section, option):
        if not self.has_option(section, option):
            return []
        return self.get(section, option).strip().splitlines()

    def getdatetime(self, section, option, format_='%Y-%m-%dT%H:%M:%S'):
        return datetime.datetime.strptime(self.get(section, option), format_)


def iterconfig(root=ROOT, assert_name='md.ini', load=ConfigParser.from_file):
    if not isinstance(root, pathlib.Path):
        root = pathlib.Path(root)
    root_len = len(root.parts)
    for d in iterfiles(root):
        assert d.name == assert_name
        path_tuple = pathlib.Path(d.path).parts[root_len:-1]
        yield path_tuple, load(d.path)


engine = sa.create_engine('sqlite:///%s' % DBFILE)


@sa.event.listens_for(sa.engine.Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    with contextlib.closing(dbapi_connection.cursor()) as cursor:
        cursor.execute('PRAGMA foreign_keys = ON')


def create_tables(bind=engine):
    Model.metadata.create_all(bind)


Model = sa.ext.declarative.declarative_base()


class Statement(Model):

    __tablename__ = 'statement'

    path = sa.Column(sa.Text, primary_key=True)
    section = sa.Column(sa.Text, primary_key=True)
    option = sa.Column(sa.Text, primary_key=True)
    line = sa.Column(sa.Integer, primary_key=True)
    value = sa.Column(sa.Text, nullable=False)


class KwPartial(functools.partial):

    _merged = collections.ChainMap

    def new_child(self, **kwargs):
        return self.__class__(self.func, **self._merged(kwargs, self.keywords))


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
    insert_statement = sa.insert(Statement, bind=conn)\
        .values({c.name: sa.bindparam(c.name) for c in Statement.__table__.columns})\
        .execute

    for path, cfg in iterconfig():
        insert = KwPartial(insert_statement, path='/'.join(path))
        for section, sec in cfg.items():
            insert = insert.new_child(section=section)
            for option, value in sec.items():
                if is_lines(section, option):
                    insert = insert.new_child(option=option)
                    for i, v in enumerate(value.strip().splitlines(), 1):
                        insert(line=i, value=v)
                else:
                    insert(option=option, line=0, value=value)


def print_rows(query, format_):
    for r in query.execute():
        print(format_.format(**r))


def stats(bind=engine):
    return sa.select([
            Statement.section, Statement.option, sa.func.count().label('n'),
        ], bind=bind)\
        .group_by(Statement.section, Statement.option)\
        .order_by(Statement.section, sa.desc('n'))


def iterlanguoids(bind=engine, _groupby=itertools.groupby, _is_lines=is_lines):
    select_paths = sa.select([Statement.path], bind=bind).distinct()\
        .order_by(Statement.path)
    select_statements = sa.select([
            Statement.section, Statement.option, Statement.line,
            Statement.value,
        ], bind=bind)\
        .where(Statement.path == sa.bindparam('path'))\
        .order_by(Statement.section, Statement.option, Statement.line)
    for p, in select_paths.execute():
        statements = select_statements.execute(path=p)
        languoid = {
            s: {o: [l.value for l in lines] if _is_lines(s, o) else next(lines).value
               for o, lines in _groupby(sections, lambda r: r.option)}
            for s, sections in _groupby(statements, lambda r: r.section)}
        yield p, languoid


def print_fields(bind=engine):
    has_scalar = sa.func.min(Statement.line) == 0
    has_list = sa.func.max(Statement.line) != 0
    query = sa.select([
            Statement.section, Statement.option, has_scalar.label('scalar'), has_list.label('list'),
        ], bind=bind)\
        .group_by(Statement.section, Statement.option)\
        .order_by(Statement.section, Statement.option)
    print('FIELDS_LIST = {')
    print_rows(query, '    ({section!r}, {option!r}): {list},  # {scalar:d}{list:d}')
    print('}')


if __name__ == '__main__':
    load(rebuild=REBUILD)
    print_rows(stats(), '{section:<22} {option:<22} {n:,}')
    print_fields()
