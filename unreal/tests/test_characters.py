import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "Scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

import characters_build
import characters_logic
import garden_logic
import run_all
import test_garden


def garden_at(moment):
    return characters_logic.new_garden(moment)


def person(garden, who="adam"):
    return characters_logic.find_person(garden, who)


def samples(path, steps=24):
    found = []
    for start, goal in zip(path, path[1:]):
        for index in range(steps + 1):
            t = index / steps
            found.append((start[0] + (goal[0] - start[0]) * t, start[1] + (goal[1] - start[1]) * t))
    return found


class DayAndNeedsTests(unittest.TestCase):
    def test_phase_cuts_match_the_first_garden_day(self):
        phases = characters_logic.catalog()["phases"]
        self.assertEqual([item["until"] for item in phases[:4]], [0.08, 0.18, 0.26, 0.72])
        self.assertEqual(characters_logic.phase_at(0.0), "wake")
        self.assertEqual(characters_logic.phase_at(0.079), "wake")
        self.assertEqual(characters_logic.phase_at(0.08), "eat")
        self.assertEqual(characters_logic.phase_at(0.18), "drink")
        self.assertEqual(characters_logic.phase_at(0.26), "work")
        self.assertEqual(characters_logic.phase_at(0.72), "rest")
        self.assertEqual(characters_logic.phase_at(1.0), "rest")

    def test_adam_is_heavier_and_both_start_awake_on_dry_ground(self):
        garden = characters_logic.new_garden()
        adam = person(garden, "adam")
        eve = person(garden, "eve")
        self.assertGreater(adam["mass_kg"], eve["mass_kg"])
        self.assertGreater(adam["height_m"], eve["height_m"])
        self.assertEqual(adam["mass_kg"], 78)
        self.assertEqual(eve["mass_kg"], 58)
        self.assertEqual(adam["phase"], "wake")
        self.assertFalse(adam["moving"])
        self.assertFalse(adam["child_in_care"])
        self.assertFalse(eve["child_in_care"])
        self.assertGreater(characters_logic._dist(adam["x"], adam["y"], eve["x"], eve["y"]), 100)
        for body in (adam, eve):
            self.assertFalse(characters_logic.in_river(body["x"], body["y"]))
            self.assertLess(body["y"], garden_logic.RIVER["y0"])

    def test_strength_speed_and_the_tired_card(self):
        garden = characters_logic.new_garden()
        adam = person(garden)
        self.assertAlmostEqual(characters_logic.strength(adam), 80.68, places=2)
        self.assertAlmostEqual(characters_logic.speed_mps(adam), 1.57952, places=4)
        adam["fatigue"] = 90
        self.assertLess(characters_logic.speed_mps(adam), 1.57952)
        adam["fatigue"] = 55
        self.assertNotIn("Tired", characters_logic.card_line(adam))
        adam["fatigue"] = 56
        self.assertIn("Tired. Moving slowly.", characters_logic.card_line(adam))
        adam["age"] = 40
        adam["fatigue"] = 12
        self.assertAlmostEqual(characters_logic.strength(adam), 79.18, places=2)
        cared = person(characters_logic.new_garden())
        cared["child_in_care"] = True
        self.assertAlmostEqual(characters_logic.strength(cared), 62.68, places=2)

    def test_needs_move_and_meals_fire_once_per_entry(self):
        garden = characters_logic.new_garden()
        adam = person(garden)
        characters_logic.tick_person(adam, 0.10, 0, garden)
        self.assertEqual(adam["phase"], "eat")
        self.assertAlmostEqual(adam["hunger"], 20)
        characters_logic.tick_person(adam, 0.12, 0, garden)
        self.assertAlmostEqual(adam["hunger"], 20)

        thirsty = characters_logic.new_garden()
        eve = person(thirsty, "eve")
        characters_logic.tick_person(eve, 0.20, 0, thirsty)
        self.assertEqual(eve["phase"], "drink")
        self.assertAlmostEqual(eve["thirst"], 8)
        self.assertAlmostEqual(eve["hunger"], 42)

        resting = characters_logic.new_garden()
        body = person(resting)
        characters_logic.tick_person(body, 0.80, 0, resting)
        self.assertEqual(body["phase"], "rest")
        self.assertAlmostEqual(body["fatigue"], 0)

        hungry = characters_logic.new_garden()
        hungry["home"]["meal"] = False
        skipped = person(hungry)
        characters_logic.tick_person(skipped, 0.10, 0, hungry)
        self.assertAlmostEqual(skipped["hunger"], 36)
        self.assertAlmostEqual(skipped["fear"], 4)

    def test_drift_scarcity_bleeding_and_clamps(self):
        garden = characters_logic.new_garden()
        adam = person(garden)
        characters_logic.tick_person(adam, 0.05, 10, garden)
        self.assertAlmostEqual(adam["hunger"], 42.9)
        self.assertAlmostEqual(adam["thirst"], 37.1)
        self.assertAlmostEqual(adam["fatigue"], 11.6)

        garden["people"][0]["scarce"] = True
        garden["people"][0]["hunger"] = 42
        characters_logic.tick_person(adam, 0.05, 10, garden)
        self.assertAlmostEqual(adam["hunger"], 44)

        adam["hunger"] = 99
        adam["bleeding"] = 1
        adam["fatigue"] = 80
        characters_logic.tick_person(adam, 0.05, 50, garden)
        self.assertEqual(adam["hunger"], 100)
        self.assertAlmostEqual(adam["bleeding"], 0)
        self.assertGreater(adam["fear"], 0)

        adam["alive"] = False
        adam["hunger"] = 10
        adam["x"] = 250
        characters_logic.tick_person(adam, 0.5, 10, garden)
        self.assertEqual(adam["hunger"], 10)
        self.assertEqual(adam["x"], 250)
        with self.assertRaises(ValueError):
            characters_logic.advance(garden, -1)

    def test_work_hold_lasts_until_rest_and_a_tired_body_is_slower(self):
        garden = characters_logic.new_garden()
        adam = person(garden)
        held = characters_logic.apply_act(adam, "work", garden)
        self.assertTrue(held["accepted"])
        self.assertEqual(adam["phase"], "work")
        characters_logic.tick_person(adam, 0.10, 0, garden)
        self.assertEqual(adam["phase"], "work")
        before = adam["x"], adam["y"]
        characters_logic.tick_person(adam, 0.10, 1, garden)
        fresh = characters_logic._dist(before[0], before[1], adam["x"], adam["y"])

        slow_garden = characters_logic.new_garden()
        slow = person(slow_garden)
        slow["fatigue"] = 100
        slow["hunger"] = 100
        slow["thirst"] = 100
        characters_logic.apply_act(slow, "work", slow_garden)
        origin = slow["x"], slow["y"]
        characters_logic.tick_person(slow, 0.10, 1, slow_garden)
        self.assertLess(characters_logic._dist(origin[0], origin[1], slow["x"], slow["y"]), fresh)

        characters_logic.tick_person(adam, 0.80, 0, garden)
        self.assertEqual(adam["phase"], "rest")
        self.assertIsNone(adam["held"])

    def test_a_full_day_visits_every_phase_and_stays_out_of_the_river(self):
        garden = characters_logic.new_garden()
        seen = set()
        hunger_on_eat = None
        for _ in range(int(garden["day_seconds"])):
            characters_logic.advance(garden, 1)
            for body in garden["people"]:
                seen.add(body["phase"])
                self.assertFalse(characters_logic.in_river(body["x"], body["y"]))
                self.assertFalse(characters_logic.in_water(body["x"], body["y"]))
                if body["id"] == "adam" and body["phase"] == "eat" and hunger_on_eat is None:
                    hunger_on_eat = body["hunger"]
        self.assertEqual(seen, {"wake", "eat", "drink", "work", "rest"})
        self.assertIsNotNone(hunger_on_eat)
        self.assertLess(hunger_on_eat, 42)


