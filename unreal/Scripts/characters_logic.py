"""Adam and Eve: needs, the day, shore paths, and dialogue hooks.

Pure Python. No Unreal import and no model call. A later voice reads the
hook this module returns and may hand a line back through accept_voice.
"""

import json
import math
from pathlib import Path

import garden_logic

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"

# Engine BasicShapes Cylinder is 100uu tall and 100uu across (radius 50).
CYLINDER_HEIGHT_UU = 100.0
CYLINDER_RADIUS_UU = 50.0

_CATALOG = None
_DIALOGUE = None


def catalog():
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = json.loads((DATA / "characters.json").read_text(encoding="utf-8"))
    return _CATALOG


def dialogue():
    global _DIALOGUE
    if _DIALOGUE is None:
        _DIALOGUE = json.loads((DATA / "dialogue.json").read_text(encoding="utf-8"))
    return _DIALOGUE


def _clamp(value, low, high):
    return max(low, min(high, value))


def phase_at(time_of_day, phases=None):
    """Match Person.PhaseAt. time_of_day is the fraction of the garden day."""
    phases = phases if phases is not None else catalog()["phases"]
    moment = float(time_of_day)
    for phase in phases:
        if moment < phase["until"]:
            return phase["id"]
    return phases[-1]["id"]


def shore_box():
    """River expanded by the shore margin. People walk outside this box."""
    river = garden_logic.RIVER
    margin = float(catalog()["shore_margin"])
    return {
        "x0": river["x0"] - margin,
        "x1": river["x1"] + margin,
        "y0": river["y0"] - margin,
        "y1": river["y1"] + margin,
    }


def in_river(x, y):
    river = garden_logic.RIVER
    return river["x0"] <= x <= river["x1"] and river["y0"] <= y <= river["y1"]


def in_water(x, y, box=None):
    box = shore_box() if box is None else box
    return box["x0"] <= x <= box["x1"] and box["y0"] <= y <= box["y1"]


def _dist(ax, ay, bx, by):
    return math.hypot(bx - ax, by - ay)


def segment_hits_box(start, goal, box):
    """True when the segment touches the closed box, including an end inside it."""
    x0, y0 = start
    x1, y1 = goal
    if in_water(x0, y0, box) or in_water(x1, y1, box):
        return True
    dx = x1 - x0
    dy = y1 - y0
    pairs = ((-dx, x0 - box["x0"]), (dx, box["x1"] - x0), (-dy, y0 - box["y0"]), (dy, box["y1"] - y0))
    u0, u1 = 0.0, 1.0
    for pi, qi in pairs:
        if pi == 0:
            if qi < 0:
                return False
            continue
        t = qi / pi
        if pi < 0:
            if t > u1:
                return False
            if t > u0:
                u0 = t
        else:
            if t < u0:
                return False
            if t < u1:
                u1 = t
    return True


def push_ashore(x, y, box=None):
    box = shore_box() if box is None else box
    if not in_water(x, y, box):
        return (x, y)
    candidates = (
        (box["x0"] - 1.0, y),
        (box["x1"] + 1.0, y),
        (x, box["y0"] - 1.0),
        (x, box["y1"] + 1.0),
    )
    return min(candidates, key=lambda point: _dist(x, y, point[0], point[1]))


def route(start, goal, box=None):
    """Walk the bank. A crossing goes around the nearer end of the river."""
    box = shore_box() if box is None else box
    start = push_ashore(start[0], start[1], box)
    goal = push_ashore(goal[0], goal[1], box)
    if _dist(start[0], start[1], goal[0], goal[1]) < 1.0:
        return [start]
    if not segment_hits_box(start, goal, box):
        return [start, goal]
    gap = float(catalog()["gate_gap"])
    west = box["x0"] - gap
    east = box["x1"] + gap

    def cost(gate):
        return abs(start[0] - gate) + abs(goal[0] - gate)

    gate = west if cost(west) <= cost(east) else east
    path = [start, (gate, start[1]), (gate, goal[1]), goal]
    # Drop a repeated point so a start already on the gate does not stall.
    compact = [path[0]]
    for point in path[1:]:
        if _dist(compact[-1][0], compact[-1][1], point[0], point[1]) >= 1.0:
            compact.append(point)
    return compact


def strength(person):
    age = person["age"]
    burden = (
        person["hunger"] * 0.18
        + person["thirst"] * 0.22
        + person["fatigue"] * 0.32
        + person["fever"] * 0.45
        + person["bleeding"] * 0.55
        + person["grief"] * 0.2
        + person["fear"] * 0.16
        + (18.0 if person["child_in_care"] else 0.0)
        + ((14.0 - age) * 1.5 if age < 14.0 else 0.0)
        + max(0.0, age - 30.0) * 0.15
    )
    return _clamp(100.0 - burden, 8.0, 100.0)


