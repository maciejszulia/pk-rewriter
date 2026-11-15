import asyncio
import unittest
from unittest import mock

from pk_rewriter import rewrite as rw

try:
    from mcp.server.mcpserver.exceptions import ToolError

    from pk_rewriter import mcp_server
except ImportError:  # the mcp extra is not installed
    mcp_server = None

CLEAN = {"message": {"content": "Zamknij okno O1."}, "prompt_eval_count": 1, "eval_count": 1, "eval_duration": 1}


@unittest.skipIf(mcp_server is None, "pip install -e '.[mcp]'")
class Mcp(unittest.TestCase):
    def call(self, name, args):
        return asyncio.run(mcp_server.server.call_tool(name, args)).structured_content

    def test_tools(self):
        names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
        self.assertEqual(names, {"pk_lint", "pk_rewrite", "pk_rule"})

    def test_lint(self):
        out = self.call("pk_lint", {"text": "Kopie bazy należy usuwać regularnie."})["result"]
        self.assertEqual(sorted(v["code"] for v in out), ["A5", "B1"])
        self.assertEqual(out[0]["sentence"], "Kopie bazy należy usuwać regularnie.")

    def test_rewrite_with_a_model_stand_in(self):
        with mock.patch.object(rw, "chat", return_value=CLEAN), mock.patch.object(rw, "MODELS", ["qwen3.5:4b"]):
            out = self.call("pk_rewrite", {"text": "Zamknij okno.", "rounds": 1})
        self.assertEqual(out, {"text": "Zamknij okno O1.", "ok": True, "rounds": 1, "violations": [],
                               "missing_numbers": []})

    def test_input_validation(self):
        with mock.patch.object(rw, "chat", return_value=CLEAN), mock.patch.object(rw, "MODELS", ["qwen3.5:4b"]):
            self.assertEqual(self.call("pk_rewrite", {"text": "x" * 2000})["ok"], True)
            for args in ({"text": ""}, {"text": "   "}, {"text": "x" * 2001}, {"text": "Zamknij okno.", "model": "llama3"},
                         {"text": "Zamknij okno.", "rounds": 0}, {"text": "Zamknij okno.", "rounds": 4}):
                with self.assertRaises(ToolError, msg=args):
                    self.call("pk_rewrite", args)
        with self.assertRaises(ToolError):
            self.call("pk_lint", {"text": "x" * 2001})

    def test_rule(self):
        self.assertEqual(self.call("pk_rule", {"code": "B1"})["text"], rw.RULES["B1"])
        with self.assertRaises(ToolError):
            self.call("pk_rule", {"code": "ZZ"})


if __name__ == "__main__":
    unittest.main()
