"""64-bit seeds, the local RNG, and the quantum-source stub.

Child seeds and physics streams are pure functions of integers. Nothing in
this module opens a socket or reads a URL.
"""

from __future__ import annotations

import hashlib
import os
import re
from abc import ABC, abstractmethod

from .constants import DERIVATION, MASK64
from .errors import QuantumSourceUnavailable

_HEX = re.compile(r"[0-9a-fA-F]{1,16}\Z")


def normalize_seed(value: int | str) -> int:
    """Return an unsigned 64-bit integer.

    Integers must already lie in ``0 .. 2**64 - 1``. Strings are hexadecimal
    (optional ``0x`` prefix, 1 to 16 digits), not decimal.
    """

    if isinstance(value, bool) or value is None:
        raise TypeError("seed must be an int or a hex string")
    if isinstance(value, int):
        if value < 0 or value > MASK64:
            raise ValueError("seed must fit in 64 bits")
        return value
    if isinstance(value, str):
        text = value.strip()
        if text[:2].lower() == "0x":
            text = text[2:]
        if not text or _HEX.fullmatch(text) is None:
            raise ValueError("seed hex must be 1 to 16 hexadecimal digits")
        return int(text, 16)
    raise TypeError("seed must be an int or a hex string")


def format_seed(seed: int) -> str:
    """16 lowercase hex digits. JSON numbers are not exact past 2**53."""

    return f"{normalize_seed(seed):016x}"


def splitmix64(state: int) -> tuple[int, int]:
    """One step of Sebastiano Vigna's SplitMix64.

    ``state`` is the incoming 64-bit state. The pair is ``(next_state, output)``.
    """

    state = (normalize_seed(state) + 0x9E3779B97F4A7C15) & MASK64
    mixed = state
    mixed = ((mixed ^ (mixed >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    mixed = ((mixed ^ (mixed >> 27)) * 0x94D049BB133111EB) & MASK64
    return state, (mixed ^ (mixed >> 31)) & MASK64


def mix_seed(parent_seed: int | str, choice_id: str) -> int:
    """Derive a child seed from a parent seed and a major-choice id.

    The message is ``derivation || NUL || parent_be64 || NUL || choice_utf8``,
    hashed with SHA-256. The child seed is the first 8 bytes, big-endian.
    """

    parent = normalize_seed(parent_seed)
    if not isinstance(choice_id, str) or choice_id == "":
        raise ValueError("choice id must be a non-empty string")
    if "\x00" in choice_id:
        raise ValueError("choice id must not contain a NUL")
    message = (
        DERIVATION.encode("ascii")
        + b"\x00"
        + parent.to_bytes(8, "big")
        + b"\x00"
        + choice_id.encode("utf-8")
    )
    return int.from_bytes(hashlib.sha256(message).digest()[:8], "big")


class SeedSource(ABC):
    """Something that can mint a fresh 64-bit root seed."""

    @abstractmethod
    def next_seed(self) -> int:
        """Return one unsigned 64-bit seed."""


class LocalRngSource(SeedSource):
    """Default seed source.

    With a seed, the stream is SplitMix64 and the same constructor seed
    replays the same roots. With no seed, each call reads 8 bytes from
    ``os.urandom`` on this machine.
    """

    def __init__(self, seed: int | str | None = None) -> None:
        self._state = None if seed is None else normalize_seed(seed)

    def next_seed(self) -> int:
        if self._state is None:
            return int.from_bytes(os.urandom(8), "big")
        self._state, word = splitmix64(self._state)
        return word


class QuantumSeedSource(SeedSource):
    """Stub for an external quantum randomness source.

    The default instance has no provider and refuses to invent bits. A caller
    may pass a local callable that returns exactly 8 bytes (a device handle,
    a hardware RNG, or an offline buffer). This class does not open a socket,
    does not accept a URL, and does not import a network stack.
    """

    def __init__(self, provider=None) -> None:
        if provider is None:
            self._provider = None
            return
        if isinstance(provider, (str, bytes, bytearray)):
            raise TypeError(
                "quantum provider must be a callable that returns 8 bytes, not a string or URL"
            )
        if not callable(provider):
            raise TypeError("quantum provider must be a callable that returns 8 bytes")
        self._provider = provider

    def next_seed(self) -> int:
        if self._provider is None:
            raise QuantumSourceUnavailable(
                "No quantum seed provider is attached. "
                "Pass a local callable that returns 8 bytes. "
                "This stub does not contact a network service."
            )
        raw = self._provider()
        if isinstance(raw, bytearray):
            raw = bytes(raw)
        if not isinstance(raw, bytes) or len(raw) != 8:
            raise ValueError("quantum provider must return exactly 8 bytes")
        return int.from_bytes(raw, "big")
