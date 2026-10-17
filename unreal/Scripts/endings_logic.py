"""Four campaign endings, ported from js/sim.js resolveEnding and js/content.js.

The hands choice (`ending:hands`) becomes wonder when silence was kept, and exile
otherwise. The first ending sticks. After it, the garden can still be walked.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "Data"

# Starting numbers match createNewGame in js/sim.js.
ORDER_START = 48
WONDER_START = 42
RELATIONS = {
    "adam": {"trust": 20, "wonder": 36, "will": 28},
    "eve": {"trust": 20, "wonder": 44, "will": 34},
}

# Adam's garden home matches the Day 1 marker. Eve stands beside him.
# The river in that slice ends at x=4500; exile is the grass past its mouth.
GARDEN_HOMES = {
    "adam": (400.0, -400.0, 110.0),
    "eve": (220.0, -260.0, 110.0),
}
EXILE_HOMES = {
    "adam": (5200.0, 980.0, 110.0),
    "eve": (4980.0, 1240.0, 110.0),
}
RIVER_EAST = 4500.0

ENDING_NODES = ("eve_choice", "serpent_meet", "serpent_why")
CONSEQUENCES = {
    "harmony": ("dismiss_serpent", "remain_in_garden"),
    "wonder": ("dismiss_serpent", "remain_in_garden"),
    "order": ("dismiss_serpent", "guard_tree", "remain_in_garden"),
    "exile": ("dismiss_serpent", "clothe", "walk_east"),
}


class CatalogError(ValueError):
    """endings.json and ending_sequences.json disagree."""


def new_state(now=0):
    return {
        "now": int(now),
        "flags": {
            "silence": False,
            "commandment_spoken": False,
            "beasts_named": False,
            "eve_made": False,
            "serpent_present": False,
            "serpent_gone": False,
            "tree_guarded": False,
            "clothed": False,
            "ending_seen": False,
        },
        "commandment": None,
        "stats": {"order": ORDER_START, "wonder": WONDER_START},
        "relations": {who: dict(values) for who, values in RELATIONS.items()},
        "homes": {who: GARDEN_HOMES[who] for who in GARDEN_HOMES},
        "ending": None,
        "log": [],
        "codex": [],
        "can_walk": True,
    }


def sanitize_commandment(raw):
    cleaned = str("" if raw is None else raw).replace("<", "").replace(">", "")
    cleaned = " ".join(cleaned.split())[:180]
    return cleaned or None


def set_commandment(state, raw):
    if state["ending"] or state["flags"]["serpent_present"] or state["flags"]["serpent_gone"]:
        return {"ok": False, "reason": "already"}
    if not state["flags"]["eve_made"]:
        return {"ok": False, "reason": "locked"}
    text = sanitize_commandment(raw)
    if not text:
        return {"ok": False, "reason": "empty"}
    state["commandment"] = text
    state["flags"]["commandment_spoken"] = True
    state["flags"]["silence"] = False
    _unlock(state, "word")
    state["log"].append(f"You spoke a commandment: “{text}”")
    refresh_story(state)
    return {"ok": True}


def choose_silence(state):
    if state["ending"] or state["flags"]["serpent_present"] or state["flags"]["serpent_gone"]:
        return {"ok": False, "reason": "already"}
    if not state["flags"]["eve_made"]:
        return {"ok": False, "reason": "locked"}
    if state["flags"]["silence"]:
        return {"ok": False, "reason": "already"}
    state["flags"]["silence"] = True
    state["flags"]["commandment_spoken"] = False
    state["commandment"] = None
    state["stats"]["wonder"] = _clamp(state["stats"]["wonder"] + 8)
    _unlock(state, "word")
    state["log"].append("You kept silent. No prohibition was set upon the tree.")
    refresh_story(state)
    return {"ok": True}


def name_beasts(state):
    state["flags"]["beasts_named"] = True
    refresh_story(state)
    return {"ok": True}


def refresh_story(state):
    """The low voice coils once the beasts are named and the word, or the silence, is set."""
    if state["ending"]:
        return state
    flags = state["flags"]
    if (
        flags["beasts_named"]
        and (flags["commandment_spoken"] or flags["silence"])
        and not flags["serpent_present"]
        and not flags["serpent_gone"]
    ):
        flags["serpent_present"] = True
        state["log"].append("Something low and bright coiled in the Tree of Knowledge.")
    return state


def load_catalog(data_dir=None):
    folder = Path(data_dir) if data_dir else DATA_DIR
    endings = json.loads((folder / "endings.json").read_text(encoding="utf-8"))
    sequences = json.loads((folder / "ending_sequences.json").read_text(encoding="utf-8"))
    problems = validate_catalog(endings, sequences)
    if problems:
        raise CatalogError("; ".join(problems))
    return {"endings": endings, "sequences": sequences}


def validate_catalog(endings, sequences):
    problems = []
    rows = endings.get("endings") or []
    ids = [row.get("id") for row in rows]
    if ids != ["harmony", "exile", "wonder", "order"]:
        problems.append("endings must be harmony, exile, wonder, order in that order")
    hands = endings.get("handsRule") or {}
    if hands.get("whenChoiceFx") != "ending:hands":
        problems.append("handsRule.whenChoiceFx must be ending:hands")
    if hands.get("ifFlagSilence") != "wonder" or hands.get("otherwise") != "exile":
        problems.append("handsRule must resolve silence to wonder and otherwise to exile")
    by_id = {}
    for row in rows:
        ending_id = row.get("id")
        by_id[ending_id] = row
        if len(row.get("paragraphs") or []) < 2:
            problems.append(f"{ending_id} needs two paragraphs")
        for cond in row.get("conditions") or []:
            problems.extend(_validate_condition(row, cond, hands))
    spec = sequences.get("endings") or {}
    if set(spec) != set(by_id):
        problems.append("sequence scaffolds must cover the four ending ids")
    folder = sequences.get("folder") or ""
    if not folder.startswith("/Game/"):
        problems.append("sequence folder must be an Unreal /Game path")
    fps = sequences.get("fps")
    if fps != 24:
        problems.append("sequence fps must be 24")
    for key in ("fadeInSeconds", "secondsPerParagraph", "holdSeconds"):
        if not isinstance(sequences.get(key), (int, float)) or sequences.get(key) <= 0:
            problems.append(f"{key} must be a positive number")
    if not sequences.get("cameraName"):
        problems.append("cameraName is required")
    for ending_id, cinematic in spec.items():
        problems.extend(_validate_shots(ending_id, cinematic.get("shots") or []))
    return problems


def choice_reachable(state, node_id):
    if node_id not in ENDING_NODES:
        return False
    flags = state["flags"]
    if flags["serpent_gone"] or state["ending"]:
        return False
    return bool(flags["serpent_present"])


def choose(state, node_id, choice_label, catalog=None):
    """Apply the ending choice. A second ending does not replace the first."""
    catalog = catalog or load_catalog()
    if state["ending"]:
        return {"ok": False, "reason": "already", "ending": state["ending"]["id"], "held": True}
    if not choice_reachable(state, node_id):
        return {"ok": False, "reason": "locked"}
    matches = _matching_conditions(catalog, node_id, choice_label, state["flags"])
    if not matches:
        return {"ok": False, "reason": "unknown"}
    ending, cond = matches[0]
    trigger = {
        "node": node_id,
        "speaker": cond.get("speaker"),
        "choice": choice_label,
        "fx": cond["fx"],
        "goto": cond.get("goto"),
    }
    for fx in cond.get("effects") or [cond["fx"]]:
        apply_fx(state, fx, trigger, catalog)
    if not state["ending"]:
        return {"ok": False, "reason": "unknown"}
    return {
        "ok": True,
        "ending": state["ending"]["id"],
        "goto": cond.get("goto"),
        "held": False,
        "sequence": state["ending"]["sequence"],
    }


def preview_choice(state, node_id, choice_label, catalog=None):
    """Which ending this choice would keep, without changing state."""
    catalog = catalog or load_catalog()
    if state["ending"]:
        return state["ending"]["id"]
    matches = _matching_conditions(catalog, node_id, choice_label, state["flags"])
    if not matches:
        return None
    return _token_ending(matches[0][1]["fx"], state["flags"], catalog["endings"]["handsRule"])


def apply_fx(state, fx, trigger=None, catalog=None):
    parts = str(fx).split(":")
    head = parts[0] if parts else ""
    if head == "flag" and len(parts) >= 2 and parts[1]:
        state["flags"][parts[1]] = True
        return {"ok": True, "fx": fx}
    if head in ("trust", "wonder", "will") and len(parts) >= 3 and parts[1] in ("adam", "eve"):
        amount = _number(parts[2])
        if amount is not None:
            bag = state["relations"][parts[1]]
            bag[head] = _clamp((bag.get(head) or 0) + amount)
        return {"ok": True, "fx": fx}
    if head == "wonder" and len(parts) == 2:
        amount = _number(parts[1])
        if amount is not None:
            state["stats"]["wonder"] = _clamp(state["stats"]["wonder"] + amount)
        return {"ok": True, "fx": fx}
    if head == "order" and len(parts) >= 2:
        amount = _number(parts[1])
        if amount is not None:
            state["stats"]["order"] = _clamp(state["stats"]["order"] + amount)
        return {"ok": True, "fx": fx}
    if head == "ending":
        token = parts[1] if len(parts) > 1 else ""
        return resolve_ending(state, token, trigger, catalog)
    return {"ok": False, "reason": "unknown", "fx": fx}


def resolve_ending(state, token, trigger=None, catalog=None):
    if state["ending"]:
        return {"ok": False, "reason": "already", "ending": state["ending"]["id"], "held": True}
    catalog = catalog or load_catalog()
    hands = catalog["endings"]["handsRule"]
    ending_id = _token_ending(f"ending:{token}" if not str(token).startswith("ending:") else token, state["flags"], hands)
    row = next((item for item in catalog["endings"]["endings"] if item["id"] == ending_id), None)
    if row is None:
        return {"ok": False, "reason": "unknown"}
    because = "silence" if token == "hands" and state["flags"]["silence"] else "no-silence" if token == "hands" else "direct"
    _apply_consequences(state, ending_id)
    asset = sequence_asset(catalog, ending_id)
    state["ending"] = {
        "id": ending_id,
        "at": int(state["now"]),
        "title": row["title"],
        "because": because,
        "trigger": dict(trigger or {}),
        "sequence": asset,
        "consequences": list(CONSEQUENCES[ending_id]),
    }
    state["flags"]["ending_seen"] = False
    state["flags"]["serpent_gone"] = True
    state["can_walk"] = True
    state["log"].append(row["title"] + ".")
    _unlock(state, "choice")
    return {"ok": True, "ending": ending_id, "sequence": asset, "held": False}


def mark_ending_seen(state):
    """The ending card is put away. Walking the garden continues."""
    if not state["ending"]:
        return {"ok": False, "reason": "empty"}
    state["flags"]["ending_seen"] = True
    state["can_walk"] = True
    return {"ok": True}


def ending_overlay_due(state):
    return bool(state["ending"]) and not state["flags"]["ending_seen"]


def can_address(state, who):
    if who == "serpent":
        return bool(state["flags"]["serpent_present"]) and not state["flags"]["serpent_gone"] and not state["ending"]
    return who in ("adam", "eve")


def epilogue_entry(state, who):
    if who == "serpent":
        if not can_address(state, "serpent"):
            return None
        return "serpent_meet"
    if who in ("adam", "eve") and state["ending"]:
        return f"{who}_epilogue_{state['ending']['id']}"
    return None


def sequence_asset(catalog, ending_id):
    folder = catalog["sequences"]["folder"].rstrip("/")
    return f"{folder}/{sequence_name(ending_id)}"


def sequence_name(ending_id):
    return f"LS_Ending_{ending_id}"


def sequence_plans(catalog):
    spec = catalog["sequences"]
    fps = int(spec["fps"])
    fade_in = _frames(spec["fadeInSeconds"], fps)
    per_paragraph = _frames(spec["secondsPerParagraph"], fps)
    hold = _frames(spec["holdSeconds"], fps)
    plans = []
    for row in catalog["endings"]["endings"]:
        paragraphs = row["paragraphs"]
        readable = per_paragraph * len(paragraphs)
        hold_frame = fade_in + readable
        end_frame = hold_frame + hold
        shots = spec["endings"][row["id"]]["shots"]
        camera_keys = []
        for shot in shots:
            camera_keys.append(
                {
                    "frame": fade_in + int(round(float(shot["at"]) * readable)),
                    "location": tuple(float(v) for v in shot["location"]),
                    "rotation": tuple(float(v) for v in shot["rotation"]),
                    "note": shot["note"],
                }
            )
        markers = [{"frame": 0, "label": f"Ending.Begin.{row['id']}", "text": row["title"]}]
        for index, paragraph in enumerate(paragraphs):
            markers.append(
                {
                    "frame": fade_in + index * per_paragraph,
                    "label": f"Ending.Paragraph.{index}",
                    "text": paragraph,
                }
            )
        markers.append(
            {
                "frame": hold_frame,
                "label": "Ending.Hold",
                "text": "The garden can still be walked.",
            }
        )
        plans.append(
            {
                "id": row["id"],
                "title": row["title"],
                "name": sequence_name(row["id"]),
                "folder": spec["folder"],
                "asset": sequence_asset(catalog, row["id"]),
                "fps": fps,
                "end_frame": end_frame,
                "fade_in_frame": fade_in,
                "hold_frame": hold_frame,
                "camera_name": spec["cameraName"],
                "camera_keys": camera_keys,
                "markers": markers,
                "fades": [
                    {"frame": 0, "amount": 1.0},
                    {"frame": fade_in, "amount": 0.0},
                ],
                "paragraphs": list(paragraphs),
            }
        )
    return plans


def _validate_condition(row, cond, hands):
    problems = []
    ending_id = row.get("id")
    fx = cond.get("fx") or ""
    effects = cond.get("effects") or []
    if not fx.startswith("ending:"):
        problems.append(f"{ending_id} condition fx must be an ending token")
    if fx not in effects:
        problems.append(f"{ending_id} effects must include {fx}")
    if cond.get("node") not in ENDING_NODES:
        problems.append(f"{ending_id} condition node is not an ending door")
    if not cond.get("choice") or not cond.get("goto"):
        problems.append(f"{ending_id} condition needs a choice and a goto")
    if cond.get("resolvesTo") and cond.get("resolvesTo") != ending_id:
        problems.append(f"{ending_id} resolvesTo does not match its id")
    resolved = _token_ending(fx, _flags_for(cond), hands)
    if resolved != ending_id:
        problems.append(f"{ending_id} condition resolves to {resolved}")
    return problems


def _validate_shots(ending_id, shots):
    problems = []
    if len(shots) < 2:
        problems.append(f"{ending_id} camera needs at least two shots")
        return problems
    previous = -1.0
    for shot in shots:
        at = shot.get("at")
        if not isinstance(at, (int, float)) or at < 0 or at > 1 or at <= previous:
            problems.append(f"{ending_id} shot times must increase from 0 to 1")
            break
        previous = float(at)
        for key in ("location", "rotation"):
            values = shot.get(key)
            if not isinstance(values, list) or len(values) != 3 or not all(isinstance(v, (int, float)) for v in values):
                problems.append(f"{ending_id} {key} must be three numbers")
        location = shot.get("location") or [0, 0, 0]
        if location[2] < 80 or location[2] > 3000:
            problems.append(f"{ending_id} camera height must stay in the garden air")
        if abs(location[0]) > 8000 or abs(location[1]) > 8000:
            problems.append(f"{ending_id} camera must stay near the valley")
    if shots[0].get("at") != 0 or shots[-1].get("at") != 1:
        problems.append(f"{ending_id} shots must start at 0 and end at 1")
    return problems


def _flags_for(cond):
    requires = cond.get("requires") or {}
    return {"silence": bool(requires.get("silence", False))}


def _matching_conditions(catalog, node_id, choice_label, flags):
    found = []
    for row in catalog["endings"]["endings"]:
        for cond in row["conditions"]:
            if cond["node"] != node_id or cond["choice"] != choice_label:
                continue
            requires = cond.get("requires") or {}
            if all(bool(flags.get(key)) == bool(value) for key, value in requires.items()):
                found.append((row, cond))
    found.sort(key=lambda item: len(item[1].get("requires") or {}), reverse=True)
    return found


def _token_ending(fx, flags, hands):
    token = str(fx).split(":")[-1]
    if token == "hands":
        if flags.get("silence"):
            return hands["ifFlagSilence"]
        return hands["otherwise"]
    if token in CONSEQUENCES:
        return token
    return None


def _apply_consequences(state, ending_id):
    state["flags"]["serpent_gone"] = True
    if ending_id == "order":
        state["flags"]["tree_guarded"] = True
    if ending_id == "exile":
        state["flags"]["clothed"] = True
        state["homes"] = {who: EXILE_HOMES[who] for who in EXILE_HOMES}


def _unlock(state, entry):
    if entry not in state["codex"]:
        state["codex"].append(entry)


def _clamp(value):
    return max(0, min(100, value))


def _number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def _frames(seconds, fps):
    return int(round(float(seconds) * fps))
