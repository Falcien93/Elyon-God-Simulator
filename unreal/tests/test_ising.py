import math
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import ising_society


def aligned(count, spin=1):
    return [spin] * count


class EnergyTests(unittest.TestCase):
    def test_aligned_society_has_the_ising_energy(self):
        spins = aligned(16, 1)
        # 4x4 periodic lattice: 32 bonds, 16 field sites.
        self.assertAlmostEqual(ising_society.energy(spins, 4, J=1.0, h=0.0), -32.0)
        self.assertAlmostEqual(ising_society.energy(spins, 4, J=1.0, h=0.5), -32.0 - 8.0)
        opposed = aligned(16, -1)
        self.assertAlmostEqual(ising_society.energy(opposed, 4, J=1.0, h=0.5), -32.0 + 8.0)

    def test_positive_field_favors_the_aligned_belief(self):
        plus = aligned(16, 1)
        minus = aligned(16, -1)
        h = 1.25
        self.assertLess(
            ising_society.energy(plus, 4, 1.0, h),
            ising_society.energy(minus, 4, 1.0, h),
        )

    def test_one_dissenter_pays_four_bonds_and_the_field(self):
        spins = aligned(16, 1)
        spins[0] = -1
        # 4 broken bonds: sum of s_i s_j drops by 8 from the aligned 32.
        self.assertAlmostEqual(ising_society.energy(spins, 4, J=2.0, h=0.25), -48.0 - 3.5)

    def test_delta_matches_the_energy_difference_on_every_site(self):
        spins = [1, -1, 1, 1, -1, -1, 1, -1, 1, 1, -1, 1, -1, 1, -1, -1]
        before = ising_society.energy(spins, 4, J=1.3, h=-0.4)
        for index in range(len(spins)):
            flipped = list(spins)
            flipped[index] = -flipped[index]
            after = ising_society.energy(flipped, 4, J=1.3, h=-0.4)
            delta = ising_society.delta_energy(spins, 4, index, J=1.3, h=-0.4)
            self.assertAlmostEqual(delta, after - before)

    def test_corner_sees_the_wrapped_neighbors(self):
        # Flipping index 0 changes the bond to the last column and the last row.
        spins = aligned(16, 1)
        delta = ising_society.delta_energy(spins, 4, 0, J=1.0, h=0.0)
        self.assertAlmostEqual(delta, 8.0)

    def test_lattice_must_be_at_least_two_by_two(self):
        with self.assertRaises(ValueError):
            ising_society.energy([1, -1, 1, -1], 4, 1.0, 0.0)
        with self.assertRaises(ValueError):
            ising_society.energy([1, -1], 1, 1.0, 0.0)
        with self.assertRaises(IndexError):
            ising_society.delta_energy([1, 1, 1, 1], 2, 7, 1.0, 0.0)

    def test_spins_are_only_plus_or_minus_one(self):
        with self.assertRaises(ValueError):
            ising_society.magnetization([1, 0, -1, 1])


class MagnetizationTests(unittest.TestCase):
    def test_mean_spin_is_the_belief(self):
        self.assertEqual(ising_society.magnetization(aligned(8, 1)), 1.0)
        self.assertEqual(ising_society.magnetization(aligned(8, -1)), -1.0)
        self.assertEqual(ising_society.magnetization([1, -1, 1, -1]), 0.0)


class MetropolisTests(unittest.TestCase):
    def test_zero_temperature_never_climbs_and_does_not_draw(self):
        spins = aligned(16, 1)

        def boom():
            raise AssertionError("uphill flips at T=0 must not draw")

        frozen = ising_society.metropolis_sweep(spins, 4, J=1.0, h=0.0, temperature=0.0, rng=boom)
        self.assertEqual(frozen, spins)
        self.assertEqual(spins, aligned(16, 1))

    def test_zero_coupling_lets_every_belief_flip(self):
        spins = aligned(16, 1)
        flipped = ising_society.metropolis_sweep(
            spins, 4, J=0.0, h=0.0, temperature=0.0, rng=lambda: 1.0
        )
        self.assertEqual(flipped, aligned(16, -1))

    def test_heat_accepts_an_uphill_flip_that_cold_rejects(self):
        spins = aligned(16, 1)
        # ΔE = 8 for the first site. A draw of 0.5 loses at T=1 and wins at T=100.
        cold = ising_society.metropolis_sweep(
            spins, 4, J=1.0, h=0.0, temperature=1.0, rng=lambda: 0.5
        )
        hot = ising_society.metropolis_sweep(
            spins, 4, J=1.0, h=0.0, temperature=100.0, rng=lambda: 0.5
        )
        self.assertEqual(cold[0], 1)
        self.assertEqual(hot[0], -1)
        self.assertEqual(spins[0], 1)

    def test_field_stronger_than_four_bonds_flips_an_opposed_society(self):
        spins = aligned(16, -1)
        # h > 4J makes every opposed flip downhill, so the draw cannot save it.
        flipped = ising_society.metropolis_sweep(
            spins, 4, J=1.0, h=4.01, temperature=0.0, rng=lambda: 1.0
        )
        self.assertEqual(flipped, aligned(16, 1))
        self.assertEqual(ising_society.magnetization(flipped), 1.0)

    def test_sweep_is_deterministic_for_a_fixed_stream(self):
        spins = [1, -1, -1, 1, 1, 1, -1, -1, -1, 1, 1, -1, 1, -1, 1, -1]
        draws = iter([0.01, 0.2, 0.8, 0.4, 0.9, 0.05, 0.5, 0.3])

        def rng():
            return next(draws)

        once = ising_society.metropolis_sweep(spins, 4, 1.0, 0.2, 2.2, rng)
        draws_again = iter([0.01, 0.2, 0.8, 0.4, 0.9, 0.05, 0.5, 0.3])
        twice = ising_society.metropolis_sweep(
            spins, 4, 1.0, 0.2, 2.2, lambda: next(draws_again)
        )
        self.assertEqual(once, twice)
        self.assertTrue(all(spin in (1, -1) for spin in once))

    def test_temperature_must_be_a_real_heat(self):
        with self.assertRaises(ValueError):
            ising_society.metropolis_sweep(aligned(4, 1), 2, 1.0, 0.0, -0.1, lambda: 0.0)
        with self.assertRaises(ValueError):
            ising_society.metropolis_sweep(aligned(4, 1), 2, 1.0, 0.0, math.nan, lambda: 0.0)


