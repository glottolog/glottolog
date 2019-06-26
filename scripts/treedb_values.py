# treedb_values.py - ini content as (path, section, option, line, value) rows

from __future__ import unicode_literals

import json
import datetime
import itertools
import functools

try:
    import pathlib2 as pathlib
except ImportError:
    import pathlib

from treedb_backend import iteritems

import sqlalchemy as sa

import treedb_files as _files
import treedb_backend as _backend


class Fields(object):
    """Define known (section, option) pairs and if they are lists of lines."""

    _fields = {
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
        ('core', 'location'): False,
        ('core', 'name_pronunciation'): False,
        ('core', 'speakers'): False,

        ('core', 'links'): True,

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

        ('iso_retirement', 'code'): False,
        ('iso_retirement', 'name'): False,
        ('iso_retirement', 'change_request'): False,
        ('iso_retirement', 'effective'): False,
        ('iso_retirement', 'reason'): False,
        ('iso_retirement', 'change_to'): True,
        ('iso_retirement', 'remedy'): False,
        ('iso_retirement', 'comment'): False,
    }

    @classmethod
    def is_known(cls, section, option):
        return (section, None) in cls._fields or (section, option) in cls._fields

    @classmethod
    def is_lines(cls, section, option):
        """Return whether the section option is treated as list of lines."""
        result = cls._fields.get((section, None))
        if result is None:
            # use .get() instead to permit unknown fields as scalar
            return cls._fields[(section, option)]
        return result


class File(_backend.Model):
    """Forward-slash-joined ids from the root to each item."""

    __tablename__ = '_file'

    id = sa.Column(sa.Integer, primary_key=True)
    glottocode = sa.Column(sa.String(8), sa.CheckConstraint('length(glottocode) = 8'), nullable=False, unique=True)
    path = sa.Column(sa.Text, sa.CheckConstraint('length(path) >= 8'), nullable=False, unique=True)
    size = sa.Column(sa.Integer, nullable=False)
    mtime = sa.Column(sa.DateTime, nullable=False)

    __table_args__ = (
        sa.CheckConstraint('substr(path, -length(glottocode)) = glottocode'),
    )


class Option(_backend.Model):
    """Unique (section, option) key of the values with lines config."""

    __tablename__ = '_option'

    id = sa.Column(sa.Integer, primary_key=True)
    section = sa.Column(sa.Text, sa.CheckConstraint("section != ''"), nullable=False)
    option = sa.Column(sa.Text, sa.CheckConstraint("option != ''"), nullable=False)
    lines = sa.Column(sa.Boolean, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(section, option),
    )


class Value(_backend.Model):
    """Item value as (path, section, option, line, value) combination."""

    __tablename__ = '_value'

    file_id = sa.Column(sa.ForeignKey('_file.id'), primary_key=True)
    option_id = sa.Column(sa.ForeignKey('_option.id'), primary_key=True)
    line = sa.Column(sa.Integer, sa.CheckConstraint('line >= 0'), primary_key=True)
    # TODO: consider adding version for selective updates
    value = sa.Column(sa.Text, sa.CheckConstraint("value != ''"), nullable=False)


def load(root=_files.ROOT, rebuild=False):
    _backend.load(make_loader(root=root), rebuild=rebuild)


def make_loader(root):
    return functools.partial(_load, root=root)


def _load(conn, root, is_lines=Fields.is_lines):

    insert_file = sa.insert(File, bind=conn).execute
    insert_value = sa.insert(Value, bind=conn).execute

    class Options(dict):
        """Insert optons on demand and cache id and lines config."""

        _insert = sa.insert(Option, bind=conn).execute

        def __missing__(self, key):
            section, option = key
            lines = is_lines(section, option)
            id_, = self._insert(section=section, option=option, lines=lines).inserted_primary_key
            self[key] = result = (id_, lines)
            return result

    options = Options()

    for path_tuple, dentry, cfg in _files.iterconfig(root):
        d_stat = dentry.stat()
        mtime = datetime.datetime.fromtimestamp(d_stat.st_mtime)
        file_id, = insert_file(glottocode=path_tuple[-1], path='/'.join(path_tuple),
                               size=d_stat.st_size, mtime=mtime).inserted_primary_key
        for section, sec in cfg.items():
            for option, value in sec.items():
                option_id, lines = options[(section, option)]
                if lines:
                    for i, v in enumerate(value.strip().splitlines(), 1):
                        insert_value(file_id=file_id, option_id=option_id,
                                    line=i, value=v)
                else:
                    insert_value(file_id=file_id, option_id=option_id,
                                line=0, value=value)


