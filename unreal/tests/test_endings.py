"""Ending state and Level Sequence scaffolds, using the garden editor mock."""

import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
DATA = Path(__file__).resolve().parents[1] / "Data"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import endings_build
import endings_logic
import run_all
from test_garden import AssetLib, FakeUnreal


class FrameRate:
    def __init__(self, numerator, denominator=1):
        self.numerator = int(numerator)
        self.denominator = int(denominator)


class FrameNumber:
    def __init__(self, value):
        self.value = int(value)


class MovieSceneMarkedFrame:
    def __init__(self):
        self.frame_number = None
        self.label = ""


class FloatChannel:
    def __init__(self, name):
        self.name = name
        self.keys = []

    def add_key(self, frame, value, sub_frame=0.0, time_unit=None, interpolation=None):
        frame_value = frame.value if hasattr(frame, "value") else int(frame)
        self.keys.append((frame_value, float(value)))


class Section:
    def __init__(self, kind):
        self.kind = kind
        self.start = None
        self.end = None
        self.camera_binding_id = None
        if kind == "transform":
            names = ("tx", "ty", "tz", "roll", "pitch", "yaw", "sx", "sy", "sz")
            self.channels = [FloatChannel(name) for name in names]
        elif kind == "fade":
            self.channels = [FloatChannel("fade")]
        else:
            self.channels = []


class Track:
    def __init__(self, track_class):
        self.track_class = track_class
        self.sections = []

    def add_section(self):
        name = self.track_class.__name__
        if "Fade" in name:
            kind = "fade"
        elif "CameraCut" in name:
            kind = "cut"
        else:
            kind = "transform"
        section = Section(kind)
        self.sections.append(section)
        return section


class Binding:
    def __init__(self, actor_class, guid):
        self.actor_class = actor_class
        self.guid = guid
        self.name = ""
        self.display_name = ""
        self.tracks = []


class MovieScene:
    def __init__(self):
        self.marked_frames = []

    def add_marked_frame(self, marked_frame):
        self.marked_frames.append(marked_frame)
        return len(self.marked_frames) - 1


class LevelSequenceAsset:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.display_rate = None
        self.playback_start = None
        self.playback_end = None
        self.tracks = []
        self.spawnables = []
        self.movie_scene = MovieScene()
        self.metadata = {}
        self._next_guid = 1

    def get_movie_scene(self):
        return self.movie_scene


class LevelSequence:
    pass


class LevelSequenceFactoryNew:
    pass


class CineCameraActor:
    pass


class MovieSceneCameraCutTrack:
    pass


class MovieSceneFadeTrack:
    pass


class MovieScene3DTransformTrack:
    pass


class MovieSceneObjectBindingSpace:
    LOCAL = 0
    ROOT = 1


class MovieSceneSequenceExtensions:
    @staticmethod
    def set_display_rate(sequence, rate):
        sequence.display_rate = rate

    @staticmethod
    def set_playback_start(sequence, start):
        sequence.playback_start = int(start)

    @staticmethod
    def set_playback_end(sequence, end):
        sequence.playback_end = int(end)

    @staticmethod
    def add_track(sequence, track_class):
        track = Track(track_class)
        sequence.tracks.append(track)
        return track

    @staticmethod
    def add_spawnable_from_class(sequence, actor_class):
        guid = f"{sequence.path}:{sequence._next_guid}"
        sequence._next_guid += 1
        binding = Binding(actor_class, guid)
        sequence.spawnables.append(binding)
        return binding

    @staticmethod
    def make_binding_id(sequence, binding, space):
        return {"sequence": sequence.path, "guid": binding.guid, "space": space}


class MovieSceneBindingExtensions:
    @staticmethod
    def set_name(binding, name):
        binding.name = name

    @staticmethod
    def set_display_name(binding, name):
        binding.display_name = name

    @staticmethod
    def add_track(binding, track_class):
        track = Track(track_class)
        binding.tracks.append(track)
        return track


class MovieSceneTrackExtensions:
    @staticmethod
    def add_section(track):
        return track.add_section()


class MovieSceneSectionExtensions:
    @staticmethod
    def set_range(section, start, end):
        section.start = int(start)
        section.end = int(end)

    @staticmethod
    def get_channels(section):
        return section.channels


class MovieSceneCameraCutSectionExtensions:
    @staticmethod
    def set_camera_binding_id(section, binding_id):
        section.camera_binding_id = binding_id


