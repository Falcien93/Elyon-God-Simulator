"""Day 1 garden layout. Pure Python so tests can run without Unreal."""

MAP_PATH = "/Game/Maps/Day1_Garden"
SEED = 1101

GARDEN_HALF = 4000.0
RIVER = {"x0": -4500.0, "x1": 4500.0, "y0": 800.0, "y1": 1600.0}
ADAM = {"x": 400.0, "y": -400.0, "z": 110.0, "clear": 400.0}
PLAYER = {"x": -800.0, "y": -1600.0, "z": 120.0}

MESH = {
    "plane": "/Engine/BasicShapes/Plane",
    "cube": "/Engine/BasicShapes/Cube",
    "sphere": "/Engine/BasicShapes/Sphere",
    "cone": "/Engine/BasicShapes/Cone",
    "cylinder": "/Engine/BasicShapes/Cylinder",
}

COUNTS = {"tree": 24, "rock": 12, "plant": 36}


def light_state(dawn):
    if dawn:
        return {
            "name": "dawn",
            "sun_intensity": 10.0,
            "sun_color": (1.0, 0.93, 0.78, 1.0),
            "sky_color": (1.0, 0.96, 0.90, 1.0),
            "fog_color": (0.75, 0.82, 0.95, 1.0),
            "sun_pitch": -48.0,
            "sun_yaw": 25.0,
            "skylight_intensity": 1.0,
            "fog_density": 0.015,
        }
    return {
        "name": "darkness",
        "sun_intensity": 0.02,
        "sun_color": (0.05, 0.07, 0.14, 1.0),
        "sky_color": (0.02, 0.03, 0.06, 1.0),
        "fog_color": (0.01, 0.015, 0.03, 1.0),
        "sun_pitch": -4.0,
        "sun_yaw": 25.0,
        "skylight_intensity": 0.02,
        "fog_density": 0.08,
    }


def _rng(seed):
    state = seed & 0xFFFFFFFF

    def nxt():
        nonlocal state
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        return state / 4294967296.0

    return nxt


def _blocked(x, y):
    in_river = RIVER["x0"] <= x <= RIVER["x1"] and RIVER["y0"] <= y <= RIVER["y1"]
    if in_river:
        return True
    dx = x - ADAM["x"]
    dy = y - ADAM["y"]
    return dx * dx + dy * dy < ADAM["clear"] * ADAM["clear"]


def scatter(kind, count, seed):
    rng = _rng(seed)
    span = GARDEN_HALF * 0.8
    placed = []
    guard = 0
    while len(placed) < count and guard < count * 50:
        guard += 1
        x = (rng() * 2.0 - 1.0) * span
        y = (rng() * 2.0 - 1.0) * span
        if _blocked(x, y):
            continue
        placed.append(
            {
                "kind": kind,
                "x": round(x, 2),
                "y": round(y, 2),
                "yaw": round(rng() * 360.0, 2),
                "scale": round(0.7 + rng() * 1.1, 3),
            }
        )
    return placed


def _static(label, mesh, x, y, z, scale, yaw=0.0):
    sx, sy, sz = scale if isinstance(scale, tuple) else (scale, scale, scale)
    return {
        "label": label,
        "kind": "static",
        "mesh": MESH[mesh],
        "x": x,
        "y": y,
        "z": z,
        "yaw": yaw,
        "scale": (sx, sy, sz),
    }


def plan_level(dawn=True):
    light = light_state(dawn)
    actors = [
        _static("Elyon.Ground", "plane", 0.0, 0.0, 0.0, (800.0, 800.0, 1.0)),
        {
            "label": "Elyon.Sun",
            "kind": "directional_light",
            "x": 0.0,
            "y": 0.0,
            "z": 4000.0,
            "pitch": light["sun_pitch"],
            "yaw": light["sun_yaw"],
        },
        {"label": "Elyon.SkyLight", "kind": "sky_light", "x": 0.0, "y": 0.0, "z": 500.0},
        {"label": "Elyon.SkyAtmosphere", "kind": "sky_atmosphere", "x": 0.0, "y": 0.0, "z": 0.0},
        {"label": "Elyon.Fog", "kind": "fog", "x": 0.0, "y": 0.0, "z": 0.0},
        {"label": "Elyon.Clouds", "kind": "clouds", "x": 0.0, "y": 0.0, "z": 0.0},
        _static("Elyon.River", "cube", 0.0, 1200.0, 4.0, (90.0, 8.0, 0.08)),
        {"label": "Elyon.PlayerStart", "kind": "player_start", "x": PLAYER["x"], "y": PLAYER["y"], "z": PLAYER["z"], "yaw": 90.0},
        _static("Elyon.Adam", "sphere", ADAM["x"], ADAM["y"], ADAM["z"], (1.1, 1.1, 2.0)),
        {"label": "Elyon.LetThereBeLight", "kind": "marker", "x": 0.0, "y": 0.0, "z": 300.0, "state": light["name"]},
    ]
    trees = scatter("tree", COUNTS["tree"], SEED)
    rocks = scatter("rock", COUNTS["rock"], SEED + 1)
    plants = scatter("plant", COUNTS["plant"], SEED + 2)
    for index, item in enumerate(trees, start=1):
        actors.append(_static(f"Elyon.Tree.{index:02d}", "cone", item["x"], item["y"], 80.0, (item["scale"], item["scale"], item["scale"] * 3.0), item["yaw"]))
    for index, item in enumerate(rocks, start=1):
        actors.append(_static(f"Elyon.Rock.{index:02d}", "cube", item["x"], item["y"], 25.0, (item["scale"], item["scale"] * 0.8, item["scale"] * 0.5), item["yaw"]))
    for index, item in enumerate(plants, start=1):
        actors.append(_static(f"Elyon.Plant.{index:02d}", "cone", item["x"], item["y"], 15.0, (item["scale"] * 0.35, item["scale"] * 0.35, item["scale"] * 0.6), item["yaw"]))
    return {"map": MAP_PATH, "dawn": bool(dawn), "light": light, "actors": actors}


def planned_labels(plan):
    return [actor["label"] for actor in plan["actors"]]


def stale_labels(existing, planned):
    keep = set(planned)
    return sorted(label for label in existing if label.startswith("Elyon.") and label not in keep)
