"""Load the playable physics bands and the major-choice catalog."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .constants import DERIVATION, PHYSICS_COUNT
from .errors import CatalogError

DATA_DIR = Path(__file__).resolve().parents[1] / "Data"
_ID = re.compile(r"[a-z][a-z0-9_]*\Z")
_physics_cache: tuple[PhysicsSpec, ...] | None = None
_choice_cache: tuple[MajorChoice, ...] | None = None
_fingerprint_cache: str | None = None


@dataclass(frozen=True)
class PhysicsSpec:
    """One playable band. Generation walks the catalog in file order."""

    id: str
    name: str
    unit: str
    nominal: float
    minimum: float
    maximum: float
    places: int


@dataclass(frozen=True)
class MajorChoice:
    """An edge God can take. The id is mixed into the child seed."""

    id: str
    label: str
    group: str
    summary: str


def _load_object(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"could not read {path.name}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"{path.name} is not JSON") from exc
    if not isinstance(payload, dict):
        raise CatalogError(f"{path.name} must be a JSON object")
    if "note" in payload and not isinstance(payload["note"], str):
        raise CatalogError(f"{path.name} note must be a string")
    return payload


def _exact_keys(payload: dict, allowed: set[str], label: str) -> None:
    extra = set(payload) - allowed
    missing = allowed - {"note"} - set(payload)
    if extra or missing:
        raise CatalogError(f"{label} keys are not usable")


def _text(value, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise CatalogError(f"{field} must be a string")
    stripped = value.strip()
    if not stripped or len(stripped) > limit:
        raise CatalogError(f"{field} must be 1 to {limit} characters")
    return stripped


def _identifier(value, field: str) -> str:
    text = _text(value, field, 40)
    if _ID.fullmatch(text) is None:
        raise CatalogError(f"{field} must be a lowercase id")
    return text


def _number(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CatalogError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise CatalogError(f"{field} must be a finite number")
    return number


def _read_physics(path: Path) -> tuple[PhysicsSpec, ...]:
    payload = _load_object(path)
    _exact_keys(payload, {"format", "constants", "note"}, path.name)
    if payload.get("format") != 1 or isinstance(payload.get("format"), bool):
        raise CatalogError(f"{path.name} format must be 1")
    rows = payload.get("constants")
    if not isinstance(rows, list):
        raise CatalogError(f"{path.name} constants must be a list")
    specs = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CatalogError(f"constant {index} must be an object")
        _exact_keys(
            row,
            {"id", "name", "unit", "nominal", "min", "max", "places"},
            f"constant {index}",
        )
        spec_id = _identifier(row["id"], f"constant {index} id")
        if spec_id in seen:
            raise CatalogError(f"duplicate constant id {spec_id}")
        seen.add(spec_id)
        places = row["places"]
        if isinstance(places, bool) or not isinstance(places, int) or places < 0 or places > 8:
            raise CatalogError(f"{spec_id} places must be an int from 0 to 8")
        minimum = _number(row["min"], f"{spec_id} min")
        maximum = _number(row["max"], f"{spec_id} max")
        nominal = _number(row["nominal"], f"{spec_id} nominal")
        if not minimum < maximum:
            raise CatalogError(f"{spec_id} min must be below max")
        if nominal < minimum or nominal > maximum:
            raise CatalogError(f"{spec_id} nominal must lie inside the band")
        specs.append(
            PhysicsSpec(
                id=spec_id,
                name=_text(row["name"], f"{spec_id} name", 80),
                unit=_text(row["unit"], f"{spec_id} unit", 40),
                nominal=nominal,
                minimum=minimum,
                maximum=maximum,
                places=places,
            )
        )
    if len(specs) != PHYSICS_COUNT:
        raise CatalogError(f"{path.name} must list {PHYSICS_COUNT} constants")
    return tuple(specs)


def _read_choices(path: Path) -> tuple[MajorChoice, ...]:
    payload = _load_object(path)
    _exact_keys(payload, {"format", "choices", "note"}, path.name)
    if payload.get("format") != 1 or isinstance(payload.get("format"), bool):
        raise CatalogError(f"{path.name} format must be 1")
    rows = payload.get("choices")
    if not isinstance(rows, list) or not rows:
        raise CatalogError(f"{path.name} choices must be a non-empty list")
    choices = []
    seen_ids = set()
    seen_labels = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CatalogError(f"choice {index} must be an object")
        _exact_keys(row, {"id", "label", "group", "summary"}, f"choice {index}")
        choice_id = _identifier(row["id"], f"choice {index} id")
        label = _text(row["label"], f"{choice_id} label", 80)
        if choice_id in seen_ids:
            raise CatalogError(f"duplicate choice id {choice_id}")
        if label in seen_labels:
            raise CatalogError(f"duplicate choice label {label}")
        seen_ids.add(choice_id)
        seen_labels.add(label)
        choices.append(
            MajorChoice(
                id=choice_id,
                label=label,
                group=_identifier(row["group"], f"{choice_id} group"),
                summary=_text(row["summary"], f"{choice_id} summary", 280),
            )
        )
    return tuple(choices)


def physics_specs(path: Path | None = None) -> tuple[PhysicsSpec, ...]:
    """Playable bands in generation order. The default file is cached."""

    global _physics_cache
    if path is None and _physics_cache is not None:
        return _physics_cache
    specs = _read_physics(DATA_DIR / "physics_constants.json" if path is None else Path(path))
    if path is None:
        _physics_cache = specs
    return specs


def major_choices(path: Path | None = None) -> tuple[MajorChoice, ...]:
    """God's major choices, in catalog order. The default file is cached."""

    global _choice_cache
    if path is None and _choice_cache is not None:
        return _choice_cache
    choices = _read_choices(DATA_DIR / "major_choices.json" if path is None else Path(path))
    if path is None:
        _choice_cache = choices
    return choices


def physics_fingerprint() -> str:
    """16 hex chars over the derivation tag and the ordered bands.

    Choice labels are not part of the fingerprint. Adding a choice does not
    invalidate a save. Changing a band, its order, or its decimal places does.
    """

    global _fingerprint_cache
    if _fingerprint_cache is not None:
        return _fingerprint_cache
    lines = [DERIVATION]
    for spec in physics_specs():
        lines.append(
            f"{spec.id}:{spec.minimum:.10f}:{spec.maximum:.10f}:{spec.places}"
        )
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    _fingerprint_cache = digest[:16]
    return _fingerprint_cache
