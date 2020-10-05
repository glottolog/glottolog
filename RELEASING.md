
Releasing glottolog/glottolog
=============================

0. Make sure you have the latest ISO 639-3 code tables from 
   https://iso639-3.sil.org/code_tables/download_tables
   put into `build/`,
1. Check out `master`, pull the latest changes then switch to a new release branch:
   ```
   git checkout master
   git pull origin master
   git checkout -b release-<version>
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
   and make sure the data can be loaded into treedb:
   ```
   workon treedb
   cd treedb
   python -c "import treedb; treedb.load(); treedb.write_csv()"
   ```
   and commit and push the changes.

Merging the BibTeX files
------------------------

3. Update automatically created files:
   - `iso6393.bib`: Run `glottolog-admin isobib`
   - `elp.bib`: Run `glottolog-admin elpbib`
   - `evobib.bib`:
     - download the latest version from https://doi.org/10.5281/zenodo.1181952
     - Run `glottolog-admin evobib evobib-converted.bib`
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
6. Draft a new release and push it online for review:
   ```bash
   glottolog-admin release <version>
   git commit -a -m"release <version>"
   git push origin release-<version>
   ```
7. Upon approval:
   ```
   git checkout master
   git pull origin
   git branch -d release-<version>
   git tag -a v<version> -m "release <version>"
   glottolog --repos=. cldf ../glottolog-cldf/cldf
   ```
8. Push all changes to origin running
   ```bash
   git push origin
   git push --tags origin
   ```
   and
   ```bash
   cd ../glottolog-cldf
   git commit -a -m"release <release>"
   git tag -a v<version> -m "release <version>"
   git push origin
   git push --tags origin
   ```
9. Create a "proper" release on GitHub and have it picked up by ZENODO.
10. Add DOI badge from ZENODO as soon as it becomes available.


Checking a pull request
=======================

1. Update the `master` branch and store languoid stats:
   ```
   git checkout master
   git pull origin
   glottolog-admin writelanguoidstats
   ```
2. Check out the PR branch and run the checks:
   ```
   git checkout <BRANCH>
   glottolog-admin check --old-languoids
   ```
3. If necessary, run `glottolog-admin updatesources` and continue with 2.


Troubleshooting
===============

If `glottolog-admin bib` fails at
```python
  File "/home/forkel/venvs/glottolog/pyglottolog/src/pyglottolog/references/bibfiles_db.py", line 559, in assign_ids
    assert Entry.allhash(conn)
AssertionError
```
check the bad entries in `build/bibfiles.sqlite3`:
```sql
sqlite> select * from entry where hash is null;
292775|21|hw:Nigam:Andhra-Pradesh||||
```

This can be due to malformed BibTeX entries - and correspondingly must
be fixed in the BibTeX before re-running `glottolog-admin bib --rebuild`.

