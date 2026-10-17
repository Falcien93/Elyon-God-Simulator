"""Incarnation: walk among them.

Pure Python. God takes a human form in a settlement that already has shelter.
Disposition is a hostility score. On endings that already allow a lethal clash
it can reach one crucifixion beat, then an underworld passage, then a
resurrection return. Harmony and order never reach that beat.

This module does not import Unreal, the garden builder, the civilizations
sketch, physics, or voice. It does not call a model or a network.
"""

import copy
import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "Data" / "incarnation.json"

PHASES = ("sky", "walking", "crucifixion", "underworld", "returned", "ascended")
ACTIONS = ("enter", "beat", "meet", "continue", "listen", "leave", "ascend")
ENDING_IDS = ("harmony", "wonder", "exile", "order")
CAUSES = ("flood", "clash")
SPEAKING_ROLES = ("leader", "prophet")

# (phase, action, resulting phase). Meet does not change phase.
LEGAL = {
    ("sky", "enter", "walking"),
    ("walking", "beat", "walking"),
    ("walking", "beat", "crucifixion"),
    ("walking", "ascend", "ascended"),
    ("crucifixion", "continue", "underworld"),
    ("underworld", "listen", "underworld"),
    ("underworld", "leave", "returned"),
    ("returned", "ascend", "ascended"),
}

# Whole words. "crucifixion" is the event's name and is not in this list.
FORBIDDEN = (
    "blood",
    "gore",
    "crucify",
    "corpse",
    "nail",
    "nails",
    "spear",
    "scream",
    "taunt",
    "naked",
    "torture",
    "wound",
    "whip",
    "thorn",
    "hell",
    "jesus",
    "christ",
    "messiah",
    "gospel",
    "psalm",
    "yahweh",
    "calvary",
    "golgotha",
)

_RULES = None


class IncarnationError(ValueError):
    """The walk refused an action this phase does not allow."""


def load_rules(path=None):
    global _RULES
    if path is None and _RULES is not None:
        return _RULES
    source = Path(path) if path is not None else DATA_PATH
    with source.open(encoding="utf-8") as handle:
        rules = json.load(handle)
    validate_rules(rules)
    if path is None:
        _RULES = rules
    return rules


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def forbidden_word(text):
    lowered = text.lower()
    for word in FORBIDDEN:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return word
    if re.search(r"\b(on a cross|the cross)\b", lowered):
        return "cross"
    return None


def validate_rules(rules):
    if rules.get("telling") != "original":
        raise IncarnationError("incarnation data must stay an original telling")
    if tuple(rules.get("phases", [])) != PHASES:
        raise IncarnationError("phase list does not match the mode")
    found = set()
    for row in rules.get("transitions", []):
        found.add((row["from"], row["action"], row["to"]))
    if found != LEGAL:
        raise IncarnationError("phase transitions do not match the mode")
    host = rules["hostility"]
    if int(host["seizeAt"]) != 81 or int(host["min"]) != 0 or int(host["max"]) != 100:
        raise IncarnationError("hostility must run from 0 to 100 and seize at 81")
    if int(host["faithLow"]) != 40 or int(host["faithHigh"]) != 60:
        raise IncarnationError("faith thresholds must stay under 40 and over 60")
    covered = []
    for band in rules["bands"]:
        covered.append((int(band["min"]), int(band["max"]), band["id"]))
    if covered != [(0, 30, "welcome"), (31, 60, "wary"), (61, 80, "hostile"), (81, 100, "seized")]:
        raise IncarnationError("disposition bands must be welcome, wary, hostile, seized")
    if set(rules["endings"]) != set(ENDING_IDS):
        raise IncarnationError("endings must stay the four the garden already locks")
    for ending_id, ending in rules["endings"].items():
        cap = int(ending["hostilityCap"])
        if cap < 0 or cap > 100:
            raise IncarnationError("hostility cap is out of range")
        if ending_id in ("harmony", "order"):
            if ending["seizure"] or cap > 60:
                raise IncarnationError("harmony and order do not seize")
        elif not ending["seizure"]:
            raise IncarnationError("wonder and exile can reach the crucifixion beat")
    if int(rules["absenceFear"]) != 10:
        raise IncarnationError("the absence raises fear by 10")
    expected = {
        "harmony": (20, -15),
        "wonder": (16, -12),
        "exile": (10, -8),
        "order": (8, -6),
    }
    for ending_id, (faith, fear) in expected.items():
        back = rules["endings"][ending_id]["return"]
        if int(back["faith"]) != faith or int(back["fear"]) != fear:
            raise IncarnationError("return deltas do not match the ending table")
    seen = set()
    for figure in rules["lost"]:
        if figure["id"] in seen:
            raise IncarnationError("a lost figure is named twice")
        seen.add(figure["id"])
        if figure["cause"] not in CAUSES or figure["role"] not in SPEAKING_ROLES:
            raise IncarnationError("the dead who speak were lost to flood or clash")
        if not figure.get("line"):
            raise IncarnationError("a lost figure has no line")
    for text in _strings(rules):
        word = forbidden_word(text)
        if word:
            raise IncarnationError(f"incarnation data refuses the word {word}")
    return rules


