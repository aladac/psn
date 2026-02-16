"""Code analyzer using tree-sitter for AST parsing."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Language configs for tree-sitter
LANGUAGE_CONFIGS = {
    ".py": {
        "language": "python",
        "function_query": "(function_definition name: (identifier) @name)",
        "class_query": "(class_definition name: (identifier) @name)",
        "import_query": """
            (import_statement name: (dotted_name) @name)
            (import_from_statement module_name: (dotted_name) @name)
        """,
        "call_query": "(call function: (identifier) @name)",
    },
    ".rs": {
        "language": "rust",
        "function_query": "(function_item name: (identifier) @name)",
        "class_query": """
            (struct_item name: (type_identifier) @name)
            (impl_item type: (type_identifier) @name)
        """,
        "import_query": "(use_declaration) @name",
        "call_query": "(call_expression function: (identifier) @name)",
    },
    ".js": {
        "language": "javascript",
        "function_query": """
            (function_declaration name: (identifier) @name)
            (arrow_function) @name
        """,
        "class_query": "(class_declaration name: (identifier) @name)",
        "import_query": "(import_statement) @name",
        "call_query": "(call_expression function: (identifier) @name)",
    },
    ".ts": {
        "language": "typescript",
        "function_query": """
            (function_declaration name: (identifier) @name)
            (arrow_function) @name
        """,
        "class_query": "(class_declaration name: (identifier) @name)",
        "import_query": "(import_statement) @name",
        "call_query": "(call_expression function: (identifier) @name)",
    },
    ".rb": {
        "language": "ruby",
        "function_query": "(method name: (identifier) @name)",
        "class_query": "(class name: (constant) @name)",
        "import_query": '(call method: (identifier) @name (#eq? @name "require"))',
        "call_query": "(call method: (identifier) @name)",
    },
    ".go": {
        "language": "go",
        "function_query": "(function_declaration name: (identifier) @name)",
        "class_query": "(type_declaration (type_spec name: (type_identifier) @name))",
        "import_query": "(import_spec path: (interpreted_string_literal) @name)",
        "call_query": "(call_expression function: (identifier) @name)",
    },
}


@dataclass
class Symbol:
    """A code symbol (function, class, method)."""

    name: str
    kind: str  # function, class, method, variable
    signature: str
    start_line: int
    end_line: int
    docstring: str | None = None
    parent: str | None = None  # For methods, the class name


@dataclass
class AnalysisResult:
    """Result of analyzing a source file."""

    path: str
    language: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language,
            "symbols": [
                {
                    "name": s.name,
                    "kind": s.kind,
                    "signature": s.signature,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "docstring": s.docstring,
                    "parent": s.parent,
                }
                for s in self.symbols
            ],
            "imports": self.imports,
            "calls": self.calls,
            "errors": self.errors,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def analyze_python(content: str, path: str) -> AnalysisResult:
    """Analyze Python code using ast module (fallback without tree-sitter)."""
    import ast

    result = AnalysisResult(path=path, language="python")

    try:
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get signature
                args = []
                for arg in node.args.args:
                    arg_str = arg.arg
                    if arg.annotation:
                        arg_str += f": {ast.unparse(arg.annotation)}"
                    args.append(arg_str)

                returns = ""
                if node.returns:
                    returns = f" -> {ast.unparse(node.returns)}"

                signature = f"def {node.name}({', '.join(args)}){returns}"

                # Get docstring
                docstring = ast.get_docstring(node)

                # Determine if method (has self/cls first arg)
                parent = None
                kind = "function"
                if args and args[0] in ("self", "cls"):
                    kind = "method"
                    # Find parent class
                    for parent_node in ast.walk(tree):
                        if isinstance(parent_node, ast.ClassDef):
                            if node in ast.walk(parent_node):
                                parent = parent_node.name
                                break

                result.symbols.append(
                    Symbol(
                        name=node.name,
                        kind=kind,
                        signature=signature,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=docstring,
                        parent=parent,
                    )
                )

            elif isinstance(node, ast.ClassDef):
                # Get base classes
                bases = [ast.unparse(b) for b in node.bases]
                signature = f"class {node.name}"
                if bases:
                    signature += f"({', '.join(bases)})"

                docstring = ast.get_docstring(node)

                result.symbols.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        signature=signature,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=docstring,
                    )
                )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    result.imports.append(f"{module}.{alias.name}")

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    result.calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    result.calls.append(node.func.attr)

    except SyntaxError as e:
        result.errors.append(f"Syntax error: {e}")
    except Exception as e:
        result.errors.append(f"Analysis error: {e}")

    # Dedupe calls
    result.calls = list(set(result.calls))

    return result


def analyze_file(path: Path) -> AnalysisResult | None:
    """Analyze a source file and extract symbols, imports, calls."""
    if not path.exists() or not path.is_file():
        return None

    ext = path.suffix.lower()

    # Currently only Python has full analysis
    if ext == ".py":
        content = path.read_text(errors="ignore")
        return analyze_python(content, str(path))

    # For other languages, return basic info (tree-sitter can be added later)
    if ext in LANGUAGE_CONFIGS:
        return AnalysisResult(
            path=str(path),
            language=LANGUAGE_CONFIGS[ext]["language"],
            errors=["Full analysis not yet implemented for this language"],
        )

    return None


def generate_symbol_id(path: str, symbol_name: str, kind: str) -> str:
    """Generate a unique ID for a symbol."""
    return hashlib.md5(f"{path}:{kind}:{symbol_name}".encode()).hexdigest()
