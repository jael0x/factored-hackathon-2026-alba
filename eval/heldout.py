import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from api.contract_models import IncomeCurrency, Intent, Locale, ProductKey, TurnLanguage
from api.domain.closed_sets import parse_member
from api.domain.locale import LOCALES
from api.domain.process.stored_events import (
    INCOME_CURRENCIES,
    INTENTS,
    PRODUCT_KEYS,
    TURN_LANGUAGES,
    parse_amount,
    require_bool,
)

HELDOUT = Path(__file__).resolve().parent / "heldout" / "v1.jsonl"
# Frozen on Oct 5, 2026, before any prompt tuning (IMPLEMENTATION.md M4): a changed set is a new version.
HELDOUT_SHA256 = "7e1db26feadfc519f06a9b6e77befdaf0e2f0bb1bd96918b866f006008c77ac7"


@dataclass(frozen=True)
class CaseContext:
    stored_product: ProductKey | None
    income_requested: bool
    asked: int


@dataclass(frozen=True)
class Expected:
    intent: Intent
    product: ProductKey | None
    language: TurnLanguage
    declared_income_amount: Decimal | None
    declared_income_currency: IncomeCurrency | None


@dataclass(frozen=True)
class HeldOutItem:
    item_id: str
    slice: str
    locale: Locale
    text: str
    context: CaseContext
    expected: Expected


class ChangedHeldOutSet(Exception):
    pass


def load_heldout(path: Path = HELDOUT, sha256: str = HELDOUT_SHA256) -> list[HeldOutItem]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ChangedHeldOutSet(f"{path.name} no longer matches its frozen sha256 {sha256}")
    return [item_of(json.loads(line, parse_float=Decimal)) for line in raw.decode().splitlines() if line]


def item_of(row: dict[str, object]) -> HeldOutItem:
    context, expected = row["context"], row["expected"]
    if not isinstance(context, dict) or not isinstance(expected, dict):
        raise TypeError(f"item {row.get('id')} needs a context and an expected object")
    return HeldOutItem(
        item_id=str(row["id"]),
        slice=str(row["slice"]),
        locale=parse_member(row["locale"], LOCALES, "locale"),
        text=str(row["text"]),
        context=CaseContext(
            stored_product=optional_product(context["stored_product"]),
            income_requested=require_bool(context["income_requested"], "income_requested"),
            asked=int(str(context["asked"])),
        ),
        expected=Expected(
            intent=parse_member(expected["intent"], INTENTS, "intent"),
            product=optional_product(expected["product"]),
            language=parse_member(expected["language"], TURN_LANGUAGES, "language"),
            declared_income_amount=parse_amount(expected["declared_income_amount"]),
            declared_income_currency=None
            if expected["declared_income_currency"] is None
            else parse_member(expected["declared_income_currency"], INCOME_CURRENCIES, "currency"),
        ),
    )


def optional_product(value: object) -> ProductKey | None:
    return None if value is None else parse_member(value, PRODUCT_KEYS, "product")