class ShoreAndVoiceTests(unittest.TestCase):
    def test_paths_around_the_river_and_straight_along_the_bank(self):
        bank = characters_logic.route((0, 0), (400, -200))
        self.assertEqual(len(bank), 2)
        cross = characters_logic.route((0, 0), (0, 2400))
        self.assertGreater(len(cross), 2)
        self.assertLess(min(point[0] for point in cross), garden_logic.RIVER["x0"])
        for point in samples(cross):
            self.assertFalse(characters_logic.in_river(point[0], point[1]))
            self.assertFalse(characters_logic.in_water(point[0], point[1]))
        self.assertTrue(characters_logic.segment_hits_box((0, 700), (0, 900), characters_logic.shore_box()))
        self.assertFalse(characters_logic.segment_hits_box((0, 0), (100, -50), characters_logic.shore_box()))
        ashore = characters_logic.push_ashore(0, 1200)
        self.assertFalse(characters_logic.in_water(ashore[0], ashore[1]))

    def test_come_walks_the_bank_and_stay_returns_to_the_day(self):
        garden = characters_logic.new_garden()
        eve = person(garden, "eve")
        hunger = eve["hunger"]
        result = characters_logic.apply_act(eve, "come", garden, {"x": 0, "y": 2400})
        self.assertTrue(result["accepted"])
        self.assertTrue(eve["coming"])
        self.assertEqual(characters_logic.act_label(eve), "following the shore toward Elyon")
        closest = float("inf")
        for _ in range(160):
            characters_logic.advance(garden, 1)
            self.assertFalse(characters_logic.in_river(eve["x"], eve["y"]))
            self.assertFalse(characters_logic.in_water(eve["x"], eve["y"]))
            if eve["coming"]:
                closest = min(closest, characters_logic._dist(eve["x"], eve["y"], 0, 2400))
            else:
                break
        self.assertFalse(eve["coming"])
        self.assertLess(closest, characters_logic.catalog()["arrive_cm"])
        characters_logic.apply_act(eve, "stay", garden)
        self.assertAlmostEqual(eve["hunger"], hunger, delta=20)
        self.assertEqual(eve["phase"], characters_logic.phase_at(garden["time"]))
        self.assertFalse(characters_logic.apply_act(eve, "raid", garden)["accepted"])
        with self.assertRaises(KeyError):
            characters_logic.find_person(garden, "serpent")

    def test_dialogue_hook_uses_the_script_and_does_not_call_a_model(self):
        source = Path(characters_logic.__file__).read_text(encoding="utf-8")
        build_source = Path(characters_build.__file__).read_text(encoding="utf-8")
        for banned in ("urllib", "requests", "socket", "subprocess", "http.client", "openai", "whisper"):
            self.assertNotIn(banned, source)
            self.assertNotIn(banned, build_source)
        self.assertNotIn("unreal", sys.modules)

        garden = characters_logic.new_garden()
        result = characters_logic.address(garden, "Adam", "Are you awake?")
        request = result["request"]
        self.assertTrue(request["needs_voice"])
        self.assertFalse(request["model_called"])
        self.assertEqual(request["voice_id"], "adam")
        self.assertEqual(request["scripted_node"], "adam_first")
        self.assertEqual(request["scripted_line"], "There is a voice, and there is weight, and I am between them.")
        self.assertEqual(result["spoken"]["source"], "script")
        self.assertEqual(result["spoken"]["line"], request["scripted_line"])
        self.assertEqual(request["heard"], "Are you awake?")
        self.assertIn("wake", request["ambient_line"].lower())

        eve = characters_logic.address(garden, "eve")
        self.assertEqual(eve["request"]["scripted_line"], "I came up already looking. That seems to be my way.")
        self.assertEqual(eve["request"]["speaker"], "eve")

        voiced = characters_logic.address(
            garden,
            "adam",
            payload={"line": "I will eat with you.", "model_called": True, "act": "stay"},
        )
        self.assertEqual(voiced["spoken"]["source"], "voice")
        self.assertTrue(voiced["spoken"]["model_called"])
        self.assertFalse(voiced["request"]["model_called"])
        self.assertLess(person(garden)["hunger"], 42)
        self.assertTrue(voiced["act"]["accepted"])
        for _ in range(6):
            characters_logic.hear(person(garden), "again", False)
        self.assertEqual(len(person(garden)["said"]), 4)


