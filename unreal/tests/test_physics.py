import json
import math
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
UNREAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import garden_logic
import level_build
import physics_build
import physics_logic as logic
import run_all
import test_garden


def _bag(obj, name):
    value = getattr(obj, name, None)
    if value is None:
        value = []
        setattr(obj, name, value)
    return value


def _mark(obj, name):
    _bag(obj, "physics_calls").append(name)


class RiverBody:
    def __init__(self):
        self.widths = {}
        self.depths = {}
        self.props = {}

    def set_river_width_at_spline_input_key(self, key, width):
        self.widths[float(key)] = width

    def set_river_depth_at_spline_input_key(self, key, depth):
        self.depths[float(key)] = depth

    def set_editor_property(self, name, value):
        self.props[name] = value


class Spline:
    def __init__(self):
        self.points = []

    def clear_spline_points(self):
        self.points.clear()

    def add_spline_point(self, location, space):
        self.points.append((location, space))


class Pontoon:
    def __init__(self):
        self.props = {}

    def set_editor_property(self, name, value):
        self.props[name] = value


class BadPontoon:
    def set_editor_property(self, name, value):
        raise RuntimeError("no pontoon")


class LogicTests(unittest.TestCase):
    def test_masses_damping_and_buoyancy(self):
        rock = logic.body_spec("rock")
        log = logic.body_spec("log")
        fruit = logic.body_spec("fruit")
        self.assertGreater(rock["mass"], log["mass"])
        self.assertGreater(log["mass"], fruit["mass"])
        self.assertGreater(rock["mass"], 50.0)
        self.assertLess(fruit["mass"], 1.0)
        self.assertEqual(rock["mass"], 120.0)
        self.assertEqual(log["mass"], 22.0)
        self.assertEqual(fruit["mass"], 0.2)
        self.assertEqual(rock["linear_damping"], 0.35)
        self.assertEqual(rock["angular_damping"], 0.55)
        self.assertEqual(log["linear_damping"], 1.1)
        self.assertGreaterEqual(fruit["linear_damping"], 0.0)
        self.assertFalse(rock["floats"])
        self.assertTrue(log["floats"])
        self.assertTrue(fruit["floats"])
        self.assertEqual(rock["collision"], "PhysicsActor")

    def test_labels_and_placements_stay_out_of_the_river_and_the_plan(self):
        self.assertEqual(logic.classify_label("Elyon.Rock.01"), "rock")
        self.assertEqual(logic.classify_label("Elyon.Log.08"), "log")
        self.assertEqual(logic.classify_label("Elyon.Fruit.12"), "fruit")
        self.assertEqual(logic.classify_label("Elyon.Plant.01"), "plant")
        self.assertIsNone(logic.classify_label("Elyon.River"))
        plan = set(garden_logic.planned_labels(garden_logic.plan_level(True)))
        logs = logic.log_placements()
        fruit = logic.fruit_placements()
        self.assertEqual(len(logs), logic.LOG_COUNT)
        self.assertEqual(len(fruit), logic.FRUIT_COUNT)
        for item in logs:
            self.assertEqual(item["z"], 80.0)
            self.assertEqual(item["pitch"], 80.0)
            self.assertGreater(item["scale"][2], item["scale"][0])
            self.assertFalse(garden_logic._blocked(item["x"], item["y"]))
            self.assertNotIn(item["label"], plan)
        for item in fruit:
            self.assertEqual(item["z"], 160.0)
            self.assertLess(math.hypot(item["x"] - logic.FRUIT_CLUSTER[0], item["y"] - logic.FRUIT_CLUSTER[1]), 250.0)
            self.assertFalse(garden_logic._blocked(item["x"], item["y"]))
            self.assertNotIn(item["label"], plan)
        for label in ("Elyon.Wind", "Elyon.WaterRiver", "Elyon.GodCamera"):
            self.assertNotIn(label, plan)
            self.assertIn(label, logic.managed_labels())

    def test_river_spline_and_wind(self):
        points = logic.river_spline_points()
        self.assertEqual(len(points), 4)
        self.assertEqual([point["x"] for point in points], [-4000.0, -1500.0, 1500.0, 4000.0])
        for point in points:
            self.assertEqual(point["y"], 1200.0)
            self.assertEqual(point["z"], 30.0)
            self.assertEqual(point["width"], 700.0)
            self.assertEqual(point["depth"], 180.0)
        wind = logic.wind_state()
        self.assertEqual(wind["strength"], 0.35)
        self.assertEqual(wind["speed"], 0.45)
        self.assertEqual(wind["min_gust"], 0.1)
        self.assertEqual(wind["max_gust"], 0.4)
        self.assertEqual(wind["yaw"], 40.0)
        self.assertEqual(wind["radius"], 0.0)
        self.assertTrue(any(path.endswith("SimpleGrassWind") for path in logic.GRASS_WIND_PATHS))
        spec = logic.god_camera_spec()
        self.assertLess(spec["pitch"], 0.0)
        self.assertGreater(spec["yaw"], 0.0)

    def test_plant_bend_uses_distance_and_does_not_imply_a_new_base(self):
        self.assertEqual(logic.bend_for_contact((0, 0), (0, 0)), 1.0)
        self.assertAlmostEqual(logic.bend_for_contact((0, 0), (140, 0)), 0.5)
        self.assertEqual(logic.bend_for_contact((0, 0), (280, 0)), 0.0)
        self.assertEqual(logic.bend_for_contact((0, 0), (281, 0)), 0.0)
        self.assertAlmostEqual(logic.plant_bend_pitch(1.0), 28.0)
        self.assertEqual(logic.plant_bend_pitch(0.0), 0.0)
        bent = logic.bend_plants(
            [{"label": "Elyon.Plant.01", "location": (0, 0, 15), "base_yaw": 33.0}],
            [(0, 0, 10), (1000, 0, 0)],
        )
        self.assertEqual(bent[0]["weight"], 1.0)
        self.assertEqual(bent[0]["pitch"], 28.0)
        self.assertEqual(bent[0]["yaw"], 33.0)

    def test_view_pick_hold_throw_push_and_divine_falloff(self):
        near = {"label": "Elyon.Fruit.01", "location": (50.0, 0.0, 0.0)}
        far = {"label": "Elyon.Rock.01", "location": (400.0, 0.0, 0.0)}
        behind = {"label": "Elyon.Log.01", "location": (-100.0, 0.0, 0.0)}
        plant = {"label": "Elyon.Plant.01", "location": (20.0, 0.0, 0.0)}
        aside = {"label": "Elyon.Rock.02", "location": (64.0, 76.8, 0.0)}
        picked = logic.nearest_along_view((0, 0, 0), (1, 0, 0), [far, behind, plant, near, aside])
        self.assertEqual(picked["label"], "Elyon.Fruit.01")
        self.assertIsNone(logic.nearest_along_view((0, 0, 0), (1, 0, 0), [aside]))
        facing = {"label": "Elyon.Rock.03", "location": (66.0, 75.1, 0.0)}
        self.assertEqual(
            logic.nearest_along_view((0, 0, 0), (1, 0, 0), [facing])["label"],
            "Elyon.Rock.03",
        )
        self.assertIsNone(
            logic.nearest_along_view((0, 0, 0), (1, 0, 0), [{"label": "Elyon.Rock.04", "location": (9000.0, 0.0, 0.0)}])
        )
        self.assertEqual(logic.hold_target((0, 0, 100), (0, 1, 0), lift=120), (0.0, 600.0, 220.0))
        self.assertEqual(logic.throw_velocity((0, -1, 0)), (0.0, -logic.THROW_SPEED, 0.0))
        self.assertEqual(logic.push_impulse((1, 0, 0)), (logic.PUSH_IMPULSE, 0.0, 0.0))
        impulses = logic.divine_force(
            (0, 0, 0),
            [
                {"label": "Elyon.Rock.01", "location": (450.0, 0.0, 0.0)},
                {"label": "Elyon.Fruit.01", "location": (900.0, 0.0, 0.0)},
                {"label": "Elyon.Plant.01", "location": (100.0, 0.0, 0.0)},
            ],
        )
        self.assertEqual(len(impulses), 1)
        self.assertEqual(impulses[0]["label"], "Elyon.Rock.01")
        self.assertAlmostEqual(impulses[0]["falloff"], 0.5)
        self.assertAlmostEqual(impulses[0]["impulse"][0], 12500.0)

    def _view(self, keys, bodies):
        return {"location": (0, 0, 100), "forward": (1, 0, 0), "keys": set(keys), "bodies": bodies}

    def test_god_hand_edges(self):
        fruit = {"label": "Elyon.Fruit.01", "location": (100.0, 0.0, 100.0)}
        state = logic.new_session()
        actions = logic.step_god(None, state, self._view({"grab"}, [fruit]))
        self.assertEqual(state["held"], "Elyon.Fruit.01")
        self.assertEqual(actions[0]["op"], "grab")
        actions = logic.step_god(None, state, self._view({"grab"}, [fruit]))
        self.assertEqual([action["op"] for action in actions], ["move"])
        self.assertEqual(actions[0]["location"][2], 100.0)
        actions = logic.step_god(None, state, self._view({"grab", "lift"}, [fruit]))
        self.assertEqual(state["hold_lift"], logic.HOLD_LIFT)
        self.assertAlmostEqual(actions[0]["location"][2], 100.0 + logic.HOLD_LIFT)
        actions = logic.step_god(None, state, self._view({"grab", "lower"}, [fruit]))
        self.assertEqual(state["hold_lift"], 0.0)
        actions = logic.step_god(None, state, self._view(set(), [fruit]))
        self.assertEqual(actions[0]["op"], "release")
        self.assertIsNone(state["held"])

        state = logic.new_session()
        logic.step_god(None, state, self._view({"grab"}, [fruit]))
        actions = logic.step_god(None, state, self._view({"grab", "throw"}, [fruit]))
        self.assertEqual(actions[0]["op"], "throw")
        self.assertEqual(actions[0]["velocity"], (logic.THROW_SPEED, 0.0, 0.0))
        self.assertIsNone(state["held"])
        actions = logic.step_god(None, state, self._view({"grab", "throw"}, [fruit]))
        self.assertNotIn("throw", [action["op"] for action in actions])
        self.assertEqual(state["held"], "Elyon.Fruit.01")

        state = logic.new_session()
        actions = logic.step_god(None, state, self._view({"push"}, [fruit]))
        self.assertEqual(actions[0]["op"], "push")
        self.assertEqual(actions[0]["impulse"], (logic.PUSH_IMPULSE, 0.0, 0.0))
        actions = logic.step_god(None, state, self._view({"push"}, [fruit]))
        self.assertEqual(actions, [])

        state = logic.new_session()
        logic.step_god(None, state, self._view({"grab"}, [fruit]))
        actions = logic.step_god(None, state, self._view({"grab", "divine"}, [fruit]))
        self.assertEqual([action["op"] for action in actions], ["release", "divine"])
        self.assertIsNone(state["held"])
        self.assertEqual(actions[1]["radius"], logic.DIVINE_RADIUS)
        self.assertEqual(actions[1]["strength"], logic.DIVINE_STRENGTH)
        self.assertEqual(actions[1]["falloff"], "RIF_LINEAR")
        actions = logic.step_god(None, state, self._view({"divine"}, [fruit]))
        self.assertFalse(any(action["op"] == "divine" for action in actions))


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        comp = test_garden.Comp

        def set_collision_profile_name(self, profile):
            self.collision_profile = profile
            _mark(self, "collision")

        def set_notify_rigid_body_collision(self, enabled):
            self.notify_collision = enabled
            _mark(self, "notify")

        def set_enable_gravity(self, enabled):
            self.gravity = enabled
            _mark(self, "gravity")

        def set_linear_damping(self, value):
            self.linear_damping = value
            _mark(self, "linear")

        def set_angular_damping(self, value):
            self.angular_damping = value
            _mark(self, "angular")

        def set_mass_override_in_kg(self, bone_name="None", mass_in_kg=0.0, override_mass=True):
            self.mass_bone = bone_name
            self.mass_kg = mass_in_kg
            self.mass_override = override_mass
            _mark(self, "mass")

        def set_use_ccd(self, enabled):
            self.ccd = enabled
            _mark(self, "ccd")

        def set_simulate_physics(self, enabled):
            self.simulate_physics = enabled
            _mark(self, "simulate")

        def set_custom_primitive_data_float(self, index, value):
            if not hasattr(self, "primitive"):
                self.primitive = {}
            self.primitive[index] = value

        def add_impulse(self, impulse, bone_name="None", vel_change=False):
            _bag(self, "impulses").append((impulse, bone_name, vel_change))

        def add_radial_impulse(self, origin, radius, strength, falloff, vel_change=False):
            _bag(self, "radial").append((origin, radius, strength, falloff, vel_change))

        def grab_component_at_location(self, component, bone, location):
            self.grabbed = (component, bone, location)

        def set_target_location(self, location):
            self.target = location

        def release_component(self):
            self.released = getattr(self, "released", 0) + 1

        for name, fn in (
            ("set_collision_profile_name", set_collision_profile_name),
            ("set_notify_rigid_body_collision", set_notify_rigid_body_collision),
            ("set_enable_gravity", set_enable_gravity),
            ("set_linear_damping", set_linear_damping),
            ("set_angular_damping", set_angular_damping),
            ("set_mass_override_in_kg", set_mass_override_in_kg),
            ("set_use_ccd", set_use_ccd),
            ("set_simulate_physics", set_simulate_physics),
            ("set_custom_primitive_data_float", set_custom_primitive_data_float),
            ("add_impulse", add_impulse),
            ("add_radial_impulse", add_radial_impulse),
            ("grab_component_at_location", grab_component_at_location),
            ("set_target_location", set_target_location),
            ("release_component", release_component),
        ):
            setattr(comp, name, fn)

        def set_actor_hidden_in_game(self, hidden):
            self.hidden_in_game = bool(hidden)

        def add_component_by_class(self, component_cls):
            component = test_garden.Comp()
            _bag(self, "added_components").append((component_cls, component))
            return component

        test_garden.Actor.set_actor_hidden_in_game = set_actor_hidden_in_game
        test_garden.Actor.add_component_by_class = add_component_by_class

    def setUp(self):
        physics_build._TICK_REGISTERED = False
        physics_build._BASE_YAW.clear()
        physics_build._SESSION = None
        physics_build._SEATED = False

    def _ue(self):
        ue = test_garden.FakeUnreal()
        ue.warnings = []
        return ue

    def _labels(self, ue, prefix):
        return [actor for actor in ue.sub.actors if actor.get_actor_label().startswith(prefix)]

    def test_apply_arms_rocks_logs_and_fruit_and_second_run_does_not_duplicate(self):
        ue = self._ue()
        run_all.main(ue)
        self.assertTrue(ue.EditorPythonScripting.alive)
        rocks = self._labels(ue, "Elyon.Rock.")
        logs = self._labels(ue, "Elyon.Log.")
        fruit = self._labels(ue, "Elyon.Fruit.")
        plants = self._labels(ue, "Elyon.Plant.")
        self.assertEqual(len(rocks), 12)
        self.assertEqual(len(logs), 8)
        self.assertEqual(len(fruit), 12)
        self.assertEqual(len(plants), 36)
        self.assertEqual(len(self._labels(ue, "Elyon.Tree.")), 24)
        for rock in rocks:
            comp = rock.get_component_by_class(ue.StaticMeshComponent)
            self.assertTrue(comp.simulate_physics)
            self.assertEqual(comp.mass_kg, 120.0)
            self.assertTrue(comp.mass_override)
            self.assertEqual(comp.mass_bone, "None")
            self.assertEqual(comp.linear_damping, 0.35)
            self.assertEqual(comp.angular_damping, 0.55)
            self.assertEqual(comp.collision_profile, "PhysicsActor")
            self.assertTrue(comp.notify_collision)
            self.assertTrue(comp.gravity)
            self.assertTrue(comp.ccd)
            self.assertLess(comp.physics_calls.index("mass"), comp.physics_calls.index("simulate"))
            self.assertLess(comp.physics_calls.index("collision"), comp.physics_calls.index("simulate"))
            self.assertFalse(getattr(rock, "added_components", []))
        for log in logs:
            comp = log.get_component_by_class(ue.StaticMeshComponent)
            self.assertEqual(comp.mass_kg, 22.0)
            self.assertEqual(comp.mesh, garden_logic.MESH["cylinder"])
            self.assertEqual(log.rotation.pitch, 80.0)
        for item in fruit:
            comp = item.get_component_by_class(ue.StaticMeshComponent)
            self.assertEqual(comp.mass_kg, 0.2)
            self.assertEqual(comp.mesh, garden_logic.MESH["sphere"])
        for plant in plants:
            comp = plant.get_component_by_class(ue.StaticMeshComponent)
            self.assertFalse(getattr(comp, "simulate_physics", False))
        ground = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Ground")
        self.assertEqual(ground.get_component_by_class(ue.StaticMeshComponent).collision_profile, "BlockAll")
        self.assertFalse(getattr(ground.get_component_by_class(ue.StaticMeshComponent), "simulate_physics", False))
        river = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.River")
        self.assertFalse(getattr(river, "hidden_in_game", False))
        self.assertTrue(any("WaterBodyRiver" in message for message in ue.warnings))
        run_all.main(ue)
        self.assertEqual(len(self._labels(ue, "Elyon.Log.")), 8)
        self.assertEqual(len(self._labels(ue, "Elyon.Fruit.")), 12)
        self.assertGreaterEqual(ue.EditorLevelLibrary.saves, 2)

    def test_water_failure_keeps_the_cube_and_still_saves(self):
        ue = self._ue()
        ue.WaterBodyRiver = type("WaterBodyRiver", (), {})
        ue.WaterBodyRiverComponent = type("WaterBodyRiverComponent", (), {})
        ue.WaterSplineComponent = type("WaterSplineComponent", (), {})
        level_build.build(dawn=True, ue=ue)
        self.assertFalse(physics_build._apply_water(ue))
        physics_build._save(ue)
        river = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.River")
        self.assertFalse(getattr(river, "hidden_in_game", False))
        self.assertTrue(any("cube river stays visible" in message for message in ue.warnings))
        self.assertGreaterEqual(ue.EditorLevelLibrary.saves, 2)

    def _install_water(self, ue):
        ue.WaterBodyRiver = type("WaterBodyRiver", (), {})
        ue.WaterBodyRiverComponent = type("WaterBodyRiverComponent", (), {})
        ue.WaterSplineComponent = type("WaterSplineComponent", (), {})
        ue.SplineCoordinateSpace = type("Space", (), {"WORLD": "WORLD"})
        ue.BuoyancyComponent = type("BuoyancyComponent", (), {})
        ue.SphericalPontoon = Pontoon
        original = test_garden.Actor.get_component_by_class

        def get_component_by_class(actor, cls):
            if cls is ue.WaterSplineComponent:
                comp = actor.comps.get(cls)
                if comp is None:
                    comp = Spline()
                    actor.comps[cls] = comp
                return comp
            if cls is ue.WaterBodyRiverComponent:
                comp = actor.comps.get(cls)
                if comp is None:
                    comp = RiverBody()
                    actor.comps[cls] = comp
                return comp
            return original(actor, cls)

        test_garden.Actor.get_component_by_class = get_component_by_class
        return original

    def test_water_success_hides_the_cube_and_floats_logs_and_fruit(self):
        ue = self._ue()
        level_build.build(dawn=True, ue=ue)
        original = self._install_water(ue)
        try:
            physics_build.apply(ue)
            physics_build.apply(ue)
        finally:
            test_garden.Actor.get_component_by_class = original
        river = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.River")
        self.assertTrue(river.hidden_in_game)
        water = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.WaterRiver")
        spline = water.get_component_by_class(ue.WaterSplineComponent)
        body = water.get_component_by_class(ue.WaterBodyRiverComponent)
        self.assertEqual(len(spline.points), 4)
        self.assertEqual(spline.points[0][1], "WORLD")
        self.assertEqual(body.widths[0.0], 700.0)
        self.assertEqual(body.depths[3.0], 180.0)
        self.assertFalse(any("was not created" in message for message in ue.warnings))
        for log in self._labels(ue, "Elyon.Log."):
            added = [pair for pair in log.added_components if pair[0] is ue.BuoyancyComponent]
            self.assertEqual(len(added), 1)
            self.assertEqual(added[0][1].props["pontoons"][0].props["radius"], 48.0)
        for item in self._labels(ue, "Elyon.Fruit."):
            added = [pair for pair in item.added_components if pair[0] is ue.BuoyancyComponent]
            self.assertEqual(added[0][1].props["pontoons"][0].props["radius"], 14.0)
        for rock in self._labels(ue, "Elyon.Rock."):
            self.assertFalse(getattr(rock, "added_components", []))

    def test_bad_pontoon_keeps_the_buoyancy_component(self):
        ue = self._ue()
        ue.BuoyancyComponent = type("BuoyancyComponent", (), {})
        ue.SphericalPontoon = BadPontoon
        level_build.build(dawn=True, ue=ue)
        physics_build.apply(ue)
        log = self._labels(ue, "Elyon.Log.")[0]
        self.assertEqual(len(log.added_components), 1)
        self.assertTrue(any("pontoon" in message.lower() for message in ue.warnings))

    def test_wind_camera_reuse_and_contact_bend(self):
        ue = self._ue()
        ue.WindDirectionalSource = type("WindDirectionalSource", (), {})
        ue.WindDirectionalSourceComponent = type("WindDirectionalSourceComponent", (), {})
        ue.CineCameraActor = type("CineCameraActor", (), {})
        ue.CineCameraComponent = type("CineCameraComponent", (), {})
        ue.PhysicsHandleComponent = type("PhysicsHandleComponent", (), {})
        level_build.build(dawn=True, ue=ue)
        physics_build.apply(ue)
        wind = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Wind")
        wind_comp = wind.get_component_by_class(ue.WindDirectionalSourceComponent)
        self.assertEqual(wind_comp.props["strength"], 0.35)
        self.assertEqual(wind_comp.props["speed"], 0.45)
        self.assertEqual(wind_comp.props["min_gust_amount"], 0.1)
        self.assertEqual(wind_comp.props["max_gust_amount"], 0.4)
        self.assertEqual(wind_comp.props["radius"], 0.0)
        self.assertFalse(wind_comp.props["point_wind"])
        self.assertAlmostEqual(wind.rotation.yaw, 40.0)
        camera = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.GodCamera")
        spec = logic.god_camera_spec()
        self.assertEqual((camera.location.x, camera.location.y, camera.location.z), (spec["x"], spec["y"], spec["z"]))
        handle = camera.get_component_by_class(ue.PhysicsHandleComponent)
        self.assertEqual(handle.props["linear_stiffness"], 700.0)
        self.assertEqual(handle.props["interpolation_speed"], 30.0)
        camera.location = test_garden.Vec(5, 6, 7)
        physics_build._TICK_REGISTERED = False
        physics_build.apply(ue)
        self.assertEqual(len(self._labels(ue, "Elyon.Wind")), 1)
        self.assertEqual((camera.location.x, camera.location.y, camera.location.z), (5, 6, 7))
        plant = self._labels(ue, "Elyon.Plant.")[0]
        base = plant.rotation.yaw
        physics_build.apply_contact_bend(ue, [(plant.location.x, plant.location.y, 0)])
        self.assertAlmostEqual(plant.rotation.pitch, logic.BEND_MAX_PITCH)
        self.assertAlmostEqual(plant.rotation.yaw, base)
        comp = plant.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(comp.primitive[0], 1.0)
        physics_build.apply_contact_bend(ue, [(plant.location.x, plant.location.y, 0)])
        self.assertAlmostEqual(plant.rotation.pitch, logic.BEND_MAX_PITCH)
        physics_build.apply_contact_bend(ue, [(plant.location.x + 10000, plant.location.y, 0)])
        self.assertEqual(plant.rotation.pitch, 0.0)
        self.assertAlmostEqual(plant.rotation.yaw, base)

    def test_grass_wind_material_is_optional(self):
        ue = self._ue()
        ue.MaterialEditingLibrary = type("MaterialEditingLibrary", (), {})()
        ue.EditorAssetLibrary.does_asset_exist = lambda path: False
        level_build.build(dawn=True, ue=ue)
        self.assertFalse(physics_build._try_simple_grass_wind(ue))
        self.assertTrue(any("SimpleGrassWind" in message for message in ue.warnings))
        created = {}

        class Editing:
            @staticmethod
            def create_material(name, package):
                created["material"] = (name, package)
                return {"material": name}

            @staticmethod
            def create_material_expression(material, cls):
                created["expression"] = cls
                return {"expr": True}

            @staticmethod
            def connect_material_property(expression, output, prop):
                created["connected"] = prop

        ue.warnings.clear()
        ue.MaterialEditingLibrary = Editing
        ue.MaterialExpressionMaterialFunctionCall = type("Call", (), {})
        ue.MaterialProperty = type("Prop", (), {"MP_WORLD_POSITION_OFFSET": "WPO"})
        ue.EditorAssetLibrary.does_asset_exist = lambda path: path == logic.GRASS_WIND_PATHS[0]
        ue.EditorAssetLibrary.load_asset = lambda path: path
        ue.EditorAssetLibrary.save_asset = lambda path: created.setdefault("saved", path)
        self.assertTrue(physics_build._try_simple_grass_wind(ue))
        self.assertEqual(created["material"], ("M_Elyon_WindLeaf", "/Game/Materials"))
        self.assertEqual(created["connected"], "WPO")
        self.assertEqual(created["saved"], "/Game/Materials/M_Elyon_WindLeaf")

    def test_handle_throw_push_and_divine_radial(self):
        ue = self._ue()
        ue.RadialImpulseFalloff = type("Falloff", (), {"RIF_LINEAR": "RIF_LINEAR"})
        level_build.build(dawn=True, ue=ue)
        physics_build.apply(ue)
        fruit = self._labels(ue, "Elyon.Fruit.")[0]
        comp = fruit.get_component_by_class(ue.StaticMeshComponent)
        handle = test_garden.Comp()
        physics_build._perform(
            ue,
            handle,
            [{"op": "grab", "label": fruit.get_actor_label(), "location": (1.0, 2.0, 3.0)}],
        )
        grabbed, bone, loc = handle.grabbed
        self.assertIs(grabbed, comp)
        self.assertEqual(bone, "None")
        self.assertEqual((loc.x, loc.y, loc.z), (1.0, 2.0, 3.0))
        physics_build._perform(
            ue,
            handle,
            [{"op": "move", "label": fruit.get_actor_label(), "location": (4.0, 5.0, 6.0)}],
        )
        self.assertEqual((handle.target.x, handle.target.y, handle.target.z), (4.0, 5.0, 6.0))
        physics_build._perform(
            ue,
            handle,
            [{"op": "throw", "label": fruit.get_actor_label(), "velocity": (logic.THROW_SPEED, 0.0, 0.0)}],
        )
        self.assertEqual(handle.released, 1)
        impulse, bone, vel_change = comp.impulses[-1]
        self.assertAlmostEqual(impulse.x, 0.2 * logic.THROW_SPEED)
        self.assertEqual(bone, "None")
        self.assertFalse(vel_change)
        physics_build._perform(
            ue,
            None,
            [{"op": "push", "label": fruit.get_actor_label(), "impulse": (0.0, logic.PUSH_IMPULSE, 0.0)}],
        )
        self.assertEqual(comp.impulses[-1][0].y, logic.PUSH_IMPULSE)
        physics_build._perform(
            ue,
            None,
            [
                {
                    "op": "divine",
                    "origin": (0.0, 0.0, 0.0),
                    "radius": logic.DIVINE_RADIUS,
                    "strength": logic.DIVINE_STRENGTH,
                    "impulses": [{"label": fruit.get_actor_label(), "impulse": (9.0, 0.0, 0.0)}],
                }
            ],
        )
        origin, radius, strength, falloff, vel_change = comp.radial[-1]
        self.assertEqual((origin.x, origin.y, origin.z), (0.0, 0.0, 0.0))
        self.assertEqual(radius, logic.DIVINE_RADIUS)
        self.assertEqual(strength, logic.DIVINE_STRENGTH)
        self.assertEqual(falloff, "RIF_LINEAR")
        self.assertFalse(vel_change)

        class OnlyImpulse:
            def __init__(self):
                self.impulses = []

            def add_impulse(self, impulse, bone_name="None", vel_change=False):
                self.impulses.append(impulse)

        actor = test_garden.Actor(ue.StaticMeshActor)
        actor.set_actor_label("Elyon.Rock.01")
        actor.comp = OnlyImpulse()
        actor.get_component_by_class = lambda cls: actor.comp
        physics_build._divine(
            ue,
            {"Elyon.Rock.01": actor},
            {
                "origin": (0.0, 0.0, 0.0),
                "radius": 900.0,
                "strength": 25000.0,
                "impulses": [{"label": "Elyon.Rock.01", "impulse": (10.0, 0.0, 0.0)}],
            },
        )
        self.assertEqual(actor.comp.impulses[0].x, 10.0)

    def test_tick_registers_once_seats_the_pawn_and_swallows_errors(self):
        ue = self._ue()
        ue.CineCameraActor = type("CineCameraActor", (), {})
        ue.PhysicsHandleComponent = type("PhysicsHandleComponent", (), {})
        registered = []
        ue.register_slate_post_tick_callback = registered.append
        level_build.build(dawn=True, ue=ue)
        physics_build.apply(ue)
        physics_build.apply(ue)
        self.assertEqual(len(registered), 1)

        spec = logic.god_camera_spec()
        rot = test_garden.Rot(spec["pitch"], spec["yaw"], 0.0)
        forward = physics_build._forward_of(ue, rot)
        origin = (spec["x"], spec["y"], spec["z"])
        body = {
            "label": "Elyon.Fruit.01",
            "kind": "fruit",
            "location": tuple(origin[index] + forward[index] * 500.0 for index in range(3)),
        }
        world = object()
        ue.UnrealEditorSubsystem = type("UnrealEditorSubsystem", (), {})
        ue.sub.get_game_world = lambda: world

        class Controller:
            def __init__(self):
                self.pawn = test_garden.Actor(type("Pawn", (), {}))
                self.control = None
                self.down = {"LeftMouseButton"}

            def get_pawn(self):
                return self.pawn

            def get_control_rotation(self):
                return self.control if self.control is not None else test_garden.Rot(0, 0, 0)

            def set_control_rotation(self, value):
                self.control = value

            def is_input_key_down(self, key):
                return getattr(key, "name", key) in self.down

        class Key:
            def __init__(self, name):
                self.name = name

        controller = Controller()
        ue.Key = Key
        ue.GameplayStatics = type(
            "GameplayStatics",
            (),
            {"get_player_controller": staticmethod(lambda game_world, index: controller)},
        )
        original_snapshot = physics_build._body_snapshot
        physics_build._body_snapshot = lambda game_ue, game_world=None: [body]
        try:
            registered[0](0.016)
        finally:
            physics_build._body_snapshot = original_snapshot
        self.assertEqual(
            (controller.pawn.location.x, controller.pawn.location.y, controller.pawn.location.z),
            origin,
        )
        self.assertAlmostEqual(controller.control.pitch, spec["pitch"])
        handle = controller.pawn.get_component_by_class(ue.PhysicsHandleComponent)
        self.assertEqual(handle.props["linear_stiffness"], 700.0)
        self.assertIsNotNone(handle.grabbed)
        self.assertEqual(handle.grabbed[1], "None")

        original_world = physics_build._game_world

        def explode(game_ue):
            raise RuntimeError("explode")

        physics_build._game_world = explode
        try:
            registered[0](0.016)
        finally:
            physics_build._game_world = original_world
        self.assertTrue(any("Physics tick failed" in message for message in ue.warnings))

    def test_config_enables_water_chaos_and_the_god_keys(self):
        project = json.loads((UNREAL / "ElyonUE.uproject").read_text(encoding="utf-8"))
        plugins = {item["Name"]: item["Enabled"] for item in project["Plugins"]}
        self.assertTrue(plugins["Water"])
        self.assertTrue(plugins["PCG"])
        engine = (UNREAL / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
        self.assertIn("[/Script/Engine.PhysicsSettings]", engine)
        self.assertIn("DefaultGravityZ=-980", engine)
        self.assertIn("bEnablePCM=True", engine)
        self.assertIn("bEnableStabilization=True", engine)
        self.assertIn("bSubstepping=True", engine)
        self.assertIn("MaxSubstepDeltaTime=0.008333", engine)
        self.assertIn("MaxSubsteps=4", engine)
        self.assertIn("bDisableCCD=False", engine)
        self.assertIn("r.DynamicGlobalIlluminationMethod=1", engine)
        inputs = (UNREAL / "Config" / "DefaultInput.ini").read_text(encoding="utf-8")
        for action, key_name in logic.ACTIONS:
            self.assertIn(f'ActionName="{action}"', inputs)
            self.assertIn(f"Key={logic.KEYS[key_name]}", inputs)
        readme = (UNREAL / "README.md").read_text(encoding="utf-8")
        self.assertIn("UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_all.py", readme)
        self.assertIn("one install package", readme)
        self.assertIn("free local LLM", readme)
        for phrase in (
            "Left mouse button grabs",
            "Q lifts",
            "Z lowers",
            "Right mouse button throws",
            "F pushes",
            "Middle mouse button",
            "divine force",
            "WindDirectionalSource",
            "Water plugin",
            "Chaos",
            "SimpleGrassWind",
        ):
            self.assertIn(phrase, readme)


if __name__ == "__main__":
    unittest.main()
