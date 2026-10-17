"""Civilizations simulation core. One deterministic tick Unreal can call.

Ising societies and Kuramoto faith sync from unreal/docs/physics-ideas.md,
composed with the utility sketch in civ_sim.py. This module does not import
Unreal and it does not call a model. Lenia and the Landauer cost stay in
the docs. Incarnation, quantum miracles, higher dimensions, and the laws
of creation stay out of this tick.

Unreal holds the dict from ``new_world`` and passes it back to ``tick``:

    import civ_tick
    world = civ_tick.new_world(seed, ending)
    world = civ_tick.tick(world)

``tick`` does not mutate its input. The seed and the tick counter drive a
fixed LCG inside the Metropolis sweep. Kuramoto itself is an ODE step with
no noise. The same world always yields the same next world.
"""

import copy
import json
import math
from pathlib import Path

import civ_rng
import civ_sim
import ising_society
import kuramoto_faith


DATA_PATH = Path(__file__).resolve().parents[1] / "Data" / "civ_core.json"

# Initial beliefs use this salt plus the settlement index, at tick 0.
# Later sweeps use the settlement index itself and the tick being run.
INIT_SALT = 1000

_TRIBE_KEYS = ("faith", "prosperity", "fear", "population", "shelter")


def load_core(path=None):
    source = Path(path) if path is not None else DATA_PATH
    with source.open(encoding="utf-8") as handle:
        return json.load(handle)


def new_world(seed, ending="harmony", silence=False, data=None):
    """Build a seeded world for one locked ending.

    `ending:hands` becomes wonder when silence was kept, otherwise exile.
    The resolved id is stored and later ticks do not vote another ending.
    """
    if type(seed) is not int:
        raise TypeError("seed must be an int")
    core = data if data is not None else load_core()
    resolved = civ_sim.resolve_ending(ending, silence=silence)
    if resolved is None:
        raise ValueError(f"unknown ending: {ending}")
    bias = core["ending_bias"][resolved]
    ising = core["ising"]
    faith = core["kuramoto"]
    layout = core["layouts"][resolved]
    names = [place["name"] for place in layout]
    if len(names) != len(set(names)):
        raise ValueError("settlement names must be unique")
    width = int(ising["width"])
    height = int(ising["height"])
    half_width = float(faith["omega_half_width"])
    settlements = []
    for index, place in enumerate(layout):
        settlements.append(
            _new_settlement(
                core,
                resolved,
                place,
                index,
                seed,
                width,
                height,
                half_width,
            )
        )
    world = {
        "seed": seed & 0xFFFFFFFF,
        "tick": 0,
        "ending": resolved,
        "field": float(ising["field"]) + float(bias["field"]),
        "temperature": max(0.0, float(ising["temperature"]) + float(bias["temperature"])),
        "J": float(ising["J"]),
        "K": max(0.0, float(faith["K"]) + float(bias["coupling"])),
        "dt": float(faith["dt"]),
        "omega_half_width": half_width,
        "epsilon": float(core["deffuant"]["epsilon"]),
        "mu": float(core["deffuant"]["mu"]),
        "opinion_pull": float(ising["opinion_pull"]),
        "faith_rate": float(ising["faith_rate"]),
        "miracle_field": float(ising["miracle_field"]),
        "miracle_coupling_gain": float(faith["miracle_coupling_gain"]),
        "prophet_narrow": float(faith["prophet_narrow"]),
        "phase_sect_threshold": float(faith["phase_sect_threshold"]),
        "width": width,
        "height": height,
        "miracles": 0,
        "prophets_heard": False,
        "critical_temperature": ising_society.critical_temperature(float(ising["J"])),
        "events": [],
        "last_actions": [],
        "settlements": settlements,
    }
    _write_faith_sync(world)
    return world


def tick(world, steps=1):
    """Advance `steps` utility, Ising, and Kuramoto updates.

    Does not mutate `world`. Voice events set model_called to false.
    """
    if type(steps) is not int or steps < 1:
        raise ValueError("steps must be a positive int")
    state = world
    for _ in range(steps):
        state = _tick_once(state)
    return state


