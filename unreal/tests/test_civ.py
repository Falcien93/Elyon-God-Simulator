import sys
import unittest
from pathlib import Path

UNREAL = Path(__file__).resolve().parents[1]
SCRIPTS = UNREAL / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import civ_sim


DOC = UNREAL / "docs" / "civilizations.md"
IDEAS = UNREAL / "docs" / "physics-ideas.md"

PHYSICS_SOURCES = (
    "https://doi.org/10.1016/S0167-2789(00)00094-4",
    "https://arxiv.org/abs/1812.05433",
    "https://doi.org/10.1038/nature10872",
    "https://arxiv.org/abs/0710.3256",
    "https://arxiv.org/abs/1502.03808",
    "https://arxiv.org/abs/quant-ph/0303081",
    "https://doi.org/10.1038/nrn2787",
    "https://arxiv.org/abs/astro-ph/0511774",
    "https://www.ea.com/seed/news/siggraph2024-pbmpm",
    "https://arxiv.org/abs/0908.4105",
    "https://arxiv.org/abs/patt-sol/9304003",
    "https://arxiv.org/abs/cond-mat/0007300",
    "https://arxiv.org/abs/1310.4691",
    "https://doi.org/10.1145/2897824.2925868",
    "https://arxiv.org/abs/2212.14787",
)

PHYSICS_FORMULAS = (
    "dθ_i/dt = ω_i + (K/N) Σ sin(θ_j − θ_i)",
    "r e^{iψ} = (1/N) Σ e^{iθ_j}",
    "K_c = 2/(π g(0))",
    "A' = clip(A + Δt·G(K*A))",
    "G = 2exp(-(u-μ)²/2σ²) - 1",
    "cost = k_B·T_world·ln2·ΔI_bits",
    "H = −J Σ s_i s_j − h Σ s_i",
    "P = min(1, e^{−ΔE/T})",
)

ENDING_TITLES = {
    "harmony": "The garden kept",
    "exile": "East of the garden",
    "wonder": "The open orchard",
    "order": "The closed question",
}


class DocTests(unittest.TestCase):
    def test_sketch_uses_shipped_ending_names(self):
        text = DOC.read_text(encoding="utf-8")
        for ending_id, title in ENDING_TITLES.items():
            self.assertIn(ending_id, text)
            self.assertIn(title, text)
        for phrase in (
            "Mass Entity",
            "Mass AI",
            "StateTree",
            "PCG",
            "World Partition",
            "Niagara",
            "Chaos",
            "Qwen3",
            "llama.cpp",
            "Open questions for John",
            "utility",
            "GOAP",
        ):
            self.assertIn(phrase, text)

    def test_physics_ideas_keep_the_given_sources(self):
        sketch = DOC.read_text(encoding="utf-8")
        ideas = IDEAS.read_text(encoding="utf-8")
        self.assertIn("physics-ideas.md", sketch)
        self.assertIn("SIGNATURE", ideas)
        self.assertIn("core civ layer", ideas)
        self.assertIn("## Later layers", ideas)
        signature = ideas.split("## Later layers", 1)[0]
        later = ideas.split("## Later layers", 1)[1]
        for url in PHYSICS_SOURCES[:4]:
            self.assertIn(url, signature)
            self.assertNotIn(url, later)
        for url in PHYSICS_SOURCES[4:]:
            self.assertIn(url, later)
            self.assertNotIn(url, signature)
        for formula in PHYSICS_FORMULAS:
            self.assertIn(formula, signature)
        self.assertIn("Strogatz 2000", signature)


class EndingTests(unittest.TestCase):
    def test_hands_follows_silence(self):
        self.assertEqual(civ_sim.resolve_ending("hands", silence=True), "wonder")
        self.assertEqual(civ_sim.resolve_ending("hands", silence=False), "exile")

    def test_named_endings_pass_through(self):
        self.assertEqual(civ_sim.resolve_ending("harmony"), "harmony")
        self.assertEqual(civ_sim.resolve_ending("order"), "order")
        self.assertIsNone(civ_sim.resolve_ending("falls"))

    def test_first_ending_sticks(self):
        self.assertEqual(
            civ_sim.resolve_ending("order", silence=True, locked="harmony"),
            "harmony",
        )
        self.assertEqual(
            civ_sim.resolve_ending("hands", silence=False, locked="wonder"),
            "wonder",
        )


