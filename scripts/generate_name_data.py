#!/usr/bin/env python3
"""Regenerate the vendored name CSVs from the `names-dataset` package.

The data (Facebook, ~533M users) ships inside the `names-dataset` PyPI
package - a dev dependency, see `requirements-dev.txt` - so no manual download
or OS-specific cache path is needed; `pip install names-dataset` is enough on
any platform. `NameDataset()` exposes the two raw dicts keyed by name:

* given names: `{name: {"country": {ISO2: pct}, "gender": {"F": p, "M": p},
  "rank": {ISO2: rank}}}`
* surnames: same shape minus a meaningful `gender` map.

For every origin in `golemorph/data/manifest.yaml` this script writes the
two vendored CSVs the loader expects:

* `<CODE>/FirstName.csv` -> `name,gender,frequency`
* `<CODE>/Surname.csv`   -> `name,frequency`

Rows are the locale's top :data:`TOP_N` by per-country rank, and `frequency`
is derived from that rank via Zipf decay (rank 1 = :data:`RANK_BASE`): the
pickles only store *relative* per-country ranks and the per-country
*distribution* of each name's users (the `country` shares sum to 1.0), not
absolute per-country counts, so the rank is the only frequency signal left.
Relative weights inside a dataset - all the sampler needs - are preserved.

Locale filters (all applied inline, *before* the top-N slice):

* All locales - both kinds: keep only Latin-script spellings (accents allowed,
  e.g. `José`), so native-script entries (Arabic, Cyrillic, Greek, CJK, Hangul)
  are dropped in favour of their romanized forms and emails stay name-based.
* CN/JP/KR - given names: drop names also in the US Top 1000 (the Facebook
  population in those countries skews to overseas users, so the US list is the
  cheapest diaspora proxy); JP additionally drops the BR Top 1000 (a
  large Japanese-Brazilian community pollutes the MA share).
* CN/JP/KR - surnames: drop "same-country" entries - surnames whose Facebook
  distribution is confined to that one country. In practice these are
  native-script given names leaked into the surname field (Korean 성식/지원),
  not real family names (the romanized top lists for CN/JP are unaffected).
* KR - given names: keep ASCII-only (romanized) spellings, so Hangul-native
  names do not displace the romanized ones used on English-language mail.
* MENA (ALG/MRN/TUN/EGY/SAU) - strip leading `Abu ` / `ابو ` patronymic
  prefixes, which are honorifics rather than given names.
* All locales - surnames: drop standalone name *particles* (El, Da, De, Von,
  ...; see :data:`SURNAME_PARTICLE_STOPLIST`), which are compound-name
  fragments split by the source, not family names.

Usage:
    pip install -r requirements-dev.txt   # provides names-dataset + PyYAML
    python scripts/generate_name_data.py
"""

from __future__ import annotations

import csv
import sys
import unicodedata
from pathlib import Path

import yaml

TOP_N = 500
RANK_BASE = 1_000_000
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "golemorph" / "data"

# Given-name Top-1000 exclusion lists, per locale ISO2 (see module docstring).
GIVEN_EXCLUSIONS: dict[str, list[str]] = {
    "CN": ["US"],
    "JP": ["US", "BR"],
    "KR": ["US"],
}
# Surname locales where same-country-only entries are dropped.
SURNAME_SAME_COUNTRY_DROP = {"CN", "JP", "KR"}
# Given names restricted to ASCII spellings.
ASCII_ONLY_GIVEN = {"KR"}
# Locales where leading Abu/ابو patronymics are stripped from both name kinds.
MENA_ABU_STRIP = {"DZ", "MA", "TN", "EG", "SA"}
ABU_PREFIXES = ("Abu ", "ابو ")

# Name *particles* that `names-dataset` stores as standalone surname entries
# because Facebook splits compound names ("El Amrani", "Da Silva", "Von Trapp")
# on the space. On their own they are not family names, yet their aggregated
# rank can place them absurdly high in a locale's list, so they are dropped
# from SURNAMES only (several double as real given names, e.g. "Ben").
# Deliberately excluded: Le, La, Lo, Do, Ba, Du, Das, Dal - genuine standalone
# surnames (Vietnamese Lê/Đỗ, Chinese Lo/Du 杜, Fula Ba, Indian/Bengali Das,
# Turkish Dal), kept to avoid false negatives despite colliding with particles.
SURNAME_PARTICLE_STOPLIST = {
    "el", "al", "ben", "bin", "ibn", "abu", "abou", "ait", "ould", "oulad",
    "bou", "abd", "sidi", "si", "da", "de", "di", "del", "della",
    "dei", "des", "dos", "van", "von", "der", "den", "ter", "zu",
}


def load_datasets() -> tuple[dict, dict]:
    """The given-name and surname dicts, straight from the `names-dataset`
    package (bundled data, so this works on any OS with no manual download)."""
    try:
        from names_dataset import NameDataset
    except ImportError:
        sys.exit(
            "names-dataset is not installed. Install the dev dependencies:\n"
            "    pip install -r requirements-dev.txt"
        )
    nd = NameDataset()
    return nd.first_names, nd.last_names


