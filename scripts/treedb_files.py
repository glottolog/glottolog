# treedb_files.py - load/write languoids/tree/**/md.ini

from __future__ import unicode_literals

import io
import sys
import pathlib
import configparser

if sys.version_info < (3,):
    from scandir import scandir
    iteritems = lambda x: x.iteritems()
else:
    from os import scandir
    iteritems = lambda x: iter(x.items())

ROOT, BASENAME = pathlib.Path('../languoids/tree'), 'md.ini'

__all__ = ['ROOT', 'iterconfig', 'to_files']


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

    def to_file(self, filename, encoding=_encoding, newline=_newline):
        with io.open(filename, 'w', encoding=encoding, newline=newline) as f:
            f.write(self._header % encoding)
            self.write(f)


def iterconfig(root=ROOT, assert_name=BASENAME, load=ConfigParser.from_file):
    """Yield ((<path_part>, ...), <ConfigParser object>) pairs.""" 
    if not isinstance(root, pathlib.Path):
        root = pathlib.Path(root)
    root_len = len(root.parts)
    for d in iterfiles(root):
        assert d.name == assert_name
        path_tuple = pathlib.Path(d.path).parts[root_len:-1]
        yield path_tuple, load(d.path)


def to_files(pairs, root=ROOT, basename=BASENAME, load=ConfigParser.from_file):
    """Write ((<path_part>, ...), <dict of dicts>) pairs to root."""
    for path_tuple, d in pairs:
        path = str(root.joinpath(*path_tuple) / basename)
        cfg = load(path)
        for section, s in iteritems(d):
            for option, value in iteritems(s):
                cfg.set(section, option, value)
        cfg.to_file(path)


def roundtrip():
    """Do a load/save cycle with all config files."""
    to_files((path_tuple, {s: dict(cfg.items(s)) for s in cfg.sections()})
             for path_tuple, cfg in iterconfig())


if __name__ == '__main__':
    print(next(iterfiles()))
    print(next(iterconfig()))
    #roundtrip()
