"""Tests for dataset loading: normalization, percentile scoring, gender split.

The CSVs are test fixtures too, so most tests here assert properties that must
hold for *any* well-formed dataset (a female persona never draws `Ivanov`),
not one particular top-of-file row.
"""

from __future__ import annotations

import pytest

from golemorph.loader import (
    load_first_names,
    load_origin,
    load_surnames,
    origins,
)
from golemorph.models import Gender


def test_every_shipped_origin_loads_with_full_metadata():
    from golemorph.loader import load_manifest

    profiles = origins()
    assert {p.code for p in profiles} == set(load_manifest())
    assert len(profiles) == 45
    for profile in profiles:
        assert profile.label and profile.nationality and profile.language
        assert profile.dial_code.startswith("+")
        assert profile.mobile_prefixes and profile.email_domains
        assert profile.cities and profile.roles
        assert profile.name_order in ("given-first", "family-first")


def test_origin_codes_are_case_insensitive():
    assert load_origin("fra").label == load_origin("FRA").label


def test_unknown_origin_names_the_valid_codes():
    with pytest.raises(ValueError, match="unknown origin 'XYZ'"):
        load_origin("XYZ")


def test_malformed_row_names_file_and_line(monkeypatch):
    """Bad rows name the file and line instead of being silently skipped."""
    from golemorph import loader

    monkeypatch.setattr(loader, "_read_rows", lambda filename: [("Jean", 4)])
    loader._all_first_names.cache_clear()
    with pytest.raises(ValueError, match="FRA/FirstName\\.csv:4:"):
        loader._all_first_names("FRA")


def test_blank_lines_and_padding_are_stripped():
    """Surrounding padding is gone, but an inner space in a real spelling
    (`El mostafa`) is legitimate and must survive untouched."""
    entries = load_surnames("MRN")
    assert all(e.name == e.name.strip() for e in entries)
    assert all(e.frequency > 0 for e in entries)
    # Compacting only for the *key* is what catches a family written twice:
    # two spellings that collapse to the same token must be one merged entry.
    keys = ["".join(e.name.split()).lower() for e in entries]
    assert len(keys) == len(set(keys)), "a family loaded under two spellings"


def test_duplicate_spellings_sum_into_one_entry(monkeypatch):
    """`El idrissi` + `Elidrissi` is one family: frequencies sum, one row."""
    from golemorph import loader

    monkeypatch.setattr(
        loader,
        "_read_rows",
        lambda filename: [
            ("El Idrissi,100", 1),
            ("Elidrissi,50", 2),
            ("El mostafa,40", 3),
        ],
    )
    loader._all_surnames.cache_clear()
    by_name = {e.name: e.frequency for e in loader._all_surnames("MRN")}
    # The twin pair merges (case-insensitive, spaces folded); the winner is
    # the more frequent raw spelling.
    assert by_name.get("El Idrissi") == 150, "spelling twins not summed"
    assert "Elidrissi" not in by_name, "the twin spelling survived the merge"
    # A family with no twin keeps its own spelling and frequency.
    assert by_name.get("El mostafa") == 40



def test_percentiles_are_a_valid_ranking():
    entries = load_first_names("FRA")
    assert all(0.0 <= e.percentile <= 100.0 for e in entries)
    # A strictly more common name never scores lower than a rarer one.
    by_freq = sorted(entries, key=lambda e: e.frequency)
    assert all(
        by_freq[i].percentile <= by_freq[i + 1].percentile + 1e-9
        for i in range(len(by_freq) - 1)
    )


def test_gendered_surnames_are_filtered_by_persona_gender():
    """A female persona must never be handed the male form `Ivanov`."""
    female = load_surnames("RUS", Gender.FEMALE)
    male = load_surnames("RUS", Gender.MALE)
    assert all(e.gender in (None, Gender.FEMALE) for e in female)
    assert all(e.gender in (None, Gender.MALE) for e in male)
    assert {e.name for e in female} & {e.name for e in male} == set()


def test_given_names_are_gendered():
    for profile in origins():
        for gender in Gender:
            names = load_first_names(profile.code, gender)
            assert names, f"{profile.code} has no {gender.value} names"
            assert all(e.gender in (None, gender) for e in names)


# --- generator filters baked into the datasets --------------------------------


def test_korean_given_names_are_ascii_only():
    """The generator restricts KR given names to ASCII (Hangul folds badly)."""
    for gender in Gender:
        for entry in load_first_names("KOR", gender):
            assert entry.name.isascii(), entry.name


def test_mena_given_names_have_no_abu_title():
    """The generator drops the "Abu ..." family-name prefix from MENA names."""
    for code in ("ALG", "MRN", "TUN", "EGY", "SAU"):
        for gender in Gender:
            for entry in load_first_names(code, gender):
                assert not entry.name.lower().startswith("abu "), entry.name
