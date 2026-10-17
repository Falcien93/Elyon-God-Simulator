"""Deterministic 32-bit LCG for the civilizations tick.

The multiplier and increment match the garden scatter stream, so a seed is
the same kind of handle across the Unreal Python tools. This module does not
import the garden and it does not import Unreal.
"""


def mix_seed(seed, tick, salt=0):
    """Fold a world seed, a tick, and a salt into one uint32."""
    mixed = (
        int(seed)
        + 0x9E3779B9 * int(tick)
        + 0x85EBCA6B * int(salt)
    ) & 0xFFFFFFFF
    return (1664525 * mixed + 1013904223) & 0xFFFFFFFF


def lcg(seed):
    """Return a callable that yields floats in [0, 1)."""
    state = int(seed) & 0xFFFFFFFF

    def nxt():
        nonlocal state
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        return state / 4294967296.0

    return nxt