class SequencerAssetLib(AssetLib):
    MAP = "/Game/Maps/Day1_Garden"

    def __init__(self):
        super().__init__()
        self.created = {}
        self.directories = []
        self.saved = []
        self.deleted = []

    def does_asset_exist(self, path):
        if path in self.created:
            return True
        return path == self.MAP and bool(self.exists)

    def load_asset(self, path):
        if path in self.created:
            return self.created[path]
        return path

    def make_directory(self, path):
        self.directories.append(path)
        return True

    def delete_asset(self, path):
        self.deleted.append(path)
        return self.created.pop(path, None) is not None

    def save_asset(self, path, only_if_is_dirty=True):
        self.saved.append(path)
        return True

    def set_metadata_tag(self, asset, tag, value):
        asset.metadata[tag] = value

    def get_metadata_tag(self, asset, tag):
        return asset.metadata.get(tag, "")


class SequencerAssetTools:
    def __init__(self, library, ue):
        self.library = library
        self.ue = ue

    def create_asset(self, asset_name, package_path, asset_class, factory):
        if asset_class is not self.ue.LevelSequence:
            raise TypeError("ending scaffolds are LevelSequence assets")
        if not isinstance(factory, self.ue.LevelSequenceFactoryNew):
            raise TypeError("LevelSequenceFactoryNew is required")
        path = f"{package_path}/{asset_name}"
        if path in self.library.created:
            raise RuntimeError(path)
        asset = LevelSequenceAsset(asset_name, path)
        self.library.created[path] = asset
        return asset


class SequencerAssetToolsHelpers:
    def __init__(self, library, ue):
        self._tools = SequencerAssetTools(library, ue)

    def get_asset_tools(self):
        return self._tools


class SequencerUnreal(FakeUnreal):
    """Garden mock plus the sequencer surface endings_build calls."""

    def __init__(self):
        super().__init__()
        library = SequencerAssetLib()
        self.EditorAssetLibrary = library
        self.EditorLevelLibrary.assets = library
        self.LevelSequence = LevelSequence
        self.LevelSequenceFactoryNew = LevelSequenceFactoryNew
        self.CineCameraActor = CineCameraActor
        self.MovieSceneCameraCutTrack = MovieSceneCameraCutTrack
        self.MovieSceneFadeTrack = MovieSceneFadeTrack
        self.MovieScene3DTransformTrack = MovieScene3DTransformTrack
        self.MovieSceneObjectBindingSpace = MovieSceneObjectBindingSpace
        self.FrameRate = FrameRate
        self.FrameNumber = FrameNumber
        self.MovieSceneMarkedFrame = MovieSceneMarkedFrame
        self.MovieSceneSequenceExtensions = MovieSceneSequenceExtensions
        self.MovieSceneBindingExtensions = MovieSceneBindingExtensions
        self.MovieSceneTrackExtensions = MovieSceneTrackExtensions
        self.MovieSceneSectionExtensions = MovieSceneSectionExtensions
        self.MovieSceneCameraCutSectionExtensions = MovieSceneCameraCutSectionExtensions
        self.AssetToolsHelpers = SequencerAssetToolsHelpers(library, self)


def ready(silence=False, now=100):
    state = endings_logic.new_state(now=now)
    state["flags"]["eve_made"] = True
    state["flags"]["beasts_named"] = True
    if silence:
        result = endings_logic.choose_silence(state)
    else:
        result = endings_logic.set_commandment(state, "Do not eat of the tree of knowledge.")
    if not result["ok"]:
        raise AssertionError(result)
    if not state["flags"]["serpent_present"]:
        raise AssertionError("serpent did not arrive")
    return state


class EndingStateTests(unittest.TestCase):
    def test_catalog_matches_the_page_and_the_eve_lines(self):
        catalog = endings_logic.load_catalog()
        self.assertEqual(
            [row["id"] for row in catalog["endings"]["endings"]],
            ["harmony", "exile", "wonder", "order"],
        )
        dialogue = json.loads((DATA / "dialogue.json").read_text(encoding="utf-8"))
        eve = next(node for node in dialogue["nodes"] if node["id"] == "eve_choice")
        by_choice = {cond["choice"]: cond for row in catalog["endings"]["endings"] for cond in row["conditions"]}
        for choice in eve["choices"]:
            self.assertEqual(by_choice[choice["label"]]["effects"], choice["fx"])
        serpent = [cond for row in catalog["endings"]["endings"] for cond in row["conditions"] if cond["speaker"] == "serpent"]
        self.assertEqual([cond["node"] for cond in serpent], ["serpent_meet", "serpent_why"])
        for cond in serpent:
            self.assertEqual(
                cond["effects"],
                ["ending:order", "flag:serpent_gone", "flag:tree_guarded", "order:16", "wonder:-14"],
            )
        speakers = {node["speaker"] for node in dialogue["nodes"]}
        self.assertEqual(speakers, {"adam", "eve"})

    def test_word_and_silence_are_mutually_exclusive_until_the_serpent_coils(self):
        state = endings_logic.new_state()
        self.assertEqual(endings_logic.set_commandment(state, "Be still.")["reason"], "locked")
        self.assertEqual(endings_logic.choose_silence(state)["reason"], "locked")
        state["flags"]["eve_made"] = True
        self.assertEqual(endings_logic.set_commandment(state, "   <>  ")["reason"], "empty")
        self.assertFalse(state["flags"]["commandment_spoken"])
        spoken = endings_logic.set_commandment(state, "  <be kind>  ")
        self.assertTrue(spoken["ok"])
        self.assertEqual(state["commandment"], "be kind")
        self.assertFalse(state["flags"]["serpent_present"])
        quiet = endings_logic.choose_silence(state)
        self.assertTrue(quiet["ok"])
        self.assertTrue(state["flags"]["silence"])
        self.assertFalse(state["flags"]["commandment_spoken"])
        self.assertIsNone(state["commandment"])
        self.assertEqual(state["stats"]["wonder"], 50)
        self.assertEqual(endings_logic.choose_silence(state)["reason"], "already")
        again = endings_logic.set_commandment(state, "Do not eat of the tree of knowledge.")
        self.assertTrue(again["ok"])
        self.assertFalse(state["flags"]["silence"])
        self.assertEqual(state["stats"]["wonder"], 50)
        endings_logic.name_beasts(state)
        self.assertTrue(state["flags"]["serpent_present"])
        self.assertEqual(endings_logic.choose_silence(state)["reason"], "already")
        self.assertIn("word", state["codex"])

    def test_four_endings_follow_the_choice_and_the_hands_rule(self):
        harmony = ready(now=80)
        chosen = endings_logic.choose(harmony, "eve_choice", "Leave the fruit. I am with you either way, and I ask you to trust me.")
        self.assertTrue(chosen["ok"])
        self.assertEqual(chosen["goto"], "eve_harmony")
        self.assertEqual(harmony["ending"]["id"], "harmony")
        self.assertEqual(harmony["ending"]["at"], 80)
        self.assertEqual(harmony["ending"]["because"], "direct")
        self.assertEqual(harmony["ending"]["sequence"], "/Game/Cinematics/Endings/LS_Ending_harmony")
        self.assertEqual(harmony["stats"]["order"], 62)
        self.assertEqual(harmony["stats"]["wonder"], 38)
        self.assertEqual(harmony["relations"]["eve"]["trust"], 30)
        self.assertEqual(harmony["relations"]["eve"]["wonder"], 44)
        self.assertFalse(harmony["flags"]["clothed"])
        self.assertFalse(harmony["flags"]["tree_guarded"])
        self.assertTrue(harmony["flags"]["serpent_gone"])
        self.assertFalse(harmony["flags"]["ending_seen"])
        self.assertEqual(harmony["homes"], endings_logic.GARDEN_HOMES)
        self.assertTrue(harmony["can_walk"])
        self.assertTrue(endings_logic.ending_overlay_due(harmony))
        self.assertEqual(harmony["log"][-1], "The garden kept.")
        self.assertIn("choice", harmony["codex"])

        exile = ready()
        endings_logic.choose(exile, "eve_choice", "I will not choose for you.")
        self.assertEqual(exile["ending"]["id"], "exile")
        self.assertEqual(exile["ending"]["because"], "no-silence")
        self.assertTrue(exile["flags"]["clothed"])
        self.assertFalse(exile["flags"]["tree_guarded"])
        self.assertEqual(exile["homes"], endings_logic.EXILE_HOMES)
        self.assertGreater(exile["homes"]["adam"][0], endings_logic.RIVER_EAST)
        self.assertGreater(exile["homes"]["eve"][0], endings_logic.RIVER_EAST)
        self.assertLess(endings_logic.GARDEN_HOMES["adam"][0], endings_logic.RIVER_EAST)
        self.assertEqual(exile["relations"]["eve"]["will"], 46)
        self.assertEqual(exile["stats"]["wonder"], 42)
        self.assertTrue(exile["can_walk"])

        wonder = ready(silence=True, now=12)
        self.assertEqual(endings_logic.preview_choice(wonder, "eve_choice", "I will not choose for you."), "wonder")
        self.assertIsNone(wonder["ending"])
        endings_logic.choose(wonder, "eve_choice", "I will not choose for you.")
        self.assertEqual(wonder["ending"]["id"], "wonder")
        self.assertEqual(wonder["ending"]["because"], "silence")
        self.assertEqual(wonder["ending"]["at"], 12)
        self.assertFalse(wonder["flags"]["clothed"])
        self.assertEqual(wonder["homes"], endings_logic.GARDEN_HOMES)
        self.assertEqual(wonder["stats"]["wonder"], 50)
        self.assertEqual(wonder["relations"]["eve"]["will"], 46)
        self.assertEqual(wonder["ending"]["consequences"], ["dismiss_serpent", "remain_in_garden"])

        order = ready()
        endings_logic.choose(order, "eve_choice", "Then I will put the fruit out of reach.")
        self.assertEqual(order["ending"]["id"], "order")
        self.assertTrue(order["flags"]["tree_guarded"])
        self.assertTrue(order["flags"]["serpent_gone"])
        self.assertFalse(order["flags"]["clothed"])
        self.assertEqual(order["homes"], endings_logic.GARDEN_HOMES)
        self.assertEqual(order["stats"]["order"], 66)
        self.assertEqual(order["stats"]["wonder"], 26)

        from_meet = ready(now=3)
        endings_logic.choose(from_meet, "serpent_meet", "Be gone from this garden.")
        self.assertEqual(from_meet["ending"]["id"], "order")
        self.assertEqual(from_meet["ending"]["trigger"]["node"], "serpent_meet")
        self.assertEqual(from_meet["ending"]["trigger"]["goto"], "serpent_gone")
        self.assertEqual(from_meet["stats"]["order"], 64)
        self.assertEqual(from_meet["stats"]["wonder"], 28)
        self.assertTrue(from_meet["flags"]["tree_guarded"])

        from_why = ready()
        endings_logic.choose(from_why, "serpent_why", "Be gone.")
        self.assertEqual(from_why["ending"]["id"], "order")
        self.assertEqual(from_why["ending"]["trigger"]["choice"], "Be gone.")

    def test_preview_does_not_mutate_and_silence_wins_a_forced_pair(self):
        state = ready()
        self.assertEqual(endings_logic.preview_choice(state, "eve_choice", "I will not choose for you."), "exile")
        self.assertIsNone(state["ending"])
        self.assertEqual(state["relations"]["eve"]["will"], 34)
        state["flags"]["silence"] = True
        self.assertEqual(endings_logic.preview_choice(state, "eve_choice", "I will not choose for you."), "wonder")

    def test_first_ending_sticks_and_the_epilogue_opens(self):
        state = ready()
        endings_logic.choose(state, "eve_choice", "Leave the fruit. I am with you either way, and I ask you to trust me.")
        held = endings_logic.choose(state, "eve_choice", "Then I will put the fruit out of reach.")
        self.assertEqual(held["reason"], "already")
        self.assertTrue(held["held"])
        self.assertEqual(state["ending"]["id"], "harmony")
        self.assertEqual(state["stats"]["order"], 62)
        self.assertFalse(state["flags"]["tree_guarded"])
        bare = endings_logic.apply_fx(state, "ending:order")
        self.assertEqual(bare["reason"], "already")
        self.assertEqual(state["ending"]["id"], "harmony")
        self.assertFalse(endings_logic.can_address(state, "serpent"))
        self.assertTrue(endings_logic.can_address(state, "eve"))
        self.assertIsNone(endings_logic.epilogue_entry(state, "serpent"))
        self.assertEqual(endings_logic.epilogue_entry(state, "adam"), "adam_epilogue_harmony")
        self.assertEqual(endings_logic.epilogue_entry(state, "eve"), "eve_epilogue_harmony")
        self.assertTrue(endings_logic.mark_ending_seen(state)["ok"])
        self.assertFalse(endings_logic.ending_overlay_due(state))
        self.assertTrue(state["can_walk"])
        self.assertEqual(endings_logic.set_commandment(state, "A later word.")["reason"], "already")

    def test_choice_is_locked_until_the_serpent_is_present(self):
        state = endings_logic.new_state()
        state["flags"]["eve_made"] = True
        locked = endings_logic.choose(state, "eve_choice", "Leave the fruit. I am with you either way, and I ask you to trust me.")
        self.assertEqual(locked["reason"], "locked")
        self.assertIsNone(state["ending"])
        unknown = endings_logic.choose(ready(), "eve_choice", "Not a real choice.")
        self.assertEqual(unknown["reason"], "unknown")
        direct = endings_logic.new_state(now=9)
        direct["flags"]["silence"] = True
        self.assertEqual(endings_logic.apply_fx(direct, "ending:hands")["ending"], "wonder")
        self.assertEqual(direct["ending"]["at"], 9)
        self.assertEqual(direct["relations"]["eve"]["will"], 34)
        other = endings_logic.new_state()
        self.assertEqual(endings_logic.apply_fx(other, "ending:wonder")["ending"], "wonder")
        self.assertEqual(endings_logic.apply_fx(endings_logic.new_state(), "ending:bogus")["reason"], "unknown")
        clamped = endings_logic.new_state()
        endings_logic.apply_fx(clamped, "wonder:-100")
        endings_logic.apply_fx(clamped, "order:80")
        endings_logic.apply_fx(clamped, "order:80")
        self.assertEqual(clamped["stats"]["wonder"], 0)
        self.assertEqual(clamped["stats"]["order"], 100)

    def test_sequence_plans_keep_each_ending_distinct(self):
        catalog = endings_logic.load_catalog()
        first = endings_logic.sequence_plans(catalog)
        second = endings_logic.sequence_plans(catalog)
        self.assertEqual(first, second)
        self.assertEqual([plan["id"] for plan in first], ["harmony", "exile", "wonder", "order"])
        by_id = {row["id"]: row for row in catalog["endings"]["endings"]}
        for plan in first:
            self.assertEqual(plan["paragraphs"], by_id[plan["id"]]["paragraphs"])
            self.assertEqual(plan["asset"], f"/Game/Cinematics/Endings/LS_Ending_{plan['id']}")
            self.assertEqual(plan["fps"], 24)
            self.assertEqual(plan["fade_in_frame"], 36)
            self.assertEqual(plan["end_frame"], 36 + 144 * len(plan["paragraphs"]) + 48)
            labels = [marker["label"] for marker in plan["markers"]]
            self.assertEqual(labels[0], f"Ending.Begin.{plan['id']}")
            self.assertEqual(labels[-1], "Ending.Hold")
            self.assertEqual(
                [marker["text"] for marker in plan["markers"] if marker["label"].startswith("Ending.Paragraph.")],
                plan["paragraphs"],
            )
            frames = [marker["frame"] for marker in plan["markers"]]
            self.assertEqual(frames, sorted(frames))
            self.assertTrue(all(0 <= frame < plan["end_frame"] for frame in frames))
            self.assertEqual(plan["fades"], [{"frame": 0, "amount": 1.0}, {"frame": 36, "amount": 0.0}])
            self.assertLess(plan["camera_keys"][-1]["location"][0], 8000)
        harmony, exile, wonder, order = first
        self.assertEqual(harmony["end_frame"], 372)
        self.assertEqual(harmony["hold_frame"], 324)
        self.assertLess(harmony["camera_keys"][-1]["location"][0], 1000)
        self.assertGreater(exile["camera_keys"][-1]["location"][0], endings_logic.RIVER_EAST)
        self.assertGreater(wonder["camera_keys"][-1]["location"][2], 1000)
        self.assertLess(wonder["camera_keys"][-1]["location"][0], endings_logic.RIVER_EAST)
        self.assertLess(order["camera_keys"][-1]["location"][0], endings_logic.RIVER_EAST)
        adam = endings_logic.GARDEN_HOMES["adam"]
        first_shot = order["camera_keys"][0]["location"]
        last_shot = order["camera_keys"][-1]["location"]
        self.assertLess(_flat(last_shot, adam), _flat(first_shot, adam))
        ends = {plan["id"]: plan["camera_keys"][-1]["location"] for plan in first}
        self.assertEqual(len(set(ends.values())), 4)
        broken = json.loads(json.dumps(catalog["sequences"]))
        del broken["endings"]["wonder"]
        self.assertTrue(endings_logic.validate_catalog(catalog["endings"], broken))

    def test_mark_seen_before_an_ending_does_nothing(self):
        state = endings_logic.new_state()
        self.assertEqual(endings_logic.mark_ending_seen(state)["reason"], "empty")
        self.assertIsNone(endings_logic.epilogue_entry(state, "eve"))


