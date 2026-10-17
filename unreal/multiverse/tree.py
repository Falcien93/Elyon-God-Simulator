"""A branching tree of universes, with save and load."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .catalog import major_choices, physics_fingerprint, physics_specs
from .constants import DERIVATION, FORMAT, MAX_NODES, ROOT_ID
from .errors import SaveError, UnknownChoice, UnknownUniverse
from .physics import derive_constants, format_constant
from .seeds import LocalRngSource, SeedSource, format_seed, mix_seed, normalize_seed

_NODE_KEYS = {"id", "seed", "parent_id", "choice_id", "depth", "child_ids", "constants"}
_SAVE_KEYS = {"format", "derivation", "physics", "focus_id", "nodes"}


@dataclass(frozen=True)
class Universe:
    """One generated universe. ``constants`` is fixed for the life of the object."""

    id: str
    seed: int
    parent_id: str | None
    choice_id: str | None
    depth: int
    constants: Mapping[str, float]
    child_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "constants", MappingProxyType(dict(self.constants)))
        object.__setattr__(self, "child_ids", tuple(self.child_ids))

    def __repr__(self) -> str:
        return f"Universe(id={self.id!r}, seed={self.seed:#018x}, depth={self.depth})"


class Multiverse:
    """Root universe plus the children God's major choices have branched."""

    def __init__(self, seed: int | str) -> None:
        normalized = normalize_seed(seed)
        root = Universe(
            id=ROOT_ID,
            seed=normalized,
            parent_id=None,
            choice_id=None,
            depth=0,
            constants=derive_constants(normalized),
        )
        self._nodes: dict[str, Universe] = {ROOT_ID: root}
        self._focus_id = ROOT_ID

    @classmethod
    def originate(cls, source: SeedSource | None = None) -> Multiverse:
        """Start a tree from one draw of ``source`` (local RNG when omitted)."""

        if source is None:
            source = LocalRngSource()
        if not isinstance(source, SeedSource):
            raise TypeError("source must be a SeedSource")
        return cls(source.next_seed())

    def __repr__(self) -> str:
        return f"Multiverse(focus={self._focus_id!r}, universes={len(self._nodes)})"

    def __len__(self) -> int:
        return len(self._nodes)

    @property
    def root(self) -> Universe:
        return self._nodes[ROOT_ID]

    @property
    def focus(self) -> Universe:
        return self._nodes[self._focus_id]

    def get(self, universe_id: str) -> Universe:
        try:
            return self._nodes[universe_id]
        except KeyError:
            raise UnknownUniverse(f"no universe named {universe_id!r}") from None

    def focus_on(self, universe_id: str) -> Universe:
        universe = self.get(universe_id)
        self._focus_id = universe.id
        return universe

    def children(self, universe_id: str | None = None) -> tuple[Universe, ...]:
        universe = self.focus if universe_id is None else self.get(universe_id)
        return tuple(self._nodes[child_id] for child_id in universe.child_ids)

    def lineage(self, universe_id: str | None = None) -> tuple[Universe, ...]:
        """Root first, the named universe last."""

        universe = self.focus if universe_id is None else self.get(universe_id)
        chain = []
        seen = set()
        current: Universe | None = universe
        while current is not None:
            if current.id in seen:
                raise SaveError(f"lineage of {universe.id} cycles")
            seen.add(current.id)
            chain.append(current)
            if current.parent_id is None:
                current = None
            else:
                current = self._nodes[current.parent_id]
        chain.reverse()
        return tuple(chain)

    def choice_path(self, universe_id: str | None = None) -> tuple[str, ...]:
        """Major-choice ids from the root edge down to this universe."""

        return tuple(
            item.choice_id
            for item in self.lineage(universe_id)
            if item.choice_id is not None
        )

    def universes(self) -> tuple[Universe, ...]:
        return tuple(self._nodes.values())

    def branch(
        self,
        choice_id: str,
        parent_id: str | None = None,
        *,
        follow: bool = True,
    ) -> Universe:
        """Branch ``choice_id`` from ``parent_id`` (the focus, when omitted).

        The same choice on the same parent returns the existing child. The
        child seed is ``mix_seed(parent.seed, choice_id)``. Constants are
        derived from that child seed alone.
        """

        if not isinstance(choice_id, str) or choice_id not in {item.id for item in major_choices()}:
            raise UnknownChoice(f"unknown major choice {choice_id!r}")
        parent = self.focus if parent_id is None else self.get(parent_id)
        child_id = f"{parent.id}/{choice_id}"
        existing = self._nodes.get(child_id)
        if existing is not None:
            if follow:
                self._focus_id = existing.id
            return existing
        child_seed = mix_seed(parent.seed, choice_id)
        child = Universe(
            id=child_id,
            seed=child_seed,
            parent_id=parent.id,
            choice_id=choice_id,
            depth=parent.depth + 1,
            constants=derive_constants(child_seed),
        )
        self._nodes[child_id] = child
        self._nodes[parent.id] = replace(parent, child_ids=parent.child_ids + (child_id,))
        if follow:
            self._focus_id = child.id
        return child

    def to_dict(self) -> dict:
        specs = {spec.id: spec for spec in physics_specs()}
        nodes = []
        for universe in self._nodes.values():
            constants = {
                spec_id: format_constant(universe.constants[spec_id], spec.places)
                for spec_id, spec in specs.items()
            }
            nodes.append(
                {
                    "id": universe.id,
                    "seed": format_seed(universe.seed),
                    "parent_id": universe.parent_id,
                    "choice_id": universe.choice_id,
                    "depth": universe.depth,
                    "child_ids": list(universe.child_ids),
                    "constants": constants,
                }
            )
        return {
            "format": FORMAT,
            "derivation": DERIVATION,
            "physics": physics_fingerprint(),
            "focus_id": self._focus_id,
            "nodes": nodes,
        }

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        payload = json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"
        try:
            with destination.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
        except OSError as exc:
            raise SaveError(f"could not write {destination}") from exc

    @classmethod
    def load(cls, path: str | Path) -> Multiverse:
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise SaveError(f"could not read {source}") from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SaveError("save is not JSON") from exc
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict) -> Multiverse:
        nodes, focus_id = _decode(payload)
        world = cls.__new__(cls)
        world._nodes = nodes
        world._focus_id = focus_id
        return world


