"""MCP server (stdio) with 3 tools: pk_lint, pk_rewrite, pk_rule. Uses the official MCP Python SDK 2.x.

Run: python -m pk_rewriter.mcp_server
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, StringConstraints

from . import pklint, rewrite

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=rewrite.MAX_CHARS)]
RULE_OF = {code: rule for code, rule, _what, _fn in pklint.CHECKS}

server = MCPServer("pk", instructions="Check and rewrite Polish text in Controlled Polish (PK).")


@server.tool()
def pk_lint(text: Text) -> list[dict]:
    """pklint violations of a Polish text: code, description, rule sentence and the sentence that breaks it."""
    return rewrite.violations(text)


@server.tool()
def pk_rewrite(text: Text, model: str = "qwen3.5:4b",
               rounds: Annotated[int, Field(ge=1, le=rewrite.MAX_ROUNDS)] = rewrite.MAX_ROUNDS) -> dict[str, Any]:
    """Rewrite a Polish text into PK with a local model: generate, check with pklint and numbers, repair."""
    if model not in rewrite.MODELS:
        raise ToolError(f"model must be one of {rewrite.MODELS}")
    try:
        res = rewrite.rewrite(text, model, rounds)
    except OSError as e:
        raise ToolError(f"Ollama call failed: {e}") from e
    best = next(r for r in res["history"] if r["text"] == res["text"])
    return {"text": res["text"], "ok": res["ok"], "rounds": res["rounds"],
            "violations": best["violations"], "missing_numbers": best["missing_numbers"]}


@server.tool()
def pk_rule(code: str) -> dict[str, Any]:
    """The PK rule behind a pklint code, for example B1 or D2."""
    if code not in rewrite.RULES:
        raise ToolError(f"code must be one of {sorted(rewrite.RULES)}")
    return {"code": code, "rule": RULE_OF[code], "what": rewrite.WHAT[code], "text": rewrite.RULES[code]}


def selftest() -> str:
    """The 3 tools answer through the MCP server; a stand-in replaces the Ollama model, so no network is used."""
    import asyncio
    from unittest import mock

    def call(name: str, args: dict) -> Any:
        return asyncio.run(server.call_tool(name, args)).structured_content

    assert {t.name for t in asyncio.run(server.list_tools())} == {"pk_lint", "pk_rewrite", "pk_rule"}
    found = call("pk_lint", {"text": "Kopie bazy należy usuwać regularnie."})["result"]
    assert sorted(v["code"] for v in found) == ["A5", "B1"], found
    clean = {"message": {"content": "Zamknij okno O1."}, "prompt_eval_count": 1, "eval_count": 1, "eval_duration": 1}
    with mock.patch.object(rewrite, "chat", return_value=clean), mock.patch.object(rewrite, "MODELS", ["qwen3.5:4b"]):
        assert call("pk_rewrite", {"text": "Zamknij okno.", "rounds": 1})["ok"] is True
        try:
            call("pk_rewrite", {"text": "Zamknij okno.", "model": "llama3"})
            raise AssertionError("an unknown model was accepted")
        except ToolError:
            pass
    assert call("pk_rule", {"code": "B1"})["text"] == rewrite.RULES["B1"]
    return "ok"


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--selftest"]:
        print(selftest())
    else:
        server.run()
