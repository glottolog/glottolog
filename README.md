# The Glottolog Data Repository

The Glottolog data repository is the place where the data served by the
[Glottolog web application](https://glottolog.org) is curated. But the repository
also provides an alternative way to access Glottolog's data locally, and possibly
even locally customized data by [forking](https://help.github.com/articles/fork-a-repo/) glottolog/glottolog.


## Accessing Glottolog data

- **This repository** is the place where Glottolog data is curated. So it's the right place to [open issues](https://github.com/glottolog/glottolog/issues) about errors you identified
  and to [propose changes](CONTRIBUTING.md). A clone of this repository is also the right thing if you need access to **all** of Glottolog's data,
  possibly including older versions and the history of changes. Since the format of the data here is tailored towards maintainability - and
  not towards accessibility - you might want to use the Python package [pyglottolog](https://github.com/glottolog/pyglottolog) to access
  it programmatically.
- [**glottolog.org**](https://glottolog.org) - the Glottolog website - may be the most convenient place to inspect and browse the latest released
  version of Glottolog data. It also provides [access to various download formats](https://glottolog.org/meta/downloads), tailored towards
  various re-use scenarios.
- [**glottolog as CLDF dataset**](https://doi.org/10.5281/zenodo.3260727) is probably the best option for accessing all of Glottolog's
  languoid data. Due to the format being [CLDF](https://cldf.clld.org), it can be used from all kinds of programming environments such
  as spreadsheet programs, programming languages like R or python, or the UNIX shell. A description of the files in this datasets is
  available in the [README](https://github.com/glottolog/glottolog-cldf/blob/master/cldf/README.md).


### How-to cite

Only released versions of the Glottolog data should be cited. These releases are
archived with and available from ZENODO at
https://doi.org/10.5281/zenodo.596479


## Types of data in Glottolog


### Languoids

Data about Glottolog languoids (languages, dialects or sub-groups, aka families) is stored in text files (one per languoid)
formatted as [INI files](https://en.wikipedia.org/wiki/INI_file)
in the `languoids/tree` subdirectory.
The directory tree mirrors the Glottolog classification of languages.


### References

The Glottolog bibliography is curated as a set of [BibTeX](https://en.wikipedia.org/wiki/BibTeX) files in the `references/bibtex` subdirectory, which are merged
into a single reference database for each release/edition.


### Metadata

Metadata - e.g. [controlled vocabularies](https://en.wikipedia.org/wiki/Controlled_vocabulary) for some of the languoid data - are stored as
INI files in the [`config`](config/) subdirectory.
