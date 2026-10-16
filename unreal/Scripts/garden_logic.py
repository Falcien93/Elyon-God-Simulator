"""Day 1 garden layout. Pure Python so tests can run without Unreal."""

MAP_PATH = "/Game/Maps/Day1_Garden"
SEED = 1101

GARDEN_HALF = 4000.0
RIVER = {"x0": -4500.0, "x1": 4500.0, "y0": 800.0, "y1": 1600.0}
ADAM = {"x": 400.0, "y": -400.0, "z": 110.0, "clear": 400.0}
PLAYER = {"x": -800.0, "y": -1600.0, "z": 120.0}

COUNTS = {"tree": 20, "rock": 16, "plant": 64}

# Free meshes, first match wins. The last path is the engine fallback.
MESH_CANDIDATES = {
    "terrain": ["/Engine/BasicShapes/Plane"],
    "tree": [
        "/Game/Fab/Foliage/SM_Tree",
        "/Game/StarterContent/Props/SM_Bush",
        "/Engine/BasicShapes/Cone",
    ],
    "rock": [
        "/Game/Fab/Foliage/SM_Rock",
        "/Game/StarterContent/Props/SM_Rock",
        "/Engine/BasicShapes/Sphere",
    ],
    "plant": [
        "/Game/Fab/Foliage/SM_Plant",
        "/Game/StarterContent/Props/SM_Bush",
        "/Engine/BasicShapes/Cone",
    ],
    "river": ["/Engine/BasicShapes/Cube"],
    "adam": ["/Engine/BasicShapes/Sphere"],
}

MATERIAL_CANDIDATES = {
    "grass": [
        "/Game/Fab/Foliage/M_Grass",
        "/Game/StarterContent/Materials/M_Ground_Grass",
        "/Game/Materials/M_Elyon_Grass",
    ],
    "leaf": [
        "/Game/Fab/Foliage/M_Leaf",
        "/Game/StarterContent/Materials/M_Ground_Moss",
        "/Game/Materials/M_Elyon_Leaf",
    ],
    "rock": [
        "/Game/StarterContent/Materials/M_Rock_Basalt",
        "/Game/Materials/M_Elyon_Rock",
    ],
    "water": [
        "/Game/StarterContent/Materials/M_Water_Lake",
        "/Game/Materials/M_Elyon_Water",
    ],
}

ROLE_MATERIAL = {
    "terrain": "grass",
    "tree": "leaf",
    "plant": "leaf",
    "rock": "rock",
    "river": "water",
}

AUTHORED_MATERIALS = {
    "/Game/Materials/M_Elyon_Grass": {"color": (0.16, 0.34, 0.08, 1.0), "roughness": 0.92},
    "/Game/Materials/M_Elyon_Leaf": {"color": (0.22, 0.4, 0.08, 1.0), "roughness": 0.72},
    "/Game/Materials/M_Elyon_Rock": {"color": (0.35, 0.28, 0.2, 1.0), "roughness": 0.88},
    "/Game/Materials/M_Elyon_Water": {"color": (0.05, 0.22, 0.24, 1.0), "roughness": 0.08},
}


def resolve_candidate(candidates, available):
    for path in candidates:
        if path in available:
            return path
    return candidates[-1]