def _decode(payload: dict) -> tuple[dict[str, Universe], str]:
    if not isinstance(payload, dict) or set(payload) != _SAVE_KEYS:
        raise SaveError("save keys must be format, derivation, physics, focus_id, and nodes")
    if payload["format"] != FORMAT or isinstance(payload["format"], bool):
        raise SaveError(f"save format must be {FORMAT}")
    if payload["derivation"] != DERIVATION:
        raise SaveError(f"save derivation must be {DERIVATION}")
    if payload["physics"] != physics_fingerprint():
        raise SaveError("save physics fingerprint does not match this catalog")
    rows = payload["nodes"]
    if not isinstance(rows, list):
        raise SaveError("save nodes must be a list")
    if len(rows) > MAX_NODES:
        raise SaveError(f"a multiverse can hold at most {MAX_NODES} universes")
    if not rows:
        raise SaveError("save has no universes")

    known_choices = {item.id for item in major_choices()}
    specs = physics_specs()
    spec_ids = {spec.id for spec in specs}
    parsed: list[tuple[dict, int]] = []
    ids = []
    for index, row in enumerate(rows):
        parsed.append((_node_fields(row, index, known_choices, spec_ids), index))
        ids.append(parsed[-1][0]["id"])
    if len(ids) != len(set(ids)):
        raise SaveError("save contains a duplicate universe id")
    if ids.count(ROOT_ID) != 1:
        raise SaveError("save must contain one root")

    by_id = {row["id"]: row for row, _index in parsed}
    _check_links(by_id)
    nodes = {}
    for row, _index in parsed:
        seed = row["seed"]
        expected_seed = seed if row["parent_id"] is None else mix_seed(by_id[row["parent_id"]]["seed"], row["choice_id"])
        if seed != expected_seed:
            raise SaveError(f"{row['id']} seed does not match its parent and choice")
        derived = derive_constants(seed)
        for spec in specs:
            text = format_constant(derived[spec.id], spec.places)
            if row["constants"][spec.id] != text:
                raise SaveError(f"{row['id']} constant {spec.id} does not match its seed")
        nodes[row["id"]] = Universe(
            id=row["id"],
            seed=seed,
            parent_id=row["parent_id"],
            choice_id=row["choice_id"],
            depth=row["depth"],
            constants=derived,
            child_ids=tuple(row["child_ids"]),
        )
    focus_id = payload["focus_id"]
    if not isinstance(focus_id, str) or focus_id not in nodes:
        raise SaveError("save focus_id is not a universe in this tree")
    return nodes, focus_id


