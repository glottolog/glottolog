
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

Almost all current ISO 693-3 codes for individual, living languages (as well as many retired codes) can be 
mapped to a Glottolog languoid. This is done by assigning a code to the `iso639-3` field in a languoid's
info file, e.g. [`aab` for Arum](https://github.com/glottolog/glottolog/blob/20dbfb6e6a37244c02f57f2f1e046f7441ae72f4/languoids/tree/atla1278/volt1241/benu1247/benu1248/alum1250/alum1251/alum1246/md.ini#L6).

The easiest way to access all correspondences is via the [Glottolog CLDF data](https://doi.org/10.5281/zenodo.3260727).
The relevant information is available from the `LanguageTable`, e.g. running
```shell
csvgrep -c ISO639P3code -r ".+" cldf/languages.csv | csvcut -c ID,ISO639P3code
```

As of Glottolog 5.3, 8184 different Glottolog languoids are mapped to 8184 different ISO 639-3 codes:
```shell
$ csvgrep -c ISO639P3code -r ".+" cldf/languages.csv | csvcut -c ID,ISO639P3code | csvstat
  1. "ID"

	Type of data:          Text
	Unique values:         8184

  2. "ISO639P3code"

	Type of data:          Text
	Unique values:         8184
	Longest value:         3 characters
	Most common values:    faa (1x)
	                       was (1x)
Row count: 8184
```


## Why doesn't language X link to Wikipedia page Y?

See [SOURCES](SOURCES.md) for a description of where from and how Glottolog aggregates data.
