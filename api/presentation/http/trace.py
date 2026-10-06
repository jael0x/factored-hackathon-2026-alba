from collections.abc import Mapping
from types import MappingProxyType
from typing import get_args
from uuid import UUID

from pydantic import BaseModel, ValidationError

from api.application.consultants.cases import TraceRecord
from api.contract_models import CaseTrace, EventName
from api.domain.closed_sets import parse_member
from api.domain.process.stored_events import EVENT_NAMES
from api.presentation.http.wire_numbers import wire_json


def event_name_of(model: type[BaseModel]) -> EventName:
    [name] = get_args(model.model_fields["event_name"].annotation)
    return parse_member(name, EVENT_NAMES, "event_name")


# The generated trace is a plain union, so the model for each event comes from its event_name, read off the union.
def trace_models() -> Mapping[EventName, type[BaseModel]]:
    [union] = get_args(CaseTrace.model_fields["events"].annotation)
    return MappingProxyType({event_name_of(model): model for model in get_args(union)})


TRACE_MODELS = trace_models()


def wire_trace_event(record: TraceRecord) -> BaseModel:
    columns = {
        "id": record.event_id,
        "event_name": record.event_name,
        "created_at": record.created_at,
        "actor": record.actor,
        "process_id": record.process_id,
        "process_state": record.process_state,
        "caused_by_event_id": record.caused_by_event_id,
    }
    payload = wire_json(record.payload)
    if not isinstance(payload, dict) or columns.keys() & payload.keys():
        raise ValueError(f"event {record.event_id} has a payload the trace cannot carry")
    model = TRACE_MODELS[record.event_name]
    try:
        return model.model_validate({**columns, **payload})
    except ValidationError as invalid:
        raise ValueError(f"event {record.event_id} does not match {model.__name__}") from invalid


def wire_trace(process_id: UUID, records: list[TraceRecord]) -> CaseTrace:
    return CaseTrace.model_validate({"process_id": process_id, "events": [wire_trace_event(r) for r in records]})
