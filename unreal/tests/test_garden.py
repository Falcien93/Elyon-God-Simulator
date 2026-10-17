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
    """Python unreal.Rotator argument order is roll, pitch, yaw."""

    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0):
        self.roll = float(roll)
        self.pitch = float(pitch)
        self.yaw = float(yaw)


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

    def get_editor_property(self, name):
        return self.props.get(name)

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

    def set_is_temporarily_hidden_in_editor(self, hidden):
        self.hidden = bool(hidden)

    def set_editor_property(self, name, value):
        self.props[name] = value

    def get_editor_property(self, name):
        return self.props.get(name)

    def get_actor_rotation(self):
        return self.rotation

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

    def get_editor_property(self, name):
        return self.props.get(name)


class AutoExposureMethod:
    AEM_HISTOGRAM = "AEM_HISTOGRAM"
    AEM_MANUAL = "AEM_MANUAL"


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


class ViewportSubsystem:
    def __init__(self):
        self.viewport = None

    def set_level_viewport_camera_info(self, location, rotation):
        self.viewport = (location, rotation)

    def get_level_viewport_camera_info(self):
        if self.viewport is None:
            return (Vec(0.0, 0.0, 0.0), Rot())
        return self.viewport


class LevelEditorSubsystem:
    def __init__(self):
        self.invalidated = 0

    def editor_invalidate_viewports(self):
        self.invalidated += 1