def light_state(dawn):
    if dawn:
        return {
            "name": "dawn",
            "sun_intensity": 8.0,
            "sun_color": (1.0, 0.55, 0.25, 1.0),
            "sky_color": (1.0, 0.78, 0.55, 1.0),
            "fog_color": (0.62, 0.36, 0.16, 1.0),
            "sun_pitch": -18.0,
            "sun_yaw": 35.0,
            "skylight_intensity": 0.45,
            "fog_density": 0.002,
            "fog_height_falloff": 0.12,
            "fog_start_distance": 3500.0,
            "fog_max_opacity": 0.35,
            "exposure_min_ev": 12.0,
            "exposure_max_ev": 14.0,
            "exposure_bias": 0.35,
        }
    return {
        "name": "darkness",
        "sun_intensity": 0.02,
        "sun_color": (0.05, 0.07, 0.14, 1.0),
        "sky_color": (0.02, 0.03, 0.06, 1.0),
        "fog_color": (0.02, 0.025, 0.04, 1.0),
        "sun_pitch": -4.0,
        "sun_yaw": 35.0,
        "skylight_intensity": 0.02,
        "fog_density": 0.02,
        "fog_height_falloff": 0.08,
        "fog_start_distance": 400.0,
        "fog_max_opacity": 0.8,
        "exposure_min_ev": -1.0,
        "exposure_max_ev": 2.0,
        "exposure_bias": 0.0,
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


def _prop(label, kind, x, y, z, yaw=0.0, **extra):
    spec = {"label": label, "kind": kind, "x": x, "y": y, "z": z, "yaw": yaw}
    spec.update(extra)
    return spec


def _shape_scale(role, scale, mesh_path):
    if not mesh_path.startswith("/Engine/BasicShapes/"):
        return (scale, scale, scale)
    if role == "terrain":
        return (800.0, 800.0, 1.0)
    if role == "tree":
        return (scale, scale, scale * 3.0)
    if role == "rock":
        return (scale, scale * 0.85, scale * 0.55)
    if role == "plant":
        return (scale * 0.35, scale * 0.35, scale * 0.55)
    if role == "river":
        return (90.0, 8.0, 0.08)
    if role == "adam":
        return (1.1, 1.1, 2.0)
    return (scale, scale, scale)


def _foliage(label, role, x, y, z, yaw=0.0, scatter_scale=1.0):
    return {
        "label": label,
        "kind": "static",
        "role": role,
        "x": x,
        "y": y,
        "z": z,
        "yaw": yaw,
        "scatter_scale": scatter_scale,
    }


def plan_level(dawn=True):
    light = light_state(dawn)
    actors = [
        _foliage("Elyon.Terrain", "terrain", 0.0, 0.0, 0.0),
        _prop("Elyon.Sun", "directional_light", 0.0, 0.0, 4000.0, pitch=light["sun_pitch"], yaw=light["sun_yaw"]),
        _prop("Elyon.SkyLight", "sky_light", 0.0, 0.0, 500.0),
        _prop("Elyon.SkyAtmosphere", "sky_atmosphere", 0.0, 0.0, 0.0),
        _prop("Elyon.Fog", "fog", 0.0, 0.0, 0.0),
        _prop("Elyon.Clouds", "clouds", 0.0, 0.0, 0.0),
        _prop("Elyon.Exposure", "post_process", 0.0, 0.0, 200.0),
        _foliage("Elyon.River", "river", 0.0, 1200.0, 4.0),
        _prop("Elyon.PlayerStart", "player_start", PLAYER["x"], PLAYER["y"], PLAYER["z"], yaw=90.0),
        _foliage("Elyon.Adam", "adam", ADAM["x"], ADAM["y"], ADAM["z"]),
        _prop("Elyon.LetThereBeLight", "marker", 0.0, 0.0, 300.0, state=light["name"]),
    ]
    trees = scatter("tree", COUNTS["tree"], SEED)
    rocks = scatter("rock", COUNTS["rock"], SEED + 1)
    plants = scatter("plant", COUNTS["plant"], SEED + 2)
    for index, item in enumerate(trees, start=1):
        actors.append(_foliage(f"Elyon.Tree.{index:02d}", "tree", item["x"], item["y"], 40.0, item["yaw"], item["scale"]))
    for index, item in enumerate(rocks, start=1):
        actors.append(_foliage(f"Elyon.Rock.{index:02d}", "rock", item["x"], item["y"], 20.0, item["yaw"], item["scale"]))
    for index, item in enumerate(plants, start=1):
        actors.append(_foliage(f"Elyon.Plant.{index:02d}", "plant", item["x"], item["y"], 8.0, item["yaw"], item["scale"]))
    return {"map": MAP_PATH, "dawn": bool(dawn), "light": light, "actors": actors}


def planned_labels(plan):
    return [actor["label"] for actor in plan["actors"]]


def stale_labels(existing, planned):
    keep = set(planned)
    return sorted(label for label in existing if label.startswith("Elyon.") and label not in keep)
