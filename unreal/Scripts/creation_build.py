"""Spawn the day 2 through day 7 maps in the Unreal editor. Idempotent per map."""

from creation_logic import HoursMissing, done_before, load_creation, plan_day
from garden_logic import planned_labels, stale_labels
from level_build import (
    CLASS_NAMES,
    _byte_color,
    _by_label,
    _destroy_stale,
    _linear_color,
    _place,
    _rot,
    _subsystem,
    _ue,
    _vec,
)


def _ensure_map(ue, map_path):
    if ue.EditorAssetLibrary.does_asset_exist(map_path):
        ue.EditorLevelLibrary.load_level(map_path)
    else:
        ue.EditorLevelLibrary.new_level(map_path)


def _apply_sky(ue, light):
    actors = _by_label(ue)
    sky = actors.get("Elyon.SkyLight")
    if sky:
        comp = sky.get_component_by_class(ue.SkyLightComponent)
        comp.set_editor_property("intensity", light["skylight_intensity"])
        comp.set_editor_property("light_color", _byte_color(ue, light["sky_color"]))
        if hasattr(comp, "recapture_sky"):
            comp.recapture_sky()
    fog = actors.get("Elyon.Fog")
    if fog:
        comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        comp.set_editor_property("fog_density", light["fog_density"])
        comp.set_editor_property("fog_inscattering_luminance", _linear_color(ue, light["fog_color"]))


def _paint_directional(ue, actor, light, prefix):
    if actor is None:
        return
    actor.set_actor_rotation(_rot(ue, light[f"{prefix}_pitch"], light[f"{prefix}_yaw"], 0.0), True)
    comp = actor.get_component_by_class(ue.DirectionalLightComponent)
    comp.set_editor_property("intensity", light[f"{prefix}_intensity"])
    comp.set_editor_property("light_color", _byte_color(ue, light[f"{prefix}_color"]))


def _move_disc(ue, actor, xyz):
    if actor is None or not xyz:
        return
    actor.set_actor_location(_vec(ue, xyz[0], xyz[1], xyz[2]), False, True)


def _apply_hours(ue, light):
    """Sun and moon colors are unreal.Color. Fog inscattering is unreal.LinearColor."""
    _apply_sky(ue, light)
    actors = _by_label(ue)
    _paint_directional(ue, actors.get("Elyon.Sun"), light, "sun")
    _paint_directional(ue, actors.get("Elyon.MoonLight"), light, "moon")
    _move_disc(ue, actors.get("Elyon.SunDisc"), light.get("sun_disc"))
    _move_disc(ue, actors.get("Elyon.Moon"), light.get("moon_disc"))
    star_scale = light.get("star_scale")
    if star_scale is not None:
        for actor in actors.values():
            if actor.get_actor_label().startswith("Elyon.Star."):
                actor.set_actor_scale3d(_vec(ue, star_scale, star_scale, star_scale))
    hours = actors.get("Elyon.Hours")
    if hours:
        hours.set_editor_property("tags", [light["name"]])


def build_day(day_id, done=None, ue=None, phase=None):
    ue = _ue(ue)
    if done is None:
        done = done_before(day_id)
    plan = plan_day(day_id, done, phase=phase)
    _ensure_map(ue, plan["map"])
    existing = list(_by_label(ue).keys())
    _destroy_stale(ue, stale_labels(existing, planned_labels(plan)))
    sub = _subsystem(ue)
    actors = _by_label(ue)
    for spec in plan["actors"]:
        actor = actors.get(spec["label"])
        if actor is None:
            cls = getattr(ue, CLASS_NAMES[spec["kind"]])
            actor = sub.spawn_actor_from_class(
                cls,
                _vec(ue, spec["x"], spec["y"], spec["z"]),
                _rot(ue, spec.get("pitch", 0.0), spec.get("yaw", 0.0), 0.0),
            )
            actors[spec["label"]] = actor
        _place(actor, ue, spec)
    if plan["phase"] == "divided":
        _apply_sky(ue, plan["light"])
    else:
        _apply_hours(ue, plan["light"])
    ue.EditorLevelLibrary.save_current_level()
    print(f"Elyon built {plan['map']} ({plan['title']})")
    return plan


def build_week(ue=None):
    ue = _ue(ue)
    data = load_creation()
    done = {"light"}
    plans = []
    for day_id in data["order"]:
        plan = build_day(day_id, done, ue=ue)
        done.update(plan["completes"])
        plans.append(plan)
    return plans


def set_hours(phase, ue=None):
    """Day, night, or evening on a level that already has the sun."""
    ue = _ue(ue)
    if phase not in ("day", "night", "evening"):
        raise ValueError(f"unknown hours phase {phase}")
    light = load_creation()["hours"][phase]
    if _by_label(ue).get("Elyon.Sun") is None:
        raise HoursMissing("this level has no luminaries")
    _apply_hours(ue, light)
    ue.EditorLevelLibrary.save_current_level()
    return light
