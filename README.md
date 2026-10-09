<div align="center">

<img src="https://raw.githubusercontent.com/HiitCat/Golemorph/main/docs/assets/golemorph.png" alt="Golemorph logo" width="160">

# Golemorph

**Coherent synthetic personas for authorized red-team spearphishing engagements.**

Every identity is internally consistent - name, email, phone, age, city and
role all follow the chosen origin, across 45 locales.

[![PyPI](https://img.shields.io/pypi/v/golemorph.svg)](https://pypi.org/project/golemorph/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

<img src="https://raw.githubusercontent.com/HiitCat/Golemorph/main/docs/assets/demo.png" alt="Golemorph generating a batch of French personas" width="900">

</div>

## Features

- **Coherent identities** - name, email, phone, age, city and role all match
  the origin's language, dial code and conventions.
- **45 locales**, grouped by region, every name romanized to Latin (accents
  kept) so emails stay readable.
- **Credible by default** - frequency-weighted sampling bounded to a percentile
  band that skips both "John Doe" names and odd, unplaceable ones.
- **Realistic emails** - several local-part layouts (`first.last`, `jdupont`,
  `dupont.jean`, ...) over region-appropriate domains.
- **Ready-to-use exports** - a rich color table for the terminal, plus `csv`,
  `json`, and a GoPhish group-import CSV.
- **Reproducible** - `--seed` makes any campaign repeatable.

## Install

Requires Python 3.11+.

```bash
pipx install golemorph
```

### From source

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# optional: tests + data regeneration
pip install -r requirements-dev.txt
```

Or run it straight from the repo root without installing (needs its runtime
deps, PyYAML and rich - `pip install -r requirements.txt`):

```bash
python3 -m golemorph --help
```

## Quick start

```bash
# 45 supported origins, grouped by region (filter: europe|americas|africa|asia)
golemorph --list-origins
golemorph --list-origins europe

# Five Russian personas, full JSON records
golemorph -o RUS -n 5 --format json

# 100 French personas, gophish CSV format saved in custom file
golemorph -o FRA -n 100 -f gophish --output targets.csv

# 50 personas, no repeated name, reproducible
golemorph -o DEU -n 50 --unique --seed 7
```

With no arguments, Golemorph prints a single American persona (the default
origin is `USA`) as a table. The default `name` format renders a rich,
color table - name, age, birth year, city, language, role, phone, email and
the `commonality` score; use `-f csv`/`json` for machine-readable output.

## Options

| Flag | Meaning | Default |
|---|---|---|
| `-o, --origin CODE` | Origin code (see `--list-origins`) | `USA` |
| `-n, --count N` | Personas to generate | `1` |
| `-u, --unique [PART]` | No repeats across the run: `full` whole name (default), `first` given names, `last` surnames | off |
| `-g, --gender G` | `Male` or `Female`; unset draws per-name gender from the dataset | mixed |
| `-f, --format FMT` | `name` (rich table), `csv`, `json`, or `gophish` | `name` |
| `--unweighted` | Uniform sampling instead of frequency-weighted | weighted |
| `--min-common PCT` | Exclude names rarer than this percentile (`0` keeps all) | `10` |
| `--max-common PCT` | Exclude names more common than this percentile, avoiding the "John Doe" effect (`100` keeps all) | `95` |
| `--seed N` | Reproducible output | random |
| `--output FILE` | Write output to a file instead of stdout | stdout |
| `--list-origins [GROUP]` | Print the origins table and exit; optional `GROUP` filter (`all`, `europe`, `americas`, `africa`, `asia`) | - |

## Output formats

- **`name`** (default): a rich, color table of the headline fields - name,
  age, birth year, city, language, role, phone, email and `commonality`.
  Color and box drawing are dropped automatically when the output is piped or
  redirected.
- **`csv`**: one row per persona with the full record - `id`, `gender`,
  `first_name`, `last_name`, `origin_code`, `origin_label`, `nationality`,
  `language`, `name_order`, `birth_year`, `age`, `email`, `phone`, `city`,
  `role`, `first_name_percentile`, `last_name_percentile`, `commonality`,
  `full_name`.
- **`json`**: one JSON array of full records, same fields as the CSV.
- **`gophish`**: the GoPhish group-import template - `First Name, Last Name,
  Email, Position` rows (Position carries the persona's role), ready to import
  directly into a GoPhish target group.

## Origins

Golemorph ships 45 origins across Europe, the Americas, Africa, the Middle
East and Asia-Pacific:

| Group | Origins |
|---|---|
| Europe | 🇦🇹 `AUT`, 🇧🇪 `BEL`, 🇧🇬 `BGR`, 🇨🇿 `CZE`, 🇩🇪 `DEU`, 🇩🇰 `DNK`, 🇪🇸 `ESP`, 🇫🇮 `FIN`, 🇫🇷 `FRA`, 🇬🇧 `GBR`, 🇬🇷 `GRC`, 🇭🇷 `HRV`, 🇭🇺 `HUN`, 🇮🇪 `IRL`, 🇮🇹 `ITA`, 🇳🇱 `NLD`, 🇳🇴 `NOR`, 🇵🇱 `POL`, 🇵🇹 `PRT`, 🇷🇺 `RUS`, 🇨🇭 `SUI`, 🇸🇮 `SVN`, 🇸🇪 `SWE`, 🇹🇷 `TUR` |
| Americas | 🇦🇷 `ARG`, 🇧🇷 `BRA`, 🇨🇦 `CAN`, 🇨🇴 `COL`, 🇲🇽 `MEX`, 🇺🇸 `USA` |
| Africa / MENA | 🇩🇿 `ALG`, 🇪🇬 `EGY`, 🇲🇦 `MRN`, 🇳🇬 `NGA`, 🇸🇦 `SAU`, 🇹🇳 `TUN`, 🇿🇦 `ZAF` |
| Asia-Pacific | 🇨🇳 `CHN`, 🇮🇩 `IDN`, 🇮🇳 `IND`, 🇯🇵 `JPN`, 🇰🇷 `KOR`, 🇲🇾 `MYS`, 🇵🇭 `PHL`, 🇸🇬 `SGP` |

`--list-origins` prints them as color tables, one per region, and takes an
optional group filter:

<p align="center">
  <img src="https://raw.githubusercontent.com/HiitCat/Golemorph/main/docs/assets/origins_europe.png" alt="golemorph --list-origins europe" width="420">
</p>

Full table with language, name order, dial code and nationality wording:
[`docs/origins.md`](docs/origins.md).

## Data

Names are sampled (by default with replacement; see `--unique`) from per-origin
CSVs generated from
[names-dataset 3.3.1](https://github.com/typpo/names-dataset) (Facebook,
~533M users) by `scripts/generate_name_data.py`:

- **Frequency-weighted** sampling, with long-tail counts decayed along a
  Zipf-like curve so mid-tier names are drawn far more often than raw counts
  alone would suggest. `--unweighted` switches to uniform.
- **Credible band**: by default the draw is bounded to a percentile band
  (`--min-common` / `--max-common`) that drops both the most common names,
  which read as "John Doe" placeholders, and the rarest, least placeable ones.
- **Unique names**: `--unique` rejects and redraws duplicates so a chosen part
  of the name never repeats across the run - `full` (whole name, the default),
  `first` (given names) or `last` (surnames). `--unique full` still lets a
  first name or surname recur in a different pairing; `first`/`last` keep that
  one field strictly distinct. Errors if the pool is too small.
- **Gendered** first names; Russian surnames carry romanized gendered forms
  (`Ivanov`/`Ivanova`), and a female persona never draws the male form.
- **Latin-only** spellings: every locale keeps its romanized names (accents
  allowed, e.g. `José`, `Müller`), so native-script entries (Arabic, Cyrillic,
  Greek, CJK, Hangul) are dropped in favour of their Latin forms and emails
  stay name-based.
- Surnames drop standalone name *particles* (`El`, `Ben`, `Da`, `De`, `Von`,
  `Ait`, ...) that the source stores as entries in their own right because it
  splits compound names on the space; genuine short surnames that collide with
  those tokens (`Le`, `Do`, `Du`, `Ba`, `Das`, `Dal`) are kept.
- Emails mix several realistic local-part layouts (`first.last`, `firstlast`,
  `jdupont`, `j.dupont`, `jean.d`, `dupont.jean`, with an optional numeric
  suffix) over a regional domain; phone numbers follow the origin's dial code
  and mobile prefix.

Regenerate the shipped data. The source dataset ships inside the
[`names-dataset`](https://pypi.org/project/names-dataset/) package (a dev
dependency), so there is nothing to download by hand and it works on any OS:

```bash
pip install -r requirements-dev.txt   # installs names-dataset + PyYAML
python3 scripts/generate_name_data.py
```

## Tests

```bash
python3 -m pytest tests/
```
