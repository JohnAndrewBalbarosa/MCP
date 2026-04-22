from __future__ import annotations

import ast
import re
from typing import Dict, List


def strip_code_fences(text: str) -> str:
    cleaned = re.sub(r"^```[\w]*\s*\n?", "", text.lstrip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.rstrip())
    return cleaned.strip()


def _python_function_headers(source: str) -> List[Dict[str, str]]:
    headers: List[Dict[str, str]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return headers

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        doc = ast.get_docstring(node) or "No docstring"
        first_line = doc.splitlines()[0].strip() if doc.strip() else "No docstring"
        inputs = [arg.arg for arg in node.args.args]
        output = "return value"
        if node.returns is not None:
            output = ast.unparse(node.returns)
        headers.append(
            {
                "name": node.name,
                "description": first_line,
                "input": ", ".join(inputs) if inputs else "none",
                "output": output,
            }
        )

    return headers


def summarize_generated_code(
    target_file: str,
    mutation_intent: str,
    replacement: str,
) -> Dict[str, object]:
    function_headers = _python_function_headers(replacement)
    function_count = len(function_headers)
    function_summaries = [
        f"{header['name']}: {header['description']}"
        for header in function_headers
    ]

    return {
        "target_file": target_file,
        "mutation_intent": mutation_intent,
        "function_count": function_count,
        "function_summaries": function_summaries,
        "function_headers": function_headers,
        "known_inputs": [header["input"] for header in function_headers if header.get("input")],
        "known_outputs": [header["output"] for header in function_headers if header.get("output")],
        "known_constraints": [],
        "branch_summary": (
            f"Applied mutation for {target_file} with {function_count} parsed function(s)"
        ),
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
