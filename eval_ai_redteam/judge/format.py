"""Transcript rendering for judge prompts.

Written fresh; the layout mirrors deepteam's ``format_turns`` so ported
judge prompts (which were tuned on that layout) keep working.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from ..types import RTTurn


def format_tools_called(tools_called: Optional[list[Any]]) -> Optional[str]:
    if not tools_called:
        return None
    parts = []
    for tool in tools_called:
        if isinstance(tool, dict):
            name = tool.get("name") or tool.get("tool") or "tool"
            args = tool.get("input_parameters") or tool.get("arguments") or tool.get("args")
            output = tool.get("output")
            line = f"{name}"
            if args is not None:
                line += f"({json.dumps(args, ensure_ascii=False, default=str)})"
            if output is not None:
                line += f" -> {json.dumps(output, ensure_ascii=False, default=str)}"
            parts.append(line)
        else:
            parts.append(str(tool))
    return "; ".join(parts)


def format_turns(turns: list[RTTurn]) -> str:
    if not turns:
        raise ValueError("There are no turns to format.")
    out = "Full Conversation To Evaluate: \n"
    for turn in turns:
        out += f"Role: {turn.role} \n"
        out += f"Content: {turn.content} \n"
        if turn.retrieval_context:
            out += f"Retrieved Context: {turn.retrieval_context} \n"
        tools = format_tools_called(turn.tools_called)
        if tools:
            out += f"Tools Called: {tools} \n\n"
        else:
            out += "\n"
    out += "End of conversation. \n"
    return out


def format_actual_output(actual_output: Optional[str]) -> str:
    return "AI'S ACTUAL OUTPUT TO EVALUATE: \n" + (actual_output or "") + "\n"
