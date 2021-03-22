# Glottolog metadata

## Languoid levels

Glottolog data is organized as a tree, mostly conveying a genealogical
classification of its nodes - called *languoids*.

Glottolog distinguishes three kinds (or *levels*) of languoids,
- **families**: non-leave nodes from the root up to **language** level.
- **languages**: either leaf nodes or nodes separating a **family** and one or more **dialect**
  nodes.
- **dialects**: nodes between **language** level up-to leafs.

Each path from the root to a leaf must contain exactly one **language**-level
languoid.

These levels are defined in [languoid_levels.ini](languoid_levels.ini).


## Language types or categories

While Glottolog aims to be a complete catalog of **spoken L1 languages**, it
also contains information about other kinds of languages. To make this information
uniformly accessible, we organize it like the data about "regular" languages
in (non-genealogical) trees called **pseudo families**.

These **pseudo families** (or non-genealogical trees) are described on the
[Glottolog website](https://glottolog.org/glottolog/glottologinformation) and
defined in [language_types.ini](language_types.ini) (marked with a non-empty `pseudo_family_id`).


## Macroareas

A *macroarea* is an area of the globe of roughly continent size.

The division of the inhabited landmass into the macroareas defined here is optimal in the following sense. It is the division
- into 6 areas,
- for which there are at least 250 languages in each area, such that
- the distance between the component parts inside each area is minimized, and
- the length of intersections between pairs of macro-areas is minimized.

See [Harald Hammarström and Mark Donohue 2014](https://glottolog.org/resource/reference/id/hh:hv:HammarstromDonohue:Macro-Areas).

The Glottolog macroareas are defined in [macroareas.ini](macroareas.ini).
Polygons with the macroarea boundaries serialized as GeoJSON are available
from [macroareas/voronoi](macroareas/voronoi).


## Document types

Glottolog's references can be described by assigning **document types**. The
list of document types is defined in [document_types.ini](document_types.ini).


### MED types

MED (**M**ost **E**xtensive **D**escription) types partition the list of document
types into a set of classes suitable to assess the [descriptive status](https://glottolog.org/meta/glossary#sec-descriptivestatusofalanguage) 
of a language.

MED types are defined in [med_types.ini](med_types.ini)


## AES status

The **A**gglomerated **E**ndangerment **S**tatus measures how endangered a 
language is according to one of the sources defined in [aes_sources.ini](aes_sources.ini).
The list of states is defined in [aes_status.ini](aes_status.ini).
