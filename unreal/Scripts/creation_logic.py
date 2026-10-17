"""Days 2 through 7 of creation. Pure Python so tests can run without Unreal.

Day 1 stays in garden_logic. Each later day is its own map and keeps the
actors made before it. Fish and birds are the fifth day. Deer, sheep, the
lion, Adam, and Eve are the sixth. Counts for those creatures, and for the
grove, match js/world.js.
"""

import json
import math
from pathlib import Path

from garden_logic import MESH

ROOT = Path(__file__).resolve().parents[1]
CREATION_PATH = ROOT / "Data" / "creation_week.json"
STORY_PATH = ROOT / "Data" / "days.json"

WORLD_W = 42
WORLD_H = 30
CELL = 200.0

CHAOS, NIGHT, WATER, DEEP, SAND, GRASS, STONE, FLOWER = range(8)

# js/world.js RESERVED and SPOT. Unit coordinates are tile centers.
RESERVED = {
    (14, 14),
    (20, 14),
    (21, 14),
    (19, 14),
    (20, 13),
    (20, 15),
    (27, 13),
    (26, 13),
    (28, 13),
}
SPOT = {
    "adam": (20.5, 14.5),
    "eve": (21.7, 14.5),
    "life": (14.5, 14.5),
    "knowledge": (27.5, 13.5),
    "descend": (20.5, 17.4),
}

STORY_ORDER = ("light", "waters", "land", "grove", "lights", "creatures", "humanity", "rest")
GAME_COUNTS = {
    "tree": 16,
    "flower": 28,
    "fish": 4,
    "bird": 3,
    "deer": 2,
    "sheep": 2,
    "lion": 1,
}
SPECIES_SEED = {"fish": 1, "bird": 2, "deer": 3, "sheep": 4, "lion": 5}

ADAM_Z = 110.0
EVE_Z = 110.0
PRESENCE_Z = 140.0
PLAYER_GROUND_Z = 120.0
PLAYER_SKY = (0.0, 0.0, 3200.0)
BIRD_Z_MIN = 280.0
BIRD_Z_SPAN = 640.0
FISH_Z = 22.0
LIFE_Z = 140.0
KNOWLEDGE_Z = 120.0
TREE_Z = 80.0
FLOWER_Z = 14.0
SUN_DISC_SCALE = (10.0, 10.0, 10.0)
MOON_DISC_SCALE = (4.5, 4.5, 4.5)

LUMINARY_PHASES = ("day", "night", "evening")
SKY_KEYS = ("name", "sky_color", "skylight_intensity", "fog_color", "fog_density")
LUMINARY_KEYS = SKY_KEYS + (
    "sun_intensity",
    "sun_color",
    "sun_pitch",
    "sun_yaw",
    "sun_disc",
    "moon_intensity",
    "moon_color",
    "moon_pitch",
    "moon_yaw",
    "moon_disc",
    "star_scale",
)


class LevelLocked(Exception):
    def __init__(self, day_id, missing):
        self.day_id = day_id
        self.missing = tuple(missing)
        super().__init__(f"{day_id} is locked until {', '.join(self.missing)}")


class HoursMissing(Exception):
    pass


class PlacementError(Exception):
    def __init__(self, kind, wanted, got):
        self.kind = kind
        self.wanted = wanted
        self.got = got
        super().__init__(f"placed {got} of {wanted} {kind}")


def _rng(seed):
    state = seed & 0xFFFFFFFF

    def nxt():
        nonlocal state
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        return state / 4294967296.0

    return nxt


def _empty_world():
    return {
        "w": WORLD_W,
        "h": WORLD_H,
        "tiles": [CHAOS] * (WORLD_W * WORLD_H),
        "entities": [],
        "flowers": [],
    }


def tile_at(world, x, y):
    if x < 0 or y < 0 or x >= world["w"] or y >= world["h"]:
        return STONE
    return world["tiles"][y * world["w"] + x]


def set_tile(world, x, y, tile):
    if x < 0 or y < 0 or x >= world["w"] or y >= world["h"]:
        return False
    world["tiles"][y * world["w"] + x] = tile
    return True


def fill_night(world):
    tiles = world["tiles"]
    for index, tile in enumerate(tiles):
        if tile == CHAOS:
            tiles[index] = NIGHT


