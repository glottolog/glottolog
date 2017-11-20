
Releasing clld/glottolog
========================

1. Check out `master` and pull the latest changes.
2. Check the tree and references running `glottolog check`


Merging the BibTeX files
------------------------

1. Update automatically created files:
   - `iso6393.bib`: Run `glottolog isobib`
   - `benjamins.bib`:
     - Switch to the clone of `clld/benjamins`
     - Pull the latest changes via FTP 
     - Recreate `benjamins.bib`, running `python to_bib.py`
     - Switch back to `clld/glottolog`
     - Run `glottolog copy_benjamins PATH/TO/clld/benjamins/benjamins.bib`
2. Run `glottolog bib`
3. Merge list of replacements for refs references/replacements.json

4. FIXME: Create list of new refs/languoids, querying the old db.
   - look up previous version in releases.ini
   - compute (new - old) for each criterion
5. Drop db

- update version info and editors

6. recreate db
7. mark new refs/languoids reading in the lists created in 4.


Releasing `pyglottolog`
-----------------------

- Make sure the tests pass:
  ```
  tox -r
  ```
- Make sure flake8 passes:
  ```
  flake8 --ignore=E711,E712,D100,D101,D103,D102,D301 --max-line-length=100 pyglottolog
  ```
- Change version to the new version number in
  - `setup.py`
  - `pyglottolog/__init__.py`
- Bump version number:
  ```
  git commit -a -m"bumped version number"
  ```
- Create a release tag:
  ```
  git tag -a pyglottolog-<version> -m"first version to be released on pypi"
  ```
- Push to github:
  ```
  git push origin
  git push --tags
  ```
- Make sure your system Python has ``setuptools-git`` installed and release to PyPI:
  ```
  git checkout tags/v$1
  python setup.py sdist register upload
  ```
