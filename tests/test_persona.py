"""Tests for persona generation, focused on the `unique` distinctness guard."""

from __future__ import annotations

import pytest

from golemorph.models import Gender
from golemorph.persona import generate_personas


def test_default_draws_may_repeat_but_are_reproducible():
    """Without `unique`, names are independent draws; a seed pins the output."""
    first = generate_personas("FRA", 10, seed=11)
    second = generate_personas("FRA", 10, seed=11)
    assert [p.full_name for p in first] == [p.full_name for p in second]


def test_unique_full_gives_no_repeated_whole_name():
    personas = generate_personas("FRA", 50, unique="full", seed=5)
    names = [p.full_name for p in personas]
    assert len(set(names)) == len(names) == 50


def test_unique_first_keeps_given_names_distinct():
    personas = generate_personas("USA", 40, unique="first", seed=3)
    firsts = [p.first_name for p in personas]
    assert len(set(firsts)) == len(firsts)  # every given name distinct


def test_unique_last_keeps_surnames_distinct():
    personas = generate_personas("USA", 40, unique="last", seed=4)
    lasts = [p.last_name for p in personas]
    assert len(set(lasts)) == len(lasts)  # every surname distinct


def test_unique_respects_forced_gender():
    personas = generate_personas("RUS", 6, gender=Gender.FEMALE, unique="full", seed=2)
    assert all(p.gender is Gender.FEMALE for p in personas)
    assert len({p.full_name for p in personas}) == 6


def test_unique_more_than_pool_raises_with_counts():
    with pytest.raises(ValueError, match="cannot draw .* distinct"):
        generate_personas("KOR", 100_000, unique="first", seed=1)


def test_unique_rejects_an_unknown_mode():
    with pytest.raises(ValueError, match="unique must be one of"):
        generate_personas("USA", 3, unique="middle", seed=1)


def test_unique_is_reproducible_under_a_seed():
    first = [p.full_name for p in generate_personas("DEU", 12, unique="full", seed=9)]
    second = [p.full_name for p in generate_personas("DEU", 12, unique="full", seed=9)]
    assert first == second
