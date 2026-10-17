"""Tests for the seed-based multiverse."""

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

UNREAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(UNREAL))

from multiverse import (  # noqa: E402
    DERIVATION,
    MASK64,
    MAX_NODES,
    PHYSICS_COUNT,
    CatalogError,
    LocalRngSource,
    Multiverse,
    QuantumSeedSource,
    QuantumSourceUnavailable,
    SaveError,
    SeedSource,
    UnknownChoice,
    UnknownUniverse,
    derive_constants,
    format_constant,
    format_seed,
    major_choices,
    mix_seed,
    normalize_seed,
    physics_fingerprint,
    physics_specs,
    splitmix64,
)
from multiverse import catalog, seeds  # noqa: E402
from multiverse.tree import _check_links  # noqa: E402

PHYSICS_IDS = (
    "gravity",
    "light_speed",
    "planck_ratio",
    "fine_structure",
    "electron_proton_ratio",
    "strong_coupling",
    "weak_coupling",
    "cosmological_ratio",
    "baryon_fraction",
    "dark_matter_fraction",
    "dark_energy_fraction",
    "expansion_rate",
    "curvature",
    "day_length_hours",
    "year_length_days",
    "axial_tilt_deg",
    "mean_temperature_c",
    "atmosphere_pressure_atm",
    "oxygen_fraction",
    "water_freezing_c",
    "water_boiling_c",
    "world_radius_km",
    "world_mass_earths",
    "star_luminosity_suns",
    "orbital_radius_au",
    "magnetic_field_gauss",
    "air_density_kg_m3",
    "sound_speed_m_s",
    "time_flow",
    "chemistry_rate",
    "mutation_rate",
)

CHOICE_IDS = (
    "let_there_be_light",
    "leave_darkness",
    "ending_harmony",
    "ending_exile",
    "ending_wonder",
    "ending_order",
    "keep_in_valley",
    "send_out",
    "bless_pact",
    "withhold_pact",
    "stop_raid",
    "allow_raid",
    "send_rain",
    "send_drought",
    "send_flood",
    "bless_present",
    "keep_commons",
)

FORBIDDEN_MODULES = {
    "socket",
    "ssl",
    "http",
    "urllib",
    "urllib3",
    "requests",
    "httpx",
    "aiohttp",
    "subprocess",
    "ftplib",
    "smtplib",
    "telnetlib",
    "websocket",
    "websockets",
}
FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "hash"}
FORBIDDEN_ATTRS = {"urlopen", "system", "popen"}


def _signature(seed):
    specs = physics_specs()
    derived = derive_constants(seed)
    return tuple(format_constant(derived[spec.id], spec.places) for spec in specs)


class SplitMixTests(unittest.TestCase):
    def test_published_vector(self):
        state, first = splitmix64(0)
        self.assertEqual(first, 0xE220A8397B1DCDAF)
        _state, second = splitmix64(state)
        self.assertEqual(second, 0x6E789E6AA1B965F4)

    def test_hex_state_and_mask(self):
        _state, word = splitmix64("0x0")
        self.assertEqual(word, 0xE220A8397B1DCDAF)
        self.assertLessEqual(word, MASK64)
        with self.assertRaises(ValueError):
            splitmix64(1 << 64)

    def test_seeded_source_draws_splitmix_not_the_seed_itself(self):
        drawn = LocalRngSource(1).next_seed()
        self.assertEqual(drawn, splitmix64(1)[1])
        self.assertNotEqual(drawn, 1)


class NormalizeTests(unittest.TestCase):
    def test_ints_and_hex(self):
        self.assertEqual(normalize_seed(0), 0)
        self.assertEqual(normalize_seed(MASK64), MASK64)
        self.assertEqual(normalize_seed("0x1"), 1)
        self.assertEqual(normalize_seed(" 0X1 "), 1)
        self.assertEqual(normalize_seed("0000000000000001"), 1)
        self.assertEqual(normalize_seed("10"), 16)
        self.assertEqual(format_seed(1), "0000000000000001")
        self.assertEqual(format_seed("0x1"), "0000000000000001")

    def test_rejects_bad_seeds(self):
        for value in (True, False, None, 1.0, 1.5, "", "0x", "0x10000000000000000", "zz", -1, 1 << 64):
            with self.assertRaises((TypeError, ValueError)):
                normalize_seed(value)


