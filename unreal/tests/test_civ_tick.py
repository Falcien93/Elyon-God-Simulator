import copy
import json
import math
import sys
import unittest
from pathlib import Path

UNREAL = Path(__file__).resolve().parents[1]
SCRIPTS = UNREAL / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import civ_rng
import civ_sim
import civ_tick
import ising_society
import kuramoto_faith


MODULES = (
    SCRIPTS / "civ_rng.py",
    SCRIPTS / "ising_society.py",
    SCRIPTS / "kuramoto_faith.py",
    SCRIPTS / "civ_tick.py",
)

FORBIDDEN = (
    "import unreal",
    "subprocess",
    "urllib",
    "socket",
    "requests",
    "llama_cpp",
    "openai",
    "http.client",
)


def _actions(world):
    return [step["action"] for step in world["last_actions"]]


def _spins(world):
    return [list(place["spins"]) for place in world["settlements"]]


def _plant(world, spin):
    for place in world["settlements"]:
        place["spins"] = [spin] * len(place["spins"])
        place["opinions"] = [float(spin)] * len(place["opinions"])
        place["magnetization"] = float(spin)


class RngTests(unittest.TestCase):
    def test_lcg_matches_the_closed_form(self):
        rng = civ_rng.lcg(1)
        self.assertAlmostEqual(rng(), 1015568748 / 4294967296.0, places=12)
        state = (1664525 * 1015568748 + 1013904223) & 0xFFFFFFFF
        self.assertAlmostEqual(rng(), state / 4294967296.0, places=12)

    def test_stream_is_seedable(self):
        first = [civ_rng.lcg(7)() for _ in range(1)]
        again = [civ_rng.lcg(7)() for _ in range(1)]
        other = [civ_rng.lcg(8)() for _ in range(1)]
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        self.assertGreaterEqual(first[0], 0.0)
        self.assertLess(first[0], 1.0)

    def test_mix_seed_stays_in_uint32(self):
        mixed = civ_rng.mix_seed(-3, 4, 9)
        self.assertEqual(mixed, civ_rng.mix_seed(-3, 4, 9))
        self.assertIsInstance(mixed, int)
        self.assertGreaterEqual(mixed, 0)
        self.assertLess(mixed, 2**32)


class DataTests(unittest.TestCase):
    def test_core_data_is_ising_and_kuramoto_only(self):
        core = civ_tick.load_core()
        self.assertEqual(core["scope"]["simulated"], ["ising", "kuramoto"])
        self.assertEqual(core["scope"]["deferred"], ["lenia", "landauer"])
        ideas = (UNREAL / "docs" / "physics-ideas.md").read_text(encoding="utf-8")
        self.assertIn(core["sources"]["kuramoto"], ideas)
        self.assertIn(core["sources"]["ising"], ideas)
        self.assertGreater(core["ising"]["miracle_field"], 4.0 * core["ising"]["J"])
        self.assertGreaterEqual(core["ising"]["width"], 2)
        self.assertGreaterEqual(core["ising"]["height"], 2)
        self.assertEqual(set(core["layouts"]), set(civ_sim.KNOWN_ENDINGS))
        for ending, places in core["layouts"].items():
            names = [place["name"] for place in places]
            self.assertEqual(len(names), len(set(names)))
            self.assertGreaterEqual(len(places), 2)
            for place in places:
                if ending == "exile":
                    self.assertEqual(place["region"], "east")
                else:
                    self.assertEqual(place["region"], "garden")