def set_field(world, field):
    """Set God's influence h. Negative favors the opposing belief."""
    value = _finite(field, "field")
    nxt = copy.deepcopy(world)
    nxt["field"] = value
    return nxt


def set_temperature(world, temperature):
    """Set the social-chaos temperature. 0 freezes uphill belief flips."""
    value = _finite(temperature, "temperature")
    if value < 0.0:
        raise ValueError("temperature must be >= 0")
    nxt = copy.deepcopy(world)
    nxt["temperature"] = value
    return nxt


def set_coupling(world, coupling):
    """Set the Kuramoto coupling K shared by the settlements."""
    value = _finite(coupling, "coupling")
    if value < 0.0:
        raise ValueError("coupling must be >= 0")
    nxt = copy.deepcopy(world)
    nxt["K"] = value
    _write_faith_sync(nxt)
    return nxt


def miracle(world):
    """Raise God's field and the faith coupling. Does not step the world.

    The field jump is the Ising miracle. The coupling jump is the Kuramoto
    miracle. A later tick is what flips the spins and moves the phases.
    """
    nxt = copy.deepcopy(world)
    nxt["field"] = nxt["field"] + nxt["miracle_field"]
    nxt["K"] = nxt["K"] + nxt["miracle_coupling_gain"]
    nxt["miracles"] = nxt["miracles"] + 1
    _write_faith_sync(nxt)
    return nxt


def intervene(world, settlement, kind):
    """Apply one of the four stat impulses from the civilizations sketch.

    This changes faith, prosperity, fear, and population only. It does not
    change the Ising field. Divine force here is still the tribe-stat shock.
    """
    nxt = copy.deepcopy(world)
    place = _find(nxt, settlement)
    tribe = _as_tribe(place)
    civ_sim.apply_intervention(tribe, kind)
    _write_tribe(place, tribe)
    return nxt


def _tick_once(world):
    nxt = copy.deepcopy(world)
    nxt["tick"] = int(nxt["tick"]) + 1
    _check_shape(nxt)
    for index, settlement in enumerate(nxt["settlements"]):
        _sweep_beliefs(nxt, settlement, index)
        _move_faith(nxt, settlement)
    _step_faith(nxt)
    actions = []
    events = []
    heard_prophet = False
    for settlement in nxt["settlements"]:
        tribe = _as_tribe(settlement)
        action, voice = civ_sim.tick(tribe)
        _write_tribe(settlement, tribe)
        actions.append({"name": settlement["name"], "action": action})
        events.extend(voice)
        if any(event.get("role") == "prophet" for event in voice):
            heard_prophet = True
    if heard_prophet and not nxt["prophets_heard"]:
        _hear_prophets(nxt)
    nxt["last_actions"] = actions
    nxt["events"] = events
    return nxt


def _sweep_beliefs(world, settlement, index):
    rng = civ_rng.lcg(civ_rng.mix_seed(world["seed"], world["tick"], index))
    previous = list(settlement["spins"])
    updated = ising_society.metropolis_sweep(
        previous,
        world["width"],
        world["J"],
        world["field"],
        world["temperature"],
        rng,
    )
    opinions = []
    for opinion, old, new in zip(settlement["opinions"], previous, updated):
        opinions.append(ising_society.reflect_opinion(opinion, new, old))
    opinions = ising_society.pull_opinions(opinions, updated, world["opinion_pull"])
    pairs = ising_society.lattice_pairs(world["width"], world["height"])
    opinions = ising_society.deffuant_step(
        opinions, pairs, world["epsilon"], world["mu"]
    )
    settlement["spins"] = updated
    settlement["opinions"] = opinions
    settlement["magnetization"] = ising_society.magnetization(updated)
    labels = ising_society.sect_labels(opinions, pairs, world["epsilon"])
    settlement["sects"] = labels
    settlement["sect_count"] = len(set(labels))


