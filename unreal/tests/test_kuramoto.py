import math
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import kuramoto_faith


class OrderTests(unittest.TestCase):
    def test_locked_phases_have_order_one(self):
        r, psi = kuramoto_faith.order_parameter([0.0, 0.0, 0.0])
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(psi, 0.0)

    def test_evenly_spaced_phases_have_no_order(self):
        phases = [0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0]
        r, _psi = kuramoto_faith.order_parameter(phases)
        self.assertAlmostEqual(r, 0.0, places=9)

    def test_a_single_phase_is_its_own_order(self):
        r, psi = kuramoto_faith.order_parameter([math.pi / 2.0])
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(psi, math.pi / 2.0, places=9)

    def test_no_settlements_are_unordered(self):
        self.assertEqual(kuramoto_faith.order_parameter([]), (0.0, 0.0))


class StepTests(unittest.TestCase):
    def test_two_oscillators_match_the_hand_step(self):
        dt = 0.25
        nxt = kuramoto_faith.step([0.0, math.pi / 2.0], [0.0, 0.0], coupling=2.0, dt=dt)
        self.assertAlmostEqual(nxt[0], 0.25)
        self.assertAlmostEqual(nxt[1], math.pi / 2.0 - 0.25)

    def test_zero_coupling_advances_each_frequency_alone(self):
        dt = 0.5
        nxt = kuramoto_faith.step([0.0, math.pi], [0.2, -0.4], coupling=0.0, dt=dt)
        self.assertAlmostEqual(nxt[0], 0.1)
        self.assertAlmostEqual(nxt[1], kuramoto_faith.wrap(math.pi - 0.2))

    def test_equal_frequencies_and_positive_coupling_synchronize(self):
        phases = [0.0, 0.5, -0.4, 1.1]
        speeds = [0.0, 0.0, 0.0, 0.0]
        r0, _psi = kuramoto_faith.order_parameter(phases)
        state = phases
        for _ in range(40):
            state = kuramoto_faith.step(state, speeds, coupling=4.0, dt=0.1)
        r1, _psi = kuramoto_faith.order_parameter(state)
        self.assertGreater(r1, r0)
        self.assertGreater(r1, 0.99)

    def test_coupling_holds_what_free_frequencies_pull_apart(self):
        speeds = [-0.6, -0.2, 0.25, 0.55]
        free = [0.0, 0.0, 0.0, 0.0]
        bound = [0.0, 0.0, 0.0, 0.0]
        for _ in range(50):
            free = kuramoto_faith.step(free, speeds, coupling=0.0, dt=0.1)
            bound = kuramoto_faith.step(bound, speeds, coupling=8.0, dt=0.1)
        r_free, _psi = kuramoto_faith.order_parameter(free)
        r_bound, _psi = kuramoto_faith.order_parameter(bound)
        self.assertGreater(r_bound, r_free)
        self.assertGreater(r_bound, 0.9)
        self.assertLess(r_free, 0.75)

    def test_step_does_not_mutate_and_repeats(self):
        phases = [0.2, -1.0, 2.0]
        speeds = [0.1, -0.3, 0.0]
        once = kuramoto_faith.step(phases, speeds, 1.2, 0.05)
        twice = kuramoto_faith.step(phases, speeds, 1.2, 0.05)
        self.assertEqual(once, twice)
        self.assertEqual(phases, [0.2, -1.0, 2.0])
        for theta in once:
            self.assertGreaterEqual(theta, -math.pi)
            self.assertLess(theta, math.pi)

    def test_angles_wrap_into_the_open_interval(self):
        self.assertAlmostEqual(kuramoto_faith.wrap(0.0), 0.0)
        self.assertAlmostEqual(kuramoto_faith.wrap(math.pi / 2.0), math.pi / 2.0)
        self.assertAlmostEqual(kuramoto_faith.wrap(3.0 * math.pi), -math.pi)
        self.assertAlmostEqual(kuramoto_faith.wrap(-3.0 * math.pi), -math.pi)

    def test_mismatched_or_bad_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            kuramoto_faith.step([0.0, 0.1], [0.2], 1.0, 0.1)
        with self.assertRaises(ValueError):
            kuramoto_faith.step([0.0], [0.0], -0.1, 0.1)
        with self.assertRaises(ValueError):
            kuramoto_faith.step([0.0], [math.nan], 0.0, 0.1)
        self.assertEqual(kuramoto_faith.step([], [], 1.0, 0.1), [])


class CriticalCouplingTests(unittest.TestCase):
    def test_uniform_band_matches_both_forms_of_k_c(self):
        gamma = 0.5
        g0 = kuramoto_faith.frequency_density(gamma)
        self.assertAlmostEqual(g0, 1.0)
        from_density = 2.0 / (math.pi * g0)
        from_width = 4.0 * gamma / math.pi
        self.assertAlmostEqual(kuramoto_faith.critical_coupling(gamma), from_density, places=12)
        self.assertAlmostEqual(kuramoto_faith.critical_coupling(gamma), from_width, places=12)

    def test_a_locked_frequency_has_no_critical_coupling(self):
        self.assertEqual(kuramoto_faith.critical_coupling(0.0), 0.0)
        self.assertTrue(math.isinf(kuramoto_faith.frequency_density(0.0)))

    def test_schism_is_falling_below_k_c(self):
        gamma = 0.5
        k_c = kuramoto_faith.critical_coupling(gamma)
        self.assertTrue(kuramoto_faith.schism(k_c - 1e-9, gamma))
        self.assertFalse(kuramoto_faith.schism(k_c, gamma))
        self.assertFalse(kuramoto_faith.schism(k_c + 1.0, gamma))

    def test_prophets_narrow_the_spread_and_lower_k_c(self):
        speeds = [0.4, -0.2, 0.1]
        narrowed = kuramoto_faith.narrow_frequencies(speeds, 0.5)
        self.assertEqual(narrowed, [0.2, -0.1, 0.05])
        self.assertEqual(speeds, [0.4, -0.2, 0.1])
        wide = kuramoto_faith.critical_coupling(0.4)
        tight = kuramoto_faith.critical_coupling(0.2)
        self.assertAlmostEqual(tight, wide * 0.5)
        with self.assertRaises(ValueError):
            kuramoto_faith.narrow_frequencies(speeds, 1.2)


class SectTests(unittest.TestCase):
    def test_spread_phases_are_separate_sects(self):
        phases = [0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0]
        labels = kuramoto_faith.faith_sects(phases, threshold=math.pi / 2.0)
        self.assertEqual(len(set(labels)), 3)

    def test_one_phase_is_one_sect(self):
        labels = kuramoto_faith.faith_sects([0.2, 0.2, 0.2], threshold=0.5)
        self.assertEqual(labels, [0, 0, 0])


class FormulaTests(unittest.TestCase):
    def test_docstring_quotes_the_kuramoto_formulas(self):
        ideas = Path(__file__).resolve().parents[1].joinpath("docs", "physics-ideas.md")
        text = ideas.read_text(encoding="utf-8")
        source = Path(kuramoto_faith.__file__).read_text(encoding="utf-8")
        for formula in (
            "dθ_i/dt = ω_i + (K/N) Σ sin(θ_j − θ_i)",
            "r e^{iψ} = (1/N) Σ e^{iθ_j}",
            "K_c = 2/(π g(0))",
        ):
            self.assertIn(formula, text)
            self.assertIn(formula, source)


if __name__ == "__main__":
    unittest.main()
