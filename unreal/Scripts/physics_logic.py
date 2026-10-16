"""Chaos bodies, river spline, wind bend, and the God hand. Pure Python."""

import math

from garden_logic import ADAM, RIVER, scatter

BODY = {
    "rock": {
        "mass": 120.0,
        "linear_damping": 0.35,
        "angular_damping": 0.55,
        "floats": False,
        "collision": "PhysicsActor",
        "pontoon_radius": 0.0,
    },
    "log": {
        "mass": 22.0,
        "linear_damping": 1.1,
        "angular_damping": 1.0,
        "floats": True,
        "collision": "PhysicsActor",
        "pontoon_radius": 48.0,
    },
    "fruit": {
        "mass": 0.2,
        "linear_damping": 0.25,
        "angular_damping": 0.35,
        "floats": True,
        "collision": "PhysicsActor",
        "pontoon_radius": 14.0,
    },
}

DYNAMIC_KINDS = ("rock", "log", "fruit")
LOG_COUNT = 8
FRUIT_COUNT = 12
LOG_Z = 80.0
FRUIT_Z = 160.0
FRUIT_CLUSTER = (-200.0, -900.0)

BEND_RADIUS = 280.0
BEND_MAX_PITCH = 28.0

GRAB_REACH = 8000.0
GRAB_FACING_DOT = 0.65
HOLD_DISTANCE = 600.0
HOLD_LIFT = 120.0
LIFT_CAP = 960.0
THROW_SPEED = 1800.0
PUSH_IMPULSE = 4000.0
DIVINE_RADIUS = 900.0
DIVINE_STRENGTH = 25000.0

RIVER_WIDTH = 700.0
RIVER_DEPTH = 180.0
RIVER_Z = 30.0

GOD_CAMERA = {"x": -1800.0, "y": -2200.0, "z": 1800.0}
HANDLE = {
    "linear_damping": 200.0,
    "linear_stiffness": 700.0,
    "angular_damping": 500.0,
    "angular_stiffness": 800.0,
    "interpolation_speed": 30.0,
}

# Action name -> input key. DefaultInput.ini must use the same keys.
KEYS = {
    "grab": "LeftMouseButton",
    "throw": "RightMouseButton",
    "push": "F",
    "lift": "Q",
    "lower": "Z",
    "divine": "MiddleMouseButton",
}

ACTIONS = (
    ("GodGrab", "grab"),
    ("GodThrow", "throw"),
    ("GodPush", "push"),
    ("GodLift", "lift"),
    ("GodLower", "lower"),
    ("DivineForce", "divine"),
)

GRASS_WIND_PATHS = (
    "/Engine/Functions/Engine_MaterialFunctions01/Texturing/SimpleGrassWind",
    "/Engine/Functions/Engine_MaterialFunctions02/WorldPositionOffset/SimpleGrassWind",
)


def body_spec(kind):
    return dict(BODY[kind])


def classify_label(label):
    if not isinstance(label, str):
        return None
    if label.startswith("Elyon.Rock."):
        return "rock"
    if label.startswith("Elyon.Log."):
        return "log"
    if label.startswith("Elyon.Fruit."):
        return "fruit"
    if label.startswith("Elyon.Plant."):
        return "plant"
    if label.startswith("Elyon.Tree."):
        return "tree"
    return None


def _clear(x, y):
    in_river = RIVER["x0"] <= x <= RIVER["x1"] and RIVER["y0"] <= y <= RIVER["y1"]
    if in_river:
        return False
    dx = x - ADAM["x"]
    dy = y - ADAM["y"]
    return dx * dx + dy * dy >= ADAM["clear"] * ADAM["clear"]


def log_placements():
    placed = []
    for index, item in enumerate(scatter("log", LOG_COUNT, 2202), start=1):
        scale = item["scale"]
        placed.append(
            {
                "label": f"Elyon.Log.{index:02d}",
                "kind": "log",
                "mesh": "cylinder",
                "x": item["x"],
                "y": item["y"],
                "z": LOG_Z,
                "pitch": 80.0,
                "yaw": item["yaw"],
                "scale": (
                    round(scale * 0.35, 3),
                    round(scale * 0.35, 3),
                    round(scale * 1.8, 3),
                ),
            }
        )
    return placed


