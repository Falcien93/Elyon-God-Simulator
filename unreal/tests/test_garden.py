import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import garden_logic
import level_build
import run_all


class Vec:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class Rot:
    def __init__(self, pitch, yaw, roll):
        self.pitch, self.yaw, self.roll = pitch, yaw, roll


class ByteColor:
    """Stand-in for unreal.Color. Channels are ints from 0 to 255."""

    def __init__(self, r, g, b, a=255):
        channels = (r, g, b, a)
        for channel in channels:
            if type(channel) is not int:
                raise TypeError("unreal.Color channels must be ints from 0 to 255")
            if channel < 0 or channel > 255:
                raise ValueError("unreal.Color channel out of range")
        self.rgba = channels


class LinearColor:
    """Stand-in for unreal.LinearColor. Channels are 0-1 floats."""

    def __init__(self, r, g, b, a=1.0):
        self.rgba = (float(r), float(g), float(b), float(a))


# light_color on directional and sky lights is FColor. Fog inscattering is FLinearColor.
FCOLOR_PROPS = {"light_color"}
LINEAR_PROPS = {"fog_inscattering_luminance"}


class Comp:
    def __init__(self):
        self.props = {}
        self.mesh = None
        self.recaptured = 0

    def set_editor_property(self, name, value):
        if name in FCOLOR_PROPS and not isinstance(value, ByteColor):
            raise TypeError(f"{name} expects unreal.Color (0-255 ints), not {type(value).__name__}")
        if name in LINEAR_PROPS and not isinstance(value, LinearColor):
            raise TypeError(f"{name} expects unreal.LinearColor, not {type(value).__name__}")
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


class EditorPythonScripting:
    def __init__(self):
        self.alive = False

    def set_keep_python_script_alive(self, keep_alive):
        self.alive = bool(keep_alive)


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
        self.Color = ByteColor
        self.LinearColor = LinearColor
        self.EditorPythonScripting = EditorPythonScripting()
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
        self.assertIsInstance(sun_comp.props["light_color"], ByteColor)
        self.assertEqual(sun_comp.props["light_color"].rgba, (255, 237, 199, 255))
        with self.assertRaises(TypeError):
            sun_comp.set_editor_property("light_color", ue.LinearColor(1.0, 0.93, 0.78, 1.0))
        sky = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.SkyLight")
        sky_comp = sky.get_component_by_class(ue.SkyLightComponent)
        self.assertIsInstance(sky_comp.props["light_color"], ByteColor)
        fog = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Fog")
        fog_comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        self.assertIsInstance(fog_comp.props["fog_inscattering_luminance"], LinearColor)
        self.assertEqual(fog_comp.props["fog_inscattering_luminance"].rgba, (0.75, 0.82, 0.95, 1.0))
        with self.assertRaises(TypeError):
            fog_comp.set_editor_property("fog_inscattering_luminance", ue.Color(191, 209, 242, 255))
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
        self.assertIsInstance(sun_comp.props["light_color"], ByteColor)
        self.assertEqual(sun_comp.props["light_color"].rgba, (13, 18, 36, 255))
        self.assertIsInstance(fog_comp.props["fog_inscattering_luminance"], LinearColor)
        marker = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.LetThereBeLight")
        self.assertEqual(marker.props["tags"], ["darkness"])

    def test_run_all_keeps_the_editor_open(self):
        ue = FakeUnreal()
        run_all.main(ue)
        self.assertTrue(ue.EditorPythonScripting.alive)


if __name__ == "__main__":
    unittest.main()
