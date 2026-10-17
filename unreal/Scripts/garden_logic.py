"""Day 1 garden layout. Pure Python so tests can run without Unreal."""

import math

MAP_PATH = "/Game/Maps/Day1_Garden"
SEQUENCE_PATH = "/Game/Cinematics/LS_GodFlythrough"
SEED = 1101
FLY_SECONDS = 28.0
FLY_HZ = 4

GARDEN_HALF = 4000.0
RIVER = {"x0": -4500.0, "x1": 4500.0, "y0": 800.0, "y1": 1600.0}
ADAM = {"x": 400.0, "y": -400.0, "z": 110.0, "clear": 400.0}
PLAYER = {"x": -800.0, "y": -1600.0, "z": 120.0}

COUNTS = {"tree": 48, "rock": 28, "plant": 200}
LAKE = {"x0": -3400.0, "x1": -600.0, "y0": -1500.0, "y1": 100.0}

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
    "lake": ["/Engine/BasicShapes/Cube"],
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
    "lake": "water",
}

AUTHORED_MATERIALS = {
    "/Game/Materials/M_Elyon_Grass": {"color": (0.16, 0.34, 0.08, 1.0), "roughness": 0.92},
    "/Game/Materials/M_Elyon_Leaf": {"color": (0.22, 0.4, 0.08, 1.0), "roughness": 0.72},
    "/Game/Materials/M_Elyon_Rock": {"color": (0.35, 0.28, 0.2, 1.0), "roughness": 0.88},
    "/Game/Materials/M_Elyon_Water": {
        "color": (0.05, 0.22, 0.24, 1.0),
        "roughness": 0.04,
        "blend": "translucent",
    },
}