class MixSeedTests(unittest.TestCase):
    def test_goldens(self):
        self.assertEqual(mix_seed(0, "send_rain"), 0x8FD1F725746BB0A4)
        self.assertEqual(mix_seed(1, "let_there_be_light"), 0xC82251958A7E1D07)
        self.assertEqual(mix_seed("0x1", "let_there_be_light"), 0xC82251958A7E1D07)

    def test_choice_and_parent_both_matter(self):
        rain = mix_seed(1, "send_rain")
        drought = mix_seed(1, "send_drought")
        other_parent = mix_seed(2, "send_rain")
        self.assertNotEqual(rain, drought)
        self.assertNotEqual(rain, other_parent)
        self.assertEqual(mix_seed(1, "send_rain"), rain)

    def test_every_catalog_choice_is_unique(self):
        seeds_for = [mix_seed(0, choice_id) for choice_id in CHOICE_IDS]
        self.assertEqual(len(set(seeds_for)), len(CHOICE_IDS))
        for choice_id in CHOICE_IDS:
            self.assertNotEqual(mix_seed(0, choice_id), 0)

    def test_rejects_empty_nul_and_non_strings(self):
        for choice in ("", "send\x00rain", None, 3):
            with self.assertRaises((TypeError, ValueError)):
                mix_seed(1, choice)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, payload):
        path = self.directory / name
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_real_catalog_shape(self):
        specs = physics_specs()
        self.assertEqual(catalog.DATA_DIR, UNREAL / "Data")
        self.assertEqual(len(specs), PHYSICS_COUNT)
        self.assertEqual(tuple(spec.id for spec in specs), PHYSICS_IDS)
        by_id = {spec.id: spec for spec in specs}
        self.assertLess(by_id["water_freezing_c"].maximum, by_id["water_boiling_c"].minimum)
        self.assertGreater(by_id["gravity"].minimum, 0)
        self.assertGreater(by_id["light_speed"].minimum, 0)
        self.assertGreaterEqual(by_id["oxygen_fraction"].minimum, 0)
        self.assertLessEqual(by_id["oxygen_fraction"].maximum, 1)
        for spec in specs:
            self.assertLess(spec.minimum, spec.maximum)
            self.assertGreaterEqual(spec.nominal, spec.minimum)
            self.assertLessEqual(spec.nominal, spec.maximum)
            self.assertGreaterEqual(spec.places, 0)
            self.assertLessEqual(spec.places, 8)
        choices = major_choices()
        self.assertEqual(tuple(choice.id for choice in choices), CHOICE_IDS)
        labels = [choice.label for choice in choices]
        self.assertEqual(len(labels), len(set(labels)))
        groups = {choice.id: choice.group for choice in choices}
        self.assertEqual(groups["let_there_be_light"], "light")
        self.assertEqual(groups["ending_harmony"], "ending")
        self.assertEqual(groups["keep_in_valley"], "valley")
        self.assertEqual(groups["bless_pact"], "covenant")
        self.assertEqual(groups["send_rain"], "sky")
        self.assertEqual(groups["bless_present"], "present")
        self.assertEqual(physics_fingerprint(), "6172e465e65d0bcd")
        self.assertEqual(physics_fingerprint(), physics_fingerprint())

    def test_doc_names_every_id_and_the_worked_example(self):
        doc = (UNREAL / "docs" / "multiverse.md").read_text(encoding="utf-8")
        readme = (UNREAL / "README.md").read_text(encoding="utf-8")
        for spec_id in PHYSICS_IDS:
            self.assertIn(f"`{spec_id}`", doc)
        for choice_id in CHOICE_IDS:
            self.assertIn(f"`{choice_id}`", doc)
        for token in (
            DERIVATION,
            "15.031",
            "373734527",
            "1.471003",
            "c82251958a7e1d07",
            "e220a8397b1dcdaf",
            "os.urandom",
            "4096",
            "SHA-256",
        ):
            self.assertIn(token, doc)
        self.assertIn("docs/multiverse.md", readme)
        self.assertIn("one install package", readme)
        self.assertIn("free local LLM", readme)

    def test_bad_physics_files(self):
        row = {
            "id": "gravity",
            "name": "Surface gravity",
            "unit": "m/s^2",
            "nominal": 9.81,
            "min": 2,
            "max": 25,
            "places": 3,
        }
        cases = [
            {"format": 1, "constants": []},
            {"format": 2, "constants": [row]},
            {"format": 1, "constants": [row], "extra": True},
            {"format": 1, "note": 1, "constants": []},
            {"format": 1, "constants": [{**row, "places": 9}]},
            {"format": 1, "constants": [{**row, "min": 25, "max": 2, "nominal": 25}]},
            {"format": 1, "constants": [{**row, "min": 2, "max": 2, "nominal": 2}]},
            {"format": 1, "constants": [{**row, "nominal": 100}]},
            {"format": 1, "constants": [{**row, "min": True}]},
            {"format": 1, "constants": [row, {**row, "id": "gravity"}]},
            [],
        ]
        for payload in cases:
            path = self._write("physics.json", payload)
            with self.assertRaises(CatalogError):
                physics_specs(path)
        text = self._write("broken.json", "{")
        with self.assertRaises(CatalogError):
            physics_specs(text)
        infinite = self._write(
            "inf.json",
            '{"format": 1, "constants": [{"id": "gravity", "name": "Surface gravity", '
            '"unit": "m/s^2", "nominal": 9.81, "min": 2, "max": 1e309, "places": 3}]}',
        )
        with self.assertRaises(CatalogError):
            physics_specs(infinite)
        self.assertEqual(len(physics_specs()), PHYSICS_COUNT)

    def test_bad_choice_files(self):
        good = {
            "id": "send_rain",
            "label": "Send rain",
            "group": "sky",
            "summary": "Rain fills the stores.",
        }
        cases = [
            {"format": 1, "choices": []},
            {"format": 1, "choices": [{**good, "id": "Send_rain"}]},
            {"format": 1, "choices": [{**good, "id": "send/rain"}]},
            {"format": 1, "choices": [{**good, "summary": "  "}]},
            {"format": 1, "choices": [good, {**good, "id": "send_drought", "label": "Send rain"}]},
            {"format": 1, "choices": [good, good]},
        ]
        for payload in cases:
            path = self._write("choices.json", payload)
            with self.assertRaises(CatalogError):
                major_choices(path)
        self.assertEqual(tuple(choice.id for choice in major_choices()), CHOICE_IDS)


