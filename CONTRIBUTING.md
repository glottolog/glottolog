# How to Contribute to Glottolog

If you have data that you might want to contribute to Glottolog,
- you may [open issues](https://github.com/glottolog/glottolog/issues) to let us know,
- submit pull requests to propose changes or additions or
- or send an email to glottolog @ eva.mpg.de .


## Adding references

Bibliographic references in Glottolog are curated as set of BibTeX files, one
for each "refprovider" or provenance context. Adding a "refprovider" requires
- adding the BibTeX file in `references/bibtex`
- registering the provider by adding some metadata in `references/BIBFILES.ini`
- noting the addition in `CHANGES.md`

If the biblography is curated and updated elsewhere, this should be noted in the
`curation` field in `BIBFILES.ini`, and if the changes are to be merged back
into Glottolog, a corresponding [command in `pyglottolog`](https://github.com/glottolog/pyglottolog/tree/master/src/pyglottolog/admin_commands) might need
to be implemented.

