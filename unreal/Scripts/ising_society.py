"""Ising society. Spins are beliefs. h is God's influence. T is social chaos.

H = −J Σ s_i s_j − h Σ s_i

Metropolis flips with P = min(1, e^{−ΔE/T}).

J is cohesion. The lattice is a finite periodic square, a sample of the
people in one settlement. T_c below is the infinite-square Onsager value,
the reference for "near T_c", not a finite-size estimate.

Deffuant bounded confidence forms sects from a continuous opinion in
[-1, 1]. People only average a belief with a neighbor already inside ε.
"""

import math


def critical_temperature(J=1.0):
    """Onsager T_c for the 2D square lattice, in units of the coupling J."""
    coupling = _positive(J, "J")
    return coupling * 2.0 / math.log(1.0 + math.sqrt(2.0))


def energy(spins, width, J, h):
    """Hamiltonian. Each bond is counted once."""
    sites, width, height = _lattice(spins, width)
    bond = 0.0
    field = 0.0
    for y in range(height):
        for x in range(width):
            i = y * width + x
            field += sites[i]
            right = y * width + (x + 1) % width
            down = ((y + 1) % height) * width + x
            bond += sites[i] * sites[right]
            bond += sites[i] * sites[down]
    return -float(J) * bond - float(h) * field


def delta_energy(spins, width, index, J, h):
    """Energy change of flipping spins[index]. Positive means uphill."""
    sites, width, height = _lattice(spins, width)
    if index < 0 or index >= len(sites):
        raise IndexError(f"spin index out of range: {index}")
    spin = sites[index]
    neighbor_sum = 0
    for neighbor in _neighbors(width, height, index):
        neighbor_sum += sites[neighbor]
    return 2.0 * spin * (float(J) * neighbor_sum + float(h))


def magnetization(spins):
    """Mean spin in [-1, 1]. +1 is a belief aligned with the positive field."""
    sites = _spins(spins)
    if not sites:
        return 0.0
    return sum(sites) / len(sites)


def metropolis_sweep(spins, width, J, h, temperature, rng):
    """One sequential Metropolis sweep. Does not mutate `spins`.

    A downhill flip is always taken. At T = 0 an uphill flip is never
    taken, and the rng is not called. T > 0 accepts an uphill flip when
    the next rng draw is below e^{−ΔE/T}.
    """
    sites, width, _height = _lattice(spins, width)
    heat = _temperature(temperature)
    coupling = float(J)
    field = float(h)
    updated = list(sites)
    for index in range(len(updated)):
        change = delta_energy(updated, width, index, coupling, field)
        if change <= 0.0:
            updated[index] = -updated[index]
            continue
        if heat <= 0.0:
            continue
        if rng() < math.exp(-change / heat):
            updated[index] = -updated[index]
    return updated


def lattice_pairs(width, height):
    """Each periodic right edge and down edge, once, row-major."""
    if width < 2 or height < 2:
        raise ValueError("lattice must be at least 2 by 2")
    pairs = []
    for y in range(height):
        for x in range(width):
            i = y * width + x
            right = y * width + (x + 1) % width
            down = ((y + 1) % height) * width + x
            pairs.append((i, right))
            pairs.append((i, down))
    return pairs


def deffuant_step(opinions, pairs, epsilon, mu):
    """Bounded-confidence update. Does not mutate `opinions`.

    When |x_i − x_j| < ε, both move toward each other by μ.
    Opinions outside that bound stay put. Results stay in [-1, 1].
    """
    xs = [_opinion(value) for value in opinions]
    bound = float(epsilon)
    rate = float(mu)
    if bound < 0.0:
        raise ValueError("epsilon must be >= 0")
    if rate < 0.0 or rate > 1.0:
        raise ValueError("mu must be in [0, 1]")
    for i, j in pairs:
        diff = xs[j] - xs[i]
        if abs(diff) < bound:
            xs[i] = _clamp_opinion(xs[i] + rate * diff)
            xs[j] = _clamp_opinion(xs[j] - rate * diff)
    return xs


def pull_opinions(opinions, spins, rate):
    """Move each opinion toward its spin. Does not mutate the inputs."""
    sites = _spins(spins)
    if len(opinions) != len(sites):
        raise ValueError("opinions and spins must have the same length")
    step = float(rate)
    if step < 0.0 or step > 1.0:
        raise ValueError("opinion pull must be in [0, 1]")
    moved = []
    for opinion, spin in zip(opinions, sites):
        # Lerp in this order so a full pull lands on the spin exactly.
        value = (1.0 - step) * _opinion(opinion) + step * float(spin)
        moved.append(_clamp_opinion(value))
    return moved


def reflect_opinion(opinion, new_spin, old_spin):
    """Keep the magnitude and follow a Metropolis flip."""
    if new_spin == old_spin:
        return _opinion(opinion)
    if opinion == 0:
        return float(new_spin)
    return _clamp_opinion(-_opinion(opinion))


def sect_labels(opinions, pairs, epsilon):
    """Connected components of people within ε of a neighbor.

    Labels are compacted to 0..k-1 in first-seen order.
    """
    count = len(opinions)
    parent = list(range(count))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    bound = float(epsilon)
    for i, j in pairs:
        if abs(_opinion(opinions[i]) - _opinion(opinions[j])) < bound:
            left, right = find(i), find(j)
            if left != right:
                parent[right] = left
    labels = []
    compact = {}
    for index in range(count):
        root = find(index)
        if root not in compact:
            compact[root] = len(compact)
        labels.append(compact[root])
    return labels


def _spins(spins):
    sites = []
    for spin in spins:
        if spin not in (1, -1):
            raise ValueError(f"spins must be +1 or -1, got {spin}")
        sites.append(int(spin))
    return sites


def _lattice(spins, width):
    sites = _spins(spins)
    if width < 2:
        raise ValueError("lattice must be at least 2 by 2")
    if len(sites) % width != 0:
        raise ValueError("spin count must divide evenly by width")
    height = len(sites) // width
    if height < 2:
        raise ValueError("lattice must be at least 2 by 2")
    return sites, width, height


def _neighbors(width, height, index):
    x = index % width
    y = index // width
    return (
        y * width + (x + 1) % width,
        y * width + (x - 1) % width,
        ((y + 1) % height) * width + x,
        ((y - 1) % height) * width + x,
    )


def _opinion(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("opinion must be finite")
    return _clamp_opinion(number)


def _clamp_opinion(value):
    return max(-1.0, min(1.0, float(value)))


def _temperature(temperature):
    heat = float(temperature)
    if not math.isfinite(heat) or heat < 0.0:
        raise ValueError("temperature must be finite and >= 0")
    return heat


def _positive(value, name):
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be finite and > 0")
    return number