def fruit_placements():
    """Loose elevated cluster so the fruit falls and stacks."""
    from garden_logic import _rng

    origin_x, origin_y = FRUIT_CLUSTER
    rng = _rng(3303)
    placed = []
    guard = 0
    while len(placed) < FRUIT_COUNT and guard < FRUIT_COUNT * 80:
        guard += 1
        angle = rng() * math.pi * 2.0
        dist = 30.0 + rng() * 180.0
        x = origin_x + math.cos(angle) * dist
        y = origin_y + math.sin(angle) * dist
        if not _clear(x, y):
            continue
        if any((x - item["x"]) ** 2 + (y - item["y"]) ** 2 < 35.0 ** 2 for item in placed):
            continue
        scale = round(0.18 + rng() * 0.08, 3)
        placed.append(
            {
                "label": f"Elyon.Fruit.{len(placed) + 1:02d}",
                "kind": "fruit",
                "mesh": "sphere",
                "x": round(x, 2),
                "y": round(y, 2),
                "z": FRUIT_Z,
                "pitch": 0.0,
                "yaw": round(rng() * 360.0, 2),
                "scale": (scale, scale, scale),
            }
        )
    return placed


def managed_labels():
    labels = [item["label"] for item in log_placements()]
    labels.extend(item["label"] for item in fruit_placements())
    labels.extend(("Elyon.Wind", "Elyon.WaterRiver", "Elyon.GodCamera"))
    return labels


def river_spline_points():
    y = (RIVER["y0"] + RIVER["y1"]) * 0.5
    xs = (-4000.0, -1500.0, 1500.0, 4000.0)
    return [
        {
            "x": x,
            "y": y,
            "z": RIVER_Z,
            "width": RIVER_WIDTH,
            "depth": RIVER_DEPTH,
            "key": float(index),
        }
        for index, x in enumerate(xs)
    ]


def wind_state():
    return {
        "label": "Elyon.Wind",
        "x": 0.0,
        "y": 0.0,
        "z": 1500.0,
        "strength": 0.35,
        "speed": 0.45,
        "min_gust": 0.1,
        "max_gust": 0.4,
        "yaw": 40.0,
        "radius": 0.0,
    }


def bend_for_contact(plant_xy, contact_xy, radius=BEND_RADIUS):
    dx = float(plant_xy[0]) - float(contact_xy[0])
    dy = float(plant_xy[1]) - float(contact_xy[1])
    dist = math.hypot(dx, dy)
    if radius <= 0.0 or dist >= radius:
        return 0.0
    return 1.0 - dist / radius


def plant_bend_pitch(weight):
    clamped = min(1.0, max(0.0, float(weight)))
    return clamped * BEND_MAX_PITCH


def bend_plants(plants, contacts, radius=BEND_RADIUS):
    bent = []
    for plant in plants:
        location = plant["location"]
        xy = (float(location[0]), float(location[1]))
        weight = 0.0
        for contact in contacts:
            weight = max(weight, bend_for_contact(xy, contact, radius))
        yaw = plant.get("base_yaw", plant.get("yaw", 0.0))
        bent.append(
            {
                "label": plant["label"],
                "weight": weight,
                "pitch": plant_bend_pitch(weight),
                "yaw": float(yaw),
            }
        )
    return bent


def look_rotation(origin, target):
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    dz = target[2] - origin[2]
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw


def god_camera_spec():
    origin = (GOD_CAMERA["x"], GOD_CAMERA["y"], GOD_CAMERA["z"])
    pitch, yaw = look_rotation(origin, (0.0, 0.0, 80.0))
    return {
        "label": "Elyon.GodCamera",
        "x": origin[0],
        "y": origin[1],
        "z": origin[2],
        "pitch": pitch,
        "yaw": yaw,
    }


def new_session():
    return {"held": None, "previous_keys": set(), "hold_lift": 0.0}


def _xyz(value):
    return (float(value[0]), float(value[1]), float(value[2]))


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _length(value):
    return math.sqrt(_dot(value, value))


def _norm(value):
    length = _length(value)
    if length <= 1e-8:
        return (0.0, 0.0, 0.0)
    return (value[0] / length, value[1] / length, value[2] / length)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def nearest_along_view(origin, forward, bodies, reach=GRAB_REACH, min_dot=GRAB_FACING_DOT):
    start = _xyz(origin)
    facing = _norm(_xyz(forward))
    best = None
    best_dist = None
    for body in bodies:
        if classify_label(body.get("label")) not in DYNAMIC_KINDS:
            continue
        delta = _sub(_xyz(body["location"]), start)
        dist = _length(delta)
        if dist < 1.0 or dist > reach:
            continue
        if _dot(_norm(delta), facing) < min_dot:
            continue
        if best_dist is None or dist < best_dist:
            best = body
            best_dist = dist
    return best


