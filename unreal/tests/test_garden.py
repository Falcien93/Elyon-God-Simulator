import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import garden_logic
import level_build


class Vec:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class Rot:
    def __init__(self, pitch, yaw, roll):
        self.pitch, self.yaw, self.roll = pitch, yaw, roll


class Color:
    def __init__(self, r, g, b, a):
        self.rgba = (r, g, b, a)


class Comp:
    def __init__(self):
        self.props = {}
        self.mesh = None
        self.recaptured = 0

    def set_editor_property(self, name, value):
        self.props[name] = value

    def set_static_mesh(self, mesh):
        self.mesh = mesh

    def recapture_sky(self):
        self.recaptured += 1


class Actor:
    def __init__(self, cls):
        self.cls = cls
        self.label = ""
        self.location = None
        self.rotation = None
        self.scale = None
        self.props = {}
        self.comps = {}

    def set_actor_label(self, label):
        self.label = label

    def get_actor_label(self):
        return self.label

    def set_actor_location(self, loc, sweep, teleport):
        self.location = loc

    def set_actor_rotation(self, rot, teleport):
        self.rotation = rot

    def set_actor_scale3d(self, scale):
        self.scale = scale

    def set_editor_property(self, name, value):
        self.props[name] = value

    def get_component_by_class(self, cls):
        comp = self.comps.get(cls)
        if comp is None:
            comp = Comp()
            self.comps[cls] = comp
        return comp


class Subsystem:
    def __init__(self):
        self.actors = []

    def get_all_level_actors(self):
        return list(self.actors)

    def spawn_actor_from_class(self, cls, loc, rot):
        actor = Actor(cls)
        actor.location = loc
        actor.rotation = rot
        self.actors.append(actor)
        return actor

    def destroy_actor(self, actor):
        self.actors.remove(actor)


class AssetLib:
    def __init__(self):
        self.exists = False

    def does_asset_exist(self, path):
        return self.exists

    def load_asset(self, path):
        return path


class LevelLib:
    def __init__(self, assets):
        self.assets = assets
        self.loaded = None
        self.created = None
        self.saves = 0

    def load_level(self, path):
        self.loaded = path

    def new_level(self, path):
        self.created = path
        self.assets.exists = True

    def save_current_level(self):
        self.saves += 1


class FakeUnreal:
    def __init__(self):
        self.EditorActorSubsystem = type("EditorActorSubsystem", (), {})
        self.StaticMeshActor = type("StaticMeshActor", (), {})
        self.DirectionalLight = type("DirectionalLight", (), {})
        self.SkyLight = type("SkyLight", (), {})
        self.SkyAtmosphere = type("SkyAtmosphere", (), {})
        self.ExponentialHeightFog = type("ExponentialHeightFog", (), {})
        self.VolumetricCloud = type("VolumetricCloud", (), {})
        self.PlayerStart = type("PlayerStart", (), {})
        self.TargetPoint = type("TargetPoint", (), {})
        self.StaticMeshComponent = type("StaticMeshComponent", (), {})
        self.DirectionalLightComponent = type("DirectionalLightComponent", (), {})
        self.SkyLightComponent = type("SkyLightComponent", (), {})
        self.ExponentialHeightFogComponent = type("ExponentialHeightFogComponent", (), {})
        self.Vector = Vec
        self.Rotator = Rot
        self.LinearColor = Color
        self.EditorAssetLibrary = AssetLib()
        self.EditorLevelLibrary = LevelLib(self.EditorAssetLibrary)
        self.sub = Subsystem()

    def get_editor_subsystem(self, cls):
        return self.sub


def labels(ue):
    return sorted(actor.get_actor_label() for actor in ue.sub.actors)


class GardenLogicTests(unittest.TestCase):
    def test_scatter_is_stable_and_keeps_clearings(self):
        first = garden_logic.scatter("tree", garden_logic.COUNTS["tree"], garden_logic.SEED)
        second = garden_logic.scatter("tree", garden_logic.COUNTS["tree"], garden_logic.SEED)
        self.assertEqual(first, second)
        self.assertEqual(len(first), garden_logic.COUNTS["tree"])
        span = garden_logic.GARDEN_HALF * 0.8
        for item in first:
            self.assertLessEqual(abs(item["x"]), span)
            self.assertLessEqual(abs(item["y"]), span)
            self.assertFalse(garden_logic._blocked(item["x"], item["y"]))

    def test_light_toggle_values(self):
        dark = garden_logic.light_state(False)
        dawn = garden_logic.light_state(True)
        self.assertEqual(dark["name"], "darkness")
        self.assertEqual(dawn["name"], "dawn")
        self.assertLess(dark["sun_intensity"], 0.1)
        self.assertGreater(dawn["sun_intensity"], 5)
        self.assertGreater(dark["fog_density"], dawn["fog_density"])

    def test_plan_has_required_actors(self):
        plan = garden_logic.plan_level(True)
        names = garden_logic.planned_labels(plan)
        for label in (
            "Elyon.Ground",
            "Elyon.Sun",
            "Elyon.SkyLight",
            "Elyon.SkyAtmosphere",
            "Elyon.Fog",
            "Elyon.Clouds",
            "Elyon.River",
            "Elyon.PlayerStart",
            "Elyon.Adam",
            "Elyon.LetThereBeLight",
        ):
            self.assertIn(label, names)
        self.assertEqual(sum(1 for name in names if name.startswith("Elyon.Tree.")), 24)
        self.assertEqual(plan["map"], "/Game/Maps/Day1_Garden")

    def test_stale_labels_only_drop_old_elyon_actors(self):
        self.assertEqual(
            garden_logic.stale_labels(["Elyon.Tree.99", "Elyon.Ground", "SkySphere"], ["Elyon.Ground"]),
            ["Elyon.Tree.99"],
        )


class LevelBuildTests(unittest.TestCase):
    def test_build_is_idempotent_and_toggles_light(self):
        ue = FakeUnreal()
        first = level_build.build(dawn=True, ue=ue)
        spawned = labels(ue)
        self.assertEqual(ue.EditorLevelLibrary.created, "/Game/Maps/Day1_Garden")
        self.assertEqual(len(spawned), len(first["actors"]))
        self.assertEqual(ue.EditorLevelLibrary.saves, 1)
        sun = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Sun")
        sun_comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        self.assertEqual(sun_comp.props["intensity"], 10.0)
        ground = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Ground")
        mesh_comp = ground.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(mesh_comp.mesh, "/Engine/BasicShapes/Plane")

        old = Actor(ue.StaticMeshActor)
        old.set_actor_label("Elyon.OldRock")
        ue.sub.actors.append(old)
        level_build.build(dawn=True, ue=ue)
        self.assertNotIn("Elyon.OldRock", labels(ue))
        self.assertEqual(len(labels(ue)), len(first["actors"]))
        self.assertEqual(ue.EditorLevelLibrary.loaded, "/Game/Maps/Day1_Garden")

        dark = level_build.let_there_be_light(False, ue=ue)
        self.assertEqual(dark["name"], "darkness")
        self.assertEqual(sun_comp.props["intensity"], 0.02)
        marker = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.LetThereBeLight")
        self.assertEqual(marker.props["tags"], ["darkness"])


if __name__ == "__main__":
    unittest.main()
