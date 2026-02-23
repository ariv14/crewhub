"""Python Code Reviewer -- demo A2A agent.

Skills:
  - review-code           Review Python code for common issues.
  - suggest-improvements  Suggest concrete improvements.

Port: 8003
Credits: 3 per task

Uses simple static-analysis heuristics -- no AST parsing or external tools.

Run standalone:
    uvicorn demo_agents.code_reviewer.agent:app --port 8003
"""

from __future__ import annotations

import re

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app

PORT = 8003
CREDITS = 3

SKILLS = [
    {
        "id": "review-code",
        "name": "Review Python Code",
        "description": "Analyse Python source code for common quality issues including missing docstrings, long functions, missing type hints, broad exception handling, and unused import patterns.",
        "inputModes": ["text"],
        "outputModes": ["text", "data"],
        "examples": [
            {
                "input": "def foo(x):\n    return x+1",
                "output": "Issues found:\n- Missing docstring for function 'foo'\n- Missing type hints for function 'foo'",
                "description": "Review a simple function",
            }
        ],
    },
    {
        "id": "suggest-improvements",
        "name": "Suggest Code Improvements",
        "description": "Return actionable suggestions to improve Python code quality, readability, and maintainability.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "def foo(x):\n    return x+1",
                "output": "Suggestions:\n1. Add a docstring explaining what 'foo' does\n2. Add type hints: def foo(x: int) -> int:",
                "description": "Suggest improvements for a simple function",
            }
        ],
    },
]


# ---------------------------------------------------------------------------
# Static analysis checks
# ---------------------------------------------------------------------------

def _find_functions(code: str) -> list[dict]:
    """Extract function definitions with line numbers and bodies."""
    functions: list[dict] = []
    lines = code.split("\n")
    func_re = re.compile(r"^(\s*)def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*\S+)?\s*:")
    i = 0
    while i < len(lines):
        m = func_re.match(lines[i])
        if m:
            indent = len(m.group(1))
            name = m.group(2)
            params = m.group(3)
            has_return_type = "->" in lines[i]
            start = i
            # Collect body
            body_lines: list[str] = []
            i += 1
            while i < len(lines):
                stripped = lines[i].rstrip()
                if stripped == "":
                    body_lines.append(stripped)
                    i += 1
                    continue
                line_indent = len(lines[i]) - len(lines[i].lstrip())
                if line_indent <= indent and stripped != "":
                    break
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines)
            has_docstring = bool(re.match(r'\s*("""|\'\'\')', body))
            functions.append({
                "name": name,
                "line": start + 1,
                "params": params,
                "has_return_type": has_return_type,
                "has_docstring": has_docstring,
                "body_lines": len(body_lines),
                "body": body,
            })
        else:
            i += 1
    return functions


def _check_imports(code: str) -> list[dict]:
    """Look for potentially unused imports (heuristic)."""
    issues: list[dict] = []
    import_re = re.compile(r"^(?:from\s+\S+\s+)?import\s+(.+)", re.MULTILINE)
    for m in import_re.finditer(code):
        names = [n.strip().split(" as ")[-1].strip() for n in m.group(1).split(",")]
        for name in names:
            if name == "*":
                issues.append({
                    "type": "wildcard-import",
                    "severity": "warning",
                    "message": f"Wildcard import found: '{m.group(0).strip()}'. Prefer explicit imports.",
                    "line": code[:m.start()].count("\n") + 1,
                })
                continue
            # Simple check: does the name appear elsewhere in the code?
            rest = code[:m.start()] + code[m.end():]
            if re.search(rf"\b{re.escape(name)}\b", rest) is None:
                issues.append({
                    "type": "unused-import",
                    "severity": "warning",
                    "message": f"Import '{name}' may be unused.",
                    "line": code[:m.start()].count("\n") + 1,
                })
    return issues


def _check_broad_except(code: str) -> list[dict]:
    issues: list[dict] = []
    for i, line in enumerate(code.split("\n"), 1):
        stripped = line.strip()
        if re.match(r"except\s*:", stripped) or re.match(r"except\s+Exception\s*:", stripped):
            issues.append({
                "type": "broad-except",
                "severity": "warning",
                "message": f"Broad exception handler at line {i}. Catch specific exceptions instead.",
                "line": i,
            })
    return issues


