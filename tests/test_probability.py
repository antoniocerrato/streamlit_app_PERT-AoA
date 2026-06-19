import unittest

from pert_aoa_core import normal_cdf, pert_beta_parameters, probability_curve


class ProbabilityTests(unittest.TestCase):
    def test_normal_cdf_handles_degenerate_sigma(self):
        self.assertEqual(normal_cdf(5.0, 5.0, 0.0), 1.0)
        self.assertEqual(normal_cdf(4.9, 5.0, 0.0), 0.0)

    def test_probability_curve_has_expected_columns(self):
        curve = probability_curve(mu=10.0, sigma=2.0, deadline=12.0, n=25)
        self.assertEqual(list(curve.columns), ["duration", "density", "cum_probability", "deadline"])
        self.assertEqual(len(curve), 25)

    def test_beta_pert_parameters_are_positive(self):
        alpha, beta = pert_beta_parameters(1.0, 3.0, 7.0)
        self.assertGreater(alpha, 0.0)
        self.assertGreater(beta, 0.0)


if __name__ == "__main__":
    unittest.main()
