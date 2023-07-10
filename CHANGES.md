# Changelog

Notable changes between releases of the Glottolog data.


## [4.8] - 2023-07-06

- Added Grambank as refprovider.
- Added ELCat as refprovider.


## [4.7] - 2022-12-05

- See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of merged PRs and https://github.com/glottolog/glottolog/milestone/8?closed=1 for a list of issues addresses in this release.


## [4.6] - 2022-05-24

- Added OFDN bibliography as refprovider.
- Added JOCP refprovider.
- Added Glossa as refprovider.
- Updated the langsci refprovider from ~2,000 to now ~50,000 references.


## [4.5] - 2021-12-10

- Added Pulotu bibliography as refprovider.
- See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [4.4] - 2021-05-14

- Renamed provider "elp" to "elpub", see https://github.com/glottolog/glottolog/issues/674
- See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [4.3] - 2020-10-01

- Added ELPublishing bibliography
- See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [4.2.1] - 2020-04-16

- Re-inserted double quotes marking pejorative alternative names from ElCat
- Fully re-activate Sebastian Bank as editor


## [4.2] - 2020-04-16

- Added D-PLACE bibliography
- Added timespan attributes for extinct languages
- See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [4.1] - 2019-11-27

- Added GeoJSON files for macroareas
- Added more links to other language resources
- See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [4.0] - 2019-06-28

- Languoid INI files may now contain a section [links], providing links
  to related resources on the web, e.g. the corresponding page at ElCat.
- To improve the documentation of the data, we have included machine-readable
  metadata in the `config` directory, providing controlled vocabularies - e.g.
  for AES status - stored in INI files.
- Glottolog data releases are now supplemented by a CLDF dataset
  (see https://github.com/glottolog/glottolog-cldf)
  for better accessibility - in particular of the languoid data, which is 
  organized as CLDF parameters, e.g. coding AES and MED for languages.


## [3.4] - 2019-04-02

See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [3.3.2] - 2018-08-22

- fixed Tangkhulic misspecification
- fixed classification of North Paman


## [3.3.1] - 2018-08-06

- fixed issue https://github.com/clld/glottolog/issues/240 whereby English was
  listed as nearly extinct language.
- fixed issue https://github.com/clld/glottolog/issues/239 whereby languoid index
  files were not in sync with the classification tree.


## [3.3] - 2018-07-25

See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [3.2] - 2018-01-25

See https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Amerged for a list of
accepted changes.


## [3.1] - 2017-11-22

### References

Two new bibliographies have been contributed:
- The bibliography of the [autotyp database](https://github.com/autotyp/autotyp-data)
- Marc Tang's collection of references relating to nominal classification


### Classification

Many changes small and not-so-small. For details refer to the individual
[pull requests](https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Aclosed)


### Other

[Aggregated/merged data on language endangerment](https://github.com/glottolog/glottolog/pulls?q=is%3Apr+is%3Aclosed) 
has been added in `[endangerment]` sections of languoid's info files.
See [SOURCES.md](SOURCES.md) for details about the sources.


## [3.0] - 2017-03-29

### References

Bibliographical records for all linguistic books and journal articles
published by John Benjamins Publishing Company have been added.

### Languoids

The language classification has changed in many - smaller and bigger - ways since Glottolog 2.7 more than a year ago. We hope to make these changes more transparent and tractable by using version control for the Glottolog data and labelling changes to the classification appropriately. 


## [2.7] - 2016-01-26

### References

We added references from a new provider:
All 2802 references cited in books published by Language Science Press have been added to Glottolog. These references will be curated and added to in the future by the Language Science Team.

### Languoids

8 languages have been added and the classification has been changed (mostly locally), resulting in 23 new family nodes and 7 updated families. 


## [2.6] - 2015-10-07

This edition introduces only minor changes to both, languoids and references. Instead, our focus was on improving the release procedures, and in particular aligning data curation and publication. We hope these improvements will allow for more frequent updates of the published version of Glottolog in the future.


## [2.5] - 2015-07-17

### References

We added references from three new providers:

- 2723 references from the Bibliographie zur luxemburgischen Linguistik
- 1018 references collected by Guillaume Jacques
- 596 references from Martin Haspelmath's bibliography

Thanks for sharing! 


### Languoids

16 languages have been added and the classification has been changed (mostly locally), resulting in 53 new family nodes and 15 updated families. 


## [2.4] - 2015-03-20

### References

We added references from three new providers:

- 68131 references from De Gruyter language and linguistics books and journals
- 2144 references from Georeferenzierte Online-Bibliographie Areallinguistik
- 1972 references from The PHOIBLE database bibliography

Thanks for sharing! 

### Languoids

76 languages have been added and the classification has been changed (mostly locally), resulting in 219 new family nodes and 52 updated families. 


### Project Infrastructure

The Glottolog data is now curated in a Git repository hosted at GitHub. Thus, changes to the data in between updates of the Glottolog website are more transparent and traceable; 


## [2.3]

### References

While we did remove thousands of obsolete references (duplicates or references that have been superseded) 2862 references have also been added and thousands have been corrected. When browsing to the URL of one of the obsolete references, you should either be redirected (in case of duplicates) with an HTTP code of 301 or you should see an HTTP 410 Gone message. 

### Languoids

76 languages have been added and classification has been changed (mostly locally), resulting in 73 new family nodes. 

### Sign Languages

Sign Languages have now better coverage and classification. Though the set of references, inventory and classification is not yet on the same level as for spoken languages. 

### Computerized assignment

Many of the relations between references and languages and of the relations between references and document types are created by a process we call computerized assignment. 

Whether relations for a specific reference have been assigned automatically is now indicated with small warning signs . This information can also used for sorting lists of references by clicking the corresponding ca column head. 

The automatic language guesser has been improved through a better training data set, and set to be less aggressive (autoclassifications that would make the descriptive status of the language increase are blocked). It is still reasonably aggressive however. 