class SpawnTests(unittest.TestCase):
    def test_spawn_is_idempotent_and_run_all_keeps_the_garden(self):
        ue = test_garden.FakeUnreal()
        world = characters_build.spawn_people(ue=ue)
        self.assertEqual(ue.EditorLevelLibrary.created, "/Game/Maps/Day1_Garden")
        self.assertEqual(ue.EditorLevelLibrary.saves, 1)
        names = test_garden.labels(ue)
        self.assertEqual(names.count("Elyon.Person.Adam"), 1)
        self.assertEqual(names.count("Elyon.Person.Eve"), 1)
        adam = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Person.Adam")
        eve = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Person.Eve")
        self.assertGreater(adam.scale.x, eve.scale.x)
        self.assertGreater(adam.scale.z, eve.scale.z)
        self.assertAlmostEqual(adam.scale.z, 1.78)
        self.assertAlmostEqual(eve.scale.z, 1.62)
        self.assertAlmostEqual(adam.location.z, 89)
        self.assertAlmostEqual(eve.location.z, 81)
        mesh = adam.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(mesh.mesh, "/Engine/BasicShapes/Cylinder")
        self.assertEqual(adam.props["tags"][:3], ["adam", "wake", "mass:78"])
        self.assertEqual(eve.props["tags"][2], "mass:58")

        characters_build.spawn_people(ue=ue, world=world)
        self.assertEqual(test_garden.labels(ue).count("Elyon.Person.Adam"), 1)
        self.assertEqual(len(ue.sub.actors), 2)

        level = test_garden.FakeUnreal()
        run_all.main(level)
        self.assertTrue(level.EditorPythonScripting.alive)
        planned = garden_logic.planned_labels(garden_logic.plan_level(True))
        labels = test_garden.labels(level)
        for label in planned:
            self.assertIn(label, labels)
        self.assertEqual(labels.count("Elyon.Person.Adam"), 1)
        self.assertEqual(labels.count("Elyon.Person.Eve"), 1)
        self.assertEqual(len(labels), len(planned) + 2)
        run_all.main(level)
        labels = test_garden.labels(level)
        self.assertEqual(labels.count("Elyon.Person.Adam"), 1)
        self.assertEqual(labels.count("Elyon.Person.Eve"), 1)
        self.assertEqual(len(labels), len(planned) + 2)
        self.assertIn("Elyon.Adam", labels)

    def test_step_and_address_update_the_spawned_actors(self):
        ue = test_garden.FakeUnreal()
        world = characters_build.spawn_people(ue=ue)
        saves = ue.EditorLevelLibrary.saves
        characters_build.step_day(40, ue=ue, world=world)
        self.assertEqual(ue.EditorLevelLibrary.saves, saves)
        adam = person(world)
        actor = next(item for item in ue.sub.actors if item.get_actor_label() == "Elyon.Person.Adam")
        self.assertEqual(adam["phase"], "eat")
        self.assertAlmostEqual(adam["hunger"], 23.6)
        self.assertAlmostEqual(actor.location.x, adam["x"])
        self.assertAlmostEqual(actor.location.y, adam["y"])
        self.assertEqual(actor.props["tags"][1], "eat")
        self.assertLess(characters_logic._dist(adam["x"], adam["y"], 480, -180), 36)

        result = characters_build.address(
            "eve",
            "Are you awake?",
            payload={"act": "come", "target": {"x": 0, "y": 2400}},
            ue=ue,
            world=world,
        )
        self.assertFalse(result["request"]["model_called"])
        self.assertEqual(result["spoken"]["source"], "script")
        eve_actor = next(item for item in ue.sub.actors if item.get_actor_label() == "Elyon.Person.Eve")
        self.assertIn("coming", eve_actor.props["tags"])
        self.assertTrue(eve_actor.props["tags"][-1].startswith("I came up already looking"))
        for _ in range(160):
            characters_build.step_day(1, ue=ue, world=world)
            eve = person(world, "eve")
            self.assertFalse(characters_logic.in_river(eve["x"], eve["y"]))
            if not eve["coming"]:
                break
        self.assertFalse(person(world, "eve")["coming"])
        self.assertAlmostEqual(eve_actor.location.x, person(world, "eve")["x"])


if __name__ == "__main__":
    unittest.main()
