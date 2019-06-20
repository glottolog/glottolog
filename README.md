# The Glottolog Data Repository

The Glottolog data repository is the place where the data served by the
[Glottolog web application](https://glottolog.org) is curated. But the repository
also provides an alternative way to access Glottolog's data locally, and possibly
even locally customized data by [forking](https://help.github.com/articles/fork-a-repo/) glottolog/glottolog.


## How-to cite

Only released versions of the Glottolog data should be cited. These releases are
archived with and available from ZENODO at
https://doi.org/10.5281/zenodo.596479


## Languoids

Data about Glottolog languoids (languages, dialects or sub-groups, aka families) is stored in text files (one per languoid)
formatted as [INI files](https://en.wikipedia.org/wiki/INI_file)
in the `languoids/tree` subdirectory.
The directory tree mirrors the Glottolog classification of languages.


## References

The Glottolog bibliography is curated as a set of [BibTeX](https://en.wikipedia.org/wiki/BibTeX) files in the `references/bibtex` subdirectory, which are merged
into a single reference database for each release/edition.


## Metadata

Metadata - e.g. [controlled vocabularies](https://en.wikipedia.org/wiki/Controlled_vocabulary) for some of the languoid data - are stored as
INI files in the `config` subdirectory.


## Accessing data programmatically

You can access the data in a clone or release of this repository from Python
programs using the [pyglottolog](https://github.com/glottolog/pyglottolog)
package.

