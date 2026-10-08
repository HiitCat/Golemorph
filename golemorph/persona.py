"""Persona generation: turn datasets plus origin metadata into full identities.

A spearphishing target needs more than a name, so everything downstream of the
name pair - email, phone, age, city, role - is generated here, coherently with
the origin and the gender of the sampled names.
"""

from __future__ import annotations

import random
import re
import unicodedata
from datetime import date

from .loader import load_first_names, load_origin, load_surnames
from .models import Gender, NameEntry, OriginProfile, Persona
from .sampler import NameSampler

_DEFAULT_MIN_AGE = 18
_DEFAULT_MAX_AGE = 64
_EMAIL_SEPARATORS = ("", ".", "_")
_EMAIL_NUMBER_SUFFIXES = ("", "", "", "{yy}", "{dd}", "{yy}{dd}")
# A --unique group is redrawn only to resolve a cross-gender full-name
# collision, which is rare, so a few attempts suffice; the cap bounds the loop.
_MAX_UNIQUE_ATTEMPTS = 100


def _ascii_slug(text: str) -> str:
    """ASCII-fold a name for an email local part (`Amélie` -> `amelie`)."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]+", "", folded.lower())


def _format_phone(rng: random.Random, profile: OriginProfile) -> str:
    """Fill the manifest phone template: `{d}` dial code, `{p}` mobile
    prefix, `{g1}`...`{gN}` groups of the random subscriber number.

    French format `{d} {p} {g1} {g2} {g3} {g4}` thus yields e.g.
    `+33 6 12 34 56 78`; Chinese `{d}{p}{g1}{g2}{g3}` yields
    `+8613812345678` - both from data, not code.
    """
    group_count = profile.phone_format.count("{g")
    size, extra = divmod(profile.subscriber_digits, group_count)
    groups, rest = [], profile.subscriber_digits
    for index in range(group_count):
        width = size + (1 if index < extra else 0)
        groups.append("".join(rng.choices("0123456789", k=width)))
        rest -= width
    assert rest == 0, "subscriber_digits must split into phone_format groups"
    fields = {f"g{index + 1}": group for index, group in enumerate(groups)}
    return profile.phone_format.format(
        d=profile.dial_code, p=rng.choice(profile.mobile_prefixes), **fields
    )


def _email_local(rng: random.Random, given: NameEntry, family: NameEntry,
                 birth_year: int) -> str:
    """A plausible local part: name slug, sometimes with a numeric suffix.

    The suffix mirrors real address-book habits (birth-year or random digits),
    and mixing it keeps a batch of personas from colliding on one domain.
    All-CJK names ASCII-fold to nothing, so fall back to `user` plus digits
    rather than shipping an empty local part.
    """
    slug = rng.choice(_EMAIL_SEPARATORS).join(
        part for part in (_ascii_slug(given.name), _ascii_slug(family.name)) if part
    )
    if not slug:
        slug = f"user{rng.randint(10, 99)}"

    suffix = rng.choice(_EMAIL_NUMBER_SUFFIXES)
    if not suffix:
        return slug
    return slug + suffix.format(yy=str(birth_year)[-2:], dd=f"{rng.randint(0, 99):02d}")


# --unique modes: which part of the name must not repeat across the run.
UNIQUE_MODES = ("first", "last", "full")
# Deterministic gender order for the unique draw, so a seed is reproducible.
_GENDER_ORDER = (Gender.FEMALE, Gender.MALE)


def _draw_unique(
    rng: random.Random,
    profile: OriginProfile,
    genders: list[Gender],
    weighted: bool,
    mode: str,
) -> list[tuple[NameEntry, NameEntry]]:
    """Draw one `(given, family)` pair per persona so that `mode` never repeats
    across the whole run (not merely within a gender)."""
    if mode == "full":
        return _draw_unique_full(rng, profile, genders, weighted)
    return _draw_unique_part(rng, profile, genders, weighted, mode)


def _draw_unique_part(
    rng: random.Random,
    profile: OriginProfile,
    genders: list[Gender],
    weighted: bool,
    mode: str,
) -> list[tuple[NameEntry, NameEntry]]:
    """`first`/`last`: the constrained part is drawn distinct *globally*.

    Genders are handled in a fixed order, each excluding the values already
    taken, so gendered pools that overlap on neutral names (e.g. surnames
    shared by both genders) never hand out the same value twice. The
    unconstrained part is drawn independently and may repeat.
    """
    pairs: list[tuple[NameEntry, NameEntry] | None] = [None] * len(genders)
    taken: set[str] = set()
    kind = "given names" if mode == "first" else "surnames"
    for persona_gender in _GENDER_ORDER:
        positions = [i for i, g in enumerate(genders) if g == persona_gender]
        if not positions:
            continue
        needed = len(positions)
        constrained_all = (
            load_first_names(profile.code, persona_gender)
            if mode == "first"
            else load_surnames(profile.code, persona_gender)
        )
        available = tuple(e for e in constrained_all if e.name not in taken)
        if needed > len(available):
            raise ValueError(
                f"cannot draw {needed} distinct {persona_gender.value} {kind} "
                f"for origin {profile.code}: only {len(available)} available"
            )
        drawn = NameSampler(available, weighted=weighted).sample_many(rng, needed)
        taken.update(entry.name for entry in drawn)
        other_pool = NameSampler(
            load_surnames(profile.code, persona_gender)
            if mode == "first"
            else load_first_names(profile.code, persona_gender),
            weighted=weighted,
        )
        for position, entry in zip(positions, drawn):
            other = other_pool.sample(rng)
            pairs[position] = (
                (entry, other) if mode == "first" else (other, entry)
            )
    return [pair for pair in pairs if pair is not None]


def _draw_unique_full(
    rng: random.Random,
    profile: OriginProfile,
    genders: list[Gender],
    weighted: bool,
) -> list[tuple[NameEntry, NameEntry]]:
    """`full`: given and surname drawn independently (either may recur); each
    persona is redrawn until its *whole* name has not been used yet. The
    combination space is large, so this almost never retries - but it raises
    rather than hang if the pool cannot supply another distinct full name."""
    samplers: dict[Gender, tuple[NameSampler, NameSampler]] = {}

    def pools(persona_gender: Gender) -> tuple[NameSampler, NameSampler]:
        if persona_gender not in samplers:
            samplers[persona_gender] = (
                NameSampler(
                    load_first_names(profile.code, persona_gender), weighted=weighted
                ),
                NameSampler(
                    load_surnames(profile.code, persona_gender), weighted=weighted
                ),
            )
        return samplers[persona_gender]

    seen: set[str] = set()
    pairs: list[tuple[NameEntry, NameEntry]] = []
    for persona_gender in genders:
        given_pool, surname_pool = pools(persona_gender)
        for _ in range(_MAX_UNIQUE_ATTEMPTS):
            given = given_pool.sample(rng)
            family = surname_pool.sample(rng)
            key = profile.full_name(given.name, family.name)
            if key not in seen:
                break
        else:
            raise ValueError(
                f"cannot draw {len(genders)} personas with distinct full names "
                f"for origin {profile.code}: ran out of unused combinations"
            )
        seen.add(key)
        pairs.append((given, family))
    return pairs


def _build_persona(
    rng: random.Random,
    profile: OriginProfile,
    index: int,
    persona_gender: Gender,
    given: NameEntry,
    family: NameEntry,
    email_domains: tuple[str, ...],
    year: int,
    min_age: int,
    max_age: int,
) -> Persona:
    """Assemble one full identity around a drawn `(given, family)` pair."""
    age = rng.randint(min_age, max_age)
    return Persona(
        id=f"{profile.code.lower()}-{index + 1:04d}",
        gender=persona_gender,
        first_name=given.name,
        last_name=family.name,
        origin_code=profile.code,
        origin_label=profile.label,
        nationality=profile.nationality,
        language=profile.language,
        name_order=profile.name_order,
        birth_year=year - age,
        age=age,
        email=f"{_email_local(rng, given, family, year - age)}@"
        f"{rng.choice(email_domains)}",
        phone=_format_phone(rng, profile),
        city=rng.choice(profile.cities),
        role=rng.choice(profile.roles),
        first_name_percentile=given.percentile,
        last_name_percentile=family.percentile,
        # Mean of two percentile ranks: comparable across datasets.
        commonality=round((given.percentile + family.percentile) / 2, 1),
        first_name_source=profile.first_names_source,
        last_name_source=profile.surnames_source,
    )


def generate_personas(
    origin_code: str,
    count: int = 1,
    gender: Gender | None = None,
    *,
    seed: int | None = None,
    weighted: bool = True,
    unique: str | None = None,
    domains: tuple[str, ...] | None = None,
    min_age: int = _DEFAULT_MIN_AGE,
    max_age: int = _DEFAULT_MAX_AGE,
) -> list[Persona]:
    """Build `count` coherent personas for one origin.

    `gender=None` draws each persona's gender independently instead of
    mixing both name pools into one bag; `weighted=False` switches to
    uniform sampling for comparisons; `seed` makes a campaign fully
    reproducible.

    `unique` rejects and redraws duplicates so a chosen part of the name never
    repeats across the run: `"first"` keeps given names distinct, `"last"`
    keeps surnames distinct, `"full"` keeps the whole name distinct (so a first
    name or a surname may still recur in a different pairing). `unique=None`
    (the default) draws each name independently, where names may repeat.
    Asking for more unique values than the origin's pool can supply raises
    `ValueError`.
    """
    if unique is not None and unique not in UNIQUE_MODES:
        raise ValueError(
            f"unique must be one of {UNIQUE_MODES} or None, got {unique!r}"
        )
    profile = load_origin(origin_code)
    email_domains = tuple(domains) if domains else profile.email_domains
    rng = random.Random(seed)
    year = date.today().year

    def _one(index: int, persona_gender: Gender, given: NameEntry,
             family: NameEntry) -> Persona:
        return _build_persona(
            rng, profile, index, persona_gender, given, family,
            email_domains, year, min_age, max_age,
        )

    personas: list[Persona] = []
    if unique is None:
        for index in range(count):
            persona_gender = gender or rng.choice((Gender.MALE, Gender.FEMALE))
            given = NameSampler(
                load_first_names(profile.code, persona_gender), weighted=weighted
            ).sample(rng)
            family = NameSampler(
                load_surnames(profile.code, persona_gender), weighted=weighted
            ).sample(rng)
            personas.append(_one(index, persona_gender, given, family))
        return personas

    # One distinct draw for the whole run: the chosen name part never repeats.
    genders = [
        gender or rng.choice((Gender.MALE, Gender.FEMALE)) for _ in range(count)
    ]
    pairs = _draw_unique(rng, profile, genders, weighted, unique)
    for index, (persona_gender, (given, family)) in enumerate(zip(genders, pairs)):
        personas.append(_one(index, persona_gender, given, family))
    return personas
