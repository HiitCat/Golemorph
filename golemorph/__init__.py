"""Golemorph: complete, coherent synthetic personas for authorized red team
spearphishing campaigns.

The public surface is deliberately small: load an origin, generate personas,
hand them to GoPhish. Everything locale-specific (name order, dial code, email
domains, cities, roles) is data in `data/manifest.yaml`, never code, so
adding a locale never means touching this package.
"""

from .loader import load_origin, load_first_names, load_surnames, origins
from .models import Gender, NameEntry, OriginProfile, Persona
from .persona import generate_personas
from .sampler import NameSampler

__version__ = "2.0.0"

__all__ = [
    "Gender",
    "NameEntry",
    "OriginProfile",
    "Persona",
    "NameSampler",
    "generate_personas",
    "load_first_names",
    "load_origin",
    "load_surnames",
    "origins",
    "__version__",
]