def _node_fields(row, index: int, known_choices: set[str], spec_ids: set[str]) -> dict:
    if not isinstance(row, dict) or set(row) != _NODE_KEYS:
        raise SaveError(f"node {index} keys are not usable")
    universe_id = row["id"]
    parent_id = row["parent_id"]
    choice_id = row["choice_id"]
    depth = row["depth"]
    if not isinstance(universe_id, str) or not universe_id or len(universe_id) > 4096:
        raise SaveError(f"node {index} id is not usable")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
        raise SaveError(f"{universe_id} depth must be a non-negative int")
    seed_text = row["seed"]
    if not isinstance(seed_text, str) or len(seed_text) != 16 or any(ch not in "0123456789abcdef" for ch in seed_text):
        raise SaveError(f"{universe_id} seed must be 16 lowercase hex digits")
    child_ids = row["child_ids"]
    if not isinstance(child_ids, list) or any(not isinstance(item, str) for item in child_ids):
        raise SaveError(f"{universe_id} child_ids must be a list of strings")
    if len(child_ids) != len(set(child_ids)):
        raise SaveError(f"{universe_id} child_ids contains a duplicate")
    constants = row["constants"]
    if not isinstance(constants, dict) or set(constants) != spec_ids:
        raise SaveError(f"{universe_id} constants do not match the physics catalog")
    if any(not isinstance(value, str) for value in constants.values()):
        raise SaveError(f"{universe_id} constants must be decimal strings")
    if parent_id is None:
        if choice_id is not None or universe_id != ROOT_ID or depth != 0:
            raise SaveError("root must have id 'root', no choice, and depth 0")
    else:
        if not isinstance(parent_id, str) or not isinstance(choice_id, str):
            raise SaveError(f"{universe_id} parent and choice must be strings")
        if choice_id not in known_choices:
            raise SaveError(f"{universe_id} choice is not a major choice")
        if universe_id != f"{parent_id}/{choice_id}":
            raise SaveError(f"{universe_id} id does not match its parent and choice")
        if depth != universe_id.count("/"):
            raise SaveError(f"{universe_id} depth does not match its id")
    return {
        "id": universe_id,
        "seed": int(seed_text, 16),
        "parent_id": parent_id,
        "choice_id": choice_id,
        "depth": depth,
        "child_ids": child_ids,
        "constants": constants,
    }


def _check_links(by_id: dict[str, dict]) -> None:
    listed = set()
    for universe_id, row in by_id.items():
        parent_id = row["parent_id"]
        if parent_id is not None and parent_id not in by_id:
            raise SaveError(f"{universe_id} parent is missing")
        for child_id in row["child_ids"]:
            child = by_id.get(child_id)
            if child is None:
                raise SaveError(f"{universe_id} lists a missing child")
            if child["parent_id"] != universe_id:
                raise SaveError(f"{child_id} parent does not list it back")
            listed.add(child_id)
        seen = set()
        current = universe_id
        while current is not None:
            if current in seen:
                raise SaveError(f"{universe_id} lineage cycles")
            seen.add(current)
            current = by_id[current]["parent_id"]
    orphans = [universe_id for universe_id in by_id if universe_id != ROOT_ID and universe_id not in listed]
    if orphans:
        raise SaveError(f"{orphans[0]} is not listed by its parent")
