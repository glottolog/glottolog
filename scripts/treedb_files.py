# treedb_files.py - load/write languoids/tree/**/md.ini

from __future__ import unicode_literals

import io
import sys
import configparser

try:
    import pathlib2 as pathlib
except ImportError:
    import pathlib

if sys.version_info.major == 2:
    from scandir import scandir
else:
    from os import scandir

from treedb_backend import iteritems

ROOT, BASENAME = pathlib.Path('../languoids/tree'), 'md.ini'

__all__ = ['ROOT', 'iterconfig', 'save']


def iterfiles(top=ROOT, verbose=False):
    """Yield DirEntry objects for all files under top."""
    # NOTE: os.walk() ignores errors and this can be more efficient
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
    """Conservative ConfigParser with encoding header."""

    _header = '# -*- coding: %s -*-\n'
    _encoding = 'utf-8'
    _newline = '\r\n'
    _init_defaults = {
        'delimiters': ('=',),
        'comment_prefixes': ('#',),
        'interpolation': None,
    }

    @classmethod
    def from_file(cls, filename, encoding=_encoding, **kwargs):
        inst = cls(**kwargs)
        with io.open(filename, encoding=encoding) as f:
            inst.read_file(f)
        return inst

    def __init__(self, defaults=None, **kwargs):
        for k, v in iteritems(self._init_defaults):
            kwargs.setdefault(k, v)
        super(ConfigParser, self).__init__(defaults=defaults, **kwargs)

    def to_file(self, filename, encoding=_encoding):
        with io.open(filename, 'w', encoding=encoding, newline=self._newline) as f:
            f.write(self._header % encoding)
            self.write(f)


def iterconfig(root=ROOT, assert_name=BASENAME, load=ConfigParser.from_file):
    """Yield ((<path_part>, ...), DirEntry, <ConfigParser object>) triples."""
    if not isinstance(root, pathlib.Path):
        root = pathlib.Path(root)
    path_slice = slice(len(root.parts), -1)
    for d in iterfiles(root):
        assert d.name == assert_name
        path_tuple = pathlib.Path(d.path).parts[path_slice]
        yield path_tuple, d, load(d.path)


def save(pairs, root=ROOT, basename=BASENAME, assume_changed=False,
         verbose=False, load=ConfigParser.from_file):
    """Write ((<path_part>, ...), <dict of dicts>) pairs to root."""
    for path_tuple, d in pairs:
        path = str(root.joinpath(*path_tuple) / basename)
        cfg = load(path)
        # FIXME: missing sections and options
        drop_sections = set(cfg.sections()).difference(set(d) | {'core', 'sources'})
        changed = assume_changed or bool(drop_sections)
        for s in drop_sections:
            cfg.remove_section(s)
        for section, s in iteritems(d):
            if section != 'core':
                drop_options = set(cfg.options(section))
                if section == 'iso_retirement':
                    drop_options.discard('change_to')
                drop_options.difference_update(set(s))
                changed = changed or bool(drop_options)
                for o in drop_options:
                    cfg.remove_option(section, o)
            for option, value in iteritems(s):
                if cfg.get(section, option) != value:
                    changed = True
                    cfg.set(section, option, value)
        if changed:
            if verbose:
                print(path)
            cfg.to_file(path)


def roundtrip(verbose=False):
    """Do a load/save cycle with all config files."""
    pairs = ((path_tuple, {s: dict(cfg.items(s)) for s in cfg.sections()})
             for path_tuple, _, cfg in iterconfig())
    save(pairs, assume_changed=True, verbose=verbose)


if __name__ == '__main__':
    print(next(iterconfig()))
    #roundtrip()
