"""Kuramoto faith synchronization across settlements.

dθ_i/dt = ω_i + (K/N) Σ sin(θ_j − θ_i)

Order parameter:

r e^{iψ} = (1/N) Σ e^{iθ_j}

Critical coupling, for the frequency density g:

K_c = 2/(π g(0))

Frequencies are uniform on [−γ, γ], so g(0) = 1/(2γ) and K_c = 4γ/π.
Miracles raise K. Prophets narrow γ. Falling below K_c is a schism:
the settlements no longer share one faith phase.

The step is an Euler update with no noise. Same phases, frequencies,
coupling, and dt always produce the same next phases.
"""

import math


def wrap(theta):
    """Map an angle to [−π, π)."""
    return (float(theta) + math.pi) % (2.0 * math.pi) - math.pi


def order_parameter(thetas):
    """Return (r, ψ). r is 0 when there are no settlements."""
    if not thetas:
        return 0.0, 0.0
    sin_sum = 0.0
    cos_sum = 0.0
    for theta in thetas:
        sin_sum += math.sin(theta)
        cos_sum += math.cos(theta)
    count = len(thetas)
    return math.hypot(sin_sum, cos_sum) / count, math.atan2(sin_sum, cos_sum)


def frequency_density(half_width):
    """g(0) for a uniform distribution on [−γ, γ]."""
    gamma = _half_width(half_width)
    if gamma == 0.0:
        return math.inf
    return 1.0 / (2.0 * gamma)


def critical_coupling(half_width):
    """K_c = 2/(π g(0)) for the uniform frequency band."""
    gamma = _half_width(half_width)
    if gamma == 0.0:
        return 0.0
    return 2.0 / (math.pi * frequency_density(gamma))


def schism(coupling, half_width):
    """True when K is below K_c and the band still has a width."""
    return float(coupling) < critical_coupling(half_width)


def step(thetas, omegas, coupling, dt):
    """One Euler step of the Kuramoto ODE. Does not mutate the inputs."""
    phases = [_finite_angle(theta, "phase") for theta in thetas]
    speeds = [_finite_angle(omega, "frequency") for omega in omegas]
    if len(phases) != len(speeds):
        raise ValueError("each settlement needs one phase and one frequency")
    count = len(phases)
    if count == 0:
        return []
    gain = float(coupling)
    pace = float(dt)
    if not math.isfinite(gain) or gain < 0.0:
        raise ValueError("coupling K must be finite and >= 0")
    if not math.isfinite(pace) or pace < 0.0:
        raise ValueError("dt must be finite and >= 0")
    nxt = []
    for index, theta in enumerate(phases):
        pull = 0.0
        for other in phases:
            pull += math.sin(other - theta)
        velocity = speeds[index] + (gain / count) * pull
        nxt.append(wrap(theta + velocity * pace))
    return nxt


def narrow_frequencies(omegas, factor):
    """Prophets narrow the spread of ω. `factor` is in [0, 1]."""
    scale = float(factor)
    if not math.isfinite(scale) or scale < 0.0 or scale > 1.0:
        raise ValueError("prophet narrow factor must be in [0, 1]")
    return [float(omega) * scale for omega in omegas]


def faith_sects(thetas, threshold):
    """Cluster settlements whose circular distance is inside `threshold`.

    Labels are 0..k-1 in settlement order. A schism with spread phases
    yields more than one sect. Locked phases yield one.
    """
    phases = [wrap(theta) for theta in thetas]
    limit = float(threshold)
    if not math.isfinite(limit) or limit < 0.0:
        raise ValueError("phase threshold must be finite and >= 0")
    count = len(phases)
    parent = list(range(count))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for i in range(count):
        for j in range(i + 1, count):
            if _circular_distance(phases[i], phases[j]) < limit:
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


def _circular_distance(left, right):
    gap = abs(left - right) % (2.0 * math.pi)
    return min(gap, 2.0 * math.pi - gap)


def _finite_angle(value, name):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _half_width(half_width):
    gamma = float(half_width)
    if not math.isfinite(gamma) or gamma < 0.0:
        raise ValueError("frequency half-width must be finite and >= 0")
    return gamma