def _rules_of(rules):
    return rules if rules is not None else load_rules()


def _ending(rules, ending_id):
    try:
        return rules["endings"][ending_id]
    except KeyError as exc:
        raise IncarnationError("the locked ending must be harmony, wonder, exile, or order") from exc


def _clamp(value, low, high):
    value = int(value)
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_id(value):
    cleaned = "".join(ch for ch in str(value).lower() if ch.isalnum() or ch == "_")
    if not cleaned or cleaned != str(value).lower():
        raise IncarnationError("a figure id must be lowercase letters, numbers, or underscore")
    return cleaned


def _copy_lost(figures):
    copied = []
    seen = set()
    for figure in figures:
        figure_id = _safe_id(figure["id"])
        if figure_id in seen:
            raise IncarnationError("a lost figure is named twice")
        if figure.get("cause") not in CAUSES or figure.get("role") not in SPEAKING_ROLES:
            raise IncarnationError("the dead who speak were lost to flood or clash")
        if not figure.get("line"):
            raise IncarnationError("a lost figure has no line")
        word = forbidden_word(figure["line"])
        if word:
            raise IncarnationError(f"incarnation data refuses the word {word}")
        seen.add(figure_id)
        copied.append(
            {
                "id": figure_id,
                "cause": figure["cause"],
                "role": figure["role"],
                "line": figure["line"],
                "x": float(figure.get("x", 0)),
                "y": float(figure.get("y", 0)),
            }
        )
    return copied


def plan_phase(phase):
    """Map key for a phase. Sky and ascended do not open a level."""
    if phase in ("walking", "crucifixion", "returned", "underworld"):
        return phase
    if phase in ("sky", "ascended"):
        return None
    raise IncarnationError(f"unknown phase: {phase}")


def band_for(hostility, rules=None):
    rules = _rules_of(rules)
    value = int(hostility)
    if value < 0 or value > 100:
        raise IncarnationError("hostility is kept from 0 to 100")
    for band in rules["bands"]:
        if int(band["min"]) <= value <= int(band["max"]):
            return band["id"]
    raise IncarnationError("hostility has no disposition band")


def rise_amount(prosperity, shelter, stores, rules=None):
    """Prosperity slows the rise. Shelter and stores together slow it again."""
    host = _rules_of(rules)["hostility"]
    base = int(host["rise"])
    divisor = int(host["prosperityDivisor"])
    prosperity = max(0, int(prosperity))
    amount = base * divisor // (divisor + prosperity)
    if amount < 1:
        amount = 1
    if shelter and stores:
        amount = amount // int(host["shelterStoresScaleDivisor"])
        if amount < 1:
            amount = 1
    return amount


