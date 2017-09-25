# Glottolog Cookbook

This cookbook contains recipes to tackle common tasks involving Glottolog data.
The data served by the [Glottolog web app](http://glottolog.org) is curated in the GitHub repository 
[`clld/glottolog`](https://github.com/clld/glottolog) and can be accessed programmatically from Python
code using the package [`pyglottolog`](https://github.com/clld/glottolog#the-python-client-library-pyglottolog) 
which comes with the repository.


- [treemaker](treemaker): Extracting a tree for a given set of languoids from the global tree.
- [`locations_of_child_languages.py`](locations_of_child_languages.py) is a script to extract locations for all languages in a given clade. It must be invoked specifying the local path to a clone of the Glottolog repository, the glottocode of the clade and the name of the CSV file to which to write the data, e.g.
  ```
  $ python locations_of_child_languages.py glottolog narr1281 narrow_bantu_locations.csv
  ```
  will result in a CSV file as follows:
  ```
  $ head narrow_bantu_locations.csv 
  name,glottocode,latitude,longitude
  Bube,bube1242,3.53638,8.68929
  Chikunda,kund1255,-15.7337,30.2804
  ```
