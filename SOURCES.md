
# Sources of Glottolog data 

Glottolog is "standing on the shoulders of giants", not so much to see further, but rather to
see *more*, namely **all** languages. Most of the information in Glottolog is aggregated from other
sources, and integrated by linking this information to *Glottocodes* - Glottolog's languoid identifiers.

The description of data sources listed below is not only intended to make this transparent, but also 
to detail the aggregation workflow, including information about whether the process is automated or
involves manual curation.


## Language inventory

Glottolog's inventory of languages is based on Harald Hammarström's enumeration of all handbooks/overviews 
(Hammarström and Nordhoff 2011) and consolidated review of them (including Ethnologue, see Hammarström 2015).


## Links

Glottolog links its inventory of [languoids](languoids/) to several other resources on the web which provide language/linguistic
information, e.g. [ISO 639-3](https://iso639-3.sil.org/) or [Wikipedia](https://www.wikipedia.org/).
These links can be categorized in terms of the curation workflow as follows:
- **individually curated**: Each individual link is added/updated/deleted "by hand" by one of the Glottolog editors.
  This is the case for the links to ISO 639-3, e.g. for [Wolaytta](https://github.com/glottolog/glottolog/blob/a90a846d2b5d1831aa57c6321ba11c15c0cf9a8a/languoids/tree/gong1255/omet1238/nort3161/cent2046/wola1242/md.ini#L6)
- **harvested**: Links are curated elsewhere and harvested automatically (typically for each Glottolog release).
- **derived**: A third category of links displayed on https://glottolog.org are links that are derived from languoid identifiers,
  e.g. links to [OLAC](http://www.language-archives.org/language/hac) based on the ISO 639-3 code associated with a languoid.

The workflow associated with a type of links may change overtime. E.g. links to [AIATSIS](https://collection.aiatsis.gov.au/austlang/language/g28)
have been harvested from information provided by Claire Bowern's Chirila database. But after the initial import
they are now curated individually.


### Wikipedia (and Wikidata) links

We harvest Wikipedia links (i.e. Wikipedia pages corresponding to Glottolog languoids) from Wikidata 
(running the SPARQL query below). So Wikipedia links are basically curated on the Wikipedia side, and 
once they make it into Wikidata, they will show up in the next Glottolog release.

Thus, the links to Wikipedia shown at https://glottolog.org are not under "Glottolog's control" in the
sense that Glottolog can change them.

```sparql
prefix schema: <http://schema.org/>
SELECT ?item ?glottocode ?wikipedia WHERE {
    ?item wdt:P1394 ?glottocode.
    OPTIONAL {
        ?wikipedia schema:about ?item .
        ?wikipedia schema:inLanguage "en" .
        FILTER (SUBSTR(str(?wikipedia), 1, 25) = "https://en.wikipedia.org/")
    }
```

This mechanism is not perfect. E.g. at the time of writing, [Mitchigamea](https://en.wikipedia.org/wiki/Mitchigamea_language)
lists `mich1247` as related Glottocode in its infobox, but this isn't available 
[via Wikidata](https://www.wikidata.org/wiki/Q12636809) (yet).


## Language endangerment data

Glottolog contains data about language endangerment drawn (and merged) from various sources listed in [`config/aes_sources.ini`](config/aes_sources.ini).

Almost all information in the Catalogue of Endangered Languages (one of our sources)
includes a citation of the original source which provided this data (e.g.
journal article, book, personal communication, etc.). You can find citation
information at the top of the "Language Information by Source" box on each
language page; if you wish to reproduce data such as speaker numbers, you may
cite the original source provided there.

<a id="aes-mapping"> </a>

Source data has been merged using the following mapping between the endangerment categories in the source databases,
resulting in what we call [*the Agglomerated Endangerment Scale (AES)*](config/aes_status.ini):


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
databases such as [WALS](https://wals.info), [ASJP](https://asjp.clld.org) and 
human reading of Ethnologue maps. As
such the coordinates in Glottolog are not a substitute for a full and
well-founded source in language locations (or variant names). For
that, one needs to look at the individual sources attributed to the
language in Glottolog.


## References

Glottolog aggregates bibliographical references from a number of so-called *providers*, i.e. individuals
or organizations sharing reference data with us in a form that is easy to integrate in Glottolog. As with
links, the reference collection contributed by a particular provider may be **harvested** (i.e. 
curated by the provider and merged into Glottolog periodically) or
**individually curated** (i.e. provided at one point, with updates - typically corrections of errors - being
done individually by Glottolog).

Information about the provider and the update workflow is given at [BIBFILES.ini](references/BIBFILES.ini).