class CriticalTemperatureTests(unittest.TestCase):
    def test_onsager_temperature_scales_with_cohesion(self):
        onsager = 2.0 / math.log(1.0 + math.sqrt(2.0))
        self.assertAlmostEqual(ising_society.critical_temperature(1.0), onsager, places=12)
        self.assertAlmostEqual(ising_society.critical_temperature(2.0), 2.0 * onsager, places=12)

    def test_cohesion_must_be_positive(self):
        with self.assertRaises(ValueError):
            ising_society.critical_temperature(0.0)


class DeffuantTests(unittest.TestCase):
    def test_close_beliefs_move_together_and_far_ones_do_not(self):
        mixed = ising_society.deffuant_step([0.0, 0.2], [(0, 1)], epsilon=0.5, mu=0.5)
        self.assertAlmostEqual(mixed[0], 0.1)
        self.assertAlmostEqual(mixed[1], 0.1)
        apart = ising_society.deffuant_step([-1.0, 1.0], [(0, 1)], epsilon=0.5, mu=0.5)
        self.assertEqual(apart, [-1.0, 1.0])

    def test_exact_confidence_bound_does_not_mix(self):
        held = ising_society.deffuant_step([0.0, 0.5], [(0, 1)], epsilon=0.5, mu=1.0)
        self.assertEqual(held, [0.0, 0.5])

    def test_wide_confidence_erases_a_split(self):
        merged = ising_society.deffuant_step([-1.0, 1.0], [(0, 1)], epsilon=2.1, mu=0.5)
        self.assertAlmostEqual(merged[0], 0.0)
        self.assertAlmostEqual(merged[1], 0.0)

    def test_opinions_stay_inside_the_unit_interval(self):
        clamped = ising_society.deffuant_step([1.0, 1.0], [(0, 1)], epsilon=0.5, mu=0.5)
        self.assertEqual(clamped, [1.0, 1.0])
        pulled = ising_society.pull_opinions([2.0, -2.0], [1, -1], rate=0.0)
        self.assertEqual(pulled, [1.0, -1.0])

    def test_pull_can_hand_the_opinion_to_the_spin(self):
        self.assertEqual(ising_society.pull_opinions([-0.2, 0.4], [1, -1], rate=1.0), [1.0, -1.0])

    def test_a_flip_reflects_the_opinion(self):
        self.assertEqual(ising_society.reflect_opinion(0.4, new_spin=-1, old_spin=1), -0.4)
        self.assertEqual(ising_society.reflect_opinion(0.4, new_spin=1, old_spin=1), 0.4)
        self.assertEqual(ising_society.reflect_opinion(0.0, new_spin=-1, old_spin=1), -1.0)

    def test_two_blocks_are_two_sects_on_a_periodic_lattice(self):
        opinions = []
        for y in range(4):
            for x in range(4):
                opinions.append(-1.0 if x < 2 else 1.0)
        pairs = ising_society.lattice_pairs(4, 4)
        labels = ising_society.sect_labels(opinions, pairs, epsilon=0.5)
        self.assertEqual(len(set(labels)), 2)
        self.assertEqual(labels[0], labels[1])
        self.assertNotEqual(labels[0], labels[2])

    def test_bad_confidence_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            ising_society.deffuant_step([0.0, 0.1], [(0, 1)], epsilon=-0.1, mu=0.5)
        with self.assertRaises(ValueError):
            ising_society.deffuant_step([0.0, 0.1], [(0, 1)], epsilon=0.5, mu=1.5)
        with self.assertRaises(ValueError):
            ising_society.pull_opinions([0.0], [1, -1], rate=0.2)


class FormulaTests(unittest.TestCase):
    def test_docstring_quotes_the_ising_formulas(self):
        ideas = Path(__file__).resolve().parents[1].joinpath("docs", "physics-ideas.md")
        text = ideas.read_text(encoding="utf-8")
        source = Path(ising_society.__file__).read_text(encoding="utf-8")
        for formula in (
            "H = −J Σ s_i s_j − h Σ s_i",
            "P = min(1, e^{−ΔE/T})",
        ):
            self.assertIn(formula, text)
            self.assertIn(formula, source)


if __name__ == "__main__":
    unittest.main()
