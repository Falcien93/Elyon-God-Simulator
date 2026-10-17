import ast
import copy
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import incarnation
import incarnation_build
import test_garden


def pressured(**overrides):
    settlement = {
        "faith": 20,
        "fear": 70,
        "prosperity": 0,
        "population": 9,
        "shelter": True,
        "stores": False,
        "region": "east",
    }
    settlement.update(overrides)
    return settlement


def walk_until(state, limit=40, **beat):
    seen = [state]
    for _ in range(limit):
        if state["phase"] != "walking":
            break
        state = incarnation.beat(state, **beat)
        seen.append(state)
    return state, seen


class RulesTests(unittest.TestCase):
    def test_data_matches_the_mode_and_stays_respectful(self):
        rules = incarnation.load_rules()
        self.assertEqual(rules["version"], 1)
        self.assertEqual(rules["telling"], "original")
        self.assertEqual(tuple(rules["phases"]), incarnation.PHASES)
        self.assertEqual(incarnation.forbidden_word("the crucifixion beat"), None)
        self.assertEqual(incarnation.forbidden_word("a corpse on a cross"), "corpse")
        planted = copy.deepcopy(rules)
        planted["lines"]["enter"] = "They scream."
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.validate_rules(planted)

    def test_design_doc_names_the_bounds(self):
        doc = (Path(__file__).resolve().parents[1] / "docs" / "incarnation.md").read_text(encoding="utf-8")
        for phrase in (
            "original telling",
            "does not quote",
            "The player never performs the death",
            "no gore",
            "underworld",
            "resurrection",
            "incarnate_returned",
        ):
            self.assertIn(phrase, doc)
        for ending, faith in (("harmony", "+20"), ("wonder", "+16"), ("exile", "+10"), ("order", "+8")):
            self.assertIn(ending, doc)
            self.assertIn(faith, doc)

    def test_module_stays_independent(self):
        source = (SCRIPTS / "incarnation.py").read_text(encoding="utf-8")
        build = (SCRIPTS / "incarnation_build.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for banned in ("unreal", "requests", "urllib", "socket", "subprocess", "civ_sim", "physics_logic", "voice_logic"):
            self.assertNotIn(banned, imported)
        self.assertNotIn("Day1_Garden", source)
        self.assertNotIn("Day1_Garden", build)
        self.assertNotIn("api.x.ai", source + build)
        for banned_action in ("kill", "crucify", "strike", "condemn"):
            self.assertNotIn(banned_action, incarnation.ACTIONS)


class DispositionTests(unittest.TestCase):
    def setUp(self):
        self.rules = incarnation.load_rules()

    def test_bands_cover_the_edges(self):
        edges = {
            0: "welcome",
            30: "welcome",
            31: "wary",
            60: "wary",
            61: "hostile",
            80: "hostile",
            81: "seized",
            100: "seized",
        }
        for value, band in edges.items():
            self.assertEqual(incarnation.band_for(value), band)
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.band_for(101)

    def test_rise_fall_and_the_slowing_of_a_settled_people(self):
        common = dict(hostility=0, cap=100, rules=self.rules)
        self.assertEqual(incarnation.rise_amount(0, False, False), 12)
        self.assertEqual(incarnation.rise_amount(0, True, False), 12)
        self.assertEqual(incarnation.rise_amount(0, True, True), 6)
        self.assertEqual(incarnation.rise_amount(100, False, False), 6)
        self.assertEqual(incarnation.rise_amount(100, True, True), 3)
        self.assertEqual(incarnation.rise_amount(10000, True, True), 1)
        rising = incarnation.next_hostility(fear=55, faith=39, prosperity=0, shelter=False, stores=False, **common)
        self.assertEqual(rising, 12)
        holding = incarnation.next_hostility(fear=54, faith=39, prosperity=0, shelter=False, stores=False, **common)
        self.assertEqual(holding, 0)
        at_forty = incarnation.next_hostility(fear=90, faith=40, prosperity=0, shelter=False, stores=False, **common)
        self.assertEqual(at_forty, 0)
        afraid_and_walking = incarnation.next_hostility(
            fear=80, faith=10, prosperity=0, shelter=True, stores=True, walked=True, spoken_to=True, **common
        )
        self.assertEqual(afraid_and_walking, 6)
        trusted = incarnation.next_hostility(hostility=20, fear=90, faith=61, prosperity=0, shelter=False, stores=False, cap=100)
        self.assertEqual(trusted, 12)
        rich_trust = incarnation.next_hostility(
            hostility=20, fear=90, faith=61, prosperity=100, shelter=True, stores=True, cap=100
        )
        self.assertEqual(rich_trust, 12)
        company = incarnation.next_hostility(
            hostility=20, fear=10, faith=60, prosperity=0, shelter=False, stores=False, walked=True, spoken_to=True, cap=100
        )
        self.assertEqual(company, 12)
        walked_only = incarnation.next_hostility(
            hostility=20, fear=10, faith=60, prosperity=0, shelter=False, stores=False, walked=True, spoken_to=False, cap=100
        )
        self.assertEqual(walked_only, 20)
        self.assertEqual(
            incarnation.next_hostility(hostility=3, fear=10, faith=80, prosperity=0, shelter=False, stores=False, cap=100),
            0,
        )
        self.assertEqual(
            incarnation.next_hostility(hostility=96, fear=80, faith=10, prosperity=0, shelter=False, stores=False, cap=100),
            100,
        )
        self.assertEqual(
            incarnation.next_hostility(hostility=55, fear=80, faith=10, prosperity=0, shelter=False, stores=False, cap=60),
            60,
        )

    def test_seizure_is_only_for_endings_that_already_clash(self):
        self.assertFalse(incarnation.seizure_fires(100, "harmony"))
        self.assertFalse(incarnation.seizure_fires(100, "order"))
        self.assertFalse(incarnation.seizure_fires(80, "wonder"))
        self.assertTrue(incarnation.seizure_fires(81, "wonder"))
        self.assertTrue(incarnation.seizure_fires(81, "exile"))
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.begin("hands")


class WalkTests(unittest.TestCase):
    def test_enter_requires_shelter_and_happens_once(self):
        waiting = incarnation.begin("exile", pressured(shelter=False))
        self.assertEqual(waiting["phase"], "sky")
        self.assertTrue(waiting["interventions_available"])
        self.assertEqual(waiting["god_camera"], "awake")
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.enter(waiting)
        self.assertEqual(waiting["phase"], "sky")
        self.assertFalse(waiting["chosen"])
        state = incarnation.enter(incarnation.begin("wonder", pressured(faith=70, fear=10)))
        self.assertEqual(state["phase"], "walking")
        self.assertEqual(state["band"], "welcome")
        self.assertEqual(state["hostility"], 0)
        self.assertFalse(state["interventions_available"])
        self.assertFalse(state["world_speech_available"])
        self.assertEqual(state["god_camera"], "asleep")
        self.assertTrue(state["pawn_among_living"])
        self.assertEqual(incarnation.leader_act(state), "receive")
        self.assertEqual(incarnation.crowd_tag(state), "welcome")
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.enter(state)

    def test_harmony_and_order_become_wary_and_do_not_seize(self):
        for ending, attitude in (("harmony", "loyalty"), ("order", "refusal")):
            state = incarnation.enter(incarnation.begin(ending, pressured()))
            state, _steps = walk_until(state, limit=30)
            self.assertEqual(state["phase"], "walking")
            self.assertEqual(state["hostility"], 60)
            self.assertEqual(state["band"], "wary")
            self.assertEqual(state["attitude"], attitude)
            self.assertEqual(incarnation.leader_act(state), "question")
            self.assertNotEqual(incarnation.leader_act(state), "seize")
            self.assertFalse(state["clash_allowed"])
            self.assertEqual(state["population"], 9)

    def test_company_lowers_hostility_when_the_people_are_not_afraid(self):
        state = incarnation.enter(
            incarnation.begin("wonder", pressured(faith=50, fear=10, prosperity=40, stores=True))
        )
        state = incarnation.beat(state, walked=True, spoken_to=True)
        self.assertEqual(state["hostility"], 0)
        state = incarnation.beat(state)
        nudged = state
        # Faith is not low enough to rise, and this beat was not company.
        self.assertEqual(nudged["hostility"], 0)
        state = incarnation.enter(incarnation.begin("wonder", pressured(faith=50, fear=10)))
        state = incarnation.beat(state)
        # Hold, then company from a raised score.
        state["hostility"] = 40
        state["band"] = incarnation.band_for(40)
        cooled = incarnation.beat(state, walked=True, spoken_to=True)
        self.assertEqual(cooled["hostility"], 32)
        self.assertEqual(cooled["band"], "wary")

    def test_exile_reaches_the_beat_then_the_passage_then_the_return(self):
        state = incarnation.enter(incarnation.begin("exile", pressured()))
        population = state["population"]
        state, steps = walk_until(state)
        self.assertEqual(steps[-2]["phase"], "walking")
        self.assertEqual(steps[-2]["hostility"], 72)
        self.assertEqual(steps[-2]["band"], "hostile")
        self.assertEqual(incarnation.leader_act(steps[-2]), "question")
        self.assertEqual(state["phase"], "crucifixion")
        self.assertEqual(state["hostility"], 84)
        self.assertEqual(state["fear"], 80)
        self.assertEqual(state["population"], population)
        self.assertFalse(state["pawn_among_living"])
        self.assertTrue(state["living_tick_paused"])
        self.assertTrue(state["fear_raised_for_absence"])
        event = state["events"][-1]
        self.assertEqual(event["kind"], "crucifixion")
        self.assertFalse(event["graphic"])
        self.assertFalse(event["player_acted"])
        self.assertEqual(event["population_delta"], 0)
        self.assertEqual(event["fear_delta"], 10)
        self.assertFalse(event["model_called"])
        self.assertEqual(incarnation.leader_act(state), "seize")
        self.assertIsNone(incarnation.crowd_tag(state))
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.ascend(state)
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.listen(state, "mira")
        passage = incarnation.continue_on(state)
        self.assertEqual(passage["phase"], "underworld")
        self.assertEqual(passage["fear"], 80)
        self.assertTrue(passage["in_passage"])
        self.assertTrue(passage["living_tick_paused"])
        self.assertFalse(passage["interventions_available"])
        heard = incarnation.listen(passage, "mira")
        heard = incarnation.listen(heard, "oren")
        heard = incarnation.listen(heard, "sela")
        self.assertEqual([item["where"] for item in heard["events"] if item.get("needs_voice")], ["underworld"] * 3)
        self.assertTrue(all(item["model_called"] is False for item in heard["events"]))
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.listen(heard, "mira")
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.ascend(heard)
        returned = incarnation.leave(heard)
        self.assertEqual(returned["phase"], "returned")
        self.assertTrue(returned["incarnate_returned"])
        self.assertEqual(returned["ending"], "exile")
        self.assertEqual(returned["region"], "east")
        self.assertEqual(returned["population"], population)
        self.assertEqual(returned["hostility"], 0)
        self.assertEqual(returned["faith"], 30)
        self.assertEqual(returned["fear"], 72)
        self.assertEqual(returned["prosperity"], 6)
        self.assertTrue(returned["clash_eased"])
        self.assertTrue(returned["pawn_among_living"])
        self.assertFalse(returned["living_tick_paused"])
        self.assertFalse(returned["wonder_restored"])
        self.assertFalse(returned["interventions_available"])
        home = incarnation.ascend(returned)
        self.assertEqual(home["phase"], "ascended")
        self.assertEqual(home["god_camera"], "awake")
        self.assertTrue(home["interventions_available"])
        self.assertTrue(home["world_speech_available"])
        self.assertTrue(home["incarnate_returned"])
        self.assertFalse(home["departed_in_peace"])
        self.assertEqual(home["ending"], "exile")
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.enter(home)

    def test_return_does_not_require_a_listener_and_clamps(self):
        state = incarnation.enter(
            incarnation.begin(
                "wonder",
                pressured(faith=20, fear=96, prosperity=97, population=1, lost=[]),
            )
        )
        state, _steps = walk_until(state)
        self.assertEqual(state["phase"], "crucifixion")
        self.assertEqual(state["fear"], 100)
        self.assertEqual(state["events"][-1]["fear_applied"], 4)
        self.assertEqual(state["population"], 1)
        passage = incarnation.act(state, "continue")
        self.assertEqual(passage["lost"], [])
        high = copy.deepcopy(passage)
        high["faith"] = 90
        returned = incarnation.act(high, "leave")
        self.assertEqual(returned["heard"], [])
        self.assertEqual(returned["faith"], 100)
        self.assertEqual(returned["fear"], 88)
        self.assertEqual(returned["prosperity"], 100)
        self.assertEqual(returned["population"], 1)
        self.assertTrue(any(item.get("where") == "return" and item["role"] == "prophet" for item in returned["events"]))
        self.assertFalse(returned["clash_eased"])

    def test_order_return_keeps_the_question_closed(self):
        state = incarnation.begin("order", pressured(region="valley"))
        # Order cannot seize, so the return table is applied by walking the passage
        # only after a wonder path. Here the peace ascent must not pretend a return.
        state = incarnation.enter(state)
        state, _steps = walk_until(state, limit=10)
        home = incarnation.ascend(state)
        self.assertTrue(home["departed_in_peace"])
        self.assertFalse(home["incarnate_returned"])
        self.assertEqual(home["faith"], 20)
        self.assertEqual(home["fear"], 70)
        self.assertFalse(home["wonder_restored"])
        self.assertFalse(home["clash_allowed"])
        self.assertEqual(home["last_hostility"], 60)

    def test_wonder_can_go_home_without_a_death(self):
        state = incarnation.enter(incarnation.begin("wonder", pressured(faith=80, fear=10, prosperity=50, stores=True)))
        before = (state["faith"], state["fear"], state["prosperity"], state["population"])
        state = incarnation.beat(state, walked=True, spoken_to=True)
        home = incarnation.ascend(state)
        self.assertEqual(home["phase"], "ascended")
        self.assertFalse(home["incarnate_returned"])
        self.assertTrue(home["departed_in_peace"])
        self.assertEqual((home["faith"], home["fear"], home["prosperity"], home["population"]), before)
        self.assertEqual(home["region"], "east")

    def test_meet_voices_leaders_only(self):
        state = incarnation.enter(incarnation.begin("harmony", pressured(faith=70, fear=10)))
        crowd = incarnation.meet(state, "adan", "crowd")
        self.assertEqual(crowd["events"], [])
        spoken = incarnation.meet(state, "leda", "leader")
        spoken = incarnation.meet(spoken, "sela", "prophet")
        self.assertEqual([item["role"] for item in spoken["events"]], ["leader", "prophet"])
        self.assertTrue(all(item["needs_voice"] and item["model_called"] is False for item in spoken["events"]))
        self.assertEqual(spoken["phase"], "walking")
        with self.assertRaises(incarnation.IncarnationError):
            incarnation.meet(state, "nope", "stranger")

    def test_exact_seize_threshold_on_a_slow_people(self):
        state = incarnation.enter(
            incarnation.begin("wonder", pressured(prosperity=100, shelter=True, stores=True))
        )
        self.assertEqual(incarnation.rise_amount(100, True, True), 3)
        state, steps = walk_until(state)
        self.assertEqual(steps[-2]["hostility"], 78)
        self.assertEqual(steps[-2]["phase"], "walking")
        self.assertEqual(state["phase"], "crucifixion")
        self.assertEqual(state["hostility"], 81)
        self.assertEqual(state["population"], 9)


class BuildTests(unittest.TestCase):
    def _walking(self):
        return incarnation.enter(incarnation.begin("wonder", pressured(faith=70, fear=10)))

    def test_sky_does_not_touch_the_level(self):
        sentinel = object()
        plan = incarnation_build.place(incarnation.begin("harmony", pressured()), ue=sentinel)
        self.assertIsNone(plan["map"])
        self.assertEqual(plan["actors"], [])

    def test_walk_places_a_human_form_with_engine_colors(self):
        ue = test_garden.FakeUnreal()
        state = self._walking()
        plan = incarnation_build.place(state, ue=ue)
        self.assertEqual(plan["map"], "/Game/Maps/Incarnation_Walk")
        self.assertNotEqual(plan["map"], "/Game/Maps/Day1_Garden")
        self.assertEqual(ue.EditorLevelLibrary.created, plan["map"])
        self.assertEqual(ue.EditorLevelLibrary.saves, 1)
        labels = sorted(actor.get_actor_label() for actor in ue.sub.actors)
        self.assertIn("Elyon.Incarnation.Pawn", labels)
        self.assertNotIn("Elyon.Incarnation.Absence", labels)
        pawn = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Incarnation.Pawn")
        mesh = pawn.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(mesh.mesh, "/Engine/BasicShapes/Sphere")
        self.assertEqual(pawn.props["tags"], ["human-form"])
        sun = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Incarnation.Sun")
        sun_comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        self.assertIsInstance(sun_comp.props["light_color"], test_garden.ByteColor)
        self.assertEqual(sun_comp.props["intensity"], 6.0)
        self.assertTrue(all(type(channel) is int for channel in sun_comp.props["light_color"].rgba))
        fog = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Incarnation.Fog")
        fog_comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        self.assertIsInstance(fog_comp.props["fog_inscattering_luminance"], test_garden.LinearColor)
        self.assertEqual(fog_comp.props["fog_inscattering_luminance"].rgba, (0.72, 0.78, 0.86, 1.0))
        with self.assertRaises(TypeError):
            sun_comp.set_editor_property("light_color", ue.LinearColor(1.0, 0.91, 0.78, 1.0))
        kept = test_garden.Actor(ue.StaticMeshActor)
        kept.set_actor_label("Elyon.Ground")
        ue.sub.actors.append(kept)
        old = test_garden.Actor(ue.StaticMeshActor)
        old.set_actor_label("Elyon.Incarnation.Old")
        ue.sub.actors.append(old)
        incarnation_build.place(state, ue=ue)
        labels = [actor.get_actor_label() for actor in ue.sub.actors]
        self.assertEqual(labels.count("Elyon.Incarnation.Pawn"), 1)
        self.assertIn("Elyon.Ground", labels)
        self.assertNotIn("Elyon.Incarnation.Old", labels)
        self.assertEqual(ue.EditorLevelLibrary.loaded, "/Game/Maps/Incarnation_Walk")

    def test_crucifixion_is_an_absence_and_the_passage_is_another_map(self):
        ue = test_garden.FakeUnreal()
        state = incarnation.enter(incarnation.begin("exile", pressured()))
        incarnation_build.place(state, ue=ue)
        state, _steps = walk_until(state)
        self.assertEqual(state["phase"], "crucifixion")
        plan = incarnation_build.place(state, ue=ue)
        labels = [actor.get_actor_label() for actor in ue.sub.actors]
        self.assertNotIn("Elyon.Incarnation.Pawn", labels)
        absence = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Incarnation.Absence")
        self.assertEqual(absence.props["tags"], ["absence"])
        blob = " ".join(labels + absence.props["tags"])
        for word in ("gore", "blood", "corpse", "cross"):
            self.assertNotIn(word, blob)
        self.assertEqual(plan["light"]["sun_intensity"], 1.2)
        passage = incarnation.continue_on(state)
        under = incarnation_build.place(passage, ue=ue)
        self.assertEqual(under["map"], "/Game/Maps/Incarnation_Underworld")
        labels = [actor.get_actor_label() for actor in ue.sub.actors]
        self.assertIn("Elyon.Incarnation.Listener.mira", labels)
        self.assertIn("Elyon.Incarnation.Listener.oren", labels)
        self.assertIn("Elyon.Incarnation.Listener.sela", labels)
        self.assertNotIn("Elyon.Incarnation.Absence", labels)
        self.assertNotIn("Elyon.Incarnation.Pawn", labels)
        returned = incarnation.leave(passage)
        incarnation_build.place(returned, ue=ue)
        labels = [actor.get_actor_label() for actor in ue.sub.actors]
        self.assertIn("Elyon.Incarnation.Pawn", labels)
        self.assertNotIn("Elyon.Incarnation.Listener.mira", labels)
        self.assertEqual(ue.EditorLevelLibrary.loaded, "/Game/Maps/Incarnation_Walk")

    def test_main_keeps_the_editor_open_on_a_welcome_walk(self):
        ue = test_garden.FakeUnreal()
        incarnation_build.main(ue)
        self.assertTrue(ue.EditorPythonScripting.alive)
        labels = [actor.get_actor_label() for actor in ue.sub.actors]
        self.assertIn("Elyon.Incarnation.Pawn", labels)
        self.assertNotIn("Elyon.Incarnation.Absence", labels)


if __name__ == "__main__":
    unittest.main()