def next_hostility(
    hostility,
    faith,
    fear,
    prosperity,
    shelter,
    stores,
    cap,
    walked=False,
    spoken_to=False,
    rules=None,
):
    """One beat of disposition.

    Rises while fear is high and faith is under 40. Otherwise falls when faith
    is over 60, or when this beat was only walking and being spoken to.
    A frightened people still turn if the rise condition is met.
    """
    rules = _rules_of(rules)
    host = rules["hostility"]
    value = int(hostility)
    faith = int(faith)
    fear = int(fear)
    if fear >= int(host["fearHigh"]) and faith < int(host["faithLow"]):
        value += rise_amount(prosperity, shelter, stores, rules)
    elif faith > int(host["faithHigh"]) or (walked and spoken_to):
        value -= int(host["fall"])
    if value < int(host["min"]):
        value = int(host["min"])
    limit = min(int(cap), int(host["max"]))
    if value > limit:
        value = limit
    return value


def seizure_fires(hostility, ending_id, rules=None):
    rules = _rules_of(rules)
    ending = _ending(rules, ending_id)
    if not ending["seizure"]:
        return False
    return int(hostility) >= int(rules["hostility"]["seizeAt"])


def leader_act(state):
    """Receive, question, or seize. Seize is absent for harmony and order."""
    if state["phase"] not in ("walking", "crucifixion"):
        return None
    if state["band"] is None:
        return None
    if not state["seizure_allowed"]:
        if state["band"] == "welcome":
            return "receive"
        return "question"
    if state["band"] == "welcome":
        return "receive"
    if state["band"] == "seized" or state["phase"] == "crucifixion":
        return "seize"
    return "question"


def crowd_tag(state):
    """The many copy the band. They do not speak and they do not call a model."""
    if state["phase"] != "walking":
        return None
    return state["band"]


def _note(state, key, rules, **extra):
    entry = {"phase": state["phase"], "text": rules["lines"][key]}
    entry.update(extra)
    state["log"].append(entry)


def _voice(state, speaker, role, where, line):
    state["events"].append(
        {
            "needs_voice": True,
            "model_called": False,
            "speaker": speaker,
            "role": role,
            "where": where,
            "line": line,
        }
    )


def begin(ending, settlement=None, rules=None):
    """Sky view, before the player chooses the walk. The ending is already locked."""
    rules = _rules_of(rules)
    ending_id = str(ending)
    tone = _ending(rules, ending_id)
    settlement = settlement or {}
    if settlement.get("lost") is None:
        lost = _copy_lost(rules["lost"])
    else:
        lost = _copy_lost(settlement["lost"])
    region = settlement.get("region") or tone.get("region") or "valley"
    faith = _clamp(settlement.get("faith", 50), 0, 100)
    fear = _clamp(settlement.get("fear", 20), 0, 100)
    prosperity = _clamp(settlement.get("prosperity", 40), 0, 100)
    population = max(1, int(settlement.get("population", 12)))
    return {
        "phase": "sky",
        "ending": ending_id,
        "ending_title": tone["title"],
        "attitude": tone["attitude"],
        "chosen": False,
        "shelter": bool(settlement.get("shelter", False)),
        "stores": bool(settlement.get("stores", False)),
        "faith": faith,
        "fear": fear,
        "prosperity": prosperity,
        "population": population,
        "region": region,
        "hostility": 0,
        "last_hostility": 0,
        "band": None,
        "seizure_allowed": bool(tone["seizure"]),
        "interventions_available": True,
        "world_speech_available": True,
        "god_camera": "awake",
        "living_tick_paused": False,
        "pawn_among_living": False,
        "in_passage": False,
        "incarnate_returned": False,
        "departed_in_peace": False,
        "clash_allowed": bool(tone["clashAllowed"]),
        "clash_eased": False,
        "wonder_restored": False,
        "fear_raised_for_absence": False,
        "lost": lost,
        "heard": [],
        "events": [],
        "log": [],
    }


