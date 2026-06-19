import unittest

import pandas as pd

from pert_aoa_core import compute_project, dataframe_to_activities, schedule_with_activity_durations


def make_activities(rows):
    return dataframe_to_activities(
        pd.DataFrame(
            rows,
            columns=["id", "optimistic", "most_likely", "pessimistic", "predecessors"],
        )
    )


class CpmTests(unittest.TestCase):
    def test_linear_project_duration_is_sum_of_durations(self):
        activities = make_activities(
            [
                ("A", 1, 1, 1, ""),
                ("B", 2, 2, 2, "A"),
                ("C", 3, 3, 3, "B"),
            ]
        )
        result = compute_project(activities, reduction_method="greedy")
        self.assertAlmostEqual(result.project_duration, 6.0)
        self.assertEqual(result.critical_activities, ["A", "B", "C"])

    def test_parallel_join_duration_is_max_path_plus_join(self):
        activities = make_activities(
            [
                ("A", 2, 2, 2, ""),
                ("B", 5, 5, 5, ""),
                ("C", 1, 1, 1, "A,B"),
            ]
        )
        result = compute_project(activities, reduction_method="greedy")
        self.assertAlmostEqual(result.project_duration, 6.0)
        row_a = result.activity_table[result.activity_table["activity"] == "A"].iloc[0]
        row_b = result.activity_table[result.activity_table["activity"] == "B"].iloc[0]
        self.assertGreater(row_a["total_float"], 0.0)
        self.assertAlmostEqual(row_b["total_float"], 0.0)

    def test_schedule_with_activity_durations_uses_supplied_values(self):
        activities = make_activities(
            [
                ("A", 1, 1, 1, ""),
                ("B", 1, 1, 1, ""),
                ("C", 1, 1, 1, "A,B"),
            ]
        )
        duration = schedule_with_activity_durations(activities, {"A": 10, "B": 2, "C": 4}, reduction_method="greedy")
        self.assertAlmostEqual(duration, 14.0)


if __name__ == "__main__":
    unittest.main()