class WorldTests(unittest.TestCase):
    def test_hands_locks_the_shipped_ending_and_the_region(self):
        wonder = civ_tick.new_world(3, "hands", silence=True)
        exile = civ_tick.new_world(3, "hands", silence=False)
        self.assertEqual(wonder["ending"], "wonder")
        self.assertEqual(exile["ending"], "exile")
        self.assertTrue(all(place["region"] == "garden" for place in wonder["settlements"]))
        self.assertTrue(all(place["region"] == "east" for place in exile["settlements"]))
        self.assertEqual(exile["settlements"][0]["name"], "east camp")

    def test_unknown_ending_and_bad_seed_are_rejected(self):
        with self.assertRaises(ValueError):
            civ_tick.new_world(1, "falls")
        with self.assertRaises(TypeError):
            civ_tick.new_world(True, "harmony")
        with self.assertRaises(TypeError):
            civ_tick.new_world(1.5, "harmony")

    def test_initial_beliefs_come_from_the_seed(self):
        world = civ_tick.new_world(11, "harmony")
        width = world["width"]
        count = width * world["height"]
        for index, place in enumerate(world["settlements"]):
            rng = civ_rng.lcg(civ_rng.mix_seed(11, 0, civ_tick.INIT_SALT + index))
            expected = [1 if rng() < 0.5 else -1 for _ in range(count)]
            self.assertEqual(place["spins"], expected)
            self.assertEqual(place["opinions"], [float(spin) for spin in expected])
            self.assertLessEqual(abs(place["omega"]), world["omega_half_width"])

    def test_different_seeds_open_different_beliefs(self):
        self.assertNotEqual(
            _spins(civ_tick.new_world(1, "harmony")),
            _spins(civ_tick.new_world(2, "harmony")),
        )

    def test_tick_is_a_pure_function_of_the_seeded_world(self):
        world = civ_tick.new_world(21, "exile")
        snapshot = json.dumps(world, sort_keys=True)
        spins = copy.deepcopy(_spins(world))
        once = civ_tick.tick(world)
        twice = civ_tick.tick(world)
        self.assertEqual(once, twice)
        self.assertEqual(world["tick"], 0)
        self.assertEqual(json.dumps(world, sort_keys=True), snapshot)
        self.assertEqual(_spins(world), spins)
        self.assertIsNot(once, world)
        replay = world
        single = world
        for _ in range(8):
            replay = civ_tick.tick(replay)
            single = civ_tick.tick(single)
        self.assertEqual(replay, single)
        self.assertEqual(civ_tick.tick(world, steps=8), replay)
        self.assertEqual(replay["tick"], 8)
        self.assertEqual(replay["ending"], "exile")

    def test_reloaded_json_ticks_the_same_way(self):
        world = civ_tick.tick(civ_tick.new_world(6, "order"), steps=2)
        loaded = json.loads(json.dumps(world))
        self.assertEqual(civ_tick.tick(world), civ_tick.tick(loaded))

    def test_first_tick_builds_shelter_and_does_not_call_a_model(self):
        world = civ_tick.new_world(4, "harmony")
        nxt = civ_tick.tick(world)
        self.assertEqual(_actions(nxt), ["build", "build", "build"])
        for place in nxt["settlements"]:
            self.assertTrue(place["shelter"])
            self.assertEqual(place["prosperity"], world["settlements"][0]["prosperity"] + 2)
        self.assertTrue(nxt["events"])
        for event in nxt["events"]:
            self.assertTrue(event["needs_voice"])
            self.assertFalse(event["model_called"])
            self.assertEqual(event["role"], "leader")

    def test_ising_sweep_is_the_one_the_tick_runs(self):
        world = civ_tick.set_field(civ_tick.set_temperature(civ_tick.new_world(4, "order"), 1.2), 0.3)
        expected = []
        for index, place in enumerate(world["settlements"]):
            rng = civ_rng.lcg(civ_rng.mix_seed(world["seed"], 1, index))
            expected.append(
                ising_society.metropolis_sweep(
                    place["spins"], world["width"], world["J"], world["field"], world["temperature"], rng
                )
            )
        self.assertEqual(_spins(civ_tick.tick(world)), expected)

    def test_kuramoto_step_is_the_one_the_tick_runs(self):
        world = civ_tick.new_world(4, "order")
        expected = kuramoto_faith.step(
            [place["theta"] for place in world["settlements"]],
            [place["omega"] for place in world["settlements"]],
            world["K"],
            world["dt"],
        )
        got = civ_tick.tick(world)
        for place, theta in zip(got["settlements"], expected):
            self.assertEqual(place["theta"], theta)
        self.assertGreaterEqual(got["order_r"], 0.0)
        self.assertLessEqual(got["order_r"], 1.0 + 1e-9)
        self.assertEqual(got["faith_order"], int(round(got["order_r"] * 100.0)))

    def test_cold_consensus_holds_and_heat_breaks_it(self):
        base = civ_tick.new_world(5, "harmony")
        _plant(base, 1)
        cold = civ_tick.tick(civ_tick.set_temperature(civ_tick.set_field(base, 0.0), 0.0))
        hot = civ_tick.tick(civ_tick.set_temperature(civ_tick.set_field(base, 0.0), 100.0))
        self.assertEqual(_spins(cold), _spins(base))
        self.assertNotEqual(_spins(hot), _spins(cold))
        self.assertEqual(cold["temperature"], 0.0)
        self.assertEqual(hot["temperature"], 100.0)

    def test_gods_field_flips_an_opposed_civilization(self):
        world = civ_tick.set_temperature(civ_tick.set_field(civ_tick.new_world(9, "exile"), 0.0), 0.0)
        _plant(world, -1)
        held = civ_tick.tick(world)
        forced = civ_tick.tick(civ_tick.set_field(world, 5.0))
        self.assertTrue(all(spin == -1 for spins in _spins(held) for spin in spins))
        self.assertTrue(all(spin == 1 for spins in _spins(forced) for spin in spins))
        self.assertEqual(forced["settlements"][0]["magnetization"], 1.0)

    def test_miracle_flips_beliefs_near_critical_temperature_and_raises_k(self):
        world = civ_tick.set_field(civ_tick.new_world(2, "wonder"), 0.0)
        world = civ_tick.set_temperature(world, world["critical_temperature"])
        _plant(world, -1)
        before_k = world["K"]
        blessed = civ_tick.miracle(world)
        self.assertEqual(world["miracles"], 0)
        self.assertEqual(world["tick"], 0)
        self.assertEqual(blessed["miracles"], 1)
        self.assertEqual(blessed["tick"], 0)
        self.assertAlmostEqual(blessed["field"], world["miracle_field"])
        self.assertAlmostEqual(blessed["K"], before_k + world["miracle_coupling_gain"])
        self.assertFalse(blessed["schism"])
        landed = civ_tick.tick(blessed)
        control = civ_tick.tick(world)
        for place in landed["settlements"]:
            self.assertEqual(place["magnetization"], 1.0)
            self.assertGreater(place["faith"], 50)
        for place in control["settlements"]:
            self.assertLess(place["magnetization"], 0.5)
            self.assertTrue(any(spin == -1 for spin in place["spins"]))

    def test_low_coupling_is_a_schism_into_faith_sects(self):
        world = civ_tick.set_coupling(civ_tick.new_world(1, "harmony"), 0.0)
        for index, place in enumerate(world["settlements"]):
            place["omega"] = 0.0
            place["theta"] = index * 2.0 * math.pi / 3.0
        nxt = civ_tick.tick(world)
        self.assertTrue(nxt["schism"])
        self.assertEqual(nxt["faith_sect_count"], 3)
        self.assertLess(nxt["K"], nxt["critical_coupling"])
        whole = civ_tick.tick(civ_tick.set_coupling(civ_tick.new_world(1, "harmony"), 3.0))
        self.assertFalse(whole["schism"])

    def test_deffuant_sects_follow_the_two_blocks(self):
        world = civ_tick.set_temperature(civ_tick.set_field(civ_tick.new_world(1, "order"), 0.0), 0.0)
        width = world["width"]
        for place in world["settlements"]:
            spins = []
            for y in range(world["height"]):
                for x in range(width):
                    spins.append(-1 if x < width // 2 else 1)
            place["spins"] = spins
            place["opinions"] = [float(spin) for spin in spins]
        nxt = civ_tick.tick(world)
        for place in nxt["settlements"]:
            self.assertEqual(place["sect_count"], 2)

    def test_prophets_narrow_frequencies_once(self):
        world = civ_tick.set_temperature(civ_tick.set_field(civ_tick.new_world(8, "wonder"), 0.0), 0.0)
        _plant(world, 1)
        for place in world["settlements"]:
            place["faith"] = 70
            place["shelter"] = True
        before = [place["omega"] for place in world["settlements"]]
        before_width = world["omega_half_width"]
        heard = civ_tick.tick(world)
        after = [place["omega"] for place in heard["settlements"]]
        self.assertTrue(heard["prophets_heard"])
        self.assertEqual(after, [omega * world["prophet_narrow"] for omega in before])
        self.assertAlmostEqual(heard["omega_half_width"], before_width * world["prophet_narrow"])
        self.assertLess(heard["critical_coupling"], world["critical_coupling"])
        roles = {event["role"] for event in heard["events"]}
        self.assertIn("prophet", roles)
        self.assertIn("leader", roles)
        again = civ_tick.tick(heard)
        self.assertEqual(
            [place["omega"] for place in again["settlements"]],
            after,
        )
        self.assertTrue(any(event["role"] == "prophet" for event in again["events"]))

    def test_harmony_and_order_do_not_clash(self):
        for ending in ("harmony", "order"):
            world = civ_tick.set_temperature(
                civ_tick.set_field(civ_tick.new_world(12, ending), 0.0), 0.0
            )
            _plant(world, -1)
            for place in world["settlements"]:
                place["shelter"] = True
                place["faith"] = 0
                place["prosperity"] = 0
                place["fear"] = 100
            seen = []
            for _ in range(12):
                world = civ_tick.tick(world)
                seen.extend(_actions(world))
                self.assertEqual(world["ending"], ending)
            self.assertNotIn("clash", seen)
            if ending == "order":
                self.assertNotIn("clash", civ_sim.settlement_goals({"ending": "order"}))

    def test_exile_can_clash_without_losing_the_east(self):
        world = civ_tick.set_temperature(civ_tick.set_field(civ_tick.new_world(3, "exile"), 0.0), 0.0)
        _plant(world, -1)
        for place in world["settlements"]:
            place["shelter"] = True
            place["faith"] = 10
            place["prosperity"] = 5
            place["fear"] = 90
        before = world["settlements"][0]["population"]
        nxt = civ_tick.tick(world)
        self.assertEqual(_actions(nxt), ["clash", "clash", "clash"])
        self.assertLess(nxt["settlements"][0]["population"], before)
        self.assertTrue(all(place["region"] == "east" for place in nxt["settlements"]))
        self.assertEqual(nxt["ending"], "exile")

    def test_faith_follows_magnetization(self):
        world = civ_tick.set_temperature(civ_tick.set_field(civ_tick.new_world(1, "harmony"), 0.0), 0.0)
        _plant(world, 1)
        for place in world["settlements"]:
            place["faith"] = 50
            place["shelter"] = True
        nxt = civ_tick.tick(world)
        # Build or trade may add a point after the pull. The pull itself is halfway to 100.
        for place in nxt["settlements"]:
            self.assertGreaterEqual(place["faith"], 75)
            self.assertLessEqual(place["faith"], 100)

    def test_interventions_change_stats_and_leave_the_field_alone(self):
        world = civ_tick.new_world(5, "exile")
        field = world["field"]
        flooded = civ_tick.intervene(world, "east camp", "flood")
        camp = flooded["settlements"][0]
        self.assertEqual(camp["population"], 16 - 8)
        self.assertLess(camp["prosperity"], world["settlements"][0]["prosperity"])
        self.assertGreater(camp["fear"], world["settlements"][0]["fear"])
        self.assertEqual(flooded["field"], field)
        self.assertEqual(world["settlements"][0]["population"], 16)
        floored = civ_tick.intervene(civ_tick.intervene(flooded, "east camp", "flood"), "east camp", "flood")
        self.assertEqual(floored["settlements"][0]["population"], 1)
        shocked = civ_tick.intervene(world, "the wild bank", "divine_force")
        self.assertEqual(shocked["field"], field)
        with self.assertRaises(KeyError):
            civ_tick.intervene(world, "the grove", "blessing")
        with self.assertRaises(ValueError):
            civ_tick.intervene(world, "east camp", "smite")

    def test_every_ending_stays_locked_across_ticks(self):
        for ending in civ_sim.KNOWN_ENDINGS:
            world = civ_tick.new_world(ending.__hash__() % 50 + 1, ending)
            world = civ_tick.tick(world, steps=6)
            self.assertEqual(world["ending"], ending)
            self.assertGreaterEqual(world["order_r"], 0.0)
            self.assertLessEqual(world["order_r"], 1.0 + 1e-9)
            for place in world["settlements"]:
                self.assertEqual(place["ending"], ending)
                self.assertTrue(all(spin in (1, -1) for spin in place["spins"]))
                self.assertTrue(all(-1.0 <= opinion <= 1.0 for opinion in place["opinions"]))
                self.assertGreaterEqual(place["population"], 1)

    def test_setters_reject_bad_numbers(self):
        world = civ_tick.new_world(1, "order")
        with self.assertRaises(ValueError):
            civ_tick.set_temperature(world, -0.01)
        with self.assertRaises(ValueError):
            civ_tick.set_coupling(world, -1.0)
        with self.assertRaises(TypeError):
            civ_tick.set_field(world, True)
        with self.assertRaises(ValueError):
            civ_tick.tick(world, steps=0)
        with self.assertRaises(ValueError):
            civ_tick.tick(world, steps=True)
        broken = civ_tick.new_world(1, "order")
        broken["settlements"][0]["ending"] = "exile"
        with self.assertRaises(ValueError):
            civ_tick.tick(broken)

    def test_modules_do_not_import_unreal_or_a_model(self):
        for path in MODULES:
            source = path.read_text(encoding="utf-8")
            for token in FORBIDDEN:
                self.assertNotIn(token, source)
            lowered = source.lower()
            self.assertNotIn("def lenia", lowered)
            self.assertNotIn("def landauer", lowered)
        text = (SCRIPTS / "civ_tick.py").read_text(encoding="utf-8").lower()
        self.assertIn("does not import", text)
        self.assertIn("landauer cost stay", text)


if __name__ == "__main__":
    unittest.main()