def carve_waters(world):
    """Sea to the south, river to the east, lake to the west. Same cuts as js/world.js."""
    for y in range(26, WORLD_H):
        for x in range(WORLD_W):
            set_tile(world, x, y, DEEP if y > 27 else WATER)
    x = 32
    for y in range(1, 27):
        if y % 5 == 0:
            x += -1 if y % 10 == 0 else 1
        x = max(29, min(WORLD_W - 2, x))
        set_tile(world, x, y, WATER)
        set_tile(world, x + 1, y, DEEP)
    lx, ly = 8, 18
    for y in range(ly - 2, ly + 3):
        for x2 in range(lx - 3, lx + 4):
            dx = (x2 - lx) / 3.0
            dy = (y - ly) / 2.2
            if dx * dx + dy * dy <= 1:
                set_tile(world, x2, y, WATER)


def raise_land(world):
    for y in range(WORLD_H):
        for x in range(WORLD_W):
            tile = tile_at(world, x, y)
            if y <= 1 and tile == NIGHT:
                set_tile(world, x, y, STONE)
            elif tile == NIGHT:
                set_tile(world, x, y, GRASS)
    for y in range(WORLD_H):
        for x in range(WORLD_W):
            if tile_at(world, x, y) != GRASS:
                continue
            shore = (
                tile_at(world, x + 1, y) == WATER
                or tile_at(world, x - 1, y) == WATER
                or tile_at(world, x, y + 1) == WATER
                or tile_at(world, x, y - 1) == WATER
                or tile_at(world, x, y + 1) == DEEP
            )
            if shore:
                set_tile(world, x, y, SAND)
    for x, y in ((20, 14), (21, 14), (19, 14), (20, 13), (20, 15), (14, 14), (27, 13), (26, 13)):
        if tile_at(world, x, y) in (SAND, NIGHT):
            set_tile(world, x, y, GRASS)


def _entity_at(world, x, y, kinds):
    tx, ty = math.floor(x), math.floor(y)
    for entity in world["entities"]:
        if entity["kind"] not in kinds:
            continue
        if math.floor(entity["x"]) == tx and math.floor(entity["y"]) == ty:
            return entity
    return None


def plant_grove(world, rng, flowers, trees):
    placed = 0
    guard = 0
    while placed < flowers and guard < flowers * 80:
        guard += 1
        x = 4 + int(rng() * (WORLD_W - 8))
        y = 4 + int(rng() * 20)
        if (x, y) in RESERVED:
            continue
        if tile_at(world, x, y) != GRASS:
            continue
        set_tile(world, x, y, FLOWER)
        world["flowers"].append((x, y))
        placed += 1
    if placed < flowers:
        raise PlacementError("flower", flowers, placed)

    world["entities"].append({"id": "tree_life", "kind": "tree_life", "x": SPOT["life"][0], "y": SPOT["life"][1]})
    world["entities"].append(
        {"id": "tree_knowledge", "kind": "tree_knowledge", "x": SPOT["knowledge"][0], "y": SPOT["knowledge"][1]}
    )

    placed = 0
    guard = 0
    tree_kinds = ("tree", "tree_life", "tree_knowledge")
    while placed < trees and guard < trees * 80:
        guard += 1
        x = 3 + int(rng() * (WORLD_W - 6))
        y = 3 + int(rng() * 21)
        if (x, y) in RESERVED:
            continue
        if tile_at(world, x, y) not in (GRASS, FLOWER):
            continue
        if _entity_at(world, x + 0.5, y + 0.5, tree_kinds):
            continue
        yaw = round(rng() * 360.0, 2)
        scale = round(0.75 + rng() * 0.9, 3)
        world["entities"].append(
            {"id": f"tree_{x}_{y}", "kind": "tree", "x": x + 0.5, "y": y + 0.5, "yaw": yaw, "scale": scale}
        )
        placed += 1
    if placed < trees:
        raise PlacementError("tree", trees, placed)


def _occupied(world):
    taken = set(RESERVED)
    for entity in world["entities"]:
        taken.add((math.floor(entity["x"]), math.floor(entity["y"])))
    return taken


def _accept_tile(world, kind, x, y):
    tile = tile_at(world, x, y)
    if kind == "fish":
        return tile in (WATER, DEEP)
    if kind == "bird":
        return tile in (GRASS, FLOWER, SAND)
    return tile in (GRASS, FLOWER)


