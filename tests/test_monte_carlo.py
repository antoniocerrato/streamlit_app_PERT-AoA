import unittest

import pandas as pd

from pert_aoa_core import dataframe_to_activities, monte_carlo_simulation


def make_activities(rows):
    return dataframe_to_activities(
        pd.DataFrame(
            rows,
            columns=["id", "optimistic", "most_likely", "pessimistic", "predecessors"],
        )
    )


class MonteCarloTests(unittest.TestCase):
    def test_deterministic_linear_project_has_constant_duration(self):
        activities = make_activities(
            [
                ("A", 1, 1, 1, ""),
                ("B", 2, 2, 2, "A"),
                ("C", 3, 3, 3, "B"),
            ]
        )
        result = monte_carlo_simulation(activities, n_iter=25, seed=1, reduction_method="greedy", deadline=6.0)
        self.assertTrue((result.durations == 6.0).all())
        self.assertEqual(result.deadline_probability, 1.0)
        self.assertTrue((result.activity_stats["critical_probability"] == 1.0).all())

    def test_parallel_join_reports_empirical_criticality(self):
        activities = make_activities(
            [
                ("A", 2, 2, 2, ""),
                ("B", 5, 5, 5, ""),
                ("C", 1, 1, 1, "A,B"),
            ]
        )
        result = monte_carlo_simulation(activities, n_iter=20, seed=2, reduction_method="greedy")
        stats = result.activity_stats.set_index("activity")
        self.assertEqual(stats.loc["A", "critical_probability"], 0.0)
        self.assertEqual(stats.loc["B", "critical_probability"], 1.0)
        self.assertEqual(stats.loc["C", "critical_probability"], 1.0)

    def test_event_statistics_include_time_and_critical_probability(self):
        activities = make_activities(
            [
                ("A", 1, 1, 1, ""),
                ("B", 1, 1, 1, "A"),
            ]
        )
        result = monte_carlo_simulation(activities, n_iter=10, seed=3, reduction_method="greedy")
        self.assertIn("early_time_mean", result.event_stats.columns)
        self.assertIn("late_time_p95", result.event_stats.columns)
        self.assertIn("critical_probability", result.event_stats.columns)
        self.assertGreaterEqual(len(result.event_stats), 2)


if __name__ == "__main__":
    unittest.main()
