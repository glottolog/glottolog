# The Glottolog Data Repository

The Glottolog data repository is the place where the data served by the
[Glottolog web application](http://glottolog.org) is curated. But the repository
also provides an alternative way to access Glottolog's data locally, and possibly
even locally customized by [forking](https://help.github.com/articles/fork-a-repo/) clld/glottolog.


## Languoids

Data about Glottolog languoids (languages, dialects or sub-groups, aka families) is stored in text files (one per languoid)
formatted as [INI files](https://en.wikipedia.org/wiki/INI_file).
The directory tree mirrors the Glottolog classification of languages.


## References

The Glottolog bibliography is curated as a set of [BibTeX](https://en.wikipedia.org/wiki/BibTeX) files, which are merged
into a single reference database for each release/edition.


## The python client library `pyglottolog`

[![Build Status](https://travis-ci.org/clld/glottolog.svg?branch=master)](https://travis-ci.org/clld/glottolog)

The data in this repository can be conveniently accessed via a command line interface
and a python API, both implemented in the python package `pyglottolog`, which is distributed
as part of this repository.

### Install

To install `pyglottolog` you need a python installation on your system, running python 2.7 or >3.4. Run
```
python setup.py develop
```
on the top level of this repository to install the requirements, `pyglottolog` and
the command line interface `glottolog`.

### CLI

Command line functionality is implemented via sub-commands of `glottolog`. The list of
available sub-commands can be inspected running
```
$ glottolog --help
usage: glottolog [-h] [--verbosity VERBOSITY] [--log-level LOG_LEVEL]
                 [--repos REPOS]
                 command ...

Main command line interface of the pyglottolog package.

positional arguments:
  command               isobib | show | edit | create | bib | tree | newick |
                        index | check | metadata | refsearch | refindex |
                        langsearch | langindex | tree2lff | lff2tree
  args

optional arguments:
  -h, --help            show this help message and exit
  --verbosity VERBOSITY
                        increase output verbosity
  --log-level LOG_LEVEL
                        log level [ERROR|WARN|INFO|DEBUG]
  --repos REPOS         path to glottolog data repository

Use 'glottolog help <cmd>' to get help about individual commands.
```

### Python API

Glottolog data can also be accessed programmatically from within python programs.
All functionality is mediated through an instance of `pyglottolog.api.Glottolog`, e.g.
```python
>>> from pyglottolog.api import Glottolog
>>> api = Glottolog('.')
>>> print(api)
<Glottolog repos v0.2-259-g27ac0ef at /.../glottolog>
```

#### Accessing languoid data
```python
>>> api.languoid('stan1295')
<Language stan1295>
>>> print(api.languoid('stan1295'))
German [stan1295]
```

#### Accessing reference data
```python
>>> print(api.bibfiles['hh.bib']['s:Karang:Tati-Harzani'])
@book{s:Karang:Tati-Harzani,
    author = {'Abd-al-'Ali Kārang},
    title = {Tāti va Harzani},
    publisher = {Tabriz: Tabriz University Press},
    address = {Tabriz},
    pages = {6+160},
    year = {1334 [1953]},
    glottolog_ref_id = {41999},
    hhtype = {grammar_sketch},
    inlg = {Farsi [pes]},
    lgcode = {Harzani [hrz]},
    macro_area = {Eurasia}
}
```