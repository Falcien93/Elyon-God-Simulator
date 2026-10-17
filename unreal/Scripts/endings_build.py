"""Build one Level Sequence scaffold for each garden ending.

Run inside Unreal Editor 5.8:

    UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/endings_build.py

Running it again replaces those sequences. Tracks are not stacked.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endings_logic import load_catalog, sequence_plans

SEQUENCER_TYPES = (
    "LevelSequence",
    "LevelSequenceFactoryNew",
    "CineCameraActor",
    "MovieSceneSequenceExtensions",
    "MovieSceneBindingExtensions",
    "MovieSceneTrackExtensions",
    "MovieSceneSectionExtensions",
    "MovieSceneCameraCutSectionExtensions",
    "MovieSceneCameraCutTrack",
    "MovieSceneFadeTrack",
    "MovieScene3DTransformTrack",
    "MovieSceneObjectBindingSpace",
    "FrameRate",
    "FrameNumber",
    "MovieSceneMarkedFrame",
    "AssetToolsHelpers",
    "EditorAssetLibrary",
)

# MovieScene3DTransformSection float channels: translation, rotation (roll, pitch, yaw), scale.
CHANNEL_TX, CHANNEL_TY, CHANNEL_TZ = 0, 1, 2
CHANNEL_ROLL, CHANNEL_PITCH, CHANNEL_YAW = 3, 4, 5
CHANNEL_SX, CHANNEL_SY, CHANNEL_SZ = 6, 7, 8


def sequencer_ready(ue):
    return all(hasattr(ue, name) for name in SEQUENCER_TYPES)


def build_endings(ue=None, data_dir=None):
    ue = _ue(ue)
    catalog = load_catalog(data_dir)
    plans = sequence_plans(catalog)
    library = ue.EditorAssetLibrary
    library.make_directory(plans[0]["folder"])
    built = []
    for plan in plans:
        sequence = _create_sequence(ue, plan)
        _author_sequence(ue, sequence, plan)
        library.save_asset(plan["asset"])
        built.append(plan)
    return built


def _ue(ue):
    if ue is not None:
        return ue
    import unreal

    return unreal


def _create_sequence(ue, plan):
    library = ue.EditorAssetLibrary
    if library.does_asset_exist(plan["asset"]):
        if not library.delete_asset(plan["asset"]):
            raise RuntimeError(f"could not replace {plan['asset']}")
    tools = ue.AssetToolsHelpers.get_asset_tools()
    sequence = tools.create_asset(
        plan["name"],
        plan["folder"],
        ue.LevelSequence,
        ue.LevelSequenceFactoryNew(),
    )
    if sequence is None:
        raise RuntimeError(f"could not create {plan['asset']}")
    return sequence


def _author_sequence(ue, sequence, plan):
    seq = ue.MovieSceneSequenceExtensions
    bindings = ue.MovieSceneBindingExtensions
    tracks = ue.MovieSceneTrackExtensions
    sections = ue.MovieSceneSectionExtensions
    cuts = ue.MovieSceneCameraCutSectionExtensions

    seq.set_display_rate(sequence, ue.FrameRate(numerator=plan["fps"], denominator=1))
    seq.set_playback_start(sequence, 0)
    seq.set_playback_end(sequence, plan["end_frame"])

    binding = seq.add_spawnable_from_class(sequence, ue.CineCameraActor)
    if hasattr(bindings, "set_name"):
        bindings.set_name(binding, plan["camera_name"])
    bindings.set_display_name(binding, plan["camera_name"])

    transform = bindings.add_track(binding, ue.MovieScene3DTransformTrack)
    transform_section = tracks.add_section(transform)
    sections.set_range(transform_section, 0, plan["end_frame"])
    _key_transform(ue, sections.get_channels(transform_section), plan["camera_keys"])

    cut = seq.add_track(sequence, ue.MovieSceneCameraCutTrack)
    cut_section = tracks.add_section(cut)
    sections.set_range(cut_section, 0, plan["end_frame"])
    binding_id = seq.make_binding_id(sequence, binding, ue.MovieSceneObjectBindingSpace.LOCAL)
    cuts.set_camera_binding_id(cut_section, binding_id)

    fade = seq.add_track(sequence, ue.MovieSceneFadeTrack)
    fade_section = tracks.add_section(fade)
    sections.set_range(fade_section, 0, plan["end_frame"])
    fade_channels = sections.get_channels(fade_section)
    if not fade_channels:
        raise RuntimeError("fade section has no float channel")
    for key in plan["fades"]:
        fade_channels[0].add_key(ue.FrameNumber(value=key["frame"]), float(key["amount"]))

    movie_scene = sequence.get_movie_scene()
    for marker in plan["markers"]:
        marked = ue.MovieSceneMarkedFrame()
        marked.frame_number = ue.FrameNumber(value=marker["frame"])
        marked.label = marker["label"]
        movie_scene.add_marked_frame(marked)

    library = ue.EditorAssetLibrary
    library.set_metadata_tag(sequence, "elyon.ending.id", plan["id"])
    library.set_metadata_tag(sequence, "elyon.ending.title", plan["title"])
    library.set_metadata_tag(sequence, "elyon.ending.hold_frame", str(plan["hold_frame"]))


def _key_transform(ue, channels, camera_keys):
    if len(channels) < 9:
        raise RuntimeError("transform section needs translation, rotation, and scale channels")
    for key in camera_keys:
        frame = ue.FrameNumber(value=key["frame"])
        x, y, z = key["location"]
        pitch, yaw, roll = key["rotation"]
        channels[CHANNEL_TX].add_key(frame, x)
        channels[CHANNEL_TY].add_key(frame, y)
        channels[CHANNEL_TZ].add_key(frame, z)
        channels[CHANNEL_ROLL].add_key(frame, roll)
        channels[CHANNEL_PITCH].add_key(frame, pitch)
        channels[CHANNEL_YAW].add_key(frame, yaw)
        channels[CHANNEL_SX].add_key(frame, 1.0)
        channels[CHANNEL_SY].add_key(frame, 1.0)
        channels[CHANNEL_SZ].add_key(frame, 1.0)


if __name__ == "__main__":
    build_endings()
