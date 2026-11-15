import re
import unittest
from pathlib import Path

from pk_rewriter import rewrite as rw

ROOT = Path(__file__).resolve().parent.parent


class PkQwen(unittest.TestCase):
    def test_modelfile_matches_the_client(self):
        mf = (ROOT / "models" / "pk-qwen" / "Modelfile").read_text(encoding="utf-8")
        self.assertEqual(re.search(r'SYSTEM """(.*?)"""', mf, re.S).group(1), rw.SYSTEM)
        params = {k: float(v) for k, v in re.findall(r"^PARAMETER (\w+) (\S+)$", mf, re.M)}
        self.assertEqual(params, {k: float(v) for k, v in rw.OPTIONS.items()})


if __name__ == "__main__":
    unittest.main()