def place_creatures(world, data, kinds, occupied):
    for kind in kinds:
        count = data["counts"][kind]
        rng = _rng(data["seed"] + SPECIES_SEED[kind])
        placed = 0
        guard = 0
        while placed < count and guard < count * 100:
            guard += 1
            x = int(rng() * WORLD_W)
            y = int(rng() * WORLD_H)
            if (x, y) in occupied or not _accept_tile(world, kind, x, y):
                continue
            occupied.add((x, y))
            yaw = round(rng() * 360.0, 2)
            extra = rng()
            world["entities"].append(
                {
                    "id": f"{kind}_{placed + 1}",
                    "kind": kind,
                    "x": x + 0.5,
                    "y": y + 0.5,
                    "yaw": yaw,
                    "extra": extra,
                }
            )
            placed += 1
        if placed < count:
            raise PlacementError(kind, count, placed)


def place_humans(world):
    for kind, spot in (("adam", SPOT["adam"]), ("eve", SPOT["eve"])):
        world["entities"].append({"id": kind, "kind": kind, "x": spot[0], "y": spot[1]})


def classify_water(world):
    bodies = {"sea": [], "deep": [], "river": [], "lake": []}
    for y in range(world["h"]):
        for x in range(world["w"]):
            tile = tile_at(world, x, y)
            if tile not in (WATER, DEEP):
                continue
            if y >= 26:
                bodies["deep" if tile == DEEP else "sea"].append((x, y))
            elif x >= 29:
                bodies["river"].append((x, y))
            else:
                bodies["lake"].append((x, y))
    return bodies


def unit_to_ue(ux, uy, z=0.0):
    x = (float(ux) - WORLD_W / 2.0) * CELL
    y = (WORLD_H / 2.0 - float(uy)) * CELL
    return (round(x, 2), round(y, 2), round(float(z), 2))


def actor_tile(actor):
    ux = actor["x"] / CELL + WORLD_W / 2.0
    uy = WORLD_H / 2.0 - actor["y"] / CELL
    return (int(math.floor(ux + 1e-6)), int(math.floor(uy + 1e-6)))


