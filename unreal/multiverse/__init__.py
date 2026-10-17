"""Seed-based multiverse: one 64-bit seed, one playable physics set, a tree of choices."""

from .catalog import (
    MajorChoice,
    PhysicsSpec,
    major_choices,
    physics_fingerprint,
    physics_specs,
)
from .constants import DERIVATION, FORMAT, MASK64, MAX_NODES, PHYSICS_COUNT, ROOT_ID
from .errors import (
    CatalogError,
    MultiverseError,
    QuantumSourceUnavailable,
    SaveError,
    SeedError,
    UnknownChoice,
    UnknownUniverse,
)
from .physics import derive_constants, format_constant
from .seeds import (
    LocalRngSource,
    QuantumSeedSource,
    SeedSource,
    format_seed,
    mix_seed,
    normalize_seed,
    splitmix64,
)
from .tree import Multiverse, Universe

__all__ = [
    "DERIVATION",
    "FORMAT",
    "MASK64",
    "MAX_NODES",
    "PHYSICS_COUNT",
    "ROOT_ID",
    "CatalogError",
    "LocalRngSource",
    "MajorChoice",
    "Multiverse",
    "MultiverseError",
    "PhysicsSpec",
    "QuantumSeedSource",
    "QuantumSourceUnavailable",
    "SaveError",
    "SeedError",
    "SeedSource",
    "UnknownChoice",
    "UnknownUniverse",
    "Universe",
    "derive_constants",
    "format_constant",
    "format_seed",
    "major_choices",
    "mix_seed",
    "normalize_seed",
    "physics_fingerprint",
    "physics_specs",
    "splitmix64",
]
