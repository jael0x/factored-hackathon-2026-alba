import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args, get_origin

from api import contract_models
from api.contract_models import IncomeCurrency
from api.domain.process.commands import CommandName
from api.domain.process.rules import ProcessRuleId
from pipeline.constants import INCOME_CURRENCY_BY_COUNTRY

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "api"
GENERATED = API / "contract_models.py"

WIRE_SETS: dict[str, frozenset[str]] = {
    name: frozenset(get_args(alias)) for name, alias in vars(contract_models).items() if get_origin(alias) is Literal
}
DOMAIN_SETS: dict[str, frozenset[str]] = {
    "CommandName": frozenset(get_args(CommandName)),
    "ProcessRuleId": frozenset(get_args(ProcessRuleId)),
}
CLOSED_SETS: dict[str, frozenset[str]] = {**WIRE_SETS, **DOMAIN_SETS}
CLOSED_VALUES: frozenset[str] = frozenset().union(*CLOSED_SETS.values())

LITERAL_OWNERS: frozenset[tuple[str, str]] = frozenset(
    {
        ("CommandName", "api/domain/process/commands.py"),
        ("ProcessRuleId", "api/domain/process/rules.py"),
        ("CustomerStatus", "api/domain/policy/engine.py"),
    }
)


@dataclass(frozen=True, order=True)
class Site:
    path: str
    line: int
    function: str | None
    value: str


@dataclass(frozen=True)
class Exemption:
    path: str
    function: str | None
    value: str


# Error labels, the keys of alba-credit-v1.yaml read where the policy file is loaded, and the source of a stated
# income fact. Each shares a spelling with a closed-set value but names something else.
EXEMPTIONS: frozenset[Exemption] = frozenset(
    {
        Exemption("api/domain/policy/engine.py", "load_policy", "policy"),
        Exemption("api/domain/policy/engine.py", "parse_rules", "rule"),
        Exemption("api/domain/policy/engine.py", "parse_status", "not_prequalified"),
        Exemption("api/domain/policy/engine.py", "parse_status", "passed"),
        Exemption("api/domain/policy/engine.py", None, "self_declared"),
    }
)


@dataclass(frozen=True)
class Scan:
    constants: tuple[tuple[str, str, str], ...]
    literal_sets: tuple[tuple[str, str], ...]
    raw_uses: tuple[Site, ...]


class RawUses(ast.NodeVisitor):
    def __init__(self, path: str, claimed: frozenset[int]) -> None:
        self.path = path
        self.claimed = claimed
        self.function: str | None = None
        self.found: list[Site] = []

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        outer = self.function
        self.function = node.name
        self.generic_visit(node)
        self.function = outer

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and node.value in CLOSED_VALUES and id(node) not in self.claimed:
            self.found.append(Site(self.path, node.lineno, self.function, node.value))


def is_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Literal"


def constant_definition(statement: ast.stmt) -> tuple[str, ast.Constant] | None:
    if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.annotation, ast.Name):
        return None
    value = statement.value
    if not isinstance(value, ast.Constant) or value.value not in CLOSED_SETS.get(statement.annotation.id, ()):
        return None
    return statement.annotation.id, value


def literal_set_name(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
        return statement.targets[0].id
    return None


def scan(path: Path) -> Scan:
    relative = path.relative_to(ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    definitions = [found for found in map(constant_definition, tree.body) if found is not None]
    named_literals = {
        id(statement.value): literal_set_name(statement)
        for statement in tree.body
        if isinstance(statement, ast.Assign) and is_literal(statement.value)
    }
    literals = [node for node in ast.walk(tree) if isinstance(node, ast.expr) and is_literal(node)]
    claimed = frozenset(
        {id(value) for _, value in definitions}
        | {id(node) for literal in literals for node in ast.walk(literal) if isinstance(node, ast.Constant)}
    )
    uses = RawUses(relative, claimed)
    uses.visit(tree)
    return Scan(
        constants=tuple((set_name, str(value.value), f"{relative}:{value.lineno}") for set_name, value in definitions),
        literal_sets=tuple((named_literals.get(id(node)) or "<inline>", relative) for node in literals),
        raw_uses=tuple(uses.found),
    )


def is_source(path: Path) -> bool:
    return path != GENERATED and not path.name.startswith("test_") and "tests" not in path.parts


def scan_api() -> tuple[Scan, ...]:
    return tuple(map(scan, sorted(filter(is_source, API.rglob("*.py")))))


def is_exempt(site: Site) -> bool:
    return Exemption(site.path, site.function, site.value) in EXEMPTIONS


def test_no_closed_set_value_is_written_raw() -> None:
    raw = sorted(site for found in scan_api() for site in found.raw_uses if not is_exempt(site))
    assert [f"{site.path}:{site.line} {site.value!r}" for site in raw] == []


def test_every_exemption_still_matches_a_use() -> None:
    used = {
        Exemption(site.path, site.function, site.value)
        for found in scan_api()
        for site in found.raw_uses
        if is_exempt(site)
    }
    assert used == EXEMPTIONS


def test_each_closed_set_value_has_at_most_one_constant() -> None:
    constants = [constant for found in scan_api() for constant in found.constants]
    counts = Counter((set_name, value) for set_name, value, _ in constants)
    repeated = sorted(site for set_name, value, site in constants if counts[(set_name, value)] > 1)
    assert repeated == []


def test_only_the_owner_declares_a_literal_set() -> None:
    declared = {literal_set for found in scan_api() for literal_set in found.literal_sets}
    assert sorted(declared) == sorted(LITERAL_OWNERS)


def test_the_load_writes_the_income_currencies_the_wire_carries() -> None:
    assert sorted(INCOME_CURRENCY_BY_COUNTRY.values()) == sorted(get_args(IncomeCurrency))
