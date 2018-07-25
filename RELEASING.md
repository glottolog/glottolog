
Releasing clld/glottolog
========================

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
5. Run `git tag -a v<version> -m "release <version>"`
6. Commit and push all changes to master.

Releasing
---------

7. Draft a new release
8. Add DOI badge from ZENODO as soon as it becomes available.


Releasing `pyglottolog`
-----------------------

- Make sure the tests pass:
  ```
  tox -r
  ```
- Make sure flake8 passes:
  ```
  flake8 pyglottolog
  ```
- Change version to the new version number in
  - `setup.py`
  - `pyglottolog/__init__.py`
- Bump version number:
  ```
  git commit -a -m "release pyglottolog <version>"
  ```
- Create a release tag:
  ```
  git tag -a pyglottolog-<version> -m "first version to be released on pypi"
  ```
- Release to PyPI:
  ```
  git checkout tags/v$1
  rm dist/*
  python setup.py sdist bdist_wheel
  twine upload dist/*
  ```
- Push to github:
  ```
  git push origin
  git push --tags
  ```
- Increment version number and append `.dev0` to the version number for the new development cycle:
  - `pyglottolog/__init__.py`
  - `setup.py`

- Commit/push the version change:
  ```shell
  git commit -a -m "bump version for development"
  git push origin
  ```