def speed_mps(person):
    return 0.45 + (1.85 - 0.45) * (strength(person) / 100.0)


def tired(person):
    return person["fatigue"] > catalog()["rates"]["slow_fatigue"]


def mesh_scale(person):
    radius_uu = person["radius_m"] * 100.0
    height_uu = person["height_m"] * 100.0
    xy = radius_uu / CYLINDER_RADIUS_UU
    z = height_uu / CYLINDER_HEIGHT_UU
    return (xy, xy, z)


def body_center_z(person):
    return person["height_m"] * 100.0 / 2.0


def _goal_for(person, garden):
    if person["coming"]:
        return person["goal"]
    phase = person["phase"]
    places = garden["places"]
    if phase == "eat":
        place = places["pot"]
    elif phase == "drink":
        place = places["cup"]
    elif phase == "work":
        place = places["work"]
    else:
        return (person["seat"][0], person["seat"][1])
    return (place[0] + person["offset"][0], place[1] + person["offset"][1])


def _retarget(person, garden):
    person["goal"] = _goal_for(person, garden)
    _set_path(person, person["goal"])


def _set_path(person, goal):
    person["goal"] = (float(goal[0]), float(goal[1]))
    person["path"] = route((person["x"], person["y"]), person["goal"])
    person["path_index"] = 0
    first = person["path"][0]
    if _dist(person["x"], person["y"], first[0], first[1]) < catalog()["waypoint_cm"]:
        person["path_index"] = 1


def _face(person, dx, dy):
    if dx * dx + dy * dy > 1.0:
        person["yaw"] = math.degrees(math.atan2(dy, dx))


def act_label(person):
    if person["coming"]:
        return "following the shore toward Elyon"
    phase = person["phase"]
    if phase == "wake":
        return "waking, seated at the fire"
    if phase == "eat":
        return "eating from the pot"
    if phase == "drink":
        return "drinking from the cup"
    if phase == "work":
        return "walking the shore to the work, then gathering"
    if phase == "rest":
        return "resting by the fire"
    return "following the shore toward Elyon"


def card_line(person):
    slow = " Tired. Moving slowly." if tired(person) else ""
    return (
        f"hunger {round(person['hunger'])}   thirst {round(person['thirst'])}   "
        f"fatigue {round(person['fatigue'])}\n"
        f"fever {round(person['fever'])}   bleeding {round(person['bleeding'])}   "
        f"grief {round(person['grief'])}   fear {round(person['fear'])}\n"
        f"age {round(person['age'])}   strength {round(strength(person))}"
        + slow
    )


def _on_enter(person, garden):
    relief = catalog()["relief"]
    home = garden["home"]
    phase = person["phase"]
    if phase == "eat":
        if home.get("meal", True):
            person["hunger"] = max(0.0, person["hunger"] - relief["meal"])
        else:
            person["hunger"] = max(0.0, person["hunger"] - relief["meal_without"])
            person["fear"] = min(100.0, person["fear"] + relief["fear_without_meal"])
    elif phase == "drink":
        drop = relief["water"] if home.get("water", True) else relief["water_without"]
        person["thirst"] = max(0.0, person["thirst"] - drop)
    elif phase == "rest":
        drop = relief["rest"] if home.get("bed", True) else relief["rest_without"]
        person["fatigue"] = max(0.0, person["fatigue"] - drop)
    _retarget(person, garden)


def _phase_now(person, time_of_day):
    natural = phase_at(time_of_day)
    if person["coming"]:
        return person["phase"]
    if natural == "rest":
        person["held"] = None
        return "rest"
    if person.get("held"):
        return person["held"]
    return natural


def _tick_body(person, dt):
    rates = catalog()["rates"]
    hunger_rate = rates["hunger_scarce"] if person["scarce"] else rates["hunger"]
    person["hunger"] = _clamp(person["hunger"] + hunger_rate * dt, 0.0, 100.0)
    person["thirst"] = _clamp(person["thirst"] + rates["thirst"] * dt, 0.0, 100.0)
    fatigue_rate = rates["fatigue_work"] if person["phase"] == "work" else rates["fatigue_idle"]
    person["fatigue"] = _clamp(person["fatigue"] + fatigue_rate * dt, 0.0, 100.0)
    if person["bleeding"] > 0.0:
        person["bleeding"] = max(0.0, person["bleeding"] - rates["bleeding_heal"] * dt)
    if person["fatigue"] > rates["tired_fatigue"]:
        person["fear"] = min(100.0, person["fear"] + rates["fear_when_tired"] * dt)


