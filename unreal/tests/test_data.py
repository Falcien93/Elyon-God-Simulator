import json
import unittest
from pathlib import Path

UNREAL = Path(__file__).resolve().parents[1]
DATA = UNREAL / "Data"

DAY_IDS = ["light", "waters", "land", "grove", "lights", "creatures", "humanity", "rest"]
ENDING_TITLES = {
    "harmony": "The garden kept",
    "exile": "East of the garden",
    "wonder": "The open orchard",
    "order": "The closed question",
}


def load(name):
    with (DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


class DataTests(unittest.TestCase):
    def test_days_follow_creation_order(self):
        days = load("days.json")
        self.assertEqual(days["source"], "js/content.js")
        self.assertEqual([day["id"] for day in days["days"]], DAY_IDS)
        for day in days["days"]:
            self.assertTrue(day["title"])
            self.assertTrue(day["detail"])
            self.assertTrue(day["evening"])

    def test_dialogue_covers_adam_and_eve(self):
        dialogue = load("dialogue.json")
        speakers = {node["speaker"] for node in dialogue["nodes"]}
        self.assertEqual(speakers, {"adam", "eve"})
        adam = next(node for node in dialogue["nodes"] if node["id"] == "adam_first")
        self.assertIn("Are you the one who pushed it there?", adam["lines"][1])
        eve = next(node for node in dialogue["nodes"] if node["id"] == "eve_choice")
        labels = [choice["label"] for choice in eve["choices"]]
        self.assertEqual(len(labels), 3)
        self.assertIn("ending:harmony", eve["choices"][0]["fx"])
        self.assertIn("ending:hands", eve["choices"][1]["fx"])
        self.assertIn("ending:order", eve["choices"][2]["fx"])

    def test_four_endings_and_hands_rule(self):
        payload = load("endings.json")
        self.assertEqual(payload["handsRule"]["ifFlagSilence"], "wonder")
        self.assertEqual(payload["handsRule"]["otherwise"], "exile")
        self.assertEqual(payload["handsRule"]["whenChoiceFx"], "ending:hands")
        endings = {ending["id"]: ending for ending in payload["endings"]}
        self.assertEqual(set(endings), set(ENDING_TITLES))
        for ending_id, title in ENDING_TITLES.items():
            self.assertEqual(endings[ending_id]["title"], title)
            self.assertGreaterEqual(len(endings[ending_id]["paragraphs"]), 2)
        exile = endings["exile"]["conditions"][0]
        wonder = endings["wonder"]["conditions"][0]
        self.assertEqual(exile["fx"], "ending:hands")
        self.assertEqual(exile["requires"], {"silence": False})
        self.assertEqual(wonder["requires"], {"silence": True})
        self.assertEqual(exile["choice"], wonder["choice"])
        order_fx = {item["fx"] for item in endings["order"]["conditions"]}
        self.assertEqual(order_fx, {"ending:order"})
        order_nodes = {item["node"] for item in endings["order"]["conditions"]}
        self.assertEqual(order_nodes, {"eve_choice", "serpent_meet", "serpent_why"})

    def test_high_end_defaults_and_bundled_llm_note(self):
        engine = (UNREAL / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
        scale = (UNREAL / "Config" / "DefaultScalability.ini").read_text(encoding="utf-8")
        readme = (UNREAL / "README.md").read_text(encoding="utf-8")
        self.assertIn("r.DynamicGlobalIlluminationMethod=1", engine)
        self.assertIn("r.ReflectionMethod=1", engine)
        self.assertIn("r.Nanite.ProjectEnabled=True", engine)
        self.assertIn("r.Shadow.Virtual.Enable=1", engine)
        self.assertIn("foliage.DensityScale=2.5", scale)
        self.assertIn("one install package", readme)
        self.assertIn("free local LLM", readme)


if __name__ == "__main__":
    unittest.main()