def _move_faith(world, settlement):
    target = (settlement["magnetization"] + 1.0) * 50.0
    rate = world["faith_rate"]
    blended = settlement["faith"] + (target - settlement["faith"]) * rate
    settlement["faith"] = _clamp_stat(blended)


def _step_faith(world):
    thetas = [place["theta"] for place in world["settlements"]]
    omegas = [place["omega"] for place in world["settlements"]]
    moved = kuramoto_faith.step(thetas, omegas, world["K"], world["dt"])
    for settlement, theta in zip(world["settlements"], moved):
        settlement["theta"] = theta
    _write_faith_sync(world)


def _write_faith_sync(world):
    thetas = [place["theta"] for place in world["settlements"]]
    order_r, order_psi = kuramoto_faith.order_parameter(thetas)
    labels = kuramoto_faith.faith_sects(thetas, world["phase_sect_threshold"])
    world["order_r"] = order_r
    world["order_psi"] = order_psi
    world["faith_order"] = int(round(order_r * 100.0))
    world["critical_coupling"] = kuramoto_faith.critical_coupling(
        world["omega_half_width"]
    )
    world["schism"] = kuramoto_faith.schism(world["K"], world["omega_half_width"])
    world["faith_sects"] = labels
    world["faith_sect_count"] = len(set(labels)) if labels else 0


def _hear_prophets(world):
    factor = world["prophet_narrow"]
    narrowed = kuramoto_faith.narrow_frequencies(
        [place["omega"] for place in world["settlements"]],
        factor,
    )
    for settlement, omega in zip(world["settlements"], narrowed):
        settlement["omega"] = omega
    world["omega_half_width"] = world["omega_half_width"] * factor
    world["prophets_heard"] = True
    _write_faith_sync(world)


def _new_settlement(core, ending, place, index, seed, width, height, half_width):
    if ending == "exile" and place["region"] != "east":
        raise ValueError("exile settlements are founded in the east")
    if ending != "exile" and place["region"] != "garden":
        raise ValueError("only exile founds a settlement outside the garden")
    count = width * height
    rng = civ_rng.lcg(civ_rng.mix_seed(seed, 0, INIT_SALT + index))
    spins = []
    for _ in range(count):
        spins.append(1 if rng() < 0.5 else -1)
    opinions = [float(spin) for spin in spins]
    theta = (rng() * 2.0 - 1.0) * math.pi
    omega = (rng() * 2.0 - 1.0) * half_width
    start = core["starting"][ending]
    pairs = ising_society.lattice_pairs(width, height)
    labels = ising_society.sect_labels(opinions, pairs, core["deffuant"]["epsilon"])
    return {
        "name": place["name"],
        "region": place["region"],
        "ending": ending,
        "faith": int(start["faith"]),
        "prosperity": int(start["prosperity"]),
        "fear": int(start["fear"]),
        "population": count,
        "shelter": False,
        "spins": spins,
        "opinions": opinions,
        "sects": labels,
        "sect_count": len(set(labels)),
        "theta": theta,
        "omega": omega,
        "magnetization": ising_society.magnetization(spins),
    }


def _as_tribe(settlement):
    tribe = {"name": settlement["name"], "ending": settlement["ending"]}
    for key in _TRIBE_KEYS:
        tribe[key] = settlement[key]
    return tribe


def _write_tribe(settlement, tribe):
    for key in _TRIBE_KEYS:
        settlement[key] = tribe[key]


def _find(world, name):
    for settlement in world["settlements"]:
        if settlement["name"] == name:
            return settlement
    raise KeyError(f"unknown settlement: {name}")


def _check_shape(world):
    if not world["settlements"]:
        raise ValueError("a world needs at least one settlement")
    count = world["width"] * world["height"]
    for settlement in world["settlements"]:
        if len(settlement["spins"]) != count or len(settlement["opinions"]) != count:
            raise ValueError(f"{settlement['name']} does not match the lattice")
        if settlement["ending"] != world["ending"]:
            raise ValueError("a settlement cannot reopen the locked ending")


def _clamp_stat(value):
    return max(0, min(100, int(round(value))))


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise TypeError(f"{name} must be a finite number")
    return number
