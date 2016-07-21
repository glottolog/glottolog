# coding: utf-8
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
import unicodedata

from six import text_type, unichr
import latexcodec

__all__ = [
    'u_escape', 'u_unescape', 'latex_to_utf8', 'ulatex_postprocess', 'ulatex_preprocess']

LATEX_TABLE = {
    u'COMBINING DOT ABOVE': [br'\.', br'\textdot'],
    u'COMBINING DOT BELOW': br'\textsubdot',
    u'COMBINING MACRON': [br'\=', br'\textbar'],
    u'COMBINING MACRON BELOW': br'\textsubbar',
    u'COMBINING COMMA BELOW': br'\,',
    u'COMBINING TILDE BELOW': br'\textsubtilde',
    u'COMBINING CARON': br'\v',
    u'COMBINING CARON BELOW': br'\textsubwedge',
    u'COMBINING CIRCUMFLEX ACCENT': br'\^',
    u'COMBINING ACUTE ACCENT': br"\'",
    u'COMBINING GRAVE ACCENT': br"\`",
    u'COMBINING LATIN SMALL LETTER C': br'\textsuperscript{c}',
    u'COMBINING RING BELOW': br'\textsubring',
    u'COMBINING OGONEK': br'\textpolhook',
    u'COMBINING TILDE': br'\~',
    u'COMBINING DOUBLE GRAVE ACCENT': br'\textdoublegrave',
    u'COMBINING BREVE BELOW': br'\textsubu',
    u'COMBINING BRIDGE BELOW': br'\textsubbridge',

    u'MODIFIER LETTER SMALL W': br'\textsuperscript{w}',
    u'SUPERSCRIPT ONE': br'\textsuperscript{1}',
    u'SUPERSCRIPT TWO': br'\textsuperscript{2}',
    u'SUPERSCRIPT THREE': br'\textsuperscript{3}',
    u'SUPERSCRIPT FOUR': br'\textsuperscript{4}',
    u'PERCENT SIGN': br'\%',
    u'LATIN SMALL LETTER D WITH HOOK': [br'\texthtd', br'\texthooktopd'],
    u'LATIN SMALL LETTER B WITH HOOK': [br'\texthtb', br'\texthooktopb'],
    u'LATIN SMALL LETTER N WITH LEFT HOOK': br'\textltailn',
    u'LATIN SMALL LETTER S WITH HOOK': br'\textrtails',
    u'LATIN SMALL LETTER ETH': br'\dh',
    u'LATIN SMALL LETTER ENG': br'\ng',
    u'LATIN CAPITAL LETTER ENG': br'\NG',
    u'LATIN SMALL LETTER OPEN O': br'\textopeno',
    u'LATIN SMALL LETTER THORN': br'\textthorn',
    u'LATIN LETTER GLOTTAL STOP': br'\textglotstop',
    u'LATIN LETTER INVERTED GLOTTAL STOP': br'\textrevglotstop',
    u'LATIN SMALL LETTER SCHWA': br'\textschwa',
    u'LATIN SMALL LETTER R WITH TAIL': br'\textrtailr',
    u'LATIN SMALL LETTER BARRED O': br'\texttheta',
    u'LATIN SMALL LETTER O WITH HORN': br'\ohorn',
    u'MODIFIER LETTER GLOTTAL STOP': br'\textraiseglotstop',
    u'LATIN SMALL LETTER I WITH STROKE': br'\textbari',
    u'LATIN SMALL LETTER E WITH TILDE': br'\~e',
    u'INVERTED QUESTION MARK': br'\textquestiondown',
    u'INVERTED EXCLAMATION MARK': [br'\textexclamationdown', br'\textexclamdown'],
    u'HORIZONTAL ELLIPSIS': br'\dots',
    u'RIGHT DOUBLE QUOTATION MARK': br'\textquotedblright',
    u'LEFT DOUBLE QUOTATION MARK': br'\textquotedblleft',
    u'LEFT-POINTING DOUBLE ANGLE QUOTATION MARK': br'\guillemotleft',
    u'RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK': br'\guillemotright',
    u'LATIN LETTER ALVEOLAR CLICK': [br'\textdoublebarpipe', br'\textdoublebarpipevar'],
    u'PLUS-MINUS SIGN': br'\plusminus',
    u'LATIN SMALL LETTER E WITH MACRON AND ACUTE': br'\textacutemacron e',
    u'LATIN SMALL LETTER E WITH OGONEK': br'\textpolhook e',
    u'LESS-THAN SIGN': br'\textless',
    u'GREATER-THAN SIGN': br'\textgreater',
    # a bit of a misuse, but that's how it is used in goba.bib:
    u'LATIN CROSS': br'\textbarpipe',
    # again a mis-use:
    u'LATIN SMALL LETTER OPEN E': br'\textepsilon',
    u'LATIN SMALL LETTER GAMMA': br'\textgamma',
    u'LATIN SMALL LETTER TURNED V': br'\textturnv',
    u'GREEK SMALL LETTER BETA': br'\textbeta',
    u'GREEK CAPITAL LETTER ETA': br'\textEta',
    u'GREEK SMALL LETTER OMEGA': br'\textomega',
    u'LATIN SMALL LETTER UPSILON': br'\textupsilon',
    u'LATIN SMALL LETTER ESH': br'\textesh',
    u'CYRILLIC SMALL LETTER HARD SIGN': br'\texthardsign',
    u'EURO SIGN': br'\eurosign',
    u'DEGREE SIGN': br'\circ',
    u'VERTICAL LINE': br'\textvertline',
    u'DOUBLE VERTICAL LINE': br'\textdoublevertline',
}