def _follow(person, dt):
    if not person["alive"]:
        person["moving"] = False
        return
    remaining = speed_mps(person) * 100.0 * dt
    waypoint = catalog()["waypoint_cm"]
    person["moving"] = False
    while remaining > 0.0 and person["path_index"] < len(person["path"]):
        tx, ty = person["path"][person["path_index"]]
        dx = tx - person["x"]
        dy = ty - person["y"]
        dist = math.hypot(dx, dy)
        if dist < waypoint:
            person["path_index"] += 1
            continue
        step = min(remaining, dist)
        person["x"] += dx / dist * step
        person["y"] += dy / dist * step
        _face(person, dx, dy)
        person["moving"] = True
        remaining -= step
    if person["path_index"] >= len(person["path"]):
        person["moving"] = False
        gx, gy = person["goal"]
        _face(person, gx - person["x"], gy - person["y"])
    if in_water(person["x"], person["y"]):
        person["x"], person["y"] = push_ashore(person["x"], person["y"])
        _set_path(person, person["goal"])


def tick_person(person, time_of_day, dt, garden):
    if dt < 0:
        raise ValueError("dt must be zero or positive")
    if not person["alive"]:
        person["moving"] = False
        return person
    _tick_body(person, dt)
    arrived = False
    if person["coming"]:
        gx, gy = person["goal"]
        if _dist(person["x"], person["y"], gx, gy) < catalog()["arrive_cm"]:
            person["coming"] = False
            arrived = True
    if not person["coming"]:
        nxt = _phase_now(person, time_of_day)
        if arrived or nxt != person["phase"]:
            person["phase"] = nxt
            _on_enter(person, garden)
    _follow(person, dt)
    return person


def hear(person, line, from_mind):
    text = (line or "").strip()
    if not text:
        return
    person["said"].append(text)
    if len(person["said"]) > 4:
        del person["said"][:-4]
    if from_mind and "eat" in text.lower():
        person["hunger"] = max(0.0, person["hunger"] - catalog()["rates"]["hear_eat_relief"])


def _scripted_line(person):
    node_id = person["scripted_node"]
    for node in dialogue()["nodes"]:
        if node["id"] == node_id:
            if node["speaker"] != person["id"]:
                raise ValueError(f"{node_id} belongs to {node['speaker']}, not {person['id']}")
            return node["lines"][0]
    raise KeyError(node_id)


def voice_request(person, heard=""):
    """Hook for a later local voice. This does not call a model."""
    return {
        "needs_voice": True,
        "model_called": False,
        "speaker": person["id"],
        "name": person["name"],
        "voice_id": person["voice_id"],
        "phase": person["phase"],
        "act": act_label(person),
        "coming": person["coming"],
        "hunger": person["hunger"],
        "thirst": person["thirst"],
        "fatigue": person["fatigue"],
        "strength": strength(person),
        "speed_mps": speed_mps(person),
        "tired": tired(person),
        "scripted_node": person["scripted_node"],
        "scripted_line": _scripted_line(person),
        "ambient_line": person["ambient"][person["phase"]],
        "heard": heard or "",
        "persona": f"{person['name']}, awake in the first garden",
        "reply_guide": (
            f"Speak as {person['name']} in the first garden, during {act_label(person)}. "
            "One or two sentences. You are that person. "
            "A later local voice may read this hook. This hook does not call one."
        ),
    }


def spoken_line(request, payload=None):
    if payload and str(payload.get("line") or "").strip():
        return {
            "line": str(payload["line"]).strip(),
            "source": "voice",
            "model_called": bool(payload.get("model_called", False)),
        }
    return {"line": request["scripted_line"], "source": "script", "model_called": False}


def _target_xy(target):
    if target is None:
        return (garden_logic.PLAYER["x"], garden_logic.PLAYER["y"])
    if isinstance(target, dict):
        return (float(target["x"]), float(target["y"]))
    return (float(target[0]), float(target[1]))


