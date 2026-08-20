import unittest

from scripts.apply_pdf_distances import apply_distances


class ApplyPdfDistancesTests(unittest.TestCase):
    def test_applies_only_reviewed_pdf_distance(self):
        network = {"edges": [{"id": "1:A:B", "distance_m": None}]}
        audit = {"entries": [{"edge_id": "1:A:B", "distance_m": 1582, "verification": "reviewed"}]}

        updated = apply_distances(network, audit)

        self.assertEqual(updated["edges"][0]["distance_m"], 1582)
        self.assertEqual(updated["edges"][0]["distance_source"], "pdf_label")

    def test_rejects_unreviewed_distance(self):
        network = {"edges": [{"id": "1:A:B", "distance_m": None}]}
        audit = {"entries": [{"edge_id": "1:A:B", "distance_m": 1582, "verification": "needs_review"}]}

        with self.assertRaisesRegex(ValueError, "unverified distance"):
            apply_distances(network, audit)

    def test_accepts_high_confidence_automatic_reading(self):
        network = {"edges": [{"id": "1:A:B", "distance_m": None}]}
        audit = {"entries": [{"edge_id": "1:A:B", "distance_m": 1200, "verification": "auto_read"}]}

        updated = apply_distances(network, audit)

        self.assertEqual(updated["edges"][0]["verification"], "auto_read")


if __name__ == "__main__":
    unittest.main()
