# _bibtex_undiacritic.py - remove latex/unicode diacritics for string comparison

import re

from unidecode import unidecode

__all__ = ['undiacritic']


class Replace(object):
    """Multiple search-replace with mutually exclusive regexes."""

    _rules = [  # ordered counterbleeding
        (r'\\AA(?:\{\})?', 'A'),
        (r'\\AE(?:\{\})?', 'Ae'),
        (r'\\aa(?:\{\})?', 'a'),
        (r'\\ae(?:\{\})?', 'e'),
        (r'\\oslash(?:\{\})?', 'o'),
        (r'\\Oslash(?:\{\})?', 'O'),
        (r'\\OE(?:\{\})?', 'OE'),
        (r'\\oe(?:\{\})?', 'oe'),
        (r'\\O(?:\{\})?', 'O'),
        (r'\\o(?:\{\})?', 'o'),
        (r'\\L(?:\{\})?', 'L'),
        (r'\\l(?:\{\})?', 'l'),
        (r'\\i(?:\{\})?', 'i'),
        (r'\\j(?:\{\})?', 'j'),
        (r'\\NG(?:\{\})?', 'NG'),
        (r'\\ng(?:\{\})?', 'ng'),
        (r'\\texteng(?:\{\})?', 'ng'),
        (r'\\ss(?:\{\})?', 'ss'),
        (r'\\textbari(?:\{\})?', 'i'),
        (r'\\textbaru(?:\{\})?', 'u'),
        (r'\\textbarI(?:\{\})?', 'I'),
        (r'\\textbarU(?:\{\})?', 'U'),
        (r'\\texthtd(?:\{\})?', 'd'),
        (r'\\texthtb(?:\{\})?', 'b'),
        (r'\\textopeno(?:\{\})?', 'o'),
        (r'\\textepsilon(?:\{\})?', 'e'),
        (r'\\textschwa(?:\{\})?', 'e'),
        (r'\\textrhooktopd(?:\{\})?', 'd'),
        (r'\\textthorn(?:\{\})?', 'th'),
    ]

    def __init__(self, pairs=_rules):
        self._old, self._new = zip(*pairs)
        self._pattern = re.compile('|'.join('(%s)' % o for o in self._old))

    def __call__(self, s):
        return self._pattern.sub(self._repl, s)

    def _repl(self, match):
        return self._new[match.lastindex - 1]


REPLACE = Replace()
COMMAND1 = re.compile(r'\\text[a-z]+\{([^}]*)\}')
COMMAND2 = re.compile(r'\\text[a-z]+')
ACCENT = re.compile(r'''\\[`'^"H~ckl=b.druvt](\{[a-zA-Z]\}|[a-zA-Z])''')
DROP = re.compile(r'\\[^\s{}]+\{|\\.|[{}]')


def undiacritic(txt):
    if isinstance(txt, unicode):
        txt = unidecode(txt)
    txt = REPLACE(txt)
    txt = COMMAND1.sub(r'\1', txt)
    txt = COMMAND2.sub('', txt)
    txt = ACCENT.sub(r'\1', txt)
    return DROP.sub('', txt)
