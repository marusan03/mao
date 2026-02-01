#!/usr/bin/env python3
"""
Custom linter to detect mutable default arguments pattern.

This catches patterns that ruff doesn't, like:
  def foo(x: list | None = None):
      if x is None:
          x = []

Usage: python scripts/check_mutable_defaults.py [files...]
"""
import ast
import sys
from pathlib import Path
from typing import Sequence


class MutableDefaultChecker(ast.NodeVisitor):
    """Check for mutable default arguments including None patterns"""

    def __init__(self, filename: str):
        self.filename = filename
        self.errors: list[str] = []
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for mutable default patterns"""
        self.current_function = node.name

        for arg in node.args.args + node.args.kwonlyargs:
            if not arg.annotation:
                continue

            # Check if annotation contains list, dict, set with Optional/None
            annotation_str = ast.unparse(arg.annotation)

            # Patterns to detect: list | None, Optional[list], dict | None, etc.
            mutable_types = ["list", "dict", "set", "List", "Dict", "Set"]
            has_none = "None" in annotation_str or "Optional" in annotation_str

            if has_none and any(mt in annotation_str for mt in mutable_types):
                # Check if there's a default of None
                defaults_start = len(node.args.args) - len(node.args.defaults)
                arg_index = node.args.args.index(arg) if arg in node.args.args else -1

                if arg_index >= defaults_start:
                    default_index = arg_index - defaults_start
                    if default_index < len(node.args.defaults):
                        default = node.args.defaults[default_index]
                        if isinstance(default, ast.Constant) and default.value is None:
                            self.errors.append(
                                f"{self.filename}:{node.lineno}:{node.col_offset}: "
                                f"Mutable default pattern detected in function '{node.name}', "
                                f"parameter '{arg.arg}': {annotation_str}. "
                                f"Use Pydantic Field(default_factory=...) or require explicit argument."
                            )

        self.generic_visit(node)
        self.current_function = None


def check_file(filepath: Path) -> list[str]:
    """Check a single file for mutable default patterns"""
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        checker = MutableDefaultChecker(str(filepath))
        checker.visit(tree)
        return checker.errors

    except SyntaxError as e:
        return [f"{filepath}:{e.lineno}: Syntax error: {e.msg}"]
    except Exception as e:
        return [f"{filepath}: Error: {e}"]


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point"""
    argv = argv if argv is not None else sys.argv[1:]

    if not argv:
        print("Usage: check_mutable_defaults.py [files...]", file=sys.stderr)
        return 1

    all_errors: list[str] = []

    for filepath in argv:
        path = Path(filepath)
        if path.suffix == ".py":
            errors = check_file(path)
            all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        print(
            f"\n❌ Found {len(all_errors)} mutable default pattern(s).",
            file=sys.stderr,
        )
        print("See docs/CODING_STANDARDS.md for correct patterns.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
