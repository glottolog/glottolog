# How to Contribute to Glottolog

If you have data that you might want to contribute to Glottolog,
- you may [open issues](https://github.com/glottolog/glottolog/issues) to let us know,
- submit pull requests to propose changes or additions or
- or send an email to glottolog @ eva.mpg.de .


## Adding references

Bibliographic references in Glottolog are curated as set of BibTeX files, one
for each [refprovider](https://glottolog.org/langdoc/langdocinformation) or provenance context.

If you just want to add a handful of references, the easiest way to do so is to propose adding
them to [Harald Hammarström's bib](https://glottolog.org/providers/hh), which is updated often.

For bigger sets of references adding a "refprovider" may be more suitable. This requires
- adding the BibTeX file in [`references/bibtex`](https://github.com/glottolog/glottolog/tree/master/references/bibtex)
- registering the provider by adding some metadata in [`references/BIBFILES.ini`](https://github.com/glottolog/glottolog/blob/master/references/BIBFILES.ini)
- noting the addition in the "UNRELEASED" section of [`CHANGES.md`](https://github.com/glottolog/glottolog/blob/master/CHANGES.md)

If the biblography is curated and updated elsewhere, this should be noted in the
`curation` field in `BIBFILES.ini`, and if the changes are to be merged back
into Glottolog, a corresponding [command in `pyglottolog`](https://github.com/glottolog/pyglottolog/tree/master/src/pyglottolog/admin_commands) might need
to be implemented.


## Adding languoid metadata

Adding languoid metadata can be done by editing the *languoid info files*, i.e. the files called `md.ini`
in [INI format](https://en.wikipedia.org/wiki/INI_file) nested under 
[`languoids/tree`](https://github.com/glottolog/glottolog/tree/master/languoids/tree).
It must be noted that some of the content of these files is curated (and possibly recreated) automatically,
vi `pyglottolog`. So before embarking on a bigger editing spree, double check with the editors whether your
intended changes make sense, i.e. will survive the next round of automated curation.

Since the Glottolog classification tree and hence the directory tree at `languoids/tree` is hard to navigate,
you might want to use https://glottolog.org to lookup languoids of interest and click the button with the pencil
icon on pages like https://glottolog.org/resource/languoid/id/pali1273 to get to the corresponding file on GitHub.
(This may fail in rare cases when the classification on GitHub has been modified after the latest Glottolog release.)
