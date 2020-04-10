
Releasing glottolog/glottolog
=============================

0. Make sure you have the latest ISO 639-3 code tables from 
   https://iso639-3.sil.org/code_tables/download_tables
   put into `build/`,
1. Check out `master` and pull the latest changes:
   ```
   git checkout master
   git pull origin master
   ```
2. Check the tree and references running
   ```
   glottolog-admin check
   ```
   making sure there are no `ÈRROR`s

   Also run
   ```shell script
   glottolog-admin update
   ```
   and commit and push the changes.

Merging the BibTeX files
------------------------

3. Update automatically created files:
   - `iso6393.bib`: Run `glottolog-admin isobib`
   - `evobib.bib`: Run `glottolog-admin evobib`
   - `dplace.bib`: Run `glottolog-admin dplacebib`
   - `benjamins.bib`:
     - Switch to the clone of `glottolog/benjamins`
     - Pull the latest changes via FTP 
     - Recreate `benjamins.bib`, running `python to_bib.py`
     - Switch back to `glottolog/glottolog`
     - Run `glottolog-admin benjaminsbib PATH/TO/benjamins/benjamins.bib`
4. Run `glottolog-admin bib` to create `build/monster-utf8.bib` - about 20mins

Releasing
---------

5. Add release notes to `CHANGES.md` and `CONTRIBUTORS.md`
6. Draft a new release running
   ```bash
   glottolog-admin release
   git commit -a -m"release <version>"
   git tag -a v<version> -m "release <version>"
   glottolog --repos=. cldf ../glottolog-cldf/cldf
   ```
7. Push all changes to origin running
   ```bash
   git push origin
   git push --tags origin
   ```
   and
   ```bash
   cd ../glottolog-cldf
   cd commit -a -m"release <release>"
   git tag -a v<version> -m "release <version>"
   git push origin
   git push --tags origin
   ```
8. Create a "proper" release on GitHub and have it picked up by ZENODO.
9. Add DOI badge from ZENODO as soon as it becomes available.