def _color(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{label} must be four channels")
    channels = []
    for channel in value:
        number = float(channel)
        if number < 0 or number > 1:
            raise ValueError(f"{label} channel out of range")
        channels.append(number)
    return tuple(channels)


def _disc(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must be x, y, z")
    return tuple(round(float(channel), 2) for channel in value)


def _hours(raw):
    if set(raw) != {"divided", "day", "night", "evening"}:
        raise ValueError("hours must define divided, day, night, and evening")
    parsed = {}
    for name, spec in raw.items():
        keys = SKY_KEYS if name == "divided" else LUMINARY_KEYS
        missing = [key for key in keys if key not in spec]
        if missing:
            raise ValueError(f"{name} is missing {', '.join(missing)}")
        if spec["name"] != name:
            raise ValueError(f"{name} light is named {spec['name']}")
        light = {
            "name": name,
            "sky_color": _color(spec["sky_color"], f"{name} sky"),
            "skylight_intensity": float(spec["skylight_intensity"]),
            "fog_color": _color(spec["fog_color"], f"{name} fog"),
            "fog_density": float(spec["fog_density"]),
        }
        if light["skylight_intensity"] < 0 or light["fog_density"] <= 0:
            raise ValueError(f"{name} sky light or fog is not usable")
        if name != "divided":
            light.update(
                {
                    "sun_intensity": float(spec["sun_intensity"]),
                    "sun_color": _color(spec["sun_color"], f"{name} sun"),
                    "sun_pitch": float(spec["sun_pitch"]),
                    "sun_yaw": float(spec["sun_yaw"]),
                    "sun_disc": _disc(spec["sun_disc"], f"{name} sun disc"),
                    "moon_intensity": float(spec["moon_intensity"]),
                    "moon_color": _color(spec["moon_color"], f"{name} moon"),
                    "moon_pitch": float(spec["moon_pitch"]),
                    "moon_yaw": float(spec["moon_yaw"]),
                    "moon_disc": _disc(spec["moon_disc"], f"{name} moon disc"),
                    "star_scale": float(spec["star_scale"]),
                }
            )
            if light["sun_intensity"] < 0 or light["moon_intensity"] < 0 or light["star_scale"] <= 0:
                raise ValueError(f"{name} luminaries need a positive scale and a non-negative intensity")
        parsed[name] = light
    day, evening, night = parsed["day"], parsed["evening"], parsed["night"]
    if not (day["sun_intensity"] > evening["sun_intensity"] > night["sun_intensity"]):
        raise ValueError("the sun must be brightest by day and dimmest at night")
    if not (night["moon_intensity"] > day["moon_intensity"]):
        raise ValueError("the moon must be brighter at night than by day")
    if not (night["star_scale"] > evening["star_scale"] > day["star_scale"]):
        raise ValueError("stars must read brightest at night and faintest by day")
    if not (day["sun_pitch"] < evening["sun_pitch"] < 0):
        raise ValueError("the evening sun sits lower than the noon sun and stays above the horizon line")
    if not (day["sun_disc"][2] > evening["sun_disc"][2]):
        raise ValueError("the noon sun sits higher than the evening sun")
    if not (day["skylight_intensity"] > evening["skylight_intensity"] > night["skylight_intensity"]):
        raise ValueError("sky light fades from day to evening to night")
    if not (day["fog_density"] < evening["fog_density"] < night["fog_density"]):
        raise ValueError("fog thickens from day to evening to night")
    return parsed


def _story_beats(story_payload):
    if story_payload.get("source") != "js/content.js":
        raise ValueError("days.json source must stay js/content.js")
    beats = {}
    for day in story_payload.get("days", []):
        for key in ("id", "numeral", "title", "detail", "evening"):
            if not day.get(key):
                raise ValueError(f"story day {day.get('id')} is missing {key}")
        beats[day["id"]] = {
            "id": day["id"],
            "numeral": day["numeral"],
            "title": day["title"],
            "detail": day["detail"],
            "evening": day["evening"],
        }
    return beats


def validate_creation(payload, story_payload):
    if payload.get("source") != "js/content.js":
        raise ValueError("creation week source must stay js/content.js")
    world = payload.get("world") or {}
    if (world.get("width"), world.get("height"), world.get("cell")) != (WORLD_W, WORLD_H, CELL):
        raise ValueError("creation week world must match the 42 by 30 garden")
    if not isinstance(payload.get("seed"), int):
        raise ValueError("seed must be an int")
    radius = payload.get("restRadius")
    if not isinstance(radius, (int, float)) or radius <= 0:
        raise ValueError("rest radius must be positive")
    sky = payload.get("sky") or {}
    firmament = float(sky.get("firmamentZ", 0))
    above = float(sky.get("watersAboveZ", 0))
    if not (above > firmament > 0):
        raise ValueError("waters above the firmament must sit higher than the firmament")
    stars = payload.get("stars") or {}
    star_count = stars.get("count")
    if not isinstance(star_count, int) or star_count < 12:
        raise ValueError("the sky needs at least twelve stars")
    radius_min = float(stars.get("radiusMin", 0))
    radius_max = float(stars.get("radiusMax", 0))
    z_min = float(stars.get("zMin", 0))
    z_max = float(stars.get("zMax", 0))
    if not (radius_max > radius_min > 0):
        raise ValueError("star radius is out of order")
    if not (firmament < z_min < z_max < above):
        raise ValueError("stars must sit in the firmament, under the waters above")
    counts = payload.get("counts")
    if counts != GAME_COUNTS:
        raise ValueError("creature and grove counts must match js/world.js")
    order = payload.get("order")
    if order != ["waters", "land", "lights", "creatures", "humanity", "rest"]:
        raise ValueError("days must run waters, land, lights, creatures, humanity, rest")
    raw_days = payload.get("days")
    if not isinstance(raw_days, list) or [day.get("id") for day in raw_days] != order:
        raise ValueError("days must follow order")
    beats = _story_beats(story_payload)
    hours = _hours(payload.get("hours") or {})
    days = []
    seen = ["light"]
    for raw in raw_days:
        for key in ("id", "numeral", "title", "detail", "map", "phase", "requires", "completes", "story"):
            if key not in raw or raw[key] in ("", None, [], {}):
                raise ValueError(f"{raw.get('id')} is missing {key}")
        if raw["story"] != raw["completes"]:
            raise ValueError(f"{raw['id']} story ids must be the beats that day completes")
        if list(raw["requires"]) != seen:
            raise ValueError(f"{raw['id']} requires {raw['requires']} but the chain is {seen}")
        completed = []
        for story_id in raw["completes"]:
            if story_id in seen:
                raise ValueError(f"duplicate complete {story_id}")
            if story_id not in beats:
                raise ValueError(f"unknown story beat {story_id}")
            completed.append(story_id)
            seen.append(story_id)
        if not str(raw["map"]).startswith("/Game/Maps/Day"):
            raise ValueError(f"{raw['id']} map must live under /Game/Maps")
        if raw["phase"] not in hours:
            raise ValueError(f"{raw['id']} uses an unknown phase")
        days.append(
            {
                "id": raw["id"],
                "numeral": raw["numeral"],
                "title": raw["title"],
                "detail": raw["detail"],
                "map": raw["map"],
                "phase": raw["phase"],
                "requires": tuple(raw["requires"]),
                "completes": tuple(completed),
                "beats": [beats[story_id] for story_id in completed],
            }
        )
    if tuple(seen) != STORY_ORDER:
        raise ValueError("the week must cover every story day once, after light")
    maps = [day["map"] for day in days]
    if len(maps) != len(set(maps)):
        raise ValueError("each day needs its own map")
    return {
        "source": payload["source"],
        "seed": payload["seed"],
        "restRadius": float(radius),
        "order": tuple(order),
        "counts": dict(counts),
        "sky": {"firmamentZ": firmament, "watersAboveZ": above},
        "stars": {
            "count": star_count,
            "radiusMin": radius_min,
            "radiusMax": radius_max,
            "zMin": z_min,
            "zMax": z_max,
        },
        "hours": hours,
        "days": days,
        "days_by_id": {day["id"]: day for day in days},
    }


def load_story(path=None):
    path = STORY_PATH if path is None else Path(path)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_creation(path=None, story_path=None):
    path = CREATION_PATH if path is None else Path(path)
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_creation(payload, load_story(story_path))


def _day(data, day_id):
    try:
        return data["days_by_id"][day_id]
    except KeyError:
        raise ValueError(f"unknown day {day_id}") from None


def _reached(data, day_id, target):
    return data["order"].index(day_id) >= data["order"].index(target)


def done_before(day_id, data=None):
    data = load_creation() if data is None else data
    _day(data, day_id)
    done = {"light"}
    for item_id in data["order"]:
        if item_id == day_id:
            break
        done.update(data["days_by_id"][item_id]["completes"])
    return done


def simulate(day_id, data=None):
    data = load_creation() if data is None else data
    _day(data, day_id)
    world = _empty_world()
    fill_night(world)
    carve_waters(world)
    if _reached(data, day_id, "land"):
        raise_land(world)
        plant_grove(world, _rng(data["seed"]), data["counts"]["flower"], data["counts"]["tree"])
    occupied = _occupied(world)
    if _reached(data, day_id, "creatures"):
        place_creatures(world, data, ("fish", "bird"), occupied)
    if _reached(data, day_id, "humanity"):
        place_creatures(world, data, ("deer", "sheep", "lion"), occupied)
        place_humans(world)
    return world


def _static(label, mesh, x, y, z, scale, yaw=0.0, role="prop", species=None):
    sx, sy, sz = scale if isinstance(scale, tuple) else (scale, scale, scale)
    actor = {
        "label": label,
        "kind": "static",
        "role": role,
        "mesh": MESH[mesh],
        "x": round(float(x), 2),
        "y": round(float(y), 2),
        "z": round(float(z), 2),
        "yaw": round(float(yaw), 2),
        "pitch": 0.0,
        "scale": (round(float(sx), 3), round(float(sy), 3), round(float(sz), 3)),
    }
    if species:
        actor["species"] = species
    return actor


def _marker(label, x, y, z, state, role):
    return {
        "label": label,
        "kind": "marker",
        "role": role,
        "x": round(float(x), 2),
        "y": round(float(y), 2),
        "z": round(float(z), 2),
        "yaw": 0.0,
        "pitch": 0.0,
        "state": state,
    }


def _light(label, kind, x, y, z, pitch, yaw, role):
    return {
        "label": label,
        "kind": kind,
        "role": role,
        "x": round(float(x), 2),
        "y": round(float(y), 2),
        "z": round(float(z), 2),
        "pitch": float(pitch),
        "yaw": float(yaw),
    }


def _tiles_where(world, pred):
    found = []
    for y in range(world["h"]):
        for x in range(world["w"]):
            if pred(x, y, tile_at(world, x, y)):
                found.append((x, y))
    return found


def _cube_over(label, tiles, z, thickness, role):
    if not tiles:
        raise PlacementError(label, 1, 0)
    xs = [tile[0] for tile in tiles]
    ys = [tile[1] for tile in tiles]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    center_x = (min_x + max_x + 1) / 2.0
    center_y = (min_y + max_y + 1) / 2.0
    x, y, zz = unit_to_ue(center_x, center_y, z)
    scale_x = (max_x - min_x + 1) * CELL / 100.0
    scale_y = (max_y - min_y + 1) * CELL / 100.0
    return _static(label, "cube", x, y, zz, (scale_x, scale_y, thickness), role=role)


def _sky_layer(data):
    firmament = data["sky"]["firmamentZ"]
    above = data["sky"]["watersAboveZ"]
    return [
        _light("Elyon.SkyLight", "sky_light", 0, 0, 500, 0, 0, "sky"),
        _light("Elyon.SkyAtmosphere", "sky_atmosphere", 0, 0, 0, 0, 0, "sky"),
        _light("Elyon.Fog", "fog", 0, 0, 0, 0, 0, "sky"),
        _light("Elyon.Clouds", "clouds", 0, 0, 0, 0, 0, "sky"),
        _static("Elyon.Firmament", "cube", 0, 0, firmament, (90, 70, 0.04), role="sky"),
        _static("Elyon.WatersAbove", "cube", 0, 0, above, (92, 72, 0.25), role="sky"),
        _marker("Elyon.Divide", 0, 0, firmament, "firmament", "sky"),
    ]


def _water_layer(world):
    bodies = classify_water(world)
    return [
        _cube_over("Elyon.Sea", bodies["sea"], 8, 0.12, "water"),
        _cube_over("Elyon.Deep", bodies["deep"], 3, 0.16, "water"),
        _cube_over("Elyon.River", bodies["river"], 10, 0.1, "water"),
        _cube_over("Elyon.Lake", bodies["lake"], 9, 0.1, "water"),
    ]


def _land_layer(world):
    ground_scale = (WORLD_W * CELL / 100.0, WORLD_H * CELL / 100.0, 1.0)
    stone = _tiles_where(world, lambda x, y, tile: tile == STONE)
    west = [tile for tile in stone if tile[0] < 29]
    east = [tile for tile in stone if tile[0] >= 29]
    shore = _tiles_where(world, lambda x, y, tile: tile == SAND and y >= 24)
    return [
        _static("Elyon.Ground", "plane", 0, 0, 0, ground_scale, role="land"),
        _cube_over("Elyon.RidgeWest", west, 80, 1.6, "land"),
        _cube_over("Elyon.RidgeEast", east, 80, 1.6, "land"),
        _cube_over("Elyon.Shore", shore, 4, 0.08, "land"),
    ]


def _plant_layer(world):
    actors = []
    for index, (x, y) in enumerate(world["flowers"], start=1):
        ux, uy, uz = unit_to_ue(x + 0.5, y + 0.5, FLOWER_Z)
        actors.append(_static(f"Elyon.Flower.{index:02d}", "cone", ux, uy, uz, (0.28, 0.28, 0.45), role="plant"))
    life = next(entity for entity in world["entities"] if entity["kind"] == "tree_life")
    knowledge = next(entity for entity in world["entities"] if entity["kind"] == "tree_knowledge")
    lx, ly, lz = unit_to_ue(life["x"], life["y"], LIFE_Z)
    kx, ky, kz = unit_to_ue(knowledge["x"], knowledge["y"], KNOWLEDGE_Z)
    actors.append(_static("Elyon.TreeOfLife", "cone", lx, ly, lz, (2.4, 2.4, 9.0), role="plant", species="tree_life"))
    actors.append(
        _static(
            "Elyon.TreeOfKnowledge",
            "cone",
            kx,
            ky,
            kz,
            (2.1, 2.1, 7.4),
            yaw=15,
            role="plant",
            species="tree_knowledge",
        )
    )
    trees = [entity for entity in world["entities"] if entity["kind"] == "tree"]
    for index, entity in enumerate(trees, start=1):
        x, y, z = unit_to_ue(entity["x"], entity["y"], TREE_Z)
        scale = entity["scale"]
        actors.append(
            _static(
                f"Elyon.Tree.{index:02d}",
                "cone",
                x,
                y,
                z,
                (scale, scale, scale * 3.0),
                yaw=entity["yaw"],
                role="plant",
                species="tree",
            )
        )
    return actors


def _place_stars(data, scale):
    spec = data["stars"]
    rng = _rng(data["seed"] + 6)
    actors = []
    for index in range(1, spec["count"] + 1):
        angle = rng() * math.tau
        radius = spec["radiusMin"] + rng() * (spec["radiusMax"] - spec["radiusMin"])
        height = spec["zMin"] + rng() * (spec["zMax"] - spec["zMin"])
        radius = min(spec["radiusMax"], max(spec["radiusMin"], radius))
        height = min(spec["zMax"], max(spec["zMin"], height))
        actors.append(
            _static(
                f"Elyon.Star.{index:02d}",
                "sphere",
                math.cos(angle) * radius,
                math.sin(angle) * radius,
                height,
                (scale, scale, scale),
                role="luminary",
                species="star",
            )
        )
    return actors


def _luminary_layer(data, light):
    sun = light["sun_disc"]
    moon = light["moon_disc"]
    actors = [
        _light("Elyon.Sun", "directional_light", 0, 0, 4000, light["sun_pitch"], light["sun_yaw"], "luminary"),
        _static("Elyon.SunDisc", "sphere", sun[0], sun[1], sun[2], SUN_DISC_SCALE, role="luminary", species="sun"),
        _light(
            "Elyon.MoonLight",
            "directional_light",
            0,
            0,
            4000,
            light["moon_pitch"],
            light["moon_yaw"],
            "luminary",
        ),
        _static("Elyon.Moon", "sphere", moon[0], moon[1], moon[2], MOON_DISC_SCALE, role="luminary", species="moon"),
        _marker("Elyon.Hours", 0, 0, 360, light["name"], "luminary"),
    ]
    actors.extend(_place_stars(data, light["star_scale"]))
    return actors


def _creature_layer(world, kinds):
    meshes = {
        "fish": ("cone", (0.9, 0.28, 0.22), FISH_Z),
        "bird": ("cone", (0.55, 0.9, 0.16), None),
        "deer": ("cone", (0.7, 0.7, 1.6), 80.0),
        "sheep": ("sphere", (0.85, 0.85, 0.7), 50.0),
        "lion": ("cube", (1.3, 0.7, 0.8), 55.0),
    }
    grouped = {kind: [] for kind in kinds}
    for entity in world["entities"]:
        if entity["kind"] in grouped:
            grouped[entity["kind"]].append(entity)
    actors = []
    for kind in kinds:
        mesh, scale, height = meshes[kind]
        for index, entity in enumerate(grouped[kind], start=1):
            if kind == "bird":
                z = BIRD_Z_MIN + entity["extra"] * BIRD_Z_SPAN
            else:
                z = height
            x, y, zz = unit_to_ue(entity["x"], entity["y"], z)
            actors.append(
                _static(
                    f"Elyon.{kind.title()}.{index:02d}",
                    mesh,
                    x,
                    y,
                    zz,
                    scale,
                    yaw=entity["yaw"],
                    role="creature",
                    species=kind,
                )
            )
    return actors


def _human_layer(world):
    actors = []
    for kind, scale, z in (("adam", (1.1, 1.1, 2.0), ADAM_Z), ("eve", (0.95, 0.95, 1.75), EVE_Z)):
        entity = next(item for item in world["entities"] if item["kind"] == kind)
        x, y, zz = unit_to_ue(entity["x"], entity["y"], z)
        label = "Elyon.Adam" if kind == "adam" else "Elyon.Eve"
        actors.append(_static(label, "sphere", x, y, zz, scale, role="human", species=kind))
    return actors


def _rest_layer():
    adam = unit_to_ue(SPOT["adam"][0], SPOT["adam"][1], 220)
    eve = unit_to_ue(SPOT["eve"][0], SPOT["eve"][1], 220)
    mid_x = (SPOT["adam"][0] + SPOT["eve"][0]) / 2.0
    mid_y = (SPOT["adam"][1] + SPOT["eve"][1]) / 2.0
    presence = unit_to_ue(mid_x, mid_y, PRESENCE_Z)
    return [
        _marker("Elyon.Presence", presence[0], presence[1], presence[2], "rest", "rest"),
        _marker("Elyon.Rest.Adam", adam[0], adam[1], adam[2], "adam", "rest"),
        _marker("Elyon.Rest.Eve", eve[0], eve[1], eve[2], "eve", "rest"),
    ]


def _player(day_id, data):
    if not _reached(data, day_id, "land"):
        return {
            "label": "Elyon.PlayerStart",
            "kind": "player_start",
            "role": "player",
            "x": PLAYER_SKY[0],
            "y": PLAYER_SKY[1],
            "z": PLAYER_SKY[2],
            "yaw": 0.0,
            "pitch": 0.0,
        }
    x, y, z = unit_to_ue(SPOT["descend"][0], SPOT["descend"][1], PLAYER_GROUND_Z)
    return {
        "label": "Elyon.PlayerStart",
        "kind": "player_start",
        "role": "player",
        "x": x,
        "y": y,
        "z": z,
        "yaw": 90.0,
        "pitch": 0.0,
    }


def _require_unique(actors):
    labels = [actor["label"] for actor in actors]
    if len(labels) != len(set(labels)):
        dupes = sorted({label for label in labels if labels.count(label) > 1})
        raise ValueError(f"duplicate labels: {', '.join(dupes)}")
    for label in labels:
        if not label.startswith("Elyon."):
            raise ValueError(f"label must start with Elyon.: {label}")


def by_label(plan):
    return {actor["label"]: actor for actor in plan["actors"]}


def assemble(day_id, world, data, phase):
    light = data["hours"][phase]
    actors = []
    actors.extend(_sky_layer(data))
    actors.extend(_water_layer(world))
    if _reached(data, day_id, "land"):
        actors.extend(_land_layer(world))
        actors.extend(_plant_layer(world))
    if _reached(data, day_id, "lights"):
        actors.extend(_luminary_layer(data, light))
    if _reached(data, day_id, "creatures"):
        actors.extend(_creature_layer(world, ("fish", "bird")))
    if _reached(data, day_id, "humanity"):
        actors.extend(_creature_layer(world, ("deer", "sheep", "lion")))
        actors.extend(_human_layer(world))
    if _reached(data, day_id, "rest"):
        actors.extend(_rest_layer())
    actors.append(_player(day_id, data))
    actors.append(_marker("Elyon.Day", 0, 0, 300, day_id, "day"))
    _require_unique(actors)
    return actors


def plan_day(day_id, done, phase=None, data=None):
    data = load_creation() if data is None else data
    spec = _day(data, day_id)
    missing = [req for req in spec["requires"] if req not in set(done)]
    if missing:
        raise LevelLocked(day_id, missing)
    use_phase = spec["phase"] if phase is None else phase
    if use_phase != spec["phase"]:
        if not _reached(data, day_id, "lights"):
            raise ValueError(f"{day_id} has no luminaries to set to {use_phase}")
        if use_phase not in LUMINARY_PHASES:
            raise ValueError(f"unknown hours phase {use_phase}")
    world = simulate(day_id, data)
    actors = assemble(day_id, world, data, use_phase)
    return {
        "id": day_id,
        "map": spec["map"],
        "numeral": spec["numeral"],
        "title": spec["title"],
        "detail": spec["detail"],
        "evening": spec["beats"][-1]["evening"],
        "phase": use_phase,
        "light": dict(data["hours"][use_phase]),
        "completes": list(spec["completes"]),
        "requires": list(spec["requires"]),
        "beats": spec["beats"],
        "restRadius": data["restRadius"],
        "actors": actors,
    }


def rested(presence, people, radius):
    reached = []
    limit = float(radius) * float(radius)
    for person in people:
        dx = person["x"] - presence["x"]
        dy = person["y"] - presence["y"]
        if dx * dx + dy * dy <= limit:
            reached.append(person["label"])
    return reached


def rest_reached(plan, radius=None):
    if radius is None:
        radius = plan["restRadius"]
    actors = by_label(plan)
    people = [actors["Elyon.Adam"], actors["Elyon.Eve"]]
    return rested(actors["Elyon.Presence"], people, radius)
