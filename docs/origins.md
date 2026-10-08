# Golemorph origins

The 45 origins shipped with Golemorph, grouped by region. Codes are case
insensitive on the command line; run `golemorph --list-origins` for the live
list with language, name order and dial code.

## Europe

| Code | Label | Language | Dial |
|---|---|---|---|
| `AUT` | Austrian | de | +43 |
| `BEL` | Belgian | nl-fr | +32 |
| `BGR` | Bulgarian | bg | +359 |
| `CZE` | Czech | cs | +420 |
| `DEU` | German | de | +49 |
| `DNK` | Danish | da | +45 |
| `ESP` | Spanish | es | +34 |
| `FIN` | Finnish | fi | +358 |
| `FRA` | French | fr | +33 |
| `GBR` | English | en | +44 |
| `GRC` | Greek | el | +30 |
| `HRV` | Croatian | hr | +385 |
| `HUN` | Hungarian | hu | +36 |
| `IRL` | Irish | en | +353 |
| `ITA` | Italian | it | +39 |
| `NLD` | Dutch | nl | +31 |
| `NOR` | Norwegian | no | +47 |
| `POL` | Polish | pl | +48 |
| `PRT` | Portuguese | pt | +351 |
| `RUS` | Russian | ru | +7 |
| `SUI` | Swiss | de-fr-it | +41 |
| `SVN` | Slovenian | sl | +386 |
| `SWE` | Swedish | sv | +46 |
| `TUR` | Turkish | tr | +90 |

## Americas

| Code | Label | Language | Dial |
|---|---|---|---|
| `ARG` | Argentine | es | +54 |
| `BRA` | Brazilian | pt | +55 |
| `CAN` | Canadian | en | +1 |
| `COL` | Colombian | es | +57 |
| `MEX` | Mexican | es | +52 |
| `USA` | American | en | +1 |

## Africa and MENA

| Code | Label | Language | Dial |
|---|---|---|---|
| `ALG` | Algerian | ar | +213 |
| `EGY` | Egyptian | ar | +20 |
| `MRN` | Moroccan | ar | +212 |
| `NGA` | Nigerian | en | +234 |
| `SAU` | Saudi | ar | +966 |
| `TUN` | Tunisian | ar | +216 |
| `ZAF` | South African | en | +27 |

## Asia-Pacific

| Code | Label | Language | Dial |
|---|---|---|---|
| `CHN` | Chinese | zh | +86 |
| `IDN` | Indonesian | id | +62 |
| `IND` | Indian | hi | +91 |
| `JPN` | Japanese | ja | +81 |
| `KOR` | Korean | ko | +82 |
| `MYS` | Malaysian | ms | +60 |
| `PHL` | Filipino | tl | +63 |
| `SGP` | Singaporean | en | +65 |

## Data quirks worth knowing

- **`RUS`** is the only origin with gendered surnames (`Иванов` vs
  `Иванова`). The feminine form is detected by the feminine suffix in both
  ASCII (`a`) and Cyrillic (`а`) - a female persona never draws the male form.
- **`KOR`** given names are ASCII-only; the generator drops Hangul given
  names because they fold to an empty email slug.
- **`CHN`/`JPN`/`KOR`** use `family-first` order (surname first, e.g.
  `Zhao Lei`). Names with no ASCII slug (all-CJK, and Cyrillic-only) fall
  back to a `user<digits>` email local part; transliterated spellings
  (pinyin, romanization) keep a name-based address.
- **`ALG`/`EGY`/`MRN`/`SAU`/`TUN`** given names have the `"Abu ..."`
  family-name prefix dropped.
- Long-tail name counts are decayed along a Zipf-like curve when the dataset
  is generated (`scripts/generate_name_data.py`), so mid-tier names are drawn
  far more often than raw Facebook counts alone would suggest.