def _require(state, *phases):
    if state["phase"] not in phases:
        raise IncarnationError(f"that action is not for the {state['phase']} phase")


def _asleep(state):
    state["interventions_available"] = False
    state["world_speech_available"] = False
    state["god_camera"] = "asleep"


def enter(state, rules=None):
    """Choose incarnation once, after the settlement has shelter."""
    rules = _rules_of(rules)
    _require(state, "sky")
    if state["chosen"]:
        raise IncarnationError("incarnation can be chosen once")
    if not state["shelter"]:
        raise IncarnationError("the walk waits until the settlement has shelter")
    nxt = copy.deepcopy(state)
    nxt["phase"] = "walking"
    nxt["chosen"] = True
    nxt["hostility"] = int(rules["hostility"]["start"])
    nxt["last_hostility"] = nxt["hostility"]
    nxt["band"] = band_for(nxt["hostility"], rules)
    nxt["pawn_among_living"] = True
    nxt["in_passage"] = False
    nxt["living_tick_paused"] = False
    _asleep(nxt)
    _note(nxt, "enter", rules)
    _note(nxt, nxt["band"], rules)
    return nxt


def beat(state, walked=False, spoken_to=False, rules=None):
    """One moment among the living. May end in the crucifixion beat."""
    rules = _rules_of(rules)
    _require(state, "walking")
    nxt = copy.deepcopy(state)
    cap = _ending(rules, nxt["ending"])["hostilityCap"]
    before = nxt["band"]
    nxt["hostility"] = next_hostility(
        nxt["hostility"],
        nxt["faith"],
        nxt["fear"],
        nxt["prosperity"],
        nxt["shelter"],
        nxt["stores"],
        cap,
        walked=bool(walked),
        spoken_to=bool(spoken_to),
        rules=rules,
    )
    nxt["last_hostility"] = nxt["hostility"]
    nxt["band"] = band_for(nxt["hostility"], rules)
    if nxt["band"] != before and nxt["band"] in rules["lines"]:
        _note(nxt, nxt["band"], rules)
    if seizure_fires(nxt["hostility"], nxt["ending"], rules):
        return _crucifixion(nxt, rules)
    return nxt


def _crucifixion(state, rules):
    """One beat. The pawn is gone. The picture does not stay. Population does not drop."""
    before = state["fear"]
    state["phase"] = "crucifixion"
    state["pawn_among_living"] = False
    state["in_passage"] = False
    state["living_tick_paused"] = True
    state["band"] = "seized"
    state["fear"] = _clamp(before + int(rules["absenceFear"]), 0, 100)
    state["fear_raised_for_absence"] = True
    _asleep(state)
    state["events"].append(
        {
            "kind": "crucifixion",
            "graphic": False,
            "player_acted": False,
            "population_delta": 0,
            "fear_delta": int(rules["absenceFear"]),
            "fear_applied": state["fear"] - before,
            "needs_voice": False,
            "model_called": False,
        }
    )
    _note(state, "crucifixion", rules, population_delta=0)
    return state


def meet(state, person_id, role, rules=None):
    """Leaders and prophets may speak. The crowd does not, and no model is called."""
    rules = _rules_of(rules)
    _require(state, "walking")
    person_id = _safe_id(person_id)
    nxt = copy.deepcopy(state)
    if role == "crowd":
        return nxt
    if role not in SPEAKING_ROLES:
        raise IncarnationError("only a leader, a prophet, or the crowd can be met")
    _voice(nxt, person_id, role, "walking", rules["meetLines"][role])
    return nxt


def continue_on(state, rules=None):
    """Leave the crucifixion beat. The passage opens. Nothing is fought for."""
    rules = _rules_of(rules)
    _require(state, "crucifixion")
    nxt = copy.deepcopy(state)
    nxt["phase"] = "underworld"
    nxt["in_passage"] = True
    nxt["pawn_among_living"] = False
    nxt["living_tick_paused"] = True
    _asleep(nxt)
    _note(nxt, "underworld", rules)
    return nxt


