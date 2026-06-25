import unittest

import pandas as pd

from pert_aoa_core import ValidationError, dataframe_to_activities, json_to_activity_dataframe, parse_predecessor_cell


def activity_df(rows):
    return pd.DataFrame(
        rows,
        columns=["id", "optimistic", "most_likely", "pessimistic", "predecessors"],
    )


class ValidationTests(unittest.TestCase):
    def test_parse_predecessors_accepts_common_separators(self):
        self.assertEqual(parse_predecessor_cell("B; A\nC"), ("A", "B", "C"))

    def test_duplicate_activity_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "repetida"):
            dataframe_to_activities(
                activity_df(
                    [
                        ("A", 1, 2, 3, ""),
                        ("A", 1, 2, 3, ""),
                    ]
                )
            )

    def test_single_duration_table_is_accepted(self):
        activities = dataframe_to_activities(
            pd.DataFrame(
                [("A", 5, ""), ("B", 2, "A")],
                columns=["id", "duration", "predecessors"],
            )
        )
        self.assertEqual(activities["A"].optimistic, 5.0)
        self.assertEqual(activities["A"].most_likely, 5.0)
        self.assertEqual(activities["A"].pessimistic, 5.0)
        self.assertEqual(activities["B"].predecessors, ("A",))

    def test_json_activity_list_is_accepted(self):
        df = json_to_activity_dataframe(
            """
            [
              {"id": "A", "duration": 5, "predecessors": []},
              {"id": "B", "duration": 2, "predecessors": ["A"]}
            ]
            """
        )
        activities = dataframe_to_activities(df)
        self.assertEqual(list(df.columns), ["id", "duration", "predecessors"])
        self.assertEqual(activities["B"].predecessors, ("A",))

    def test_json_activity_object_with_pert_estimates_is_accepted(self):
        df = json_to_activity_dataframe(
            """
            {
              "activities": [
                {"id": "A", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ""}
              ]
            }
            """
        )
        activities = dataframe_to_activities(df)
        self.assertEqual(list(df.columns), ["id", "optimistic", "most_likely", "pessimistic", "predecessors"])
        self.assertEqual(activities["A"].mean, 2.0)

    def test_unknown_predecessor_suggests_a_correction(self):
        with self.assertRaisesRegex(ValidationError, "Añade esas actividades"):
            dataframe_to_activities(activity_df([("A", 1, 2, 3, "Z")]))

    def test_self_predecessor_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "Elimina esa referencia"):
            dataframe_to_activities(activity_df([("A", 1, 2, 3, "A")]))

    def test_cycle_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "ciclo"):
            dataframe_to_activities(
                activity_df(
                    [
                        ("A", 1, 2, 3, "C"),
                        ("B", 1, 2, 3, "A"),
                        ("C", 1, 2, 3, "B"),
                    ]
                )
            )


if __name__ == "__main__":
    unittest.main()
