import unittest

import pandas as pd

from pert_aoa_core import (
    activity_transitive_closure,
    build_canonical_aoa,
    build_reduced_aoa,
    compute_project,
    dataframe_to_activities,
    derived_activity_precedence,
    dummy_count,
    generate_random_project,
    has_unique_real_activity_event_pairs,
    topological_order_events,
)


def make_activities(rows):
    return dataframe_to_activities(
        pd.DataFrame(
            rows,
            columns=["id", "optimistic", "most_likely", "pessimistic", "predecessors"],
        )
    )


CASES = {
    "linear": [
        ("A", 1, 1, 1, ""),
        ("B", 2, 2, 2, "A"),
        ("C", 3, 3, 3, "B"),
    ],
    "parallel_join": [
        ("A", 2, 2, 2, ""),
        ("B", 5, 5, 5, ""),
        ("C", 1, 1, 1, "A,B"),
    ],
    "diamond": [
        ("A", 1, 1, 1, ""),
        ("B", 2, 2, 2, "A"),
        ("C", 3, 3, 3, "A"),
        ("D", 4, 4, 4, "B,C"),
    ],
    "shared_predecessors": [
        ("A", 1, 1, 1, ""),
        ("B", 1, 1, 1, ""),
        ("C", 2, 2, 2, "A,B"),
        ("D", 3, 3, 3, "A,B"),
        ("E", 4, 4, 4, "C,D"),
    ],
}


class ReductionTests(unittest.TestCase):
    def assert_exact_precedence(self, activities, events, arcs):
        self.assertEqual(derived_activity_precedence(events, arcs), activity_transitive_closure(activities))

    def test_named_cases_preserve_exact_precedence(self):
        for name, rows in CASES.items():
            with self.subTest(name=name):
                activities = make_activities(rows)
                canonical_events, canonical_arcs = build_canonical_aoa(activities)
                events, arcs, info = build_reduced_aoa(activities, reduction_method="greedy")

                topological_order_events(events, arcs)
                self.assert_exact_precedence(activities, events, arcs)
                self.assertLessEqual(dummy_count(arcs), dummy_count(canonical_arcs))
                self.assertEqual(info.canonical_dummy_arcs, dummy_count(canonical_arcs))
                self.assertEqual(info.reduced_dummy_arcs, dummy_count(arcs))

    def test_none_mode_keeps_canonical_counts(self):
        activities = make_activities(CASES["diamond"])
        result = compute_project(activities, reduction_method="none")
        info = result.reduction_info
        self.assertEqual(info.method_used, "none")
        self.assertEqual(info.canonical_events, info.reduced_events)
        self.assertEqual(info.canonical_arcs, info.reduced_arcs)
        self.assertEqual(info.canonical_dummy_arcs, info.reduced_dummy_arcs)
        self.assert_exact_precedence(activities, result.events, result.arcs)

    def test_reduction_does_not_merge_parallel_real_activities(self):
        activities = make_activities(CASES["diamond"])
        events, arcs, info = build_reduced_aoa(activities, reduction_method="greedy")
        self.assert_exact_precedence(activities, events, arcs)
        self.assertTrue(has_unique_real_activity_event_pairs(arcs))
        self.assertGreater(info.reduced_dummy_arcs, 0)

    def test_random_projects_preserve_exact_precedence(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                activities = generate_random_project(n_activities=9, edge_probability=0.3, seed=seed)
                result = compute_project(activities, reduction_method="greedy")
                self.assert_exact_precedence(activities, result.events, result.arcs)
                self.assertTrue(has_unique_real_activity_event_pairs(result.arcs))
                self.assertTrue((result.activity_table["total_float"] >= -1e-7).all())


if __name__ == "__main__":
    unittest.main()