_LC_TABLES = (
    latexcodec.codec._LATEX_UNICODE_TABLE, latexcodec.codec._ULATEX_UNICODE_TABLE)

assert u'\xe4'.encode('latex') == r'\"a'
assert r'\"a'.decode('latex') == u'\xe4'

for unicode_text, latex_text in LATEX_TABLE.iteritems():
    if not isinstance(latex_text, (list, tuple)):
        latex_text = [latex_text]
    uchar = unicodedata.lookup(unicode_text)
    for table in _LC_TABLES:
        for lt in latex_text:
            table.register(uchar, lt)


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

numcharref_patterns = [
    re.compile('\\\\?&#(?P<dec>[0-9]+);'),
    re.compile('\?\[\\\\u\s*(?P<dec>[0-9]+)\]')]

command_patterns = [
    re.compile('\\\\%s\{(?P<arg>[^\}]+)\}' % name) for name in ['url', 'emph']]


def numcharref_repl(m):
    return unichr(int(m.group('dec')))


def is_combining(c):
    try:
        return unicodedata.name(c).startswith('COMBINING')
    except ValueError:
        return False


def ulatex_preprocess(s):
    s = s.decode('utf8')
    for p in numcharref_patterns:
        s = p.sub(numcharref_repl, s)
    for p in command_patterns:
        s = p.sub(lambda m: m.group('arg'), s)
    s = unicodedata.normalize('NFC', s)
    for c in s:
        if is_combining(c):
            print s
            raise ValueError
    return s


def ulatex_postprocess(s, debracket=re.compile(u"\{([^\}]+)\}")):
    if not isinstance(s, text_type):
        s = s.decode('ascii')
    s = debracket.sub(u"\\1", debracket.sub(u"\\1", s.replace('{}', '')))
    n = []
    comb = []
    for c in s:
        if is_combining(c):
            comb.append(c)
        else:
            n.append(c)
            while comb:
                n.append(comb.pop())
    return unicodedata.normalize('NFC', u''.join(n))


def ulatex_decode(s):
    return ulatex_postprocess(ulatex_preprocess(s).decode('ulatex'))


# legacy

def latex_to_utf8(s, verbose=True, debracket=re.compile("\{(.)\}")):
    us = s.decode("latex")
    us = debracket.sub("\\1", us)
    if verbose:
        remaininglatex(us)
    return us


platexspc = [re.compile(pattern) for pattern in [
    r'''\\(?P<typ>[^\%'\`\^\~\=\_\"\s\{]+)\{(?P<ch>[a-zA-Z]?)\}''',  # \typ{opt ch}
    r'''\\(?P<typ>['\`\^\~\=\_\"]+?)\{(?P<ch>[a-zA-Z])\}''',  # \typ {ch}
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