# Forest, rocks, and the terrain mesh. Plants stay ordinary cards.
NANITE_ROLES = ("terrain", "tree", "rock")
WATER_ROLES = ("river", "lake")


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
            "fog_color": (0.75, 0.78, 0.82, 1.0),
            "sun_pitch": -18.0,
            "sun_yaw": 35.0,
            "skylight_intensity": 0.45,
            "fog_density": 0.0008,
            "fog_height_falloff": 0.22,
            "fog_start_distance": 8000.0,
            "fog_max_opacity": 0.15,
            "exposure_min_ev": 12.0,
            "exposure_max_ev": 14.0,
            "exposure_bias": 0.35,
            "enable_volumetric_fog": False,
            "volumetric_fog_albedo": (0.8, 0.82, 0.84, 1.0),
            "volumetric_fog_emissive": (0.0, 0.0, 0.0, 1.0),
            "volumetric_fog_scattering_distribution": 0.2,
            "volumetric_fog_extinction_scale": 0.15,
            "volumetric_fog_distance": 12000.0,
            "volumetric_fog_start_distance": 4000.0,
            "directional_inscattering_exponent": 8.0,
            "directional_inscattering_start_distance": 4000.0,
            "directional_inscattering": (0.85, 0.72, 0.5, 1.0),
            "cast_volumetric_shadow": False,
            "volumetric_scattering_intensity": 0.2,
            "atmosphere_sun_light": True,
            "light_source_angle": 0.7,
            "enable_light_shaft_bloom": False,
            "enable_light_shaft_occlusion": False,
            "bloom_scale": 0.0,
            "bloom_threshold": 1.0,
            "bloom_max_brightness": 1.0,
            "bloom_tint": (1.0, 0.9, 0.75, 1.0),
            "bloom_intensity": 0.05,
            "vignette_intensity": 0.0,
            "scene_fringe_intensity": 0.0,
            "lens_flare_intensity": 0.0,
            "white_temp": 5200.0,
            "mie_anisotropy": 0.7,
            "mie_scattering_scale": 0.008,
            "sky_luminance_factor": (1.0, 0.96, 0.9, 1.0),
            "aerial_pespective_view_distance_scale": 1.0,
            "cloud_bottom_km": 1.6,
            "cloud_height_km": 4.5,
        }
    return {
        "name": "darkness",
        "sun_intensity": 0.02,
        "sun_color": (0.05, 0.07, 0.14, 1.0),
        "sky_color": (0.02, 0.03, 0.06, 1.0),
            "fog_color": (0.04, 0.05, 0.08, 1.0),
            "sun_pitch": -4.0,
            "sun_yaw": 35.0,
            "skylight_intensity": 0.02,
            "fog_density": 0.0025,
            "fog_height_falloff": 0.2,
            "fog_start_distance": 5000.0,
            "fog_max_opacity": 0.28,
        "exposure_min_ev": -1.0,
        "exposure_max_ev": 2.0,
        "exposure_bias": 0.0,
            "enable_volumetric_fog": False,
            "volumetric_fog_albedo": (0.15, 0.18, 0.28, 1.0),
            "volumetric_fog_emissive": (0.0, 0.0, 0.0, 1.0),
            "volumetric_fog_scattering_distribution": 0.1,
            "volumetric_fog_extinction_scale": 0.2,
            "volumetric_fog_distance": 8000.0,
            "volumetric_fog_start_distance": 2000.0,
            "directional_inscattering_exponent": 4.0,
            "directional_inscattering_start_distance": 4000.0,
            "directional_inscattering": (0.04, 0.05, 0.08, 1.0),
            "cast_volumetric_shadow": False,
            "volumetric_scattering_intensity": 0.0,
            "atmosphere_sun_light": True,
            "light_source_angle": 0.5,
            "enable_light_shaft_bloom": False,
            "enable_light_shaft_occlusion": False,
            "bloom_scale": 0.0,
            "bloom_threshold": 1.0,
            "bloom_max_brightness": 1.0,
            "bloom_tint": (0.2, 0.25, 0.4, 1.0),
            "bloom_intensity": 0.0,
            "vignette_intensity": 0.0,
            "scene_fringe_intensity": 0.0,
            "lens_flare_intensity": 0.0,
            "white_temp": 9000.0,
            "mie_anisotropy": 0.6,
            "mie_scattering_scale": 0.004,
            "sky_luminance_factor": (0.15, 0.2, 0.35, 1.0),
            "aerial_pespective_view_distance_scale": 1.0,
            "cloud_bottom_km": 2.0,
            "cloud_height_km": 3.5,
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
    in_lake = LAKE["x0"] <= x <= LAKE["x1"] and LAKE["y0"] <= y <= LAKE["y1"]
    if in_river or in_lake:
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
    if role == "lake":
        return (28.0, 16.0, 0.05)
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


def _catmull(points, u):
    count = len(points) - 1
    scaled = max(0.0, min(0.999999, u)) * count
    index = int(scaled)
    t = scaled - index
    p0 = points[max(index - 1, 0)]
    p1 = points[index]
    p2 = points[min(index + 1, count)]
    p3 = points[min(index + 2, count)]

    def axis(k):
        return 0.5 * (
            (2.0 * p1[k])
            + (-p0[k] + p2[k]) * t
            + (2.0 * p0[k] - 5.0 * p1[k] + 4.0 * p2[k] - p3[k]) * t * t
            + (-p0[k] + 3.0 * p1[k] - 3.0 * p2[k] + p3[k]) * t * t * t
        )

    return (axis(0), axis(1), axis(2))


def _look_angles(origin, target):
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    dz = target[2] - origin[2]
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw


def god_flight():
    """A slow god-view arc. Z stays above the garden. Pitch looks down, then toward the sun."""
    controls = [
        ((-2800.0, -2600.0, 2800.0), (0.0, 200.0, 40.0)),
        ((-900.0, -400.0, 1700.0), (400.0, -400.0, 80.0)),
        ((200.0, 500.0, 1400.0), (0.0, 1200.0, 30.0)),
        ((1900.0, 1500.0, 2000.0), (-2400.0, -1800.0, 1700.0)),
        ((-200.0, -2100.0, 3000.0), (200.0, 400.0, 40.0)),
    ]
    positions = [item[0] for item in controls]
    looks = [item[1] for item in controls]
    steps = int(FLY_SECONDS * FLY_HZ)
    samples = []
    for step in range(steps + 1):
        u = step / steps
        position = _catmull(positions, u)
        look = _catmull(looks, u)
        lifted = (position[0], position[1], max(position[2], 1200.0))
        pitch, yaw = _look_angles(lifted, look)
        samples.append(
            {
                "t": round(u * FLY_SECONDS, 4),
                "x": round(lifted[0], 2),
                "y": round(lifted[1], 2),
                "z": round(lifted[2], 2),
                "pitch": round(pitch, 3),
                "yaw": round(yaw, 3),
            }
        )
    return samples


def plan_level(dawn=True):
    light = light_state(dawn)
    flight = god_flight()
    opening = flight[0]
    actors = [
        _foliage("Elyon.Terrain", "terrain", 0.0, 0.0, 0.0),
        _prop("Elyon.Sun", "directional_light", 0.0, 0.0, 4000.0, pitch=light["sun_pitch"], yaw=light["sun_yaw"]),
        _prop("Elyon.SkyLight", "sky_light", 0.0, 0.0, 500.0),
        _prop("Elyon.SkyAtmosphere", "sky_atmosphere", 0.0, 0.0, 0.0),
        _prop("Elyon.Fog", "fog", 0.0, 0.0, 0.0),
        _prop("Elyon.Clouds", "clouds", 0.0, 0.0, 0.0),
        _prop("Elyon.Exposure", "post_process", 0.0, 0.0, 200.0),
        _foliage("Elyon.River", "river", 0.0, 1200.0, 4.0),
        _foliage("Elyon.Lake", "lake", -2000.0, -700.0, 3.0),
        _prop(
            "Elyon.GodCamera",
            "cine_camera",
            opening["x"],
            opening["y"],
            opening["z"],
            pitch=opening["pitch"],
            yaw=opening["yaw"],
        ),
        _prop("Elyon.GodFlythrough", "level_sequence", 0.0, 0.0, 0.0),
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
    return {"map": MAP_PATH, "dawn": bool(dawn), "light": light, "actors": actors, "flight": flight}


def planned_labels(plan):
    return [actor["label"] for actor in plan["actors"]]


def stale_labels(existing, planned):
    keep = set(planned)
    return sorted(label for label in existing if label.startswith("Elyon.") and label not in keep)