class InterventionTests(unittest.TestCase):
    def test_flood_hurts_numbers_and_raises_fear(self):
        tribe = civ_sim.new_tribe("exile", faith=20, prosperity=50, fear=10, population=40)
        civ_sim.apply_intervention(tribe, "flood")
        self.assertLess(tribe["population"], 40)
        self.assertLess(tribe["prosperity"], 50)
        self.assertGreater(tribe["fear"], 10)
        self.assertLess(tribe["faith"], 20)

    def test_flood_can_raise_faith(self):
        tribe = civ_sim.new_tribe("harmony", faith=70, prosperity=50, fear=10, population=40)
        civ_sim.apply_intervention(tribe, "flood")
        self.assertGreater(tribe["faith"], 70)

    def test_blessing_raises_prosperity_and_faith(self):
        tribe = civ_sim.new_tribe("harmony", faith=40, prosperity=30, fear=20, population=20)
        civ_sim.apply_intervention(tribe, "blessing")
        self.assertGreater(tribe["prosperity"], 30)
        self.assertGreater(tribe["faith"], 40)
        self.assertLess(tribe["fear"], 20)

    def test_divine_force_splits_awe_and_terror(self):
        high = civ_sim.new_tribe("wonder", faith=60, fear=10, prosperity=40)
        low = civ_sim.new_tribe("wonder", faith=20, fear=10, prosperity=40)
        civ_sim.apply_intervention(high, "divine_force")
        civ_sim.apply_intervention(low, "divine_force")
        self.assertGreater(high["faith"], 60)
        self.assertLess(low["faith"], 20)
        self.assertGreater(high["fear"], 10)
        self.assertGreater(low["fear"], 10)


class TribeTests(unittest.TestCase):
    def test_fearful_tribe_clashes_more_than_a_settled_one(self):
        afraid = civ_sim.new_tribe(
            "exile", faith=10, prosperity=10, fear=90, shelter=True
        )
        settled = civ_sim.new_tribe(
            "exile", faith=80, prosperity=80, fear=10, shelter=True
        )
        afraid_scores = civ_sim.utilities(afraid)
        settled_scores = civ_sim.utilities(settled)
        self.assertGreater(afraid_scores["clash"], settled_scores["clash"])
        self.assertEqual(civ_sim.choose(afraid), "clash")
        self.assertNotEqual(civ_sim.choose(settled), "clash")

    def test_harmony_does_not_clash(self):
        tribe = civ_sim.new_tribe(
            "harmony", faith=0, prosperity=0, fear=100, shelter=True
        )
        self.assertNotEqual(civ_sim.choose(tribe), "clash")
        self.assertEqual(civ_sim.settlement_goals(tribe)[0], "shelter")

    def test_order_cannot_clash(self):
        tribe = civ_sim.new_tribe(
            "order", faith=0, prosperity=0, fear=100, shelter=True
        )
        self.assertNotIn("clash", civ_sim.settlement_goals(tribe))
        self.assertNotEqual(civ_sim.choose(tribe), "clash")
        self.assertEqual(civ_sim.utilities(tribe)["clash"], -1000)

    def test_exile_founds_east_of_the_garden(self):
        exile = civ_sim.found_settlement(civ_sim.new_tribe("exile"), "East camp")
        kept = civ_sim.found_settlement(civ_sim.new_tribe("harmony"), "The grove")
        self.assertEqual(exile["region"], "east")
        self.assertEqual(kept["region"], "garden")
        self.assertEqual(exile["goals"], ["shelter", "trade", "clash"])

    def test_first_tick_builds_shelter(self):
        tribe = civ_sim.new_tribe("harmony", shelter=False)
        action, _events = civ_sim.tick(tribe)
        self.assertEqual(action, "build")
        self.assertTrue(tribe["shelter"])

    def test_leader_voice_does_not_call_a_model(self):
        tribe = civ_sim.new_tribe("wonder", faith=70, shelter=True)
        _action, events = civ_sim.tick(tribe)
        self.assertTrue(events)
        roles = {event["role"] for event in events}
        self.assertIn("leader", roles)
        self.assertIn("prophet", roles)
        for event in events:
            self.assertTrue(event["needs_voice"])
            self.assertFalse(event["model_called"])
        source = Path(civ_sim.__file__).read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("llama_cpp", source)


if __name__ == "__main__":
    unittest.main()