def iterrecords(bind=_backend.engine, _groupby=itertools.groupby):
    """Yield (path, <dict of <dicts of strings/string_lists>>) pairs."""
    select_paths = sa.select([File.path], bind=bind).order_by(File.path)
    select_values = sa.select([
            Option.section, Option.option, Option.lines, Value.line, Value.value,
        ], bind=bind)\
        .select_from(sa.join(File, Value).join(Option))\
        .where(File.path == sa.bindparam('path'))\
        .order_by(Option.section, Option.option, Value.line)
    for p, in select_paths.execute():
        values = select_values.execute(path=p)
        record = {
            s: {o: [l.value for l in lines] if islines else next(lines).value
               for (o, islines), lines in _groupby(sections, lambda r: (r.option, r.lines))}
            for s, sections in _groupby(values, lambda r: r.section)}
        yield p, record


def to_csv(filename='values.csv', bind=_backend.engine, encoding='utf-8'):
    """Write (path, section, option, line, value) rows to <filename>.csv."""
    query = sa.select([
            File.path, Option.section, Option.option, Value.line, Value.value,
        ], bind=bind).select_from(sa.join(File, Value).join(Option))\
        .order_by(File.path, Option.section, Option.option, Value.line)
    rows = query.execute()
    with _backend._csv_open(filename, 'w', encoding=encoding) as f:
        _backend._csv_write(f, encoding, header=rows.keys(), rows=rows)


def to_json(filename=None, bind=_backend.engine, encoding='utf-8'):
    """Write (path, json) rows to <databasename>-json.csv."""
    if filename is None:
        filename = '%s-json.csv' % pathlib.Path(bind.url.database).stem
    rows = ((path, json.dumps(data)) for path, data in iterrecords(bind=bind))
    with _backend._csv_open(filename, 'w', encoding=encoding) as f:
        _backend._csv_write(f, encoding, header=['path', 'json'], rows=rows)


def to_files(bind=_backend.engine, verbose=False, is_lines=Fields.is_lines):
    """Write (path, section, option, line, value) rows back into config files."""
    def iterpairs(records):
        for p, r in records:
            path_tuple = pathlib.Path(p).parts
            for section, s in iteritems(r):
                for option in s:
                    if is_lines(section, option):
                        s[option] = '\n'.join([''] + s[option])
            yield path_tuple, r

    _files.save(iterpairs(iterrecords(bind=bind)), verbose=verbose)


def print_fields(bind=_backend.engine):
    has_scalar = (sa.func.min(Value.line) == 0).label('scalar')
    has_lines = (sa.func.max(Value.line) != 0).label('lines')
    query = sa.select([
            Option.section, Option.option, has_scalar, has_lines,
        ], bind=bind)\
        .select_from(sa.join(Option, Value))\
        .group_by(Option.section, Option.option)\
        .order_by(Option.section, Option.option)
    print('FIELDS_LIST = {')
    _backend.print_rows(query, '    ({section!r}, {option!r}): {lines},  # 0x{scalar:d}{lines:d}')
    print('}')


def print_stats(bind=_backend.engine, execute=False):
    query = sa.select([
            Option.section, Option.option, sa.func.count().label('n'),
        ], bind=bind)\
        .select_from(sa.join(Option, Value))\
        .group_by(Option.section, Option.option)\
        .order_by(Option.section, sa.desc('n'))
    _backend.print_rows(query, '{section:<22} {option:<22} {n:,}')


def dropfunc(func, bind=_backend.engine, save=True, verbose=True):
    def wrapper(bind=bind, save=save, verbose=verbose):
        delete_query = func()
        rows_deleted = bind.execute(delete_query).rowcount
        if rows_deleted and save:
            to_files(bind=bind, verbose=verbose)
        return rows_deleted
    return wrapper


@dropfunc
def drop_duplicate_sources():
    other = sa.orm.aliased(Value)
    return sa.delete(Value)\
        .where(sa.exists()
            .where(Option.id == Value.option_id)
            .where(Option.section == 'sources'))\
        .where(sa.exists()
            .where(other.file_id == Value.file_id)
            .where(other.option_id == Value.option_id)
            .where(other.value == Value.value)
            .where(other.line < Value.line))


@dropfunc
def drop_duplicated_triggers():
    other = sa.orm.aliased(Value)
    return sa.delete(Value)\
        .where(sa.exists()
            .where(Option.id == Value.option_id)
            .where(Option.section == 'triggers'))\
        .where(sa.exists()
            .where(other.file_id == Value.file_id)
            .where(other.option_id == Value.option_id)
            .where(other.value == Value.value)
            .where(other.line < Value.line))


@dropfunc
def drop_duplicated_crefs():
    other = sa.orm.aliased(Value)
    return sa.delete(Value)\
        .where(sa.exists()
            .where(Option.id == Value.option_id)
            .where(Option.section == 'classification')
            .where(Option.option.in_(('familyrefs', 'subrefs'))))\
        .where(sa.exists()
            .where(other.file_id == Value.file_id)
            .where(other.option_id == Value.option_id)
            .where(other.value == Value.value)
            .where(other.line < Value.line))


if __name__ == '__main__':
    load()
    print(next(iterrecords()))
    #to_csv()
    #to_json()
    #to_files()
    print_stats()
    print_fields()
    #drop_duplicate_sources()
    #drop_duplicated_triggers()
    #drop_duplicated_crefs()
