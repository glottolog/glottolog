
# Frequently asked questions

## How to validate Glottocodes?

Syntactically, a valid Glottocode is a 8-letter string, matching the regular expression `[0-9a-z]{4}[0-9]{4}`. Using `pyglottocode` this validation should be done as
```python
>>> from pyglottolog.languoids import Glottocode
>>> assert Glottocode.pattern.match('abcd1234')
```

Valid Glottocodes in the sense of codes that have already been assigned to a languoid can be accessed through the Glottolog API as follows:
```python
>>> from pyglottolog import Glottolog
>>> gl = Glottolog()
>>> codes = list(gl.glottocodes)
>>> len(codes)
111094
>>> codes[0]
'beqa1234'
```

Valid Glottocodes in the sense of codes of languoids in the current classification can be accessed through the Glottolog API as follows:
```python
>>> from pyglottolog import Glottolog
>>> gl = Glottolog()
>>> gl.languoid('beqa1234') is None  # code no longer in Glottolog
True
>>> gl.languoid('stan1295').name  # active code
'German'
```

## How to map ISO codes to Glottocodes?

TODO

