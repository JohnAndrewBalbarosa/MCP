from __future__ import annotations

import ast
import re
from typing import Dict, List


def strip_code_fences(text: str) -> str:
    cleaned = re.sub(r"^```[\w]*\s*\n?", "", text.lstrip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.rstrip())
    return cleaned.strip()


def _python_function_summaries(source: str) -> List[str]:
    summaries: List[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return summaries

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        doc = ast.get_docstring(node) or "No docstring"
        first_line = doc.splitlines()[0].strip() if doc.strip() else "No docstring"
        summaries.append(f"{node.name}: {first_line}")

    return summaries


def summarize_generated_code(
    target_file: str,
    mutation_intent: str,
    replacement: str,
) -> Dict[str, object]:
    functions = _python_function_summaries(replacement)
    if not functions:
        function_count = 0
    else:
        function_count = len(functions)

    return {
        "target_file": target_file,
        "mutation_intent": mutation_intent,
        "function_count": function_count,
        "function_summaries": functions,
        "replacement_head": " ".join(replacement.split())[:180],
    }


def render_compact_summary(summary: Dict[str, object]) -> str:
    target_file = str(summary.get("target_file", ""))
    mutation_intent = str(summary.get("mutation_intent", ""))
    function_summaries = summary.get("function_summaries", [])

    if isinstance(function_summaries, list) and function_summaries:
        function_text = "; ".join(str(item) for item in function_summaries)
    else:
        function_text = "No parsed functions"

    return (
        f"file={target_file} | intent={mutation_intent} | "
        f"functions={function_text}"
    )
