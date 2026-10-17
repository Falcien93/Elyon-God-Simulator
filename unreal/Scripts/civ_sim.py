"""Pure-Python sketch of the post-Day-6 civilizations layer.

The crowd scores build, trade, and clash. Leaders and prophets only mark
needs_voice. This module does not import Unreal and does not call a model.
"""

KNOWN_ENDINGS = ("harmony", "exile", "wonder", "order")

# Goal order for a settlement. Clash is dropped when the ending forbids it.
GOAL_ORDER = ("shelter", "trade", "clash")

# Tie-break favors earlier acts when scores match.
ACTION_RANK = {"build": 0, "trade": 1, "clash": 2}


def resolve_ending(ending_id, silence=False, locked=None):
    """Mirror js/sim.js resolveEnding. The first ending sticks.

    ending:hands becomes wonder when silence was kept, otherwise exile.
    Unknown ids resolve to None and do not lock.
    """
    if locked:
        return locked
    resolved = ending_id
    if ending_id == "hands":
        resolved = "wonder" if silence else "exile"
    if resolved not in KNOWN_ENDINGS:
        return None
    return resolved


def new_tribe(ending, name="tribe", **overrides):
    if ending not in KNOWN_ENDINGS:
        raise ValueError(f"unknown ending: {ending}")
    tribe = {
        "name": name,
        "ending": ending,
        "faith": 50,
        "prosperity": 40,
        "fear": 20,
        "population": 40,
        "shelter": False,
    }
    tribe.update(overrides)
    tribe["ending"] = ending
    return tribe


def _clamp(value, lo, hi):
    return max(lo, min(hi, int(round(value))))


def apply_intervention(tribe, kind):
    """Change faith, prosperity, fear, and population. Returns the tribe."""
    faith = tribe["faith"]
    if kind == "flood":
        tribe["faith"] = _clamp(faith + (6 if faith >= 40 else -6), 0, 100)
        tribe["prosperity"] = _clamp(tribe["prosperity"] - 18, 0, 100)
        tribe["fear"] = _clamp(tribe["fear"] + 22, 0, 100)
        tribe["population"] = max(1, tribe["population"] - 8)
    elif kind == "blessing":
        tribe["faith"] = _clamp(faith + 12, 0, 100)
        tribe["prosperity"] = _clamp(tribe["prosperity"] + 16, 0, 100)
        tribe["fear"] = _clamp(tribe["fear"] - 10, 0, 100)
        tribe["population"] = tribe["population"] + 2
    elif kind == "punishment":
        tribe["faith"] = _clamp(faith + (6 if faith >= 55 else -8), 0, 100)
        tribe["prosperity"] = _clamp(tribe["prosperity"] - 12, 0, 100)
        tribe["fear"] = _clamp(tribe["fear"] + 18, 0, 100)
        tribe["population"] = max(1, tribe["population"] - 1)
    elif kind == "divine_force":
        # Awe when faith is already high, terror when it is low.
        tribe["faith"] = _clamp(faith + (8 if faith >= 50 else -8), 0, 100)
        tribe["prosperity"] = _clamp(tribe["prosperity"] - 4, 0, 100)
        tribe["fear"] = _clamp(tribe["fear"] + 14, 0, 100)
    else:
        raise ValueError(f"unknown intervention: {kind}")
    return tribe


def settlement_goals(tribe):
    """Shelter, then trade, then clash. Order never lists clash."""
    goals = ["shelter", "trade"]
    if tribe["ending"] != "order":
        goals.append("clash")
    return goals


def utilities(tribe):
    """Score the three acts. Order cannot clash. Harmony almost never does."""
    faith = tribe["faith"]
    prosperity = tribe["prosperity"]
    fear = tribe["fear"]
    ending = tribe["ending"]
    sheltered = bool(tribe.get("shelter"))

    build = 30 + (0 if sheltered else 40) + max(0, 50 - prosperity) * 0.4
    trade = (25 if sheltered else 0) + prosperity * 0.15 + faith * 0.05
    clash = fear * 0.5 + max(0, 40 - faith) * 0.4 - prosperity * 0.15

    if ending == "harmony":
        build += 6
        trade += 8
        clash -= 30
    elif ending == "wonder":
        trade += 6
        clash -= 18
    elif ending == "exile":
        build += 4
        trade += 2
        clash += 6
    elif ending == "order":
        build += 12
        clash = -1000

    return {"build": build, "trade": trade, "clash": clash}


def choose(tribe):
    scores = utilities(tribe)
    return max(scores, key=lambda name: (scores[name], -ACTION_RANK[name]))


def found_settlement(tribe, name):
    """Exile founds east of the garden. Every other ending stays inside it."""
    region = "east" if tribe["ending"] == "exile" else "garden"
    return {
        "name": name,
        "region": region,
        "ending": tribe["ending"],
        "goals": settlement_goals(tribe),
    }


def voice_event(tribe, role):
    return {
        "needs_voice": True,
        "role": role,
        "tribe": tribe["name"],
        "model_called": False,
    }


def tick(tribe):
    """One utility step. May append leader or prophet voice events."""
    if not tribe.get("shelter"):
        action = "build"
    else:
        action = choose(tribe)

    if action == "build":
        tribe["shelter"] = True
        tribe["prosperity"] = _clamp(tribe["prosperity"] + 2, 0, 100)
    elif action == "trade":
        tribe["prosperity"] = _clamp(tribe["prosperity"] + 3, 0, 100)
        tribe["faith"] = _clamp(tribe["faith"] + 1, 0, 100)
    elif action == "clash":
        tribe["population"] = max(1, tribe["population"] - 2)
        tribe["fear"] = _clamp(tribe["fear"] + 4, 0, 100)
        tribe["prosperity"] = _clamp(tribe["prosperity"] - 3, 0, 100)

    events = []
    if tribe.get("shelter") and action in ("build", "trade", "clash"):
        events.append(voice_event(tribe, "leader"))
    if tribe["ending"] == "wonder" and tribe["faith"] >= 60:
        events.append(voice_event(tribe, "prophet"))
    return action, events
