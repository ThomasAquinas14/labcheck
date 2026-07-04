from __future__ import annotations

from dataclasses import dataclass
import ast
import builtins
from pathlib import Path
import re

from .models import NotebookDocument

READ_PATTERNS = [
    re.compile(r"pd\.read_(?:csv|parquet|json|excel)\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"(?<![\w.])open\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*['\"]r[bt]?['\"]\s*)?\)"),
    re.compile(r"np\.load\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"torch\.load\(\s*['\"]([^'\"]+)['\"]"),
]

WRITE_PATTERNS = [
    re.compile(r"to_(?:csv|parquet|json|excel)\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"savefig\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"(?<![\w.])open\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"](?:w|wb|wt|a|ab|at|x|xb|xt)['\"]"),
    re.compile(r"torch\.save\([^,]+,\s*['\"]([^'\"]+)['\"]"),
]

RANDOM_USAGE_PATTERNS = [
    re.compile(r"\brandom\."),
    re.compile(r"\bnp\.random\."),
    re.compile(r"\bnumpy\.random\."),
    re.compile(r"\btorch\.(?:rand|randn|randint|bernoulli|multinomial)\b"),
]

SEED_PATTERNS = [
    re.compile(r"\brandom\.seed\("),
    re.compile(r"\bnp\.random\.seed\("),
    re.compile(r"\bnumpy\.random\.seed\("),
    re.compile(r"\btorch\.manual_seed\("),
]

RANDOM_USAGE_CALL_PREFIXES = (
    "random.",
    "np.random.",
    "numpy.random.",
)

TORCH_RANDOM_CALLS = {
    "torch.bernoulli",
    "torch.multinomial",
    "torch.rand",
    "torch.randn",
    "torch.randint",
}

SEED_CALL_NAMES = {
    "random.seed",
    "np.random.seed",
    "numpy.random.seed",
    "torch.manual_seed",
}

README_COMMAND_PATTERNS = [
    re.compile(r"python(?:3)?\s+([^\s`]+\.py)\b"),
    re.compile(r"jupyter\s+notebook\s+([^\s`]+\.ipynb)\b"),
    re.compile(r"bash\s+([^\s`]+\.sh)\b"),
]
README_COMMAND_START_PATTERN = re.compile(
    r"^(?:python(?:3)?\s+[^\s`]+\.py\b|jupyter\s+notebook\s+[^\s`]+\.ipynb\b|bash\s+[^\s`]+\.sh\b)"
)
README_RUN_INSTRUCTION_PATTERN = re.compile(
    r"^(?:"
    r"python(?:3)?\s+(?:-m\s+[\w.]+|[^\s`]+\.py)\b|"
    r"jupyter\s+(?:notebook|lab)(?:\s+[^\s`]+\.ipynb\b)?|"
    r"pip\s+install\b|"
    r"python(?:3)?\s+-m\s+pip\s+install\b|"
    r"conda\s+env\s+create\b|"
    r"poetry\s+(?:install|run)\b|"
    r"uv\s+(?:sync|run)\b|"
    r"make(?:\s+\w[\w.-]*)?\b|"
    r"bash\s+[^\s`]+\.sh\b|"
    r"pytest\b|"
    r"snakemake\b|"
    r"dvc\s+repro\b"
    r")"
)

STRING_ASSIGNMENT_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
READ_VARIABLE_PATTERNS = [
    re.compile(r"pd\.read_(?:csv|parquet|json|excel)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"(?<![\w.])open\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:,\s*['\"]r[bt]?['\"]\s*)?\)"),
    re.compile(r"np\.load\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"torch\.load\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
]

WRITE_VARIABLE_PATTERNS = [
    re.compile(r"to_(?:csv|parquet|json|excel)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"savefig\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"(?<![\w.])open\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*['\"](?:w|wb|wt|a|ab|at|x|xb|xt)['\"]"),
    re.compile(r"torch\.save\([^,]+,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
]


@dataclass(slots=True)
class SourceArtifact:
    path: Path
    kind: str
    content: str
    reads: list[str]
    writes: list[str]
    uses_randomness: bool
    seeds_randomness: bool


@dataclass(slots=True)
class ReadmeReference:
    command: str
    referenced_path: str


@dataclass(slots=True)
class HiddenStateIssue:
    cell_index: int
    names: list[str]


def _normalize_source(text: str) -> str:
    return text.replace("\\\r\n", "").replace("\\\n", "")


def extract_paths(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    normalized = _normalize_source(text)
    matches: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(normalized):
            matches.append(match.group(1))
    return matches


def _extract_string_assignments(text: str) -> dict[str, str]:
    normalized = _normalize_source(text)
    return {match.group(1): match.group(2) for match in STRING_ASSIGNMENT_PATTERN.finditer(normalized)}


def _extract_variable_paths(text: str, patterns: list[re.Pattern[str]], assignments: dict[str, str]) -> list[str]:
    normalized = _normalize_source(text)
    matches: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(normalized):
            variable_name = match.group(1)
            if variable_name in assignments:
                matches.append(assignments[variable_name])
    return matches


def analyze_notebook(notebook: NotebookDocument) -> SourceArtifact:
    content = "\n\n".join(notebook.sources)
    assignments = _extract_string_assignments(content)
    return SourceArtifact(
        path=notebook.path,
        kind="notebook",
        content=content,
        reads=extract_paths(content, READ_PATTERNS) + _extract_variable_paths(content, READ_VARIABLE_PATTERNS, assignments),
        writes=extract_paths(content, WRITE_PATTERNS) + _extract_variable_paths(content, WRITE_VARIABLE_PATTERNS, assignments),
        uses_randomness=any(pattern.search(content) for pattern in RANDOM_USAGE_PATTERNS),
        seeds_randomness=any(pattern.search(content) for pattern in SEED_PATTERNS),
    )


def analyze_python_file(path: Path) -> SourceArtifact:
    content = path.read_text(encoding="utf-8")
    assignments = _extract_string_assignments(content)
    uses_randomness, seeds_randomness = _python_randomness_flags(content)
    return SourceArtifact(
        path=path,
        kind="python",
        content=content,
        reads=extract_paths(content, READ_PATTERNS) + _extract_variable_paths(content, READ_VARIABLE_PATTERNS, assignments),
        writes=extract_paths(content, WRITE_PATTERNS) + _extract_variable_paths(content, WRITE_VARIABLE_PATTERNS, assignments),
        uses_randomness=uses_randomness,
        seeds_randomness=seeds_randomness,
    )


def _python_randomness_flags(content: str) -> tuple[bool, bool]:
    """Detect actual randomness calls in Python code while ignoring comments and strings."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return (
            any(pattern.search(content) for pattern in RANDOM_USAGE_PATTERNS),
            any(pattern.search(content) for pattern in SEED_PATTERNS),
        )

    uses_randomness = False
    seeds_randomness = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        if call_name in SEED_CALL_NAMES:
            seeds_randomness = True
        if call_name in TORCH_RANDOM_CALLS or any(
            call_name.startswith(prefix) for prefix in RANDOM_USAGE_CALL_PREFIXES
        ):
            uses_randomness = True
    return uses_randomness, seeds_randomness


def _call_name(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def analyze_readme(path: Path) -> list[ReadmeReference]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    references: list[ReadmeReference] = []
    for line in _readme_command_candidate_lines(content):
        for pattern in README_COMMAND_PATTERNS:
            for match in pattern.finditer(line):
                references.append(
                    ReadmeReference(
                        command=match.group(0),
                        referenced_path=match.group(1),
                    )
                )
    return references


def readme_has_run_instructions(path: Path) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return any(README_RUN_INSTRUCTION_PATTERN.match(line) for line in _readme_general_candidate_lines(content))


def _readme_command_candidate_lines(content: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not stripped:
            continue

        candidate = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
        candidate = re.sub(r"^(?:[$>]\s*)", "", candidate)
        if in_fence or README_COMMAND_START_PATTERN.match(candidate):
            lines.append(candidate)
    return lines


def _readme_general_candidate_lines(content: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not stripped:
            continue

        candidate = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
        candidate = re.sub(r"^(?:[$>]\s*)", "", candidate)
        if in_fence or README_RUN_INSTRUCTION_PATTERN.match(candidate):
            lines.append(candidate)
    return lines


def _assigned_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.split(".")[0])
    return names


def _loaded_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return names


class _LoadCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self._locals_stack: list[set[str]] = []

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if any(node.id in local_names for local_names in reversed(self._locals_stack)):
                return
            self.names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._visit_arguments(node.args)
        if node.returns is not None:
            self.visit(node.returns)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_arguments(node.args)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension([node.key, node.value], node.generators)

    def _visit_arguments(self, node: ast.arguments) -> None:
        for default in node.defaults:
            self.visit(default)
        for default in node.kw_defaults:
            if default is not None:
                self.visit(default)
        for arg in [*node.posonlyargs, *node.args, *node.kwonlyargs]:
            if arg.annotation is not None:
                self.visit(arg.annotation)
        if node.vararg and node.vararg.annotation is not None:
            self.visit(node.vararg.annotation)
        if node.kwarg and node.kwarg.annotation is not None:
            self.visit(node.kwarg.annotation)

    def _visit_comprehension(self, value_nodes: list[ast.AST], generators: list[ast.comprehension]) -> None:
        local_names: set[str] = set()
        self._locals_stack.append(local_names)
        try:
            for generator in generators:
                self.visit(generator.iter)
                local_names.update(_names_assigned_in_target(generator.target))
                for condition in generator.ifs:
                    self.visit(condition)
            for value_node in value_nodes:
                self.visit(value_node)
        finally:
            self._locals_stack.pop()


def _loads_in_node(node: ast.AST) -> set[str]:
    collector = _LoadCollector()
    collector.visit(node)
    return collector.names


def _names_assigned_in_target(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
    return names


def _names_assigned_in_pattern(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.MatchAs) and child.name:
            names.add(child.name)
        elif isinstance(child, ast.MatchStar) and child.name:
            names.add(child.name)
    return names


def _analyze_statements(statements: list[ast.stmt], known_names: set[str]) -> tuple[set[str], set[str]]:
    current_known = set(known_names)
    missing: set[str] = set()

    for statement in statements:
        statement_missing, statement_assigned = _analyze_statement(statement, current_known)
        missing.update(name for name in statement_missing if name not in current_known)
        current_known.update(statement_assigned)

    return missing, current_known - known_names


def _analyze_statement(statement: ast.stmt, known_names: set[str]) -> tuple[set[str], set[str]]:
    if isinstance(statement, ast.Import):
        assigned = {alias.asname or alias.name.split(".")[0] for alias in statement.names}
        return set(), assigned

    if isinstance(statement, ast.ImportFrom):
        assigned = {alias.asname or alias.name for alias in statement.names}
        return set(), assigned

    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _loads_in_node(statement), {statement.name}

    if isinstance(statement, ast.ClassDef):
        missing = set()
        for decorator in statement.decorator_list:
            missing.update(_loads_in_node(decorator))
        for base in statement.bases:
            missing.update(_loads_in_node(base))
        for keyword in statement.keywords:
            missing.update(_loads_in_node(keyword.value))
        class_missing, _ = _analyze_statements(statement.body, set(known_names))
        missing.update(class_missing)
        return missing, {statement.name}

    if isinstance(statement, ast.Assign):
        missing = _loads_in_node(statement.value)
        assigned = set()
        for target in statement.targets:
            assigned.update(_names_assigned_in_target(target))
        return missing, assigned

    if isinstance(statement, ast.AnnAssign):
        missing = _loads_in_node(statement.annotation)
        if statement.value is not None:
            missing.update(_loads_in_node(statement.value))
            return missing, _names_assigned_in_target(statement.target)
        return missing, set()

    if isinstance(statement, ast.AugAssign):
        missing = _loads_in_node(statement.target) | _loads_in_node(statement.value)
        return missing, _names_assigned_in_target(statement.target)

    if isinstance(statement, ast.For | ast.AsyncFor):
        missing = _loads_in_node(statement.iter)
        target_names = _names_assigned_in_target(statement.target)
        body_missing, body_assigned = _analyze_statements(statement.body, known_names | target_names)
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, known_names | target_names)
        return missing | body_missing | orelse_missing, target_names | body_assigned | orelse_assigned

    if isinstance(statement, ast.While):
        missing = _loads_in_node(statement.test)
        body_missing, body_assigned = _analyze_statements(statement.body, set(known_names))
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, set(known_names))
        return missing | body_missing | orelse_missing, body_assigned | orelse_assigned

    if isinstance(statement, ast.If):
        missing = _loads_in_node(statement.test)
        body_missing, body_assigned = _analyze_statements(statement.body, set(known_names))
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, set(known_names))
        return missing | body_missing | orelse_missing, body_assigned | orelse_assigned

    if isinstance(statement, ast.With | ast.AsyncWith):
        missing = set()
        assigned = set()
        current_known = set(known_names)
        for item in statement.items:
            missing.update(_loads_in_node(item.context_expr))
            if item.optional_vars is not None:
                names = _names_assigned_in_target(item.optional_vars)
                assigned.update(names)
                current_known.update(names)
        body_missing, body_assigned = _analyze_statements(statement.body, current_known)
        return missing | body_missing, assigned | body_assigned

    if isinstance(statement, ast.Try):
        body_missing, body_assigned = _analyze_statements(statement.body, set(known_names))
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, set(known_names))
        final_missing, final_assigned = _analyze_statements(statement.finalbody, set(known_names))
        missing = body_missing | orelse_missing | final_missing
        assigned = body_assigned | orelse_assigned | final_assigned
        for handler in statement.handlers:
            handler_known = set(known_names)
            if handler.type is not None:
                missing.update(_loads_in_node(handler.type))
            if handler.name:
                handler_known.add(handler.name)
                assigned.add(handler.name)
            handler_missing, handler_assigned = _analyze_statements(handler.body, handler_known)
            missing.update(handler_missing)
            assigned.update(handler_assigned)
        return missing, assigned

    if isinstance(statement, ast.Match):
        missing = _loads_in_node(statement.subject)
        assigned = set()
        for case in statement.cases:
            case_known = set(known_names)
            pattern_names = _names_assigned_in_pattern(case.pattern)
            case_known.update(pattern_names)
            assigned.update(pattern_names)
            if case.guard is not None:
                missing.update(_loads_in_node(case.guard))
            case_missing, case_assigned = _analyze_statements(case.body, case_known)
            missing.update(case_missing)
            assigned.update(case_assigned)
        return missing, assigned

    return _loads_in_node(statement), set()


def find_hidden_state_issues(notebook: NotebookDocument) -> list[HiddenStateIssue]:
    known_names = set(dir(builtins))
    issues: list[HiddenStateIssue] = []

    for index, source in enumerate(notebook.sources, start=1):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        missing, assigned = _analyze_statements(tree.body, known_names)
        missing = sorted(name for name in missing if name not in known_names)
        if missing:
            issues.append(HiddenStateIssue(cell_index=index, names=missing))
        known_names.update(assigned)
    return issues