def _flat(location, home):
    return (location[0] - home[0]) ** 2 + (location[1] - home[1]) ** 2


class EndingSequenceBuildTests(unittest.TestCase):
    def test_build_is_idempotent_and_run_all_uses_it_when_sequencer_scripting_is_loaded(self):
        self.assertFalse(endings_build.sequencer_ready(FakeUnreal()))
        ue = SequencerUnreal()
        built = endings_build.build_endings(ue=ue)
        self.assertEqual([plan["id"] for plan in built], ["harmony", "exile", "wonder", "order"])
        self.assertEqual(ue.EditorAssetLibrary.directories, ["/Game/Cinematics/Endings"])
        self.assertEqual(ue.EditorAssetLibrary.deleted, [])
        self.assertEqual(len(ue.EditorAssetLibrary.created), 4)
        harmony = ue.EditorAssetLibrary.created["/Game/Cinematics/Endings/LS_Ending_harmony"]
        self.assertEqual(harmony.display_rate.numerator, 24)
        self.assertEqual(harmony.display_rate.denominator, 1)
        self.assertEqual(harmony.playback_start, 0)
        self.assertEqual(harmony.playback_end, 372)
        self.assertEqual(len(harmony.spawnables), 1)
        camera = harmony.spawnables[0]
        self.assertEqual(camera.name, "EndingCamera")
        self.assertEqual(camera.display_name, "EndingCamera")
        self.assertIs(camera.actor_class, CineCameraActor)
        transform = camera.tracks[0].sections[0]
        self.assertEqual(transform.kind, "transform")
        self.assertEqual(transform.end, 372)
        self.assertEqual(transform.channels[4].keys[0], (36, -6.0))
        self.assertEqual(transform.channels[6].keys[0][1], 1.0)
        self.assertEqual(len(harmony.tracks), 2)
        cut = harmony.tracks[0].sections[0]
        self.assertEqual(cut.kind, "cut")
        self.assertEqual(cut.camera_binding_id["guid"], camera.guid)
        self.assertEqual(cut.camera_binding_id["space"], 0)
        fade = harmony.tracks[1].sections[0]
        self.assertEqual(fade.channels[0].keys, [(0, 1.0), (36, 0.0)])
        labels = [frame.label for frame in harmony.movie_scene.marked_frames]
        self.assertEqual(labels, ["Ending.Begin.harmony", "Ending.Paragraph.0", "Ending.Paragraph.1", "Ending.Hold"])
        self.assertEqual(harmony.metadata["elyon.ending.id"], "harmony")
        self.assertEqual(harmony.metadata["elyon.ending.title"], "The garden kept")
        self.assertEqual(harmony.metadata["elyon.ending.hold_frame"], "324")

        endings_build.build_endings(ue=ue)
        self.assertEqual(len(ue.EditorAssetLibrary.created), 4)
        self.assertEqual(len(ue.EditorAssetLibrary.deleted), 4)
        rebuilt = ue.EditorAssetLibrary.created["/Game/Cinematics/Endings/LS_Ending_harmony"]
        self.assertEqual(len(rebuilt.tracks), 2)
        self.assertEqual(len(rebuilt.spawnables), 1)
        self.assertEqual(len(rebuilt.movie_scene.marked_frames), 4)

        fresh = SequencerUnreal()
        run_all.main(fresh)
        self.assertTrue(fresh.EditorPythonScripting.alive)
        self.assertEqual(fresh.EditorLevelLibrary.created, "/Game/Maps/Day1_Garden")
        self.assertEqual(len(fresh.EditorAssetLibrary.created), 4)
        sun = next(actor for actor in fresh.sub.actors if actor.get_actor_label() == "Elyon.Sun")
        sun_comp = sun.get_component_by_class(fresh.DirectionalLightComponent)
        self.assertEqual(sun_comp.props["intensity"], 10.0)
        self.assertIn("/Game/Cinematics/Endings/LS_Ending_exile", fresh.EditorAssetLibrary.created)


if __name__ == "__main__":
    unittest.main()
