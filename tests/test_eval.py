import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
import run_eval  # noqa: E402


class ChrF(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(run_eval.chrf("Zamknij okno O1.", "Zamknij  okno O1."), 100.0)
        self.assertEqual(run_eval.chrf("abc", "xyz"), 0.0)
        self.assertEqual(run_eval.chrf("", "abc"), 0.0)

    def test_recall_weighs_more_than_precision(self):
        ref = "Zamknij okno O1 w sali S1."
        short, long = "Zamknij okno O1.", "Zamknij okno O1 w sali S1 po zajęciach."
        self.assertGreater(run_eval.chrf(long, ref), run_eval.chrf(short, ref))


if __name__ == "__main__":
    unittest.main()