class SystemLibrary:
    def __init__(self):
        self.commands = []

    def execute_console_command(self, world, command):
        self.commands.append(command)


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
        self.SkyLightSourceType = type("SkyLightSourceType", (), {"SLS_CAPTURED_SCENE": "SLS_CAPTURED_SCENE"})
        self.ComponentMobility = type("ComponentMobility", (), {"MOVABLE": "MOVABLE"})
        self.ExponentialHeightFogComponent = type("ExponentialHeightFogComponent", (), {})
        self.Vector = Vec
        self.Rotator = Rot
        self.Color = ByteColor
        self.LinearColor = LinearColor
        self.EditorPythonScripting = EditorPythonScripting()
        self.EditorAssetLibrary = AssetLib()
        self.EditorLevelLibrary = LevelLib(self.EditorAssetLibrary)
        self.UnrealEditorSubsystem = type("UnrealEditorSubsystem", (), {})
        self.LevelEditorSubsystem = type("LevelEditorSubsystem", (), {})
        self.viewport_subsystem = ViewportSubsystem()
        self.level_editor = LevelEditorSubsystem()
        self.SystemLibrary = SystemLibrary()
        self.logs = []
        self.warnings = []
        self.sub = Subsystem()

    def log(self, message):
        self.logs.append(message)

    def log_warning(self, message):
        self.warnings.append(message)
        self.logs.append(message)

    def get_editor_subsystem(self, cls):
        if cls is self.UnrealEditorSubsystem:
            return self.viewport_subsystem
        if cls is self.LevelEditorSubsystem:
            return self.level_editor
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
        self.assertGreaterEqual(dawn["sun_intensity"], 100000.0)
        self.assertGreaterEqual(dawn["sun_pitch"], -25.0)
        self.assertLessEqual(dawn["sun_pitch"], -15.0)
        # ISO 100, 1/250 s, f/8 is about EV 14, inside the [-4, 16] cache window.
        self.assertEqual(dawn["exposure_bias"], 0.0)
        self.assertTrue(dawn["apply_physical_camera_exposure"])
        ev = garden_logic.physical_ev100(dawn["camera_fstop"], dawn["camera_shutter_speed"], dawn["camera_iso"])
        self.assertAlmostEqual(ev, 14.0, delta=0.1)
        self.assertGreaterEqual(ev, -4.0)
        self.assertLessEqual(ev, 16.0)
        self.assertFalse(dark.get("apply_physical_camera_exposure", False))
        self.assertEqual(dark["exposure_bias"], -2.0)
        self.assertLess(dawn["fog_density"], 0.01)
        self.assertLessEqual(dawn["fog_max_opacity"], 0.22)
        self.assertGreater(dawn["fog_start_distance"], 1000.0)
        self.assertGreater(garden_logic.OVERVIEW["z"], 2000.0)
        self.assertNotIn("exposure_histogram_min_ev", dawn)
        self.assertEqual(dawn["skylight_intensity"], 0.6)
        self.assertEqual(dawn["white_temp"], 4300.0)
        self.assertEqual(dawn["cloud_view_sample_scale"], 0.6)
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
        self.assertEqual(sum(1 for name in names if name.startswith("Elyon.Trunk.")), garden_logic.COUNTS["tree"])
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
            "/Engine/BasicShapes/Sphere",
        )
        self.assertEqual(
            garden_logic.resolve_candidate(garden_logic.MESH_CANDIDATES["plant"], set()),
            "/Engine/BasicShapes/Sphere",
        )
        self.assertEqual(
            garden_logic.resolve_candidate(garden_logic.MESH_CANDIDATES["trunk"], set()),
            "/Engine/BasicShapes/Cylinder",
        )
        self.assertEqual(
            garden_logic.resolve_candidate(
                garden_logic.MATERIAL_CANDIDATES["water"],
                {"/Water/Materials/WaterSurface/Water_Material_Lake"},
            ),
            "/Water/Materials/WaterSurface/Water_Material_Lake",
        )
        self.assertEqual(
            garden_logic.resolve_candidate(garden_logic.MATERIAL_CANDIDATES["water"], set()),
            "/Game/Materials/M_Elyon_Water",
        )
        self.assertTrue(garden_logic.AUTHORED_MATERIALS["/Game/Materials/M_Elyon_Grass"]["variation"])
        self.assertTrue(garden_logic.AUTHORED_MATERIALS["/Game/Materials/M_Elyon_Water"]["animated"])
        self.assertFalse(garden_logic.trunk_hidden(set()))
        self.assertTrue(garden_logic.trunk_hidden({"/Game/Fab/Foliage/SM_Tree"}))
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
        self.assertEqual(sun_comp.props["intensity"], 120000.0)
        self.assertEqual(sun.rotation.pitch, -20.0)
        self.assertEqual(sun.rotation.yaw, 35.0)
        self.assertIsInstance(sun_comp.props["light_color"], ByteColor)
        self.assertEqual(sun_comp.props["light_color"].rgba, (255, 140, 64, 255))
        with self.assertRaises(TypeError):
            sun_comp.set_editor_property("light_color", ue.LinearColor(1.0, 0.55, 0.25, 1.0))
        sky = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.SkyLight")
        sky_comp = sky.get_component_by_class(ue.SkyLightComponent)
        self.assertIsInstance(sky_comp.props["light_color"], ByteColor)
        self.assertEqual(sky_comp.props["light_color"].rgba, (255, 189, 128, 255))
        self.assertEqual(sky_comp.props["intensity"], 0.6)
        self.assertTrue(sky_comp.props["real_time_capture"])
        self.assertEqual(sky_comp.props["source_type"], "SLS_CAPTURED_SCENE")
        self.assertEqual(sky_comp.props["mobility"], "MOVABLE")
        self.assertFalse(sky_comp.props["lower_hemisphere_is_black"])
        self.assertEqual(sky_comp.recaptured, 1)
        fog = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Fog")
        fog_comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        self.assertIsInstance(fog_comp.props["fog_inscattering_luminance"], LinearColor)
        self.assertEqual(fog_comp.props["fog_inscattering_luminance"].rgba, (0.96, 0.7, 0.46, 1.0))
        self.assertEqual(fog_comp.props["fog_density"], 0.0016)
        self.assertEqual(fog_comp.props["start_distance"], 4500.0)
        self.assertEqual(fog_comp.props["fog_max_opacity"], 0.2)
        with self.assertRaises(TypeError):
            fog_comp.set_editor_property("fog_inscattering_luminance", ue.Color(158, 92, 41, 255))
        terrain = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Terrain")
        mesh_comp = terrain.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(mesh_comp.mesh, "/Engine/BasicShapes/Plane")
        self.assertEqual((terrain.scale.x, terrain.scale.y, terrain.scale.z), (800.0, 800.0, 1.0))
        tree = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Tree.01")
        tree_mesh = tree.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(tree_mesh.mesh, "/Engine/BasicShapes/Sphere")
        first_tree = garden_logic.scatter("tree", garden_logic.COUNTS["tree"], garden_logic.SEED)[0]
        crown_z, crown_scale = garden_logic.tree_canopy_placement(first_tree["scale"], tree_mesh.mesh)
        self.assertAlmostEqual(tree.location.z, crown_z)
        self.assertEqual((tree.scale.x, tree.scale.y, tree.scale.z), crown_scale)
        trunk = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Trunk.01")
        trunk_mesh = trunk.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(trunk_mesh.mesh, "/Engine/BasicShapes/Cylinder")
        trunk_z, trunk_scale = garden_logic.trunk_placement(first_tree["scale"])
        self.assertAlmostEqual(trunk.location.z, trunk_z)
        self.assertEqual((trunk.scale.x, trunk.scale.y, trunk.scale.z), trunk_scale)
        self.assertFalse(getattr(trunk, "hidden", False))
        clouds = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Clouds")
        cloud_comp = clouds.get_component_by_class(ue.VolumetricCloudComponent)
        self.assertEqual(cloud_comp.props["layer_bottom_altitude"], 1.2)
        self.assertEqual(cloud_comp.props["layer_height"], 2.8)
        self.assertEqual(cloud_comp.props["view_sample_count_scale"], 0.6)
        self.assertIsInstance(cloud_comp.props["ground_albedo"], LinearColor)
        self.assertEqual(cloud_comp.props["ground_albedo"].rgba, (0.55, 0.32, 0.16, 1.0))
        exposure = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Exposure")
        self.assertTrue(exposure.props["unbound"])
        self.assertEqual(exposure.props["priority"], 10.0)
        settings = exposure.props["settings"]
        self.assertEqual(settings.props["auto_exposure_method"], "AEM_MANUAL")
        self.assertEqual(settings.props["auto_exposure_bias"], 0.0)
        self.assertNotIn("auto_exposure_histogram_log_min", settings.props)
        self.assertNotIn("auto_exposure_histogram_log_max", settings.props)
        self.assertTrue(settings.props["auto_exposure_apply_physical_camera_exposure"])
        self.assertEqual(settings.props["camera_iso"], 100.0)
        self.assertEqual(settings.props["camera_shutter_speed"], 250.0)
        self.assertEqual(settings.props["depth_of_field_fstop"], 8.0)
        self.assertEqual(settings.props["bloom_intensity"], 0.05)
        self.assertEqual(settings.props["vignette_intensity"], 0.0)
        self.assertEqual(settings.props["scene_fringe_intensity"], 0.0)
        self.assertEqual(settings.props["lens_flare_intensity"], 0.0)
        self.assertEqual(settings.props["screen_space_reflection_intensity"], 70.0)
        self.assertEqual(settings.props["white_temp"], 4300.0)
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
        self.assertEqual(dark_settings.props["auto_exposure_method"], "AEM_MANUAL")
        self.assertEqual(dark_settings.props["auto_exposure_bias"], -2.0)
        self.assertFalse(dark_settings.props["auto_exposure_apply_physical_camera_exposure"])
        self.assertEqual(fog_comp.props["fog_density"], 0.0025)
        self.assertFalse(sun_comp.props["enable_light_shaft_bloom"])
        self.assertEqual(dark_settings.props["vignette_intensity"], 0.0)
        self.assertEqual(settings.props["white_temp"], 4300.0)
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
        self.assertGreater(tree.location.z, 100.0)
        trunk = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Trunk.01")
        trunk_mesh = trunk.get_component_by_class(ue.StaticMeshComponent)
        self.assertEqual(trunk_mesh.mesh, "/Engine/BasicShapes/Cylinder")
        self.assertGreater(trunk.scale.z, 1.0)
        self.assertFalse(getattr(trunk, "hidden", False))
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
        tree = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Tree.01")
        self.assertEqual(tree.location.z, 0.0)
        trunk = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.Trunk.01")
        self.assertLess(trunk.scale.x, 0.05)
        self.assertTrue(trunk.hidden)

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

        added_tracks = []

        class Sequence:
            def set_display_rate(self, rate):
                self.rate = rate

            def set_playback_start(self, frame):
                self.playback_start = frame

            def set_playback_end(self, frame):
                self.playback_end = frame

            def add_track(self, track_type):
                added_tracks.append(track_type)
                return Track()

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
        self.assertEqual(added_tracks, [ue.MovieSceneCameraCutTrack])
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
        self.assertIn("Elyon run_all finished", ue.logs)
        self.assertIn("Elyon garden build finished", ue.logs)
        self.assertLess(ue.logs.index("Elyon garden build finished"), ue.logs.index("Elyon run_all finished"))
        self.assertEqual(ue.SystemLibrary.commands, ["HighResShot 1920x1080"])
        self.assertIn("frame check skipped", "\n".join(ue.logs))
        location, rotation = ue.viewport_subsystem.viewport
        self.assertEqual((location.x, location.y, location.z), (0.0, -4800.0, 2600.0))
        self.assertEqual((rotation.pitch, rotation.yaw), (-24.0, 90.0))

    def test_sky_recapture_runs_on_the_next_editor_tick(self):
        ue = FakeUnreal()
        callbacks = []

        def register(fn):
            callbacks.append(fn)
            return 7

        def unregister(handle):
            self.assertEqual(handle, 7)

        ue.register_slate_post_tick_callback = register
        ue.unregister_slate_post_tick_callback = unregister
        level_build.build(dawn=True, ue=ue)
        sky = next(actor for actor in ue.sub.actors if actor.get_actor_label() == "Elyon.SkyLight")
        sky_comp = sky.get_component_by_class(ue.SkyLightComponent)
        self.assertEqual(sky_comp.recaptured, 0)
        self.assertIn("Elyon sky recapture queued", ue.logs)
        self.assertIn("Elyon garden build finished", ue.logs)
        self.assertEqual(len(callbacks), 1)
        callbacks[0](0.0)
        self.assertEqual(sky_comp.recaptured, 1)
        self.assertIn("Elyon sky recapture finished", ue.logs)

    def test_diag_shot_logs_lighting_and_saves_from_the_overview(self):
        import diag_shot

        ue = FakeUnreal()
        level_build.build(dawn=True, ue=ue)
        ue.viewport_subsystem.viewport = (Vec(1.0, 2.0, 3.0), Rot())
        diag_shot.diagnose(ue)
        text = "\n".join(ue.logs)
        self.assertIn("intensity_lux=120000.0", text)
        self.assertIn("pitch=-20.0", text)
        self.assertIn("yaw=35.0", text)
        self.assertIn("roll=0.0", text)
        self.assertIn("method=AEM_MANUAL", text)
        self.assertIn("bias=0.0", text)
        self.assertIn("physical_camera=True", text)
        self.assertIn("iso=100.0", text)
        self.assertIn("shutter=250.0", text)
        self.assertIn("fstop=8.0", text)
        self.assertIn("x=1.0 y=2.0 z=3.0", text)
        self.assertEqual(ue.SystemLibrary.commands, ["HighResShot 1920x1080"])
        self.assertIn("Saved/Screenshots", text)
        self.assertIn("frame check skipped", text)
        location, rotation = ue.viewport_subsystem.viewport
        self.assertEqual((location.x, location.y, location.z), (0.0, -4800.0, 2600.0))
        self.assertEqual(rotation.pitch, -24.0)
        self.assertEqual(rotation.yaw, 90.0)
        self.assertGreater(ue.level_editor.invalidated, 0)
        swapped = ue.Rotator(-20.0, 35.0, 0.0)
        self.assertEqual((swapped.pitch, swapped.yaw, swapped.roll), (35.0, 0.0, -20.0))

    def test_shot_check_flags_black_and_white_frames(self):
        import shot_check

        black = shot_check.write_rgb_png(4, 4, lambda _x, _y: (0, 0, 0))
        white = shot_check.write_rgb_png(4, 4, lambda _x, _y: (255, 255, 255))
        day = shot_check.write_rgb_png(4, 4, lambda x, _y: (40, 80, 30) if x < 2 else (180, 140, 90))
        # A corner gizmo must not hide an otherwise black frame.
        gizmo = shot_check.write_rgb_png(
            8,
            8,
            lambda x, y: (255, 0, 0) if x == 0 and y == 7 else (0, 0, 0),
        )
        self.assertEqual(shot_check.classify_png(black, stride=1)[0], "black")
        self.assertEqual(shot_check.classify_png(white, stride=1)[0], "white")
        self.assertEqual(shot_check.classify_png(day, stride=1)[0], "ok")
        self.assertEqual(shot_check.classify_png(gizmo, stride=1)[0], "black")

    def test_authored_grass_varies_and_water_moves(self):
        ue = FakeUnreal()
        created = []

        class Expr:
            def __init__(self, cls):
                self.cls = cls
                self.props = {}

            def set_editor_property(self, name, value):
                self.props[name] = value

        class Material:
            def __init__(self):
                self.props = {}

            def set_editor_property(self, name, value):
                self.props[name] = value

        class Library:
            @staticmethod
            def create_material_expression(material, cls, x, y):
                expr = Expr(cls)
                created.append(expr)
                return expr

            @staticmethod
            def connect_material_expressions(source, source_pin, dest, dest_pin):
                created.append(("link", source_pin, dest_pin))

            @staticmethod
            def connect_material_property(expr, output, prop):
                created.append(("prop", prop))

            @staticmethod
            def recompile_material(material):
                return None

        class Tools:
            def create_asset(self, name, path, cls, factory):
                return Material()

        class Helpers:
            @staticmethod
            def get_asset_tools():
                return Tools()

        ue.AssetToolsHelpers = Helpers
        ue.Material = type("Material", (), {})
        ue.MaterialFactoryNew = lambda: None
        ue.MaterialEditingLibrary = Library
        ue.MaterialExpressionNoise = type("Noise", (), {})
        ue.MaterialExpressionConstant3Vector = type("Constant3", (), {})
        ue.MaterialExpressionConstant = type("Constant", (), {})
        ue.MaterialExpressionLinearInterpolate = type("Lerp", (), {})
        ue.MaterialExpressionTime = type("Time", (), {})
        ue.MaterialExpressionSine = type("Sine", (), {})
        ue.MaterialProperty = type(
            "MaterialProperty",
            (),
            {"MP_BASE_COLOR": "MP_BASE_COLOR", "MP_ROUGHNESS": "MP_ROUGHNESS", "MP_OPACITY": "MP_OPACITY"},
        )
        ue.BlendMode = type("BlendMode", (), {"BLEND_TRANSLUCENT": "BLEND_TRANSLUCENT"})
        ue.MaterialShadingModel = type("Shading", (), {"MSM_SINGLELAYERWATER": "MSM_SINGLELAYERWATER"})
        saved = []
        ue.EditorAssetLibrary.save_asset = lambda path, only_if_is_dirty=False: saved.append(path)

        grass = level_build._author_material(
            ue, "/Game/Materials/M_Elyon_Grass", garden_logic.AUTHORED_MATERIALS["/Game/Materials/M_Elyon_Grass"]
        )
        noise = next(expr for expr in created if getattr(expr, "cls", None) is ue.MaterialExpressionNoise)
        self.assertEqual(noise.props["scale"], 0.003)
        pins = [item[2] for item in created if isinstance(item, tuple) and item[0] == "link"]
        self.assertIn("A", pins)
        self.assertIn("B", pins)
        self.assertIn("Alpha", pins)
        self.assertIn("MP_BASE_COLOR", [item[1] for item in created if isinstance(item, tuple) and item[0] == "prop"])
        self.assertIsNotNone(grass)

        created.clear()
        water = level_build._author_material(
            ue, "/Game/Materials/M_Elyon_Water", garden_logic.AUTHORED_MATERIALS["/Game/Materials/M_Elyon_Water"]
        )
        kinds = {expr.cls for expr in created if hasattr(expr, "cls")}
        self.assertIn(ue.MaterialExpressionTime, kinds)
        self.assertIn(ue.MaterialExpressionSine, kinds)
        self.assertEqual(water.props["shading_model"], "MSM_SINGLELAYERWATER")
        self.assertEqual(water.props["blend_mode"], "BLEND_TRANSLUCENT")
        self.assertNotIn("MP_OPACITY", [item[1] for item in created if isinstance(item, tuple) and item[0] == "prop"])
        self.assertIn("/Game/Materials/M_Elyon_Water", saved)

    def test_material_links_fall_back_to_a_flat_color(self):
        ue = FakeUnreal()

        class Expr:
            def __init__(self):
                self.props = {}

            def set_editor_property(self, name, value):
                self.props[name] = value

        class Material:
            def set_editor_property(self, name, value):
                return None

        class Library:
            @staticmethod
            def create_material_expression(material, cls, x, y):
                return Expr()

            @staticmethod
            def connect_material_expressions(source, source_pin, dest, dest_pin):
                raise RuntimeError("bad pin")

            @staticmethod
            def connect_material_property(expr, output, prop):
                return None

            @staticmethod
            def recompile_material(material):
                return None

        class Tools:
            def create_asset(self, name, path, cls, factory):
                return Material()

        class Helpers:
            @staticmethod
            def get_asset_tools():
                return Tools()

        ue.AssetToolsHelpers = Helpers
        ue.Material = type("Material", (), {})
        ue.MaterialFactoryNew = lambda: None
        ue.MaterialEditingLibrary = Library
        ue.MaterialExpressionNoise = type("Noise", (), {})
        ue.MaterialExpressionConstant3Vector = type("Constant3", (), {})
        ue.MaterialExpressionConstant = type("Constant", (), {})
        ue.MaterialExpressionLinearInterpolate = type("Lerp", (), {})
        ue.MaterialProperty = type("MaterialProperty", (), {"MP_BASE_COLOR": "base", "MP_ROUGHNESS": "rough"})
        ue.EditorAssetLibrary.save_asset = lambda path, only_if_is_dirty=False: None
        level_build._author_material(
            ue, "/Game/Materials/M_Elyon_Grass", garden_logic.AUTHORED_MATERIALS["/Game/Materials/M_Elyon_Grass"]
        )
        self.assertTrue(any("flat color" in message for message in ue.warnings))


if __name__ == "__main__":
    unittest.main()