class DeriveTests(unittest.TestCase):
    def test_seed_one_worked_example(self):
        derived = derive_constants(1)
        self.assertEqual(derive_constants("0x1"), derived)
        self.assertEqual(derive_constants("0000000000000001"), derived)
        self.assertEqual(tuple(derived), PHYSICS_IDS)
        self.assertEqual(format_constant(derived["gravity"], 3), "15.031")
        self.assertEqual(format_constant(derived["light_speed"], 0), "373734527")
        self.assertEqual(format_constant(derived["planck_ratio"], 6), "1.471003")

    def test_bands_and_decimal_roundtrip(self):
        specs = physics_specs()
        seeds_to_try = list(range(200)) + [MASK64]
        gravities = set()
        for seed in range(1000):
            gravities.add(format_constant(derive_constants(seed)["gravity"], 3))
        self.assertGreaterEqual(len(gravities), 900)
        for seed in seeds_to_try:
            derived = derive_constants(seed)
            self.assertEqual(derive_constants(seed), derived)
            for spec in specs:
                value = derived[spec.id]
                self.assertGreaterEqual(value, spec.minimum)
                self.assertLessEqual(value, spec.maximum)
                self.assertIsInstance(value, float)
                text = format_constant(value, spec.places)
                self.assertEqual(format_constant(float(text), spec.places), text)

    def test_every_bit_flip_changes_the_universe(self):
        base = _signature(1)
        for bit in range(64):
            self.assertNotEqual(_signature(1 ^ (1 << bit)), base)


