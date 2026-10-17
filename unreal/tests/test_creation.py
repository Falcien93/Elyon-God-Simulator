import copy
import inspect
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
TESTS = Path(__file__).resolve().parent
UNREAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import creation_build
import creation_logic
import run_creation
from test_garden import Actor, ByteColor, FakeUnreal, LinearColor, labels

MAPS = [
    "/Game/Maps/Day2_Waters",
    "/Game/Maps/Day3_Land",
    "/Game/Maps/Day4_Lights",
    "/Game/Maps/Day5_Creatures",
    "/Game/Maps/Day6_Humanity",
    "/Game/Maps/Day7_Rest",
]


def load_raw():
    with (UNREAL / "Data" / "creation_week.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def load_story():
    with (UNREAL / "Data" / "days.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def species_xy(plan, species):
    return [(actor["x"], actor["y"]) for actor in plan["actors"] if actor.get("species") == species]


class SwitchingUnreal(FakeUnreal):
    """The stock mock has one level. The editor swaps actors when the map changes."""

    def __init__(self):
        super().__init__()
        self.maps = {}
        self.current = None
        self.assets = set()
        self.created_maps = []
        lib = self.EditorLevelLibrary

        def exists(path):
            return path in self.assets

        def new_level(path):
            self._switch(path, True)

        def load_level(path):
            self._switch(path, False)

        def save():
            lib.saves += 1
            if self.current is not None:
                self.maps[self.current] = list(self.sub.actors)

        self.EditorAssetLibrary.does_asset_exist = exists
        lib.new_level = new_level
        lib.load_level = load_level
        lib.save_current_level = save

    def _switch(self, path, create):
        if self.current is not None:
            self.maps[self.current] = list(self.sub.actors)
        self.current = path
        if create:
            if path not in self.created_maps:
                self.created_maps.append(path)
            self.assets.add(path)
            self.EditorLevelLibrary.created = path
            self.sub.actors = []
        else:
            self.EditorLevelLibrary.loaded = path
            self.sub.actors = list(self.maps.get(path, []))
        self.maps[path] = self.sub.actors


class CreationLogicTests(unittest.TestCase):
    def setUp(self):
        self.data = creation_logic.load_creation()

    def test_week_follows_the_story_and_the_garden_counts(self):
        story = {day["id"]: day for day in load_story()["days"]}
        self.assertEqual([day["map"] for day in self.data["days"]], MAPS)
        self.assertEqual(self.data["counts"], creation_logic.GAME_COUNTS)
        self.assertEqual(self.data["order"], ("waters", "land", "lights", "creatures", "humanity", "rest"))
        for spec in self.data["days"]:
            self.assertEqual([beat["id"] for beat in spec["beats"]], list(spec["completes"]))
            for beat in spec["beats"]:
                self.assertEqual(beat, {key: story[beat["id"]][key] for key in beat})
        land = self.data["days_by_id"]["land"]
        self.assertEqual(land["title"], "Dry land")
        self.assertEqual(land["beats"][1]["title"], "Seed")
        creatures = self.data["days_by_id"]["creatures"]
        self.assertEqual(creatures["numeral"], "the fifth day")
        self.assertEqual(creatures["beats"][0]["numeral"], "the fifth and sixth days")
        self.assertEqual(creatures["beats"][0]["title"], "Living creatures")

    def test_validator_rejects_a_dim_day_and_a_missing_beat(self):
        raw = load_raw()
        story = load_story()
        broken = copy.deepcopy(raw)
        broken["hours"]["day"]["sun_intensity"] = 0.01
        broken["hours"]["night"]["sun_intensity"] = 8
        with self.assertRaises(ValueError):
            creation_logic.validate_creation(broken, story)
        dropped = copy.deepcopy(raw)
        dropped["days"][1]["completes"] = ["land"]
        dropped["days"][1]["story"] = ["land"]
        with self.assertRaises(ValueError):
            creation_logic.validate_creation(dropped, story)

    def test_waters_divide_sky_and_three_bodies(self):
        plan = creation_logic.plan_day("waters", {"light"}, data=self.data)
        self.assertEqual(plan["map"], "/Game/Maps/Day2_Waters")
        self.assertEqual(plan["phase"], "divided")
        self.assertEqual(plan["evening"], "Evening came, and morning — the second day.")
        actors = creation_logic.by_label(plan)
        roles = {actor["role"] for actor in plan["actors"]}
        self.assertEqual(roles, {"sky", "water", "player", "day"})
        for label in ("Elyon.Sun", "Elyon.Ground", "Elyon.TreeOfLife", "Elyon.Adam", "Elyon.LetThereBeLight"):
            self.assertNotIn(label, actors)
        self.assertLess(actors["Elyon.Deep"]["y"], actors["Elyon.Sea"]["y"])
        self.assertLess(actors["Elyon.Sea"]["y"], actors["Elyon.Lake"]["y"])
        self.assertGreater(actors["Elyon.River"]["x"], 0)
        self.assertLess(actors["Elyon.Lake"]["x"], 0)
        self.assertGreater(actors["Elyon.WatersAbove"]["z"], actors["Elyon.Firmament"]["z"])
        self.assertEqual(actors["Elyon.Day"]["state"], "waters")
        self.assertEqual(actors["Elyon.PlayerStart"]["z"], creation_logic.PLAYER_SKY[2])
        world = creation_logic.simulate("waters", self.data)
        self.assertEqual(creation_logic.tile_at(world, 8, 18), creation_logic.WATER)
        self.assertEqual(creation_logic.tile_at(world, 10, 28), creation_logic.DEEP)
        bodies = creation_logic.classify_water(world)
        covered = []
        for tiles in bodies.values():
            covered.extend(tiles)
        water_tiles = [
            (x, y)
            for y in range(world["h"])
            for x in range(world["w"])
            if creation_logic.tile_at(world, x, y) in (creation_logic.WATER, creation_logic.DEEP)
        ]
        self.assertEqual(sorted(covered), sorted(water_tiles))
        self.assertTrue(all(bodies[name] for name in ("sea", "deep", "river", "lake")))

    def test_land_raises_the_grove_and_keeps_the_waters(self):
        waters = creation_logic.plan_day("waters", {"light"}, data=self.data)
        land = creation_logic.plan_day("land", creation_logic.done_before("land", self.data), data=self.data)
        water_labels = ("Elyon.Sea", "Elyon.River", "Elyon.Lake", "Elyon.Deep", "Elyon.Firmament")
        waters_by = creation_logic.by_label(waters)
        land_by = creation_logic.by_label(land)
        for label in water_labels:
            self.assertEqual((land_by[label]["x"], land_by[label]["y"]), (waters_by[label]["x"], waters_by[label]["y"]))
        self.assertEqual(sum(1 for actor in land["actors"] if actor["label"].startswith("Elyon.Tree.")), 16)
        self.assertEqual(sum(1 for actor in land["actors"] if actor["label"].startswith("Elyon.Flower.")), 28)
        life = land_by["Elyon.TreeOfLife"]
        knowledge = land_by["Elyon.TreeOfKnowledge"]
        self.assertGreater(life["scale"][2], knowledge["scale"][2])
        self.assertEqual(
            (life["x"], life["y"], life["z"]),
            creation_logic.unit_to_ue(*creation_logic.SPOT["life"], creation_logic.LIFE_Z),
        )
        self.assertLess(land_by["Elyon.RidgeWest"]["x"], land_by["Elyon.RidgeEast"]["x"])
        self.assertLess(land_by["Elyon.Shore"]["y"], life["y"])
        self.assertEqual(land_by["Elyon.Ground"]["mesh"], "/Engine/BasicShapes/Plane")
        world = creation_logic.simulate("land", self.data)
        for actor in land["actors"]:
            if actor.get("species") != "tree":
                continue
            tx, ty = creation_logic.actor_tile(actor)
            self.assertNotIn((tx, ty), creation_logic.RESERVED)
            self.assertIn(
                creation_logic.tile_at(world, tx, ty),
                (creation_logic.GRASS, creation_logic.FLOWER),
            )
        self.assertEqual(land["evening"], "The ground answered. Fruit took its color.")
        again = creation_logic.plan_day("land", creation_logic.done_before("land", self.data), data=self.data)
        self.assertEqual(land["actors"], again["actors"])

    def test_lights_keep_their_order(self):
        done = creation_logic.done_before("lights", self.data)
        day = creation_logic.plan_day("lights", done, phase="day", data=self.data)
        evening = creation_logic.plan_day("lights", done, phase="evening", data=self.data)
        night = creation_logic.plan_day("lights", done, phase="night", data=self.data)
        self.assertEqual(sum(1 for actor in day["actors"] if actor["label"].startswith("Elyon.Star.")), 36)
        day_by = creation_logic.by_label(day)
        self.assertGreater(day_by["Elyon.SunDisc"]["scale"][0], day_by["Elyon.Moon"]["scale"][0])
        self.assertGreater(day_by["Elyon.SunDisc"]["z"], creation_logic.by_label(evening)["Elyon.SunDisc"]["z"])
        self.assertGreater(day["light"]["sun_intensity"], evening["light"]["sun_intensity"])
        self.assertGreater(night["light"]["star_scale"], day["light"]["star_scale"])
        heights = [actor["z"] for actor in day["actors"] if actor.get("species") == "star"]
        self.assertGreater(min(heights), self.data["sky"]["firmamentZ"])
        self.assertLess(max(heights), self.data["sky"]["watersAboveZ"])
        radii = [((actor["x"] ** 2) + (actor["y"] ** 2)) ** 0.5 for actor in day["actors"] if actor.get("species") == "star"]
        self.assertGreaterEqual(min(radii), self.data["stars"]["radiusMin"] - 0.05)
        with self.assertRaises(ValueError):
            creation_logic.plan_day("waters", {"light"}, phase="night", data=self.data)

    def test_fish_stay_in_the_water_and_birds_stay_over_land(self):
        done = creation_logic.done_before("creatures", self.data)
        plan = creation_logic.plan_day("creatures", done, data=self.data)
        world = creation_logic.simulate("creatures", self.data)
        fish = [actor for actor in plan["actors"] if actor.get("species") == "fish"]
        birds = [actor for actor in plan["actors"] if actor.get("species") == "bird"]
        self.assertEqual(len(fish), 4)
        self.assertEqual(len(birds), 3)
        self.assertEqual({actor.get("species") for actor in plan["actors"] if actor["role"] == "creature"}, {"fish", "bird"})
        for actor in fish:
            self.assertEqual(actor["z"], creation_logic.FISH_Z)
            self.assertIn(creation_logic.tile_at(world, *creation_logic.actor_tile(actor)), (creation_logic.WATER, creation_logic.DEEP))
        for actor in birds:
            self.assertGreaterEqual(actor["z"], creation_logic.BIRD_Z_MIN)
            self.assertIn(
                creation_logic.tile_at(world, *creation_logic.actor_tile(actor)),
                (creation_logic.GRASS, creation_logic.FLOWER, creation_logic.SAND),
            )
        self.assertNotIn("Elyon.Adam", creation_logic.by_label(plan))
        self.assertNotIn("Elyon.Deer.01", creation_logic.by_label(plan))

    def test_land_animals_humans_and_rest(self):
        human = creation_logic.plan_day("humanity", creation_logic.done_before("humanity", self.data), data=self.data)
        earlier = creation_logic.plan_day("creatures", creation_logic.done_before("creatures", self.data), data=self.data)
        self.assertEqual(species_xy(earlier, "fish"), species_xy(human, "fish"))
        self.assertEqual(species_xy(earlier, "bird"), species_xy(human, "bird"))
        world = creation_logic.simulate("humanity", self.data)
        for species, count in (("deer", 2), ("sheep", 2), ("lion", 1)):
            found = [actor for actor in human["actors"] if actor.get("species") == species]
            self.assertEqual(len(found), count)
            for actor in found:
                tile = creation_logic.actor_tile(actor)
                self.assertNotIn(tile, creation_logic.RESERVED)
                self.assertIn(creation_logic.tile_at(world, *tile), (creation_logic.GRASS, creation_logic.FLOWER))
        actors = creation_logic.by_label(human)
        self.assertGreater(actors["Elyon.Adam"]["scale"][2], actors["Elyon.Eve"]["scale"][2])
        adam = creation_logic.unit_to_ue(*creation_logic.SPOT["adam"], creation_logic.ADAM_Z)
        eve = creation_logic.unit_to_ue(*creation_logic.SPOT["eve"], creation_logic.EVE_Z)
        self.assertEqual((actors["Elyon.Adam"]["x"], actors["Elyon.Adam"]["y"], actors["Elyon.Adam"]["z"]), adam)
        self.assertEqual((actors["Elyon.Eve"]["x"], actors["Elyon.Eve"]["y"], actors["Elyon.Eve"]["z"]), eve)
        self.assertNotIn("Elyon.Presence", actors)

        rest = creation_logic.plan_day("rest", creation_logic.done_before("rest", self.data), data=self.data)
        self.assertEqual(rest["phase"], "evening")
        self.assertEqual(rest["evening"], "You rested, and the work did not unwind.")
        self.assertEqual(creation_logic.rest_reached(rest), ["Elyon.Adam", "Elyon.Eve"])
        player = creation_logic.by_label(rest)["Elyon.PlayerStart"]
        people = [creation_logic.by_label(rest)["Elyon.Adam"], creation_logic.by_label(rest)["Elyon.Eve"]]
        self.assertEqual(creation_logic.rested(player, people, rest["restRadius"]), [])
        far = {"label": "Elyon.Presence", "x": 0.0, "y": -8000.0}
        self.assertEqual(creation_logic.rested(far, people, rest["restRadius"]), [])
        self.assertEqual(species_xy(rest, "tree"), species_xy(human, "tree"))

    def test_a_later_day_stays_locked(self):
        with self.assertRaises(creation_logic.LevelLocked) as caught:
            creation_logic.plan_day("humanity", {"light"}, data=self.data)
        self.assertEqual(caught.exception.day_id, "humanity")
        self.assertIn("creatures", caught.exception.missing)
        self.assertIn("grove", caught.exception.missing)
        with self.assertRaises(creation_logic.LevelLocked) as waters:
            creation_logic.plan_day("waters", set(), data=self.data)
        self.assertEqual(waters.exception.missing, ("light",))
        with self.assertRaises(ValueError):
            creation_logic.plan_day("eighth", {"light"}, data=self.data)
        self.assertNotIn("import unreal", inspect.getsource(creation_logic))


class CreationBuildTests(unittest.TestCase):
    def test_one_map_rebuilds_and_keeps_color_types(self):
        ue = FakeUnreal()
        done = creation_logic.done_before("waters")
        plan = creation_build.build_day("waters", done, ue=ue)
        self.assertEqual(ue.EditorLevelLibrary.created, "/Game/Maps/Day2_Waters")
        self.assertEqual(len(labels(ue)), len(plan["actors"]))
        self.assertNotIn("Elyon.Sun", labels(ue))
        sky = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.SkyLight")
        sky_comp = sky.get_component_by_class(ue.SkyLightComponent)
        self.assertIsInstance(sky_comp.props["light_color"], ByteColor)
        self.assertEqual(sky_comp.recaptured, 1)
        fog = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Fog")
        fog_comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        self.assertIsInstance(fog_comp.props["fog_inscattering_luminance"], LinearColor)
        self.assertEqual(fog_comp.props["fog_inscattering_luminance"].rgba, plan["light"]["fog_color"])
        sea = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Sea")
        self.assertEqual(sea.get_component_by_class(ue.StaticMeshComponent).mesh, "/Engine/BasicShapes/Cube")
        day = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Day")
        self.assertEqual(day.props["tags"], ["waters"])

        old = Actor(ue.StaticMeshActor)
        old.set_actor_label("Elyon.OldRock")
        ue.sub.actors.append(old)
        keeper = Actor(ue.StaticMeshActor)
        keeper.set_actor_label("SkySphere")
        ue.sub.actors.append(keeper)
        creation_build.build_day("waters", done, ue=ue)
        self.assertNotIn("Elyon.OldRock", labels(ue))
        self.assertIn("SkySphere", labels(ue))
        self.assertEqual(len([label for label in labels(ue) if label.startswith("Elyon.")]), len(plan["actors"]))
        self.assertEqual(ue.EditorLevelLibrary.loaded, "/Game/Maps/Day2_Waters")
        with self.assertRaises(creation_logic.HoursMissing):
            creation_build.set_hours("night", ue=ue)
        with self.assertRaises(ValueError):
            creation_build.set_hours("noon", ue=ue)

    def test_a_locked_day_does_not_open_a_map(self):
        ue = FakeUnreal()
        with self.assertRaises(creation_logic.LevelLocked):
            creation_build.build_day("rest", {"light"}, ue=ue)
        self.assertEqual(ue.sub.actors, [])
        self.assertEqual(ue.EditorLevelLibrary.saves, 0)
        self.assertIsNone(ue.EditorLevelLibrary.created)

    def test_hours_switch_on_the_fourth_day(self):
        ue = FakeUnreal()
        done = creation_logic.done_before("lights")
        creation_build.build_day("lights", done, ue=ue, phase="night")
        sun = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Sun")
        sun_comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        moon = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.MoonLight")
        moon_comp = moon.get_component_by_class(ue.DirectionalLightComponent)
        self.assertEqual(sun_comp.props["intensity"], 0.02)
        self.assertEqual(sun_comp.props["light_color"].rgba, (13, 18, 36, 255))
        self.assertIsInstance(sun_comp.props["light_color"], ByteColor)
        self.assertGreater(moon_comp.props["intensity"], sun_comp.props["intensity"])
        with self.assertRaises(TypeError):
            sun_comp.set_editor_property("light_color", ue.LinearColor(0.05, 0.07, 0.14, 1.0))
        fog = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Fog")
        fog_comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        with self.assertRaises(TypeError):
            fog_comp.set_editor_property("fog_inscattering_luminance", ue.Color(10, 13, 23, 255))

        light = creation_build.set_hours("day", ue=ue)
        self.assertEqual(light["name"], "day")
        self.assertEqual(sun_comp.props["intensity"], 10.0)
        self.assertEqual(sun_comp.props["light_color"].rgba, (255, 237, 199, 255))
        self.assertEqual(fog_comp.props["fog_inscattering_luminance"].rgba, (0.75, 0.82, 0.95, 1.0))
        hours = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Hours")
        self.assertEqual(hours.props["tags"], ["day"])
        star = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Star.01")
        self.assertEqual(star.scale.x, light["star_scale"])
        disc = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.SunDisc")
        self.assertEqual((disc.location.x, disc.location.y, disc.location.z), light["sun_disc"])

        creation_build.set_hours("evening", ue=ue)
        self.assertEqual(sun_comp.props["intensity"], 3.2)
        self.assertEqual(sun_comp.props["light_color"].rgba, (255, 158, 82, 255))
        self.assertEqual(hours.props["tags"], ["evening"])

    def test_week_keeps_each_map_and_the_editor_open(self):
        ue = SwitchingUnreal()
        plans = creation_build.build_week(ue)
        self.assertEqual([plan["map"] for plan in plans], MAPS)
        self.assertEqual(ue.created_maps, MAPS)
        self.assertEqual(ue.EditorLevelLibrary.saves, 6)
        self.assertNotIn("/Game/Maps/Day1_Garden", ue.created_maps)

        def names(path):
            return {actor.get_actor_label() for actor in ue.maps[path]}

        self.assertIn("Elyon.Sea", names(MAPS[0]))
        self.assertNotIn("Elyon.Ground", names(MAPS[0]))
        self.assertIn("Elyon.TreeOfLife", names(MAPS[1]))
        self.assertNotIn("Elyon.Sun", names(MAPS[1]))
        self.assertIn("Elyon.Sun", names(MAPS[2]))
        self.assertNotIn("Elyon.Fish.01", names(MAPS[2]))
        self.assertIn("Elyon.Fish.01", names(MAPS[3]))
        self.assertIn("Elyon.Bird.01", names(MAPS[3]))
        self.assertNotIn("Elyon.Adam", names(MAPS[3]))
        self.assertIn("Elyon.Adam", names(MAPS[4]))
        self.assertIn("Elyon.Eve", names(MAPS[4]))
        self.assertIn("Elyon.Lion.01", names(MAPS[4]))
        self.assertNotIn("Elyon.Presence", names(MAPS[4]))
        self.assertIn("Elyon.Presence", names(MAPS[5]))
        sun = next(actor for actor in ue.maps[MAPS[5]] if actor.get_actor_label() == "Elyon.Sun")
        sun_comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        self.assertEqual(sun_comp.props["intensity"], 3.2)
        self.assertEqual(sun_comp.props["light_color"].rgba, (255, 158, 82, 255))
        noon = next(actor for actor in ue.maps[MAPS[2]] if actor.get_actor_label() == "Elyon.Sun")
        noon_comp = noon.get_component_by_class(ue.DirectionalLightComponent)
        self.assertEqual(noon_comp.props["intensity"], 10.0)
        for plan in plans:
            stored = [actor.get_actor_label() for actor in ue.maps[plan["map"]] if actor.get_actor_label().startswith("Elyon.")]
            self.assertEqual(len(stored), len(plan["actors"]))
        ground = next(actor for actor in ue.maps[MAPS[1]] if actor.get_actor_label() == "Elyon.Ground")
        self.assertEqual(ground.get_component_by_class(ue.StaticMeshComponent).mesh, "/Engine/BasicShapes/Plane")
        adam = next(actor for actor in ue.maps[MAPS[4]] if actor.get_actor_label() == "Elyon.Adam")
        self.assertEqual(adam.get_component_by_class(ue.StaticMeshComponent).mesh, "/Engine/BasicShapes/Sphere")

        old = Actor(ue.StaticMeshActor)
        old.set_actor_label("Elyon.OldRock")
        ue.sub.actors.append(old)
        creation_build.build_week(ue)
        self.assertEqual(ue.created_maps, MAPS)
        self.assertEqual(ue.EditorLevelLibrary.saves, 12)
        self.assertNotIn("Elyon.OldRock", names(MAPS[5]))
        self.assertEqual(len(names(MAPS[5])), len(plans[5]["actors"]))

        run_creation.main(ue)
        self.assertTrue(ue.EditorPythonScripting.alive)
        self.assertEqual(ue.EditorLevelLibrary.saves, 18)

    def test_day1_map_stays_the_startup_map(self):
        engine = (UNREAL / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
        self.assertIn("EditorStartupMap=/Game/Maps/Day1_Garden", engine)
        self.assertIn("GameDefaultMap=/Game/Maps/Day1_Garden", engine)


if __name__ == "__main__":
    unittest.main()
