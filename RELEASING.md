
Releasing clld/glottolog
========================

0. Make sure 
   - you have the latest ISO 639-3 code tables from 
     https://iso639-3.sil.org/code_tables/download_tables
     put into `build/`,
   - run `glottolog isoretirements`
   - and commited and pushed the changes.
1. Check out `master` and pull the latest changes:
```
git checkout master
git pull origin master
```
2. Check the tree and references running
```
glottolog check
```
making sure there are no `ÈRROR`s

Also run
```
glottolog index
```
and commit up-to-date languoid index pages.


Merging the BibTeX files
------------------------

3. Update automatically created files:
   - `iso6393.bib`: Run `glottolog isobib`
   - `evobib.bib`: Run `glottolog evobib`
   - `benjamins.bib`:
     - Switch to the clone of `clld/benjamins`
     - Pull the latest changes via FTP 
     - Recreate `benjamins.bib`, running `python to_bib.py`
     - Switch back to `clld/glottolog`
     - Run `glottolog copy_benjamins PATH/TO/benjamins/benjamins.bib`
4. Run `glottolog bib` to create `build/monster-utf8.bib`
5. Add the release to CHANGES.md

Releasing
---------

6. Add release notes to `CHANGES.md` and `CONTRIBUTORS.md`
7. Draft a new release running
```
glottolog --repos=. release
git commit -a -m"release <version>"
git tag -a v<version> -m "release <version>"
```
8. Push all changes to origin running
```bash
git push origin
git push --tags origin
```
9. Create a "proper" release on GitHub and have it picked up by ZENODO.
10. Add DOI badge from ZENODO as soon as it becomes available.