class TreeTests(unittest.TestCase):
    def test_root_and_worked_child(self):
        world = Multiverse(1)
        self.assertEqual(world.root.seed, 1)
        self.assertEqual(world.root.id, "root")
        self.assertIsNone(world.root.parent_id)
        self.assertIsNone(world.root.choice_id)
        self.assertEqual(world.root.depth, 0)
        self.assertEqual(len(world), 1)
        self.assertEqual(world.focus.id, "root")
        child = world.branch("let_there_be_light")
        self.assertEqual(child.seed, 0xC82251958A7E1D07)
        self.assertEqual(child.id, "root/let_there_be_light")
        self.assertEqual(child.parent_id, "root")
        self.assertEqual(child.choice_id, "let_there_be_light")
        self.assertEqual(child.depth, 1)
        self.assertEqual(child.constants, derive_constants(child.seed))
        self.assertNotEqual(_signature(child.seed), _signature(world.root.seed))
        self.assertEqual(world.focus.id, child.id)
        self.assertEqual(world.choice_path(), ("let_there_be_light",))
        self.assertEqual(tuple(item.id for item in world.lineage()), ("root", child.id))

    def test_constants_are_frozen(self):
        world = Multiverse(1)
        with self.assertRaises(TypeError):
            world.root.constants["gravity"] = 0
        with self.assertRaises(AttributeError):
            world.root.child_ids.append("root/send_rain")

    def test_idempotent_branch_and_siblings(self):
        world = Multiverse(1)
        held = world.root
        first = world.branch("send_rain", follow=False)
        self.assertEqual(held.child_ids, ())
        self.assertEqual(world.root.child_ids, ("root/send_rain",))
        self.assertEqual(world.focus.id, "root")
        again = world.branch("send_rain")
        self.assertIs(again, first)
        self.assertEqual(len(world), 2)
        self.assertEqual(world.focus.id, first.id)
        world.branch("send_drought", parent_id="root", follow=False)
        self.assertEqual(
            world.root.child_ids,
            ("root/send_rain", "root/send_drought"),
        )
        self.assertEqual(world.focus.id, first.id)
        self.assertNotEqual(world.get("root/send_rain").seed, world.get("root/send_drought").seed)

    def test_grandchild_mixes_the_child_seed(self):
        world = Multiverse(1)
        rain = world.branch("send_rain")
        harmony = world.branch("ending_harmony")
        present = world.branch("bless_present")
        self.assertEqual(harmony.seed, mix_seed(rain.seed, "ending_harmony"))
        self.assertNotEqual(harmony.seed, mix_seed(1, "ending_harmony"))
        self.assertEqual(
            present.id,
            "root/send_rain/ending_harmony/bless_present",
        )
        self.assertEqual(
            world.choice_path(),
            ("send_rain", "ending_harmony", "bless_present"),
        )
        self.assertEqual(present.depth, 3)

    def test_every_choice_branches_from_root_and_from_a_child(self):
        world = Multiverse("0x10")
        again = Multiverse("10")
        self.assertEqual(world.root.seed, again.root.seed)
        for choice_id in CHOICE_IDS:
            child = world.branch(choice_id, parent_id="root", follow=False)
            other = again.branch(choice_id, parent_id="root", follow=False)
            self.assertEqual(child.seed, other.seed)
            self.assertEqual(child.seed, mix_seed(world.root.seed, choice_id))
            grandchild = world.branch("keep_commons", parent_id=child.id, follow=False)
            self.assertEqual(grandchild.seed, mix_seed(child.seed, "keep_commons"))
        self.assertEqual(len(world.children("root")), len(CHOICE_IDS))
        self.assertEqual(again.to_dict()["nodes"][0]["seed"], world.to_dict()["nodes"][0]["seed"])

    def test_unknown_choice_and_unknown_parent_add_nothing(self):
        world = Multiverse(1)
        for choice in ("Send_rain", "", "not_a_choice", None, 4):
            with self.assertRaises(UnknownChoice):
                world.branch(choice)
        self.assertEqual(len(world), 1)
        with self.assertRaises(UnknownUniverse) as caught:
            world.branch("send_rain", parent_id="root/missing")
        self.assertIn("root/missing", str(caught.exception))
        with self.assertRaises(UnknownUniverse):
            world.focus_on("missing")
        self.assertEqual(len(world), 1)

    def test_parent_constants_stay_put(self):
        fresh = Multiverse(1)
        world = Multiverse(1)
        world.branch("send_flood")
        self.assertEqual(world.root.constants, fresh.root.constants)
        self.assertEqual(world.root.seed, fresh.root.seed)


class SaveLoadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _world(self):
        world = Multiverse(1)
        world.branch("let_there_be_light")
        world.branch("send_rain")
        world.branch("send_drought", parent_id="root", follow=False)
        return world

    def test_roundtrip_bytes_and_focus(self):
        world = self._world()
        path = self.directory / "multiverse.json"
        world.save(path)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("\r", text)
        self.assertTrue(text.endswith("\n"))
        self.assertNotIn("http", text)
        self.assertNotIn("api_key", text)
        loaded = Multiverse.load(path)
        self.assertEqual(loaded.to_dict(), world.to_dict())
        self.assertEqual(loaded.focus.id, "root/let_there_be_light/send_rain")
        loaded.branch("ending_order")
        second = self.directory / "again.json"
        loaded.save(second)
        self.assertEqual(Multiverse.load(second).to_dict(), loaded.to_dict())
        world.save(path)
        same = path.read_bytes()
        world.save(path)
        self.assertEqual(path.read_bytes(), same)

    def test_node_order_does_not_change_the_tree(self):
        world = self._world()
        payload = world.to_dict()
        payload["nodes"].reverse()
        loaded = Multiverse.from_dict(payload)
        self.assertEqual(loaded.focus.id, world.focus.id)
        self.assertEqual(
            {node["id"]: node for node in loaded.to_dict()["nodes"]},
            {node["id"]: node for node in world.to_dict()["nodes"]},
        )

    def test_tampered_saves(self):
        world = self._world()
        base = world.to_dict()

        def miss(mutate, token):
            payload = json.loads(json.dumps(base))
            mutate(payload)
            with self.assertRaises(SaveError) as caught:
                Multiverse.from_dict(payload)
            self.assertIn(token, str(caught.exception))

        miss(lambda payload: payload.__setitem__("format", 2), "format")
        miss(lambda payload: payload.__setitem__("derivation", "other"), "derivation")
        miss(lambda payload: payload.__setitem__("physics", "0000000000000000"), "fingerprint")
        miss(lambda payload: payload.__setitem__("focus_id", "missing"), "focus_id")
        miss(lambda payload: payload.__setitem__("extra", True), "save keys")
        miss(lambda payload: payload.__setitem__("nodes", []), "no universes")
        miss(lambda payload: payload["nodes"][1].__setitem__("seed", "0000000000000002"), "seed")
        miss(lambda payload: payload["nodes"][0]["constants"].__setitem__("gravity", "1.000"), "gravity")
        miss(lambda payload: payload["nodes"][0].__setitem__("seed", 1), "seed")
        miss(lambda payload: payload["nodes"][0].__setitem__("seed", "000000000000000A"), "seed")
        miss(lambda payload: payload["nodes"][0].__setitem__("child_ids", "root/let_there_be_light"), "child_ids")
        miss(lambda payload: payload["nodes"][0].__setitem__("depth", True), "depth")
        miss(lambda payload: payload["nodes"][0]["constants"].__setitem__("gravity", 15.031), "decimal")
        miss(lambda payload: payload["nodes"][0]["constants"].pop("gravity"), "constants")
        miss(lambda payload: payload["nodes"][0].__setitem__("child_ids", []), "not listed")
        miss(
            lambda payload: payload["nodes"][0].__setitem__(
                "child_ids",
                ["root/let_there_be_light", "root/missing"],
            ),
            "missing child",
        )
        miss(lambda payload: payload["nodes"].pop(0), "one root")

        capped = json.loads(json.dumps(base))
        capped["nodes"] = [{}] * (MAX_NODES + 1)
        with self.assertRaises(SaveError) as caught:
            Multiverse.from_dict(capped)
        self.assertIn("4096", str(caught.exception))

    def test_cycle_guard(self):
        with self.assertRaises(SaveError) as caught:
            _check_links(
                {
                    "a": {"parent_id": "b", "child_ids": []},
                    "b": {"parent_id": "a", "child_ids": []},
                }
            )
        self.assertIn("cycles", str(caught.exception))

    def test_load_io_errors(self):
        missing = self.directory / "missing.json"
        with self.assertRaises(SaveError) as caught:
            Multiverse.load(missing)
        self.assertIn("could not read", str(caught.exception))
        with self.assertRaises(SaveError) as caught:
            Multiverse.load(self.directory)
        self.assertIn("could not read", str(caught.exception))
        broken = self.directory / "broken.json"
        broken.write_text("{", encoding="utf-8")
        with self.assertRaises(SaveError) as caught:
            Multiverse.load(broken)
        self.assertIn("not JSON", str(caught.exception))
        with self.assertRaises(SaveError):
            Multiverse.from_dict([1, 2])
        with self.assertRaises(SaveError) as caught:
            Multiverse(1).save(self.directory)
        self.assertIn("could not write", str(caught.exception))


