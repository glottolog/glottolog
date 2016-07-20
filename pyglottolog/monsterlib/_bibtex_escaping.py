# _bibtex_escaping.py - latex escapes and unicode bracket escapes

"""TODO: replace in source files OR add de-/encoding rule

\textsubdot{
\textsubbar{
\textsuperscript{ c
\~e
\textsubline{
\texthtd
\textvertline
\textesh
\textbaru
\textbari
\textsubring
\textgamma
\textupsilon


\texthooktop{
\textsubwedge{
\textemdash
\textendash
\textthreequarters
\texthooktopd
\textrevglotstop
\;
\:

---, --, ``'', {}, \textdot, \textsubdot,  \v{j} -> \v\j

see also:
  _bibtex_undiacritic.py rules
  http://github.com/clld/clld/blob/master/clld/lib/bibtex.py
  http://github.com/clld/clld/blob/master/clld/lib/latex.py
  http://github.com/mcmtroffaes/latexcodec/blob/develop/latexcodec/codec.py#L97

FIXME: tex-escape/character entity mix in anla.bib titlealt

\textpolhook{ -> \k{}?
\&
"""

import re
import codecs

import latexcodec

__all__ = ['u_escape', 'u_unescape', 'latex_to_utf8']

LATEX_TABLE = {
    u'\N{LATIN SMALL LETTER ENG}': br'\ng',
    u'\N{LATIN CAPITAL LETTER ENG}': br'\NG',
    u'\N{LATIN SMALL LETTER OPEN O}': br'\textopeno',
    u'\N{LATIN SMALL LETTER THORN}': br'\textthorn',
    u'\N{LATIN SMALL LETTER GLOTTAL STOP}': br'\textglotstop',
    u'\N{MODIFIER LETTER GLOTTAL STOP}': br'\textraiseglotstop',
    u'\N{LATIN SMALL LETTER I WITH STROKE}': br'\textbari',
}

_LC_TABLES = (latexcodec.codec._LATEX_UNICODE_TABLE,)

assert u'\xe4'.encode('latex') == r'\"a'
assert r'\"a'.decode('latex') == u'\xe4'

for unicode_text, latex_text in LATEX_TABLE.iteritems():
    for table in _LC_TABLES:
        table.register(unicode_text, latex_text)


def u_escape(s):
    def iterchunks(s):
        for c in s:
            o = ord(c)
            if o <= 127:
                yield c
            else:
                yield r'?[\u%d]' % o

    return ''.join(iterchunks(s))


def u_unescape(s, pattern=re.compile(r'\?\[\\u(\d{3,5})\]')):
    def iterchunks(s, matches):
        pos = 0
        for m in matches:
            start, end = m.span()
            yield s[pos:start]
            yield unichr(int(m.group(1)))
            pos = end
        yield s[pos:]

    return ''.join(iterchunks(s, pattern.finditer(s)))


class U_escapeCodec(codecs.Codec):

    def encode(self, input, erors='strict'):
        return u_escape(input.encode('ascii')), len(input)

    def decode(self, input, erors='strict'):
        return u_unescape(input.decode('ascii')), len(input)


class U_escapeStreamWriter(U_escapeCodec, codecs.StreamWriter):
    pass


class U_escapeStreamReader(U_escapeCodec, codecs.StreamReader):
    pass


def _find_u_escape(encoding):
    if encoding == 'ascii+u_escape':
        return codecs.CodecInfo(name='ascii+u_escape',
            encode=U_escapeCodec().encode, decode=U_escapeCodec().decode,
            streamwriter=U_escapeStreamWriter, streamreader=U_escapeStreamReader)


codecs.register(_find_u_escape)


# legacy

def latex_to_utf8(s, verbose=True, debracket=re.compile("\{(.)\}")):
    us = s.decode("latex")
    us = debracket.sub("\\1", us)
    if verbose:
        remaininglatex(us)
    return us


platexspc = [re.compile(pattern) for pattern in [
    r'''\\(?P<typ>[^\%'\`\^\~\=\_\"\s\{]+)\{(?P<ch>[a-zA-Z]?)\}''',
    r'''\\(?P<typ>['\`\^\~\=\_\"]+?)\{(?P<ch>[a-zA-Z])\}''',
    r'\\(?P<typ>[^a-zA-Z\s\%\_])(?P<ch>[a-zA-Z])',
    r'\\(?P<typ>[^a-zA-Z\s\%\{\_]+)(?P<ch>[a-zA-Z])',
    r'\\(?P<typ>[^\{\%\_]+)\{(?P<ch>[^\}]+)\}',
    r'\\(?P<typ>[^\{\_\\\s\%]+)(?P<ch>\s)',
]]


def remaininglatex(txt):
    for pattern in platexspc:
        o = pattern.findall(txt)
        if o:
            print o[:100] #txt[o.start()-10:o.start()+10], o.groups()
