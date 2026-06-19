import unittest

import pandas as pd

from pert_aoa_core import ValidationError, dataframe_to_activities, parse_predecessor_cell


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
