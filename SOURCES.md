
# Sources of Glottolog data 

## Language endangerment data

Glottolog contains data about language endangerment drawn (and merged) from various sources:

- [ElCat](http://endangeredlanguages.com/):

> Catalogue of Endangered Languages. 2015. The University of Hawaii at Manoa and Eastern Michigan University. http://www.endangeredlanguages.com

  Almost all information in the Catalogue of Endangered Languages includes a citation of the original source which provided this data (e.g. journal article, book, personal communication, etc.). You can find citation information at the top of the "Language Information by Source" box on each language page; if you wish to reproduce data such as speaker numbers, you may cite the original source provided there. 

- The [UNESCO Atlas of the World's Languages in Danger](http://www.unesco.org/languages-atlas/):

> Moseley, Christopher (ed.). 2010. Atlas of the World’s Languages in Danger, 3rd edn. Paris, UNESCO Publishing. Online version: http://www.unesco.org/culture/en/endangeredlanguages/atlas

- [Ethnologue, 20th edition](https://www.ethnologue.com/ethnoblog/gary-simons/welcome-20th-edition)

- Glottolog's own assessment.

The actual source of each individual language's endangerment status is given in the
`[endangerment]` section of the info file.

Source data has been merged using the following mapping between the endangerment categories in the source databases,
resulting in what we call *the Agglomerated Endangerment Scale (AES)*:


UNESCO       | LES-ELCat  | EGIDS           | AES
---          | ---        | ---             | ---
safe         | at risk    | <ul><li>1 (National)</li><li>2 (Regional)</li><li>3 (Trade) </li><li>4 (Educational)</li><li>5 (Written) </li><li>6a (Vigorous)</li></ul>   | Not endangered
vulnerable   | vulnerable | 6b (Threatened) | 6b (Threatened)
definitely endangered | <ul><li>threatened</li><li>endangered</li></ul> | 7 (Shifting) | 7 (Shifting)
severely endangered | severely endangered | 8a (Moribund) | 8a (Moribund)
critically endangered | critically endangered | 8b (Nearly extinct) | 8b (Nearly extinct)
extinct |  <ul><li>dormant</li><li>awakening</li></ul>  | <ul><li>9 (Dormant)</li><li>9 (Reawakening)</li><li>9 (Second language only)</li><li>10 (Extinct)</li></ul> | 10 (Extinct)


## Language location

Glottolog provides coordinates for nearly all language-level
languoids. The coordinate often represents the geographical
centre-point of the area where the speakers live, but may also
indicate a historical location, the demographic centre-point or some
other representative point. Like (variant) names and country locations
(but unlike language division and classification), coordinates are
attributes close to observation and are therefore not given with a
specific source in Glottolog. However, it is expected that any source
attributed to the language in Glottolog would indicate a location
compatible with the coordinate given in Glottolog. The actual sources
for the coordinates in Glottolog are varied and include both
individual points submitted by various users and ourselves as well as
databases such as [WALS](http://wals.info), [ASJP](http://asjp.clld.org) and 
human reading of Ethnologue maps. As
such the coordinates in Glottolog are not a substitute for a full and
well-founded source in language locations (or variant names). For
that, one needs to look at the individual sources attributed to the
language in Glottolog.