def hold_target(origin, forward, distance=HOLD_DISTANCE, lift=0.0):
    start = _xyz(origin)
    facing = _norm(_xyz(forward))
    return (
        start[0] + facing[0] * distance,
        start[1] + facing[1] * distance,
        start[2] + facing[2] * distance + float(lift),
    )


def throw_velocity(forward, speed=THROW_SPEED):
    facing = _norm(_xyz(forward))
    return (facing[0] * speed, facing[1] * speed, facing[2] * speed)


def push_impulse(forward, strength=PUSH_IMPULSE):
    facing = _norm(_xyz(forward))
    return (facing[0] * strength, facing[1] * strength, facing[2] * strength)


def divine_force(origin, bodies, radius=DIVINE_RADIUS, strength=DIVINE_STRENGTH):
    """Linear falloff. Strength is zero at the radius and full on top of the click."""
    start = _xyz(origin)
    impulses = []
    for body in bodies:
        label = body.get("label")
        if classify_label(label) not in DYNAMIC_KINDS:
            continue
        delta = _sub(_xyz(body["location"]), start)
        dist = _length(delta)
        if dist < 1.0 or dist >= radius:
            continue
        falloff = 1.0 - dist / radius
        direction = _norm(delta)
        magnitude = strength * falloff
        impulses.append(
            {
                "label": label,
                "falloff": falloff,
                "impulse": (
                    direction[0] * magnitude,
                    direction[1] * magnitude,
                    direction[2] * magnitude,
                ),
            }
        )
    return impulses


def step_god(ue, state, view):
    """Advance one God-hand frame. `ue` is unused so tests can pass None."""
    del ue
    keys = set(view.get("keys") or ())
    previous = set(state.get("previous_keys") or ())
    pressed = keys - previous
    origin = _xyz(view["location"])
    forward = _xyz(view["forward"])
    bodies = list(view.get("bodies") or ())
    actions = []

    if "divine" in pressed:
        if state.get("held"):
            actions.append({"op": "release", "label": state["held"]})
            state["held"] = None
            state["hold_lift"] = 0.0
        actions.append(
            {
                "op": "divine",
                "origin": origin,
                "radius": DIVINE_RADIUS,
                "strength": DIVINE_STRENGTH,
                "falloff": "RIF_LINEAR",
                "impulses": divine_force(origin, bodies),
            }
        )
    elif "throw" in pressed and state.get("held"):
        actions.append(
            {
                "op": "throw",
                "label": state["held"],
                "velocity": throw_velocity(forward),
            }
        )
        state["held"] = None
        state["hold_lift"] = 0.0
    elif "grab" in keys:
        if not state.get("held"):
            target = nearest_along_view(origin, forward, bodies)
            if target is not None:
                state["held"] = target["label"]
                state["hold_lift"] = 0.0
                actions.append(
                    {
                        "op": "grab",
                        "label": target["label"],
                        "location": _xyz(target["location"]),
                    }
                )
        if state.get("held"):
            if "lift" in keys:
                state["hold_lift"] = min(LIFT_CAP, float(state.get("hold_lift") or 0.0) + HOLD_LIFT)
            if "lower" in keys:
                state["hold_lift"] = max(0.0, float(state.get("hold_lift") or 0.0) - HOLD_LIFT)
            actions.append(
                {
                    "op": "move",
                    "label": state["held"],
                    "location": hold_target(origin, forward, HOLD_DISTANCE, state.get("hold_lift") or 0.0),
                }
            )
    elif state.get("held"):
        actions.append({"op": "release", "label": state["held"]})
        state["held"] = None
        state["hold_lift"] = 0.0

    if "push" in pressed:
        label = state.get("held")
        if not label:
            target = nearest_along_view(origin, forward, bodies)
            label = target["label"] if target else None
        if label:
            actions.append({"op": "push", "label": label, "impulse": push_impulse(forward)})

    state["previous_keys"] = set(keys)
    return actions
