
Releasing clld/glottolog
========================

1. Check out `master` and pull the latest changes.
2. Check the tree and references running `glottolog check`


Merging the BibTeX files
------------------------

1. Update automatically created files:
   - `iso6393.bib`: Run `glottolog isobib`
   - `benjamins.bib`: TODO
2. Run `glottolog bib`
3. Merge list of replacements for refs

4. Create list of new refs/languoids, querying the old db.
5. Drop db

- update version info and editors

6. recreate db
7. mark new refs/languoids reading in the lists created in 4.