def apply_act(person, act, garden, target=None):
    """Local acts a later voice may return. stay does not serve a second meal."""
    known = catalog()["acts"]
    if act not in known:
        return {"accepted": False, "act": act, "reason": "unknown act"}
    if act == "come":
        person["coming"] = True
        _set_path(person, _target_xy(target))
        return {"accepted": True, "act": "come", "goal": person["goal"]}
    if act in ("stay", "resume"):
        person["coming"] = False
        person["held"] = None
        person["phase"] = phase_at(garden["time"])
        _retarget(person, garden)
        return {"accepted": True, "act": act, "phase": person["phase"]}
    person["coming"] = False
    person["held"] = "work"
    if person["phase"] != "work":
        person["phase"] = "work"
        _on_enter(person, garden)
    else:
        _retarget(person, garden)
    return {"accepted": True, "act": "work", "phase": "work"}


def address(garden, who, heard="", payload=None):
    person = find_person(garden, who)
    request = voice_request(person, heard)
    spoken = spoken_line(request, payload)
    hear(person, spoken["line"], from_mind=spoken["source"] == "voice")
    act_result = None
    if payload and payload.get("act"):
        act_result = apply_act(person, payload["act"], garden, payload.get("target"))
    return {"request": request, "spoken": spoken, "act": act_result}


def find_person(garden, who):
    key = (who or "").strip().lower()
    for person in garden["people"]:
        if person["id"] == key or person["name"].lower() == key:
            return person
    raise KeyError(who)


def _dry_point(x, y, label):
    if in_river(x, y) or in_water(x, y):
        raise ValueError(f"{label} sits in the water at {x}, {y}")


def make_person(spec, places):
    body = catalog()["body_defaults"]
    seat = (float(spec["seat"]["x"]), float(spec["seat"]["y"]))
    _dry_point(seat[0], seat[1], spec["id"])
    person = {
        "id": spec["id"],
        "name": spec["name"],
        "mass_kg": float(spec["mass_kg"]),
        "height_m": float(spec["height_m"]),
        "radius_m": float(spec["radius_m"]),
        "mesh": spec["mesh"],
        "label": spec["label"],
        "voice_id": spec["voice_id"],
        "scripted_node": spec["scripted_node"],
        "ambient": dict(spec["ambient"]),
        "seat": seat,
        "offset": (float(spec["offset"]["x"]), float(spec["offset"]["y"])),
        "x": seat[0],
        "y": seat[1],
        "yaw": 0.0,
        "hunger": float(body["hunger"]),
        "thirst": float(body["thirst"]),
        "fatigue": float(body["fatigue"]),
        "fever": float(body["fever"]),
        "bleeding": float(body["bleeding"]),
        "grief": float(body["grief"]),
        "fear": float(body["fear"]),
        "age": float(body["age"]),
        "child_in_care": bool(body["child_in_care"]),
        "trust": int(body["trust"]),
        "scarce": bool(body["scarce"]),
        "alive": True,
        "phase": "wake",
        "held": None,
        "coming": False,
        "moving": False,
        "goal": seat,
        "path": [seat],
        "path_index": 1,
        "said": [],
    }
    for place_name, place in places.items():
        _dry_point(place[0] + person["offset"][0], place[1] + person["offset"][1], f"{spec['id']} {place_name}")
    return person


def new_garden(time_of_day=None):
    data = catalog()
    moment = data["start_time"] if time_of_day is None else float(time_of_day)
    places = {name: (float(point["x"]), float(point["y"])) for name, point in data["places"].items()}
    for name, point in places.items():
        _dry_point(point[0], point[1], name)
    garden = {
        "map": data["map"],
        "time": moment,
        "day_seconds": int(data["day_seconds"]),
        "places": places,
        "home": {"meal": True, "water": True, "bed": True},
        "people": [make_person(spec, places) for spec in data["people"]],
    }
    for person in garden["people"]:
        person["phase"] = phase_at(moment)
        _retarget(person, garden)
    return garden


def advance(garden, dt):
    if dt < 0:
        raise ValueError("dt must be zero or positive")
    garden["time"] = (garden["time"] + float(dt) / garden["day_seconds"]) % 1.0
    for person in garden["people"]:
        tick_person(person, garden["time"], dt, garden)
    return garden


def actor_spec(person):
    scale = mesh_scale(person)
    line = person["said"][-1] if person["said"] else ""
    tags = [person["id"], person["phase"], f"mass:{int(round(person['mass_kg']))}"]
    if person["coming"]:
        tags.append("coming")
    if line:
        tags.append(line[:80])
    return {
        "label": person["label"],
        "kind": "static",
        "mesh": garden_logic.MESH[person["mesh"]],
        "x": person["x"],
        "y": person["y"],
        "z": body_center_z(person),
        "yaw": person["yaw"],
        "scale": scale,
        "tags": tags,
    }


def actor_specs(garden):
    return [actor_spec(person) for person in garden["people"]]
