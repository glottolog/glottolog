# _bibtex_undiacritic.py - remove latex/unicode diacritics for string comparison

import re

from unidecode import unidecode
from six import text_type


COMMAND1 = re.compile(r'\\[a-z]+\{([^}]*)\}')
COMMAND2 = re.compile(r'\\text[a-z]+')
ACCENT = re.compile(r'''\\[`'^"H~ckl=b.druvt](\{[a-zA-Z]\}|[a-zA-Z])''')
DROP = re.compile(r'\\[^\s{}]+\{|\\.|[{}]')


def undiacritic(txt):
    assert isinstance(txt, text_type)
    txt = unidecode(txt)
    txt = COMMAND1.sub(r'\1', txt)
    txt = COMMAND2.sub('', txt)
    txt = ACCENT.sub(r'\1', txt)
    return DROP.sub('', txt)
