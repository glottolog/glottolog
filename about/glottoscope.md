# About GlottoScope

[GlottoScope](https://glottolog.org/langdoc/status) provides a visualisation of the combination of 
*Agglomerated Endangerment Scale (AES)* and *Most Extensive Description* of the languages of the world 
(but since descriptive status can only be reliably computed from Glottolog data for spoken L1 languages 
and sign languages, we only include these).

GlottoScope was designed and developed by Robert Forkel and Harald Hammarström in 2014. Comments and 
beta-testing were provided by a number of individuals including Hedvig Skirgård, Martin Haspelmath, 
Matti Miestamo, Mark Dingemanse, Lyle Campbell, Tapani Salminen and audiences at several demo sessions.

For more information see

> Harald Hammarström and Thom Castermans and Robert Forkel and Kevin Verbeek and Michel A. Westenberg and Bettina Speckmann. 2018. *Simultaneous Visualization of Language Endangerment and Language Description*. http://hdl.handle.net/10125/24792

## Agglomerated Endangerment Status

The Agglomerated Endangerment Status measures how endangered a language is. Originally, most of the endangerment 
assessments were aggregated from
- [The Catalogue of Endangered Languages (ELCat)](https://endangeredlanguages.com)
- [UNESCO Atlas of the World's Languages in Danger](https://unesdoc.unesco.org/ark:/48223/pf0000187026)
- [Ethnologue](https://www.ethnologue.com) 

Over time, assessments from other sources were included as well. For a full list of sources, see
[AES sources](../config/aes_sources.ini).

Since we aggregate endangerment assessments from different sources, the coding schemes used by the sources
must be harmonized. The mapping between source schemes and AES is described in [AES status](../config/aes_status.ini).


## Descriptive Status

The descriptive status of a language measures how extensive a grammatical description there exists for a language.
For the purpose of the descriptive status Glottolog's regular [document types](glossary.md#documenttype) 
are mapped to a more coarse grained [Most Extensive Description (MED)](glossary.md#med) type as follows:

MED type         | Document type
---              | ---
long grammar     | Grammar with more than 300 pages
grammar          | Grammar with less than 300 pages
grammar sketch   | Grammar sketch
phonology/text   | New Testament, Text, Phonology, (typological) Study Of A Specific Feature or Dictionary
Wordlist or less | Wordlist or less
