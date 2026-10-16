import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import level_build
import test_garden
import voice_logic
import voice_session

SAMPLES = ("LIGHT", "WATER", "GROW", "CALM", "DESTROY")


def _boom(_prompt):
    raise AssertionError("the phrase matcher should not call the model")


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.table = voice_logic.load_table()

    def test_table_lists_the_five_starter_intents(self):
        self.assertEqual([item["id"] for item in self.table["intents"]], list(SAMPLES))
        light = self.table["by_id"]["LIGHT"]["phrases"]
        for phrase in ("let there be light", "light", "bring forth light"):
            self.assertIn(phrase, light)

    def test_light_synonyms_stay_on_the_phrase_path(self):
        for line in ("let there be light", "Light!", "bring forth light", "elyon, let there be light"):
            hit = voice_logic.resolve_utterance(line, self.table, llm=_boom)
            self.assertEqual(hit["id"], "LIGHT", line)
            self.assertEqual(hit["via"], "phrase")
            self.assertFalse(hit["model_called"])

    def test_other_starter_phrases(self):
        cases = {
            "fill the river": "WATER",
            "bring the rain": "WATER",
            "make it rain": "WATER",
            "let the garden grow": "GROW",
            "be still": "CALM",
            "lightning": "DESTROY",
            "lightning strike": "DESTROY",
        }
        for line, intent_id in cases.items():
            hit = voice_logic.resolve_utterance(line, self.table, llm=_boom)
            self.assertEqual(hit["id"], intent_id, line)
            self.assertFalse(hit["model_called"])

    def test_later_word_wins_a_tie(self):
        hit = voice_logic.match_phrase("light the lake", self.table)
        self.assertEqual(hit["id"], "WATER")

    def test_sample_phrases_and_keyboard_map(self):
        for line, intent_id in zip(self.table["phraseSamples"], SAMPLES):
            hit = voice_logic.resolve_utterance(line, self.table, llm=_boom)
            self.assertEqual(hit["id"], intent_id, line)
        self.assertEqual(voice_logic.command_for_key("One", self.table)["id"], "LIGHT")
        self.assertEqual(voice_logic.command_for_key("V", self.table)["type"], "push_to_talk")
        self.assertEqual(voice_logic.command_for_key("P", self.table, 1)["text"], "fill the river")

    def test_unknown_line_skips_a_missing_model(self):
        hit = voice_logic.resolve_utterance("hello", self.table, llm=None)
        self.assertIsNone(hit["id"])
        self.assertFalse(hit["model_called"])
        self.assertEqual(hit["via"], "none")

    def test_model_is_only_the_fallback(self):
        def llm(_prompt):
            return 'Sure {"intent":"GROW","confidence":0.8}'

        hit = voice_logic.resolve_utterance("hello", self.table, llm=llm)
        self.assertEqual(hit["id"], "GROW")
        self.assertEqual(hit["via"], "llm")
        self.assertTrue(hit["model_called"])
        self.assertIsNone(voice_logic.parse_llm_json("not json", self.table))
        self.assertIsNone(voice_logic.parse_llm_json('{"intent":"NONE","confidence":0.9}', self.table))
        self.assertIsNone(voice_logic.parse_llm_json('{"intent":"GROW","confidence":0.2}', self.table))
        prompt = voice_logic.llm_prompt("hello", self.table)
        for intent_id in SAMPLES:
            self.assertIn(intent_id, prompt)
        self.assertIn("JSON", prompt)

    def test_duplicate_ids_are_rejected(self):
        path = ROOT / "Data" / "intents.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["intents"].append(dict(payload["intents"][0]))
        copy = ROOT / "Data" / "intents-duplicate.json"
        copy.write_text(json.dumps(payload), encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                voice_logic.load_table(copy)
        finally:
            copy.unlink()


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.table = voice_logic.load_table()

    def _apply(self, line, world=None, gaze=(0.0, -200.0, 40.0)):
        resolved = voice_logic.resolve_utterance(line, self.table, llm=_boom)
        return voice_logic.apply_intent(world or voice_logic.new_world(), resolved, gaze)

    def test_light_lifts_a_dark_garden(self):
        dark = voice_logic.new_world()
        dark["light"] = "darkness"
        dark["sun"] = 0.02
        dark["skylight"] = 0.02
        world = self._apply("let there be light", dark)
        self.assertEqual(world["light"], "dawn")
        self.assertEqual(world["sun"], voice_logic.dawn_sun_lux())
        self.assertGreaterEqual(world["skylight"], 1.35)

    def test_water_fills_then_rains(self):
        once = self._apply("fill the river")
        self.assertEqual(once["water"], 1.0)
        self.assertFalse(once["rain"])
        twice = self._apply("bring the rain", once)
        self.assertTrue(twice["rain"])

    def test_grow_calm_and_destroy(self):
        grown = self._apply("let the garden grow", gaze=(5.0, 6.0, 7.0))
        labels = [point["label"] for point in grown["growth"]]
        self.assertEqual(labels, [f"Elyon.Growth.{index:02d}" for index in range(1, 9)])
        self.assertEqual(grown["pcg"]["graph"], "/Game/PCG/GrowAroundGaze")
        self.assertEqual(grown["pcg"]["count"], 8)
        calm = self._apply("be still")
        self.assertEqual(calm["wind"], 0.0)
        self.assertEqual(calm["storm"], 0.0)
        self.assertEqual(calm["clouds"], 0.15)
        struck = self._apply("lightning strike", gaze=(3.0, 4.0, 5.0))
        self.assertEqual(struck["strikes"][0]["impulse"], 25000)
        self.assertTrue(struck["strikes"][0]["lightning"])
        self.assertEqual(struck["strikes"][0]["at"], [3.0, 4.0, 5.0])


class ToolingTests(unittest.TestCase):
    def test_whisper_keeps_the_gpu_unless_asked(self):
        table = voice_logic.load_table()
        gpu = voice_logic.whisper_command("take.wav", table, "whisper-cli", "ggml-small.en.bin")
        self.assertNotIn("-ng", gpu)
        self.assertEqual(gpu[:6], ["whisper-cli", "-m", "ggml-small.en.bin", "-f", "take.wav", "-l"])
        cpu = json.loads(json.dumps(table))
        cpu["stt"]["gpu"] = False
        self.assertIn("-ng", voice_logic.whisper_command("take.wav", cpu, "whisper-cli", "model.bin"))

    def test_model_choice_prefers_small_en(self):
        table = voice_logic.load_table()
        small = voice_logic.choose_whisper_model(table, lambda path: "small.en" in path)
        self.assertIn("ggml-small.en.bin", small)
        base = voice_logic.choose_whisper_model(table, lambda path: path.endswith("ggml-base.en.bin"))
        self.assertTrue(base.endswith("ggml-base.en.bin"))

    def test_record_command_is_a_short_wav_list(self):
        command = voice_logic.ffmpeg_record_command("take.wav", spec="pulse:default")
        self.assertIsInstance(command, list)
        self.assertEqual(command[command.index("-ar") + 1], "16000")
        self.assertEqual(command[command.index("-ac") + 1], "1")
        self.assertEqual(command[command.index("-t") + 1], "4")
        self.assertNotIsInstance(command, str)

    def test_matcher_module_does_not_spawn_processes(self):
        source = (ROOT / "Scripts" / "voice_logic.py").read_text(encoding="utf-8")
        session = (ROOT / "Scripts" / "voice_session.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertIn("shell=False", session)
        self.assertNotIn("shell=True", session)

    def test_missing_binaries_do_not_spawn(self):
        table = voice_logic.load_table()
        for key in (
            "ELYON_WHISPER",
            "ELYON_WHISPER_MODEL",
            "ELYON_LLAMA",
            "ELYON_LLAMA_MODEL",
            "ELYON_FFMPEG",
            "ELYON_FFMPEG_INPUT",
        ):
            os.environ.pop(key, None)

        def boom(*_args, **_kwargs):
            raise AssertionError("subprocess ran")

        original = voice_session.subprocess.run
        voice_session.subprocess.run = boom
        try:
            self.assertIsNone(voice_session.capture_transcript(table))
            self.assertIsNone(voice_session.ask_local_llm("hello", table))
        finally:
            voice_session.subprocess.run = original

    def test_llama_command_is_json_only(self):
        table = voice_logic.load_table()
        command = voice_logic.llama_command("hi", table, "llama-cli", "Qwen3-4B.gguf")
        self.assertEqual(command[command.index("-n") + 1], "80")
        self.assertIn("--temp", command)
        self.assertIn("-no-cnv", command)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.ue = test_garden.FakeUnreal()
        level_build.build(dawn=True, ue=self.ue)
        level_build.let_there_be_light(False, ue=self.ue)
        self.state = voice_session.install(self.ue, llm=None, runner=None)

    def _actor(self, label):
        return next(actor for actor in self.ue.sub.actors if actor.get_actor_label() == label)

    def test_install_shows_a_subtitle_and_run_all_stays_open(self):
        self.assertIn("voice", self._actor("Elyon.VoiceSubtitle").props["tags"])
        ue = test_garden.FakeUnreal()
        import run_all

        run_all.main(ue)
        self.assertTrue(ue.EditorPythonScripting.alive)
        self.assertIn("Elyon.VoiceSubtitle", [actor.get_actor_label() for actor in ue.sub.actors])

    def test_number_key_brings_the_dawn(self):
        voice_session.press(self.ue, self.state, "One")
        sun = self._actor("Elyon.Sun").get_component_by_class(self.ue.DirectionalLightComponent)
        sky = self._actor("Elyon.SkyLight").get_component_by_class(self.ue.SkyLightComponent)
        self.assertEqual(sun.props["intensity"], voice_logic.dawn_sun_lux())
        self.assertGreaterEqual(sky.props["intensity"], 1.35)
        self.assertIn("Let there be light.", self._actor("Elyon.VoiceSubtitle").props["tags"])

    def test_water_fills_the_river_then_rains(self):
        voice_session.press(self.ue, self.state, "Two")
        river = self._actor("Elyon.River")
        self.assertEqual(river.location.z, 20.0)
        self.assertEqual(river.scale.z, 0.45)
        self.assertFalse(any(actor.get_actor_label() == "Elyon.Rain.01" for actor in self.ue.sub.actors))
        voice_session.press(self.ue, self.state, "Two")
        self.assertEqual(self._actor("Elyon.Rain.01").location.z, 900.0)

    def test_grow_spawns_foliage_and_optional_pcg(self):
        self.ue.PCGVolume = type("PCGVolume", (), {})
        voice_session.press(self.ue, self.state, "Three")
        self.assertEqual(self._actor("Elyon.Growth.01").scale.x, self.state["world"]["foliage_scale"])
        tags = self._actor("Elyon.PCGGrow").props["tags"]
        self.assertIn("/Game/PCG/GrowAroundGaze", tags)

    def test_calm_settles_wind_and_fog(self):
        voice_session.press(self.ue, self.state, "Four")
        self.assertEqual(self._actor("Elyon.Wind").props["tags"], ["wind", "0.0"])
        fog = self._actor("Elyon.Fog").get_component_by_class(self.ue.ExponentialHeightFogComponent)
        self.assertEqual(fog.props["fog_density"], 0.008)

    def test_destroy_strikes_and_impulses_nearby_meshes(self):
        plant = self._actor("Elyon.Plant.01")
        plant.set_actor_location(self.ue.Vector(10.0, -180.0, 40.0), False, True)
        calls = []
        mesh = plant.get_component_by_class(self.ue.StaticMeshComponent)

        def add_radial_impulse(origin, radius, strength):
            calls.append((radius, strength))

        mesh.add_radial_impulse = add_radial_impulse
        voice_session.press(self.ue, self.state, "Five")
        self.assertIn("25000", self._actor("Elyon.Lightning.01").props["tags"])
        self.assertIn((900.0, 25000.0), calls)

    def test_phrase_key_and_push_to_talk(self):
        voice_session.press(self.ue, self.state, "P")
        self.assertIn("let there be light", self._actor("Elyon.VoiceSubtitle").props["tags"])
        self.assertEqual(
            self._actor("Elyon.Sun").get_component_by_class(self.ue.DirectionalLightComponent).props["intensity"],
            voice_logic.dawn_sun_lux(),
        )
        voice_session.release_talk(self.ue, self.state, None)
        self.assertIn("Press 1-5", self._actor("Elyon.VoiceSubtitle").props["tags"][1])
        voice_session.release_talk(self.ue, self.state, lambda: "let there be light")
        self.assertEqual(self.state["world"]["light"], "dawn")

    def test_poll_edges_keys_once(self):
        class Key:
            def __init__(self, name):
                self.name = name

        class Controller:
            def __init__(self):
                self.down = set()

            def is_input_key_down(self, key):
                return key.name in self.down

        controller = Controller()
        self.ue.Key = Key
        self.ue.get_play_in_editor_player = lambda: controller
        controller.down.add("P")
        voice_session._poll(self.ue, self.state)
        voice_session._poll(self.ue, self.state)
        self.assertEqual(self.state["phrase_i"], 1)
        controller.down.discard("P")
        controller.down.add("V")
        self.state["runner"] = lambda: "be still"
        voice_session._poll(self.ue, self.state)
        self.assertTrue(self.state["listen"])
        controller.down.discard("V")
        voice_session._poll(self.ue, self.state)
        self.assertFalse(self.state["listen"])
        self.assertEqual(self._actor("Elyon.Wind").props["tags"], ["wind", "0.0"])


if __name__ == "__main__":
    unittest.main()
