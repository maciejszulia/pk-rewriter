import sys
import unittest
from pathlib import Path

from pk_rewriter import pklint

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pk_text  # noqa: E402


class ReadmePl(unittest.TestCase):
    def test_readme_pl_has_0_pklint_violations(self):
        text = pk_text.prose((ROOT / "README.pl.md").read_text(encoding="utf-8"))
        hits, _words, _sentences, examples = pklint.lint(text)
        self.assertEqual(dict(hits), {}, examples)


if __name__ == "__main__":
    unittest.main()