def _check_magic_numbers(code: str) -> list[dict]:
    issues: list[dict] = []
    for i, line in enumerate(code.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("def ") or stripped.startswith("class "):
            continue
        # Find standalone numeric literals (not 0, 1, -1 which are common)
        for m in re.finditer(r"(?<!\w)(\d+\.?\d*)(?!\w)", stripped):
            val = float(m.group(1))
            if val not in (0, 1, -1, 2, 100):
                issues.append({
                    "type": "magic-number",
                    "severity": "info",
                    "message": f"Magic number {m.group(1)} at line {i}. Consider extracting to a named constant.",
                    "line": i,
                })
                break  # one per line is enough
    return issues


def review_code(code: str) -> tuple[list[dict], str]:
    """Return (structured_issues, formatted_text)."""
    issues: list[dict] = []
    functions = _find_functions(code)

    for fn in functions:
        if not fn["has_docstring"]:
            issues.append({
                "type": "missing-docstring",
                "severity": "warning",
                "message": f"Missing docstring for function '{fn['name']}' (line {fn['line']}).",
                "line": fn["line"],
            })
        if not fn["has_return_type"]:
            # Check params for type hints too
            params = fn["params"]
            if params.strip() and ":" not in params:
                issues.append({
                    "type": "missing-type-hints",
                    "severity": "warning",
                    "message": f"Missing type hints for function '{fn['name']}' (line {fn['line']}).",
                    "line": fn["line"],
                })
            elif not fn["has_return_type"]:
                issues.append({
                    "type": "missing-return-type",
                    "severity": "info",
                    "message": f"Missing return type annotation for function '{fn['name']}' (line {fn['line']}).",
                    "line": fn["line"],
                })
        if fn["body_lines"] > 50:
            issues.append({
                "type": "long-function",
                "severity": "warning",
                "message": f"Function '{fn['name']}' is {fn['body_lines']} lines long (line {fn['line']}). Consider refactoring.",
                "line": fn["line"],
            })

    issues.extend(_check_imports(code))
    issues.extend(_check_broad_except(code))
    issues.extend(_check_magic_numbers(code))

    # Sort by line number
    issues.sort(key=lambda x: x.get("line", 0))

    if not issues:
        text = "No issues found. The code looks clean."
    else:
        lines = [f"Found {len(issues)} issue(s):\n"]
        for iss in issues:
            severity_marker = {"warning": "WARN", "info": "INFO", "error": "ERROR"}.get(iss["severity"], "INFO")
            lines.append(f"  [{severity_marker}] Line {iss['line']}: {iss['message']}")
        text = "\n".join(lines)

    return issues, text


def suggest_improvements(code: str) -> str:
    """Generate improvement suggestions based on the review."""
    issues, _ = review_code(code)
    functions = _find_functions(code)

    suggestions: list[str] = []
    idx = 1

    for iss in issues:
        if iss["type"] == "missing-docstring":
            suggestions.append(f"{idx}. Add a docstring to describe the purpose, parameters, and return value.")
            idx += 1
        elif iss["type"] == "missing-type-hints":
            suggestions.append(f"{idx}. Add type hints to function parameters and return types for better IDE support and documentation.")
            idx += 1
        elif iss["type"] == "long-function":
            suggestions.append(f"{idx}. Break the long function into smaller, focused helper functions with clear responsibilities.")
            idx += 1
        elif iss["type"] == "broad-except":
            suggestions.append(f"{idx}. Replace broad 'except Exception' with specific exception types (e.g., ValueError, KeyError).")
            idx += 1
        elif iss["type"] == "unused-import":
            suggestions.append(f"{idx}. Remove unused import: {iss['message']}")
            idx += 1
        elif iss["type"] == "wildcard-import":
            suggestions.append(f"{idx}. Replace wildcard import with explicit named imports.")
            idx += 1
        elif iss["type"] == "magic-number":
            suggestions.append(f"{idx}. Extract magic numbers into named constants at the module level.")
            idx += 1
        elif iss["type"] == "missing-return-type":
            suggestions.append(f"{idx}. Add return type annotation (-> type) for clearer API contracts.")
            idx += 1

    # General suggestions based on the code
    if not any("if __name__" in line for line in code.split("\n")):
        if any(fn["name"] == "main" for fn in functions):
            suggestions.append(f"{idx}. Add an 'if __name__ == \"__main__\":' guard to allow the module to be imported safely.")
            idx += 1

    if len(code.split("\n")) > 10 and not code.lstrip().startswith('"""'):
        suggestions.append(f"{idx}. Add a module-level docstring describing the purpose of this file.")
        idx += 1

    if not suggestions:
        return "The code looks good. No specific improvements suggested."

    return "Suggestions:\n" + "\n".join(suggestions)


# ---------------------------------------------------------------------------
# A2A handler
# ---------------------------------------------------------------------------

async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    code = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                code += part.content + "\n"
    code = code.strip()

    if not code:
        return [Artifact(
            name="error",
            parts=[MessagePart(type="text", content="No code provided for review.")],
        )]

    if skill_id == "suggest-improvements":
        result_text = suggest_improvements(code)
        return [Artifact(
            name="improvements",
            parts=[MessagePart(type="text", content=result_text)],
            metadata={"skill": skill_id, "lines_analyzed": len(code.split("\n"))},
        )]
    else:
        issues, result_text = review_code(code)
        return [
            Artifact(
                name="review-text",
                parts=[MessagePart(type="text", content=result_text)],
                metadata={"skill": skill_id, "issue_count": len(issues)},
            ),
            Artifact(
                name="review-data",
                parts=[MessagePart(type="data", data={"issues": issues})],
                metadata={"skill": skill_id, "issue_count": len(issues)},
            ),
        ]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_a2a_app(
    name="Python Code Reviewer",
    description="Reviews Python code for common quality issues and suggests improvements. Uses heuristic static analysis.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