class SeedSourceTests(unittest.TestCase):
    def test_local_replay_and_urandom(self):
        first = LocalRngSource(1)
        second = LocalRngSource("0x1")
        self.assertEqual(
            [first.next_seed() for _ in range(5)],
            [second.next_seed() for _ in range(5)],
        )
        for seed in (first.next_seed(), LocalRngSource().next_seed()):
            self.assertIsInstance(seed, int)
            self.assertGreaterEqual(seed, 0)
            self.assertLessEqual(seed, MASK64)

        original = seeds.os.urandom
        try:
            def forbid(_count):
                raise AssertionError("seeded local RNG called os.urandom")

            seeds.os.urandom = forbid
            LocalRngSource(7).next_seed()

            calls = []

            def fake(count):
                calls.append(count)
                return b"\x00" * 7 + b"\x2a"

            seeds.os.urandom = fake
            self.assertEqual(LocalRngSource().next_seed(), 0x2A)
            self.assertEqual(calls, [8])
        finally:
            seeds.os.urandom = original

    def test_originate_draws_once(self):
        class Once(SeedSource):
            def __init__(self):
                self.calls = 0

            def next_seed(self):
                self.calls += 1
                return 5

        source = Once()
        world = Multiverse.originate(source)
        world.branch("send_rain")
        world.branch("send_drought")
        self.assertEqual(source.calls, 1)
        self.assertEqual(world.root.seed, 5)
        self.assertEqual(len(Multiverse.originate(LocalRngSource(3))), 1)
        with self.assertRaises(TypeError):
            Multiverse.originate(object())

        class Bad(SeedSource):
            def next_seed(self):
                return -1

        with self.assertRaises(ValueError):
            Multiverse.originate(Bad())

    def test_quantum_stub(self):
        with self.assertRaises(QuantumSourceUnavailable) as caught:
            QuantumSeedSource().next_seed()
        self.assertIn("network", str(caught.exception))
        with self.assertRaises(TypeError) as caught:
            QuantumSeedSource("https://example.invalid/qrng")
        self.assertIn("URL", str(caught.exception))
        with self.assertRaises(TypeError):
            QuantumSeedSource(b"\x00" * 8)
        self.assertEqual(QuantumSeedSource(lambda: b"\xff" * 8).next_seed(), MASK64)
        self.assertEqual(QuantumSeedSource(lambda: bytearray(b"\x00" * 7 + b"\x2a")).next_seed(), 0x2A)
        calls = {"n": 0}

        def provider():
            calls["n"] += 1
            return b"\x01" + b"\x00" * 7

        self.assertEqual(QuantumSeedSource(provider).next_seed(), 1 << 56)
        self.assertEqual(calls["n"], 1)
        for raw in (b"\x00" * 7, None, "eightbyt", [0] * 8):
            with self.assertRaises(ValueError):
                QuantumSeedSource(lambda raw=raw: raw).next_seed()

        original = seeds.os.urandom

        def forbid(_count):
            raise AssertionError("quantum stub called os.urandom")

        seeds.os.urandom = forbid
        try:
            QuantumSeedSource(lambda: b"\x00" * 8).next_seed()
        finally:
            seeds.os.urandom = original

        world = Multiverse.originate(QuantumSeedSource(lambda: b"\x00" * 8))
        self.assertEqual(world.root.seed, 0)


class PackageSafetyTests(unittest.TestCase):
    def test_no_network_imports_or_dynamic_exec(self):
        package = UNREAL / "multiverse"
        files = list(package.glob("*.py"))
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split(".")[0], FORBIDDEN_MODULES, path.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], FORBIDDEN_MODULES, path.name)
                elif isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name):
                        self.assertNotIn(func.id, FORBIDDEN_NAMES, path.name)
                    elif isinstance(func, ast.Attribute):
                        self.assertNotIn(func.attr, FORBIDDEN_ATTRS, path.name)

    def test_import_does_not_pull_the_editor_module(self):
        self.assertNotIn("unreal", sys.modules)


if __name__ == "__main__":
    unittest.main()