def top_by_rank(names: dict, iso2: str) -> list[tuple[str, dict]]:
    """Entries ranked for `iso2`, ascending rank, name as tie-breaker."""
    ranked = [
        (name, entry)
        for name, entry in names.items()
        if iso2 in entry.get("rank", {})
    ]
    ranked.sort(key=lambda pair: (pair[1]["rank"][iso2], pair[0]))
    return ranked


def top_names(names: dict, iso2: str, limit: int = 1000) -> set[str]:
    """The `limit` most frequent names overall in `iso2`."""
    return {name for name, _ in top_by_rank(names, iso2)[:limit]}


def frequency(entry: dict, iso2: str) -> int:
    """Zipf-decayed weight from the per-country rank (rank 1 = RANK_BASE)."""
    return max(1, round(RANK_BASE / entry["rank"][iso2]))


def given_gender(entry: dict) -> str:
    """`Male`/`Female` from the gender split; neutral below 50%."""
    split = entry.get("gender", {})
    if not split:
        return ""
    if split.get("F", 0) >= split.get("M", 0):
        return "Female" if split["F"] >= 0.5 else ""
    return "Male" if split["M"] >= 0.5 else ""


def is_latin(name: str) -> bool:
    """True if every letter in `name` is Latin script (accents allowed, e.g.
    `José`, `Francçois`, `Müller`). Non-Latin scripts - Arabic, Cyrillic,
    Greek, CJK, Hangul, ... - are rejected so each locale keeps only its
    romanized/Latin spellings. A name with no letters (digits/punctuation
    only) is rejected too."""
    letters = [c for c in name if c.isalpha()]
    if not letters:
        return False
    for c in letters:
        try:
            if not unicodedata.name(c).startswith("LATIN"):
                return False
        except ValueError:  # unnamed char: treat as non-Latin
            return False
    return True


def strip_abu(name: str) -> str:
    for prefix in ABU_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):].strip()
    return name


def dedupe(rows: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Drop exact-duplicate names (keep the first = highest-ranked row)."""
    seen: set[str] = set()
    out = []
    for row in rows:
        if row[0] not in seen:
            seen.add(row[0])
            out.append(row)
    return out


def select_rows(
    names: dict, iso2: str, kind: str, excluded: set[str]
) -> list[tuple[str, int]]:
    """Top-N rows for `iso2`; all locale filters run before the slice."""
    rows: list[tuple[str, int]] = []
    for name, entry in top_by_rank(names, iso2):
        name = name.strip()
        if iso2 in MENA_ABU_STRIP:
            name = strip_abu(name)
        if not name or name in excluded:
            continue
        if not is_latin(name):  # keep only romanized/Latin spellings
            continue
        if kind == "surname" and name.lower() in SURNAME_PARTICLE_STOPLIST:
            continue
        if kind == "given" and iso2 in ASCII_ONLY_GIVEN and not name.isascii():
            continue
        if (
            kind == "surname"
            and iso2 in SURNAME_SAME_COUNTRY_DROP
            and list(entry.get("country", {})) == [iso2]
        ):
            continue
        rows.append((name, frequency(entry, iso2)))
        if len(rows) >= TOP_N:
            break
    return dedupe(rows)


def generate_first_names(first_names: dict, iso2: str, output: Path) -> int:
    excluded = set()
    for source in GIVEN_EXCLUSIONS.get(iso2, []):
        excluded |= top_names(first_names, source)
    rows = select_rows(first_names, iso2, "given", excluded)
    rows.sort(key=lambda row: (-row[1], row[0]))
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "gender", "frequency"])
        for name, freq in rows:
            gender = ""
            for candidate in (name, name.title()):
                if candidate in first_names:
                    gender = given_gender(first_names[candidate])
                    break
            writer.writerow([name, gender, freq])
    return len(rows)


def generate_surnames(last_names: dict, iso2: str, output: Path) -> int:
    rows = select_rows(last_names, iso2, "surname", set())
    rows.sort(key=lambda row: (-row[1], row[0]))
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "frequency"])
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    with (DATA / "manifest.yaml").open(encoding="utf-8") as handle:
        origins = yaml.safe_load(handle)["origins"]
    first_names, last_names = load_datasets()
    for code, entry in origins.items():
        iso2 = entry["iso2"]
        first_file = entry["datasets"]["first_names"]["file"]
        last_file = entry["datasets"]["surnames"]["file"]
        (DATA / first_file).parent.mkdir(parents=True, exist_ok=True)
        (DATA / last_file).parent.mkdir(parents=True, exist_ok=True)
        n_first = generate_first_names(first_names, iso2, DATA / first_file)
        n_last = generate_surnames(last_names, iso2, DATA / last_file)
        print(f"{code} ({iso2}): {n_first} first names, {n_last} surnames")
    print("done")


if __name__ == "__main__":
    main()
