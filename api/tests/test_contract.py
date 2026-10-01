import hashlib
from pathlib import Path
from typing import Union, get_args, get_origin

import yaml
from fastapi.routing import APIRoute
from pydantic import ValidationError

from api import contract_models
from api.contract_models import Certificate, CloseCaseRequest
from api.main import app

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "api-spec" / "openapi.yaml"
MODELS_PATH = ROOT / "api" / "contract_models.py"
SCHEMA_PATH = ROOT / "web" / "src" / "api" / "schema.d.ts"

EXPECTED_PATHS = {
    "/health",
    "/ready",
    "/config",
    "/customers/search",
    "/session/code",
    "/session",
    "/agents/search",
    "/agent/session/code",
    "/agent/session",
    "/me",
    "/agent/me",
    "/products",
    "/messages",
    "/case/{process_id}",
    "/agent/queue",
    "/agent/case/{process_id}",
    "/agent/case/{process_id}/trace",
    "/agent/case/{process_id}/close",
}


def spec_text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def spec_sha256() -> str:
    return hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()


def load_spec() -> dict:
    loaded = yaml.safe_load(spec_text())
    assert isinstance(loaded, dict)
    return loaded


def test_spec_paths_are_the_wire_surface() -> None:
    assert set(load_spec()["paths"]) == EXPECTED_PATHS


def test_generated_files_match_the_spec_hash() -> None:
    digest = spec_sha256()
    assert MODELS_PATH.read_text(encoding="utf-8").startswith(f"# spec-sha256: {digest}\n")
    assert SCHEMA_PATH.read_text(encoding="utf-8").startswith(f"// spec-sha256: {digest}\n")


def test_typescript_schema_names_every_operation() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    for path, item in load_spec()["paths"].items():
        assert f'"{path}"' in schema
        for method, operation in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            assert operation["operationId"] in schema


def test_live_routes_are_declared_on_the_spec() -> None:
    paths = load_spec()["paths"]
    live = [route for route in app.routes if isinstance(route, APIRoute)]
    assert live
    for route in live:
        assert route.path in paths
        declared: set[str] = set()
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            operation = paths[route.path][method.lower()]
            for body in operation["responses"].values():
                schema = body.get("content", {}).get("application/json", {}).get("schema", {})
                ref = schema.get("$ref")
                if isinstance(ref, str):
                    declared.add(ref.rsplit("/", 1)[-1])
        assert _model_modules(route.response_model) == {"api.contract_models"}
        assert _model_names(route.response_model) == declared


def test_every_spec_enum_has_a_named_alias() -> None:
    enums = {
        name: schema["enum"]
        for name, schema in load_spec()["components"]["schemas"].items()
        if schema.get("type") == "string" and schema.get("enum")
    }
    assert enums
    for name, values in enums.items():
        assert list(get_args(getattr(contract_models, name))) == values


def test_close_body_is_only_the_two_outcomes() -> None:
    closed = CloseCaseRequest.model_validate({"outcome": "PREQUALIFIED"})
    assert closed.outcome == "PREQUALIFIED"
    try:
        CloseCaseRequest.model_validate({"outcome": "REFER"})
    except ValidationError:
        rejected = True
    else:
        rejected = False
    assert rejected
    try:
        CloseCaseRequest.model_validate({"outcome": "NOT_PREQUALIFIED", "text": "hola"})
    except ValidationError:
        extra_rejected = True
    else:
        extra_rejected = False
    assert extra_rejected


def test_certificate_income_fields_are_null_when_the_fact_is_missing() -> None:
    certificate = Certificate.model_validate(
        {
            "locale": "es",
            "outcome": "PREQUALIFIED",
            "body": "Juan precalifica.",
            "product": "credit_card",
            "income_local": None,
            "income_currency": None,
            "income_usd": None,
            "as_of": None,
        }
    )
    assert certificate.income_local is None
    assert certificate.income_currency is None
    assert certificate.income_usd is None
    assert certificate.as_of is None
    dumped = certificate.model_dump()
    assert "credit_limit" not in dumped
    assert "interest_rate" not in dumped


def _model_names(model: object) -> set[str]:
    origin = get_origin(model)
    if origin is Union or (origin is not None and getattr(origin, "__name__", "") == "UnionType"):
        return set().union(*(_model_names(arg) for arg in get_args(model)))
    name = getattr(model, "__name__", "")
    return {name} if isinstance(name, str) and name else set()


def _model_modules(model: object) -> set[str]:
    origin = get_origin(model)
    if origin is Union:
        return set().union(*(_model_modules(arg) for arg in get_args(model)))
    if origin is not None and getattr(origin, "__name__", "") == "UnionType":
        return set().union(*(_model_modules(arg) for arg in get_args(model)))
    module = getattr(model, "__module__", "")
    return {module}
