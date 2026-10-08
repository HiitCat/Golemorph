"""Typed data models shared across the Golemorph package.

Everything the generator needs about a locale (phone format, name order, email
domains, cities, roles) is *data*, declared in `data/manifest.yaml` and read
through :mod:`golemorph.loader` - adding a locale never means touching code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class Gender(str, Enum):
    """Gender of a name entry or of a generated persona.

    Values match the strings used in the shipped CSV datasets, so parsing is a
    plain `Gender(value)` call: a bad value then fails loudly at load time
    instead of silently corrupting a campaign.
    """

    MALE = "Male"
    FEMALE = "Female"


@dataclass(frozen=True)
class NameEntry:
    """One row of a name dataset (given names: `name,gender,frequency`;
    surnames: `name,frequency`).

    `gender` is `None` for gender-neutral entries (surnames in most
    locales) and set for gendered ones: given names, and gendered surname
    variants such as Russian `Ivanov`/`Ivanova`. Both sides of the name
    are tagged so the sampler can filter them consistently with the persona.

    `percentile` is a defensible commonality score: the entry's percentile
    rank (0-100, higher = more common) within its own dataset, which makes
    given-name and surname scores comparable.
    """

    name: str
    frequency: int
    gender: Gender | None = None
    percentile: float = 0.0


@dataclass(frozen=True)
class OriginProfile:
    """Everything needed to generate coherent personas for one origin."""

    code: str
    label: str
    language: str
    nationality: str
    name_order: str  # "given-first" or "family-first"
    dial_code: str
    phone_format: str  # template: {d} dial code, {p} mobile prefix, {g1..} number groups
    subscriber_digits: int
    mobile_prefixes: tuple[str, ...]
    email_domains: tuple[str, ...]
    cities: tuple[str, ...]
    roles: tuple[str, ...]
    first_names_file: str
    first_names_source: str
    surnames_file: str
    surnames_source: str
    gendered_surnames: bool = False

    def full_name(self, given: str, family: str) -> str:
        """Given/family names joined in the locale's natural order."""
        pair = (family, given) if self.name_order == "family-first" else (given, family)
        return " ".join(pair)


@dataclass(frozen=True)
class Persona:
    """A complete operational identity, not just a name."""

    id: str
    gender: Gender | None
    first_name: str
    last_name: str
    origin_code: str
    origin_label: str
    nationality: str
    language: str
    name_order: str
    birth_year: int
    age: int
    email: str
    phone: str
    city: str
    role: str
    first_name_percentile: float
    last_name_percentile: float
    commonality: float
    first_name_source: str = ""
    last_name_source: str = ""

    @property
    def full_name(self) -> str:
        """Display name in the locale's natural order (`Wang Wei` for CHN)."""
        pair = (self.last_name, self.first_name) \
            if self.name_order == "family-first" else (self.first_name, self.last_name)
        return " ".join(pair)

    def to_dict(self) -> dict:
        """Full record for the `json`/`csv` export formats."""
        row = asdict(self)
        row["gender"] = self.gender.value if self.gender else ""
        row["full_name"] = self.full_name
        return row

    def to_gophish(self) -> dict:
        """Row matching the GoPhish group-import CSV template, whose columns
        are `First Name, Last Name, Email, Position` (Position carries the
        persona's role)."""
        return {
            "First Name": self.first_name,
            "Last Name": self.last_name,
            "Email": self.email,
            "Position": self.role,
        }
