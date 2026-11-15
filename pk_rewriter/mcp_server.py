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


if __name__ == "__main__":
    server.run()