def listen(state, figure_id, rules=None):
    """One line from someone already lost. Hearing them is not a price for the return."""
    rules = _rules_of(rules)
    _require(state, "underworld")
    figure_id = _safe_id(figure_id)
    figure = next((item for item in state["lost"] if item["id"] == figure_id), None)
    if figure is None:
        raise IncarnationError("that person is not in the passage")
    if figure_id in state["heard"]:
        raise IncarnationError("that person has already spoken")
    nxt = copy.deepcopy(state)
    nxt["heard"].append(figure_id)
    _voice(nxt, figure_id, figure["role"], "underworld", figure["line"])
    return nxt


def leave(state, rules=None):
    """Resurrection. The same human form returns to the center. The ending stays locked."""
    rules = _rules_of(rules)
    _require(state, "underworld")
    nxt = copy.deepcopy(state)
    tone = _ending(rules, nxt["ending"])
    back = tone["return"]
    nxt["phase"] = "returned"
    nxt["in_passage"] = False
    nxt["pawn_among_living"] = True
    nxt["living_tick_paused"] = False
    nxt["incarnate_returned"] = True
    nxt["departed_in_peace"] = False
    nxt["hostility"] = 0
    nxt["last_hostility"] = 0
    nxt["band"] = band_for(0, rules)
    nxt["faith"] = _clamp(nxt["faith"] + int(back["faith"]), 0, 100)
    nxt["fear"] = _clamp(nxt["fear"] + int(back["fear"]), 0, 100)
    nxt["prosperity"] = _clamp(nxt["prosperity"] + int(rules["prosperityOnReturn"]), 0, 100)
    nxt["wonder_restored"] = False
    if tone.get("easeClash"):
        nxt["clash_eased"] = True
    _asleep(nxt)
    _note(nxt, "returned", rules)
    if tone.get("prophetsOnReturn"):
        _voice(nxt, "prophet", "prophet", "return", rules["returnProphet"])
    return nxt


def ascend(state, rules=None):
    """Wake the god view. From the walk this is a peace. From the return it keeps the flag."""
    rules = _rules_of(rules)
    if state["phase"] == "walking":
        nxt = copy.deepcopy(state)
        nxt["last_hostility"] = nxt["hostility"]
        nxt["hostility"] = 0
        nxt["band"] = None
        nxt["phase"] = "ascended"
        nxt["pawn_among_living"] = False
        nxt["in_passage"] = False
        nxt["departed_in_peace"] = True
        nxt["living_tick_paused"] = False
        nxt["interventions_available"] = True
        nxt["world_speech_available"] = True
        nxt["god_camera"] = "awake"
        _note(nxt, "peace", rules)
        _note(nxt, "ascended", rules)
        return nxt
    if state["phase"] == "returned":
        nxt = copy.deepcopy(state)
        nxt["phase"] = "ascended"
        nxt["pawn_among_living"] = False
        nxt["in_passage"] = False
        nxt["living_tick_paused"] = False
        nxt["interventions_available"] = True
        nxt["world_speech_available"] = True
        nxt["god_camera"] = "awake"
        _note(nxt, "ascended", rules)
        return nxt
    raise IncarnationError(f"that action is not for the {state['phase']} phase")


def act(state, action, **kwargs):
    if action not in ACTIONS:
        raise IncarnationError(f"unknown action: {action}")
    if action == "enter":
        return enter(state)
    if action == "beat":
        return beat(state, walked=kwargs.get("walked", False), spoken_to=kwargs.get("spoken_to", False))
    if action == "meet":
        return meet(state, kwargs["person_id"], kwargs["role"])
    if action == "continue":
        return continue_on(state)
    if action == "listen":
        return listen(state, kwargs["figure_id"])
    if action == "leave":
        return leave(state)
    return ascend(state)
