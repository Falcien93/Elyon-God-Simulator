"""Derive a universe's physics constants from its 64-bit seed."""

from __future__ import annotations

from .catalog import PhysicsSpec, physics_specs
from .seeds import normalize_seed, splitmix64

_TOP_BITS = 53
_TOP_SPAN = float(1 << _TOP_BITS)


def format_constant(value: float, places: int) -> str:
    """Decimal text for a quantized constant. This is the save-file form."""

    return f"{float(value):.{places}f}"


def _unit(word: int) -> float:
    """Map a SplitMix64 word into (0, 1) with the top 53 bits.

    Those bits are exact in IEEE-754 binary64. The low 11 bits are dropped
    before the float conversion so the fraction does not depend on rounding
    a full 64-bit integer into a float.
    """

    top = word >> (64 - _TOP_BITS)
    return (top + 0.5) / _TOP_SPAN


def _quantize(value: float, spec: PhysicsSpec) -> float:
    quantized = round(value, spec.places)
    if quantized < spec.minimum:
        quantized = spec.minimum
    elif quantized > spec.maximum:
        quantized = spec.maximum
    if quantized == 0:
        quantized = 0.0
    return float(quantized)


def derive_constants(seed: int | str, specs: tuple[PhysicsSpec, ...] | None = None) -> dict[str, float]:
    """Draw each band once, in catalog order, from ``seed``.

    The seed is the SplitMix64 state. Each constant consumes one output word.
    The word is mapped uniformly across that constant's ``[min, max]`` and
    then quantized with Python ``round`` (half to even) to ``places``.
    """

    state = normalize_seed(seed)
    chosen = physics_specs() if specs is None else specs
    derived = {}
    for spec in chosen:
        state, word = splitmix64(state)
        value = spec.minimum + _unit(word) * (spec.maximum - spec.minimum)
        derived[spec.id] = _quantize(value, spec)
    return derived
