import unittest

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p25_uqno_aggregate_train import (
    _split,
)


class P25RepeatedSplitContracts(unittest.TestCase):
    def test_split_is_stable_for_same_geometry_and_salt(self):
        self.assertEqual(_split("geometry-17", 3), _split("geometry-17", 3))

    def test_nonzero_salt_changes_split_key_without_changing_default(self):
        self.assertEqual(_split("geometry-17", 0), _split("geometry-17"))
        values = {_split(f"geometry-{i}", 0) for i in range(100)}
        shifted = {_split(f"geometry-{i}", 1) for i in range(100)}
        self.assertEqual(values, {"train", "calibration", "test"})
        self.assertEqual(shifted, {"train", "calibration", "test"})


if __name__ == "__main__":
    unittest.main()
