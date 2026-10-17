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
FCOLOR_PROPS = {"light_color", "bloom_tint", "volumetric_fog_albedo"}
LINEAR_PROPS = {
    "fog_inscattering_luminance",
    "directional_inscattering_luminance",
    "volumetric_fog_emissive",
}


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


class PostProcessSettings:
    def __init__(self):
        self.props = {}

    def set_editor_property(self, name, value):
        self.props[name] = value


class AutoExposureMethod:
    AEM_HISTOGRAM = "AEM_HISTOGRAM"


class AssetLib:
    def __init__(self):
        self.map_ready = False
        self.present = set()

    def does_asset_exist(self, path):
        if path == "/Game/Maps/Day1_Garden":
            return self.map_ready
        return path in self.present

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
        self.assets.map_ready = True

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
        self.PostProcessVolume = type("PostProcessVolume", (), {})
        self.PostProcessSettings = PostProcessSettings
        self.AutoExposureMethod = AutoExposureMethod
        self.CineCameraActor = type("CineCameraActor", (), {})
        self.CineCameraComponent = type("CineCameraComponent", (), {})
        self.LevelSequenceActor = type("LevelSequenceActor", (), {})
        self.SkyAtmosphereComponent = type("SkyAtmosphereComponent", (), {})
        self.VolumetricCloudComponent = type("VolumetricCloudComponent", (), {})
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
            "Elyon.Terrain",
            "Elyon.Sun",
            "Elyon.SkyLight",
            "Elyon.SkyAtmosphere",
            "Elyon.Fog",
            "Elyon.Clouds",
            "Elyon.Exposure",
            "Elyon.River",
            "Elyon.Lake",
            "Elyon.GodCamera",
            "Elyon.GodFlythrough",
            "Elyon.PlayerStart",
            "Elyon.Adam",
            "Elyon.LetThereBeLight",
        ):
            self.assertIn(label, names)
        self.assertNotIn("Elyon.Ground", names)
        self.assertEqual(sum(1 for name in names if name.startswith("Elyon.Tree.")), garden_logic.COUNTS["tree"])
        self.assertEqual(sum(1 for name in names if name.startswith("Elyon.Rock.")), garden_logic.COUNTS["rock"])
        self.assertEqual(sum(1 for name in names if name.startswith("Elyon.Plant.")), garden_logic.COUNTS["plant"])
        self.assertEqual(plan["map"], "/Game/Maps/Day1_Garden")

    def test_god_flight_stays_high_and_moves_smoothly(self):
        flight = garden_logic.god_flight()
        self.assertGreaterEqual(flight[-1]["t"], 20.0)
        self.assertGreater(abs(flight[0]["x"] - flight[-1]["x"]) + abs(flight[0]["y"] - flight[-1]["y"]), 500.0)
        previous = None
        toward_sun = False
        for sample in flight:
            self.assertGreaterEqual(sample["z"], 1200.0)
            self.assertLess(sample["pitch"], 15.0)
            if previous is not None:
                step = (
                    (sample["x"] - previous["x"]) ** 2
                    + (sample["y"] - previous["y"]) ** 2
                    + (sample["z"] - previous["z"]) ** 2
                ) ** 0.5
                self.assertLess(step, 800.0)
            previous = sample
            # The low sun sits toward negative X/Y. One stretch of the path looks that way.
            if sample["x"] > 1000.0 and sample["yaw"] < -90.0:
                toward_sun = True
        self.assertTrue(toward_sun)
        dawn = garden_logic.light_state(True)
        dark = garden_logic.light_state(False)
        self.assertFalse(dawn["enable_volumetric_fog"])
        self.assertFalse(dark["enable_volumetric_fog"])
        self.assertFalse(dawn["enable_light_shaft_bloom"])
        self.assertFalse(dark["enable_light_shaft_bloom"])
        self.assertEqual(dawn["vignette_intensity"], 0.0)
        self.assertEqual(dawn["scene_fringe_intensity"], 0.0)
        self.assertEqual(dawn["lens_flare_intensity"], 0.0)
        self.assertLess(dawn["fog_max_opacity"], 0.25)
        self.assertLess(dawn["bloom_intensity"], 0.15)

    def test_free_meshes_prefer_starter_then_engine_shapes(self):
        starter = {
            "/Game/StarterContent/Props/SM_Bush",
            "/Game/StarterContent/Props/SM_Rock",
        }
        self.assertEqual(
            garden_logic.resolve_candidate(garden_logic.MESH_CANDIDATES["tree"], starter),
            "/Game/StarterContent/Props/SM_Bush",
        )
        self.assertEqual(
            garden_logic.resolve_candidate(garden_logic.MESH_CANDIDATES["rock"], starter),
            "/Game/StarterContent/Props/SM_Rock",
        )
        self.assertEqual(
            garden_logic.resolve_candidate(garden_logic.MESH_CANDIDATES["tree"], set()),
            "/Engine/BasicShapes/Cone",
        )
        self.assertEqual(
            garden_logic.resolve_candidate(garden_logic.MESH_CANDIDATES["terrain"], set()),
            "/Engine/BasicShapes/Plane",
        )
        for group in list(garden_logic.MESH_CANDIDATES.values()) + list(garden_logic.MATERIAL_CANDIDATES.values()):
            for path in group:
                self.assertFalse(path.startswith("/Game/Marketplace"))

    def test_stale_labels_only_drop_old_elyon_actors(self):
        self.assertEqual(
            garden_logic.stale_labels(["Elyon.Tree.99", "Elyon.Ground", "SkySphere"], ["Elyon.Terrain"]),
            ["Elyon.Ground", "Elyon.Tree.99"],
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
        self.assertEqual(sun_comp.props["intensity"], 8.0)
        self.assertIsInstance(sun_comp.props["light_color"], ByteColor)
        self.assertEqual(sun_comp.props["light_color"].rgba, (255, 140, 64, 255))
        with self.assertRaises(TypeError):
            sun_comp.set_editor_property("light_color", ue.LinearColor(1.0, 0.55, 0.25, 1.0))
        sky = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.SkyLight")
        sky_comp = sky.get_component_by_class(ue.SkyLightComponent)
        self.assertIsInstance(sky_comp.props["light_color"], ByteColor)
        self.assertEqual(sky_comp.props["light_color"].rgba, (255, 199, 140, 255))
        fog = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Fog")
        fog_comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        self.assertIsInstance(fog_comp.props["fog_inscattering_luminance"], LinearColor)
        self.assertEqual(fog_comp.props["fog_inscattering_luminance"].rgba, (0.75, 0.78, 0.82, 1.0))
        self.assertEqual(fog_comp.props["fog_density"], 0.0008)
        self.assertEqual(fog_comp.props["start_distance"], 8000.0)
        self.assertEqual(fog_comp.props["fog_max_opacity"], 0.15)
        with self.assertRaises(TypeError):
            fog_comp.set_editor_property("fog_inscattering_luminance", ue.Color(158, 92, 41, 255))
        terrain = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Terrain")
        mesh_comp = terrain.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(mesh_comp.mesh, "/Engine/BasicShapes/Plane")
        self.assertEqual((terrain.scale.x, terrain.scale.y, terrain.scale.z), (800.0, 800.0, 1.0))
        tree = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Tree.01")
        tree_mesh = tree.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(tree_mesh.mesh, "/Engine/BasicShapes/Cone")
        exposure = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Exposure")
        self.assertTrue(exposure.props["unbound"])
        self.assertEqual(exposure.props["priority"], 10.0)
        settings = exposure.props["settings"]
        self.assertEqual(settings.props["auto_exposure_method"], "AEM_HISTOGRAM")
        self.assertEqual(settings.props["auto_exposure_min_brightness"], 12.0)
        self.assertEqual(settings.props["auto_exposure_max_brightness"], 14.0)
        self.assertEqual(settings.props["auto_exposure_bias"], 0.35)
        self.assertEqual(settings.props["bloom_intensity"], 0.05)
        self.assertEqual(settings.props["vignette_intensity"], 0.0)
        self.assertEqual(settings.props["scene_fringe_intensity"], 0.0)
        self.assertEqual(settings.props["lens_flare_intensity"], 0.0)
        self.assertEqual(settings.props["screen_space_reflection_intensity"], 70.0)
        self.assertEqual(settings.props["white_temp"], 5200.0)
        self.assertFalse(fog_comp.props["enable_volumetric_fog"])
        self.assertIsInstance(fog_comp.props["volumetric_fog_albedo"], ByteColor)
        self.assertIsInstance(fog_comp.props["volumetric_fog_emissive"], LinearColor)
        self.assertIsInstance(fog_comp.props["directional_inscattering_luminance"], LinearColor)
        self.assertFalse(sun_comp.props["cast_volumetric_shadow"])
        self.assertFalse(sun_comp.props["enable_light_shaft_bloom"])
        self.assertIsInstance(sun_comp.props["bloom_tint"], ByteColor)
        self.assertEqual(sun_comp.props["bloom_tint"].rgba, (255, 230, 191, 255))
        self.assertFalse(tree_mesh.props["disallow_nanite"])
        self.assertNotIn("SkySphere", labels(ue))
        with self.assertRaises(TypeError):
            fog_comp.set_editor_property("volumetric_fog_albedo", ue.LinearColor(1, 1, 1, 1))
        camera = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.GodCamera")
        lens = camera.get_component_by_class(ue.CineCameraComponent)
        self.assertEqual(lens.props["current_focal_length"], 24.0)
        self.assertEqual(lens.props["current_aperture"], 8.0)
        self.assertGreaterEqual(camera.location.z, 1200.0)
        lake = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Lake")
        lake_mesh = lake.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(lake_mesh.mesh, "/Engine/BasicShapes/Cube")

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
        dark_settings = exposure.props["settings"]
        self.assertEqual(dark_settings.props["auto_exposure_min_brightness"], -1.0)
        self.assertEqual(dark_settings.props["auto_exposure_max_brightness"], 2.0)
        self.assertEqual(fog_comp.props["fog_density"], 0.0025)
        self.assertFalse(sun_comp.props["enable_light_shaft_bloom"])
        self.assertEqual(dark_settings.props["vignette_intensity"], 0.0)
        self.assertEqual(settings.props["white_temp"], 5200.0)
        self.assertEqual(dark_settings.props["white_temp"], 9000.0)

    def test_starter_content_replaces_engine_shapes(self):
        ue = FakeUnreal()
        ue.EditorAssetLibrary.present.update(
            {
                "/Game/StarterContent/Props/SM_Bush",
                "/Game/StarterContent/Props/SM_Rock",
                "/Game/StarterContent/Materials/M_Ground_Grass",
            }
        )
        level_build.build(dawn=True, ue=ue)
        tree = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Tree.01")
        tree_mesh = tree.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(tree_mesh.mesh, "/Game/StarterContent/Props/SM_Bush")
        self.assertEqual(tree.scale.x, tree.scale.y)
        self.assertEqual(tree.scale.x, tree.scale.z)
        rock = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Rock.01")
        rock_mesh = rock.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(rock_mesh.mesh, "/Game/StarterContent/Props/SM_Rock")

    def test_project_forest_and_rocks_enable_nanite(self):
        ue = FakeUnreal()

        class MeshAsset:
            def __init__(self):
                self.props = {}

            def set_editor_property(self, name, value):
                self.props[name] = value

        class NaniteSettings:
            def __init__(self):
                self.props = {}

            def set_editor_property(self, name, value):
                self.props[name] = value

        ue.MeshNaniteSettings = NaniteSettings
        loaded = {}

        def load_asset(path):
            loaded.setdefault(path, MeshAsset())
            return loaded[path]

        ue.EditorAssetLibrary.load_asset = load_asset
        ue.EditorAssetLibrary.present.update(
            {
                "/Game/Fab/Foliage/SM_Tree",
                "/Game/Fab/Foliage/SM_Rock",
            }
        )
        level_build.build(dawn=True, ue=ue)
        self.assertTrue(loaded["/Game/Fab/Foliage/SM_Tree"].props["nanite_settings"].props["enabled"])
        self.assertTrue(loaded["/Game/Fab/Foliage/SM_Rock"].props["nanite_settings"].props["enabled"])
        self.assertNotIn("nanite_settings", loaded["/Engine/BasicShapes/Plane"].props)
        plant = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Plant.01")
        plant_mesh = plant.get_component_by_class(ue.StaticMeshComponent)
        self.assertNotIn("disallow_nanite", plant_mesh.props)

    def test_sky_uses_the_engine_aerial_perspective_spelling(self):
        ue = FakeUnreal()
        level_build.build(dawn=True, ue=ue)
        sky = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.SkyAtmosphere")
        comp = sky.get_component_by_class(ue.SkyAtmosphereComponent)
        self.assertEqual(comp.props["aerial_pespective_view_distance_scale"], 1.0)
        self.assertNotIn("aerial_perspective_view_distance_scale", comp.props)
        self.assertNotIn("aerial_perspective_view_distance_scale", garden_logic.light_state(False))

    def test_flythrough_range_uses_display_rate_ints(self):
        ue = FakeUnreal()
        ranges = []
        keys = []

        class Section:
            def set_range(self, start, end):
                if type(start) is not int or type(end) is not int:
                    raise TypeError("Cannot nativize FrameNumber as StartFrame (IntProperty)")
                ranges.append((start, end))

            def set_camera_binding_id(self, binding_id):
                self.binding_id = binding_id

        class Track:
            def add_section(self):
                return Section()

        class Binding:
            def add_track(self, cls):
                return Track()

        class Sequence:
            def set_display_rate(self, rate):
                self.rate = rate

            def set_playback_start(self, frame):
                self.playback_start = frame

            def set_playback_end(self, frame):
                self.playback_end = frame

        class Tools:
            def create_asset(self, name, path, cls, factory):
                return Sequence()

        class Helpers:
            @staticmethod
            def get_asset_tools():
                return Tools()

        class Channel:
            def add_key(self, frame, value):
                keys.append(frame)

        class SequenceExtensions:
            @staticmethod
            def add_possessable(sequence, camera):
                return Binding()

            @staticmethod
            def add_master_track(sequence, cls):
                return Track()

            @staticmethod
            def get_binding_id(sequence, binding):
                return "binding"

        class SectionExtensions:
            @staticmethod
            def get_channel(section, name):
                return Channel()

        ue.LevelSequence = type("LevelSequence", (), {})
        ue.LevelSequenceFactoryNew = lambda: None
        ue.AssetToolsHelpers = Helpers
        ue.FrameRate = lambda numerator, denominator: (numerator, denominator)
        ue.FrameNumber = lambda number: ("frame", int(number))
        ue.MovieSceneSequenceExtensions = SequenceExtensions
        ue.MovieSceneSectionExtensions = SectionExtensions
        ue.MovieScene3DTransformTrack = type("TransformTrack", (), {})
        ue.MovieSceneCameraCutTrack = type("CutTrack", (), {})
        ue.EditorAssetLibrary.save_asset = lambda path, only_if_is_dirty=False: None
        warnings = []
        ue.log_warning = warnings.append
        level_build.build(dawn=True, ue=ue)
        end = int(round(garden_logic.god_flight()[-1]["t"] * 24))
        self.assertEqual(ranges, [(0, end), (0, end)])
        self.assertTrue(keys)
        self.assertTrue(all(isinstance(frame, tuple) and frame[0] == "frame" for frame in keys))
        self.assertEqual(ue.EditorLevelLibrary.saves, 1)
        self.assertFalse(any("flythrough" in message for message in warnings))

    def test_flythrough_failure_still_saves_the_garden(self):
        ue = FakeUnreal()
        ue.LevelSequence = type("LevelSequence", (), {})
        ue.LevelSequenceFactoryNew = type("Factory", (), {})

        class Tools:
            def get_asset_tools(self):
                raise RuntimeError("sequencer unavailable")

        ue.AssetToolsHelpers = Tools()
        level_build.build(dawn=True, ue=ue)
        self.assertEqual(ue.EditorLevelLibrary.saves, 1)
        self.assertIn("Elyon.GodCamera", labels(ue))
        self.assertIn("Elyon.Lake", labels(ue))

    def test_run_all_keeps_the_editor_open(self):
        ue = FakeUnreal()
        run_all.main(ue)
        self.assertTrue(ue.EditorPythonScripting.alive)


if __name__ == "__main__":
    unittest.main()
