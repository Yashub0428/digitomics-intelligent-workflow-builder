from typing import Any, TypeVar

from pydantic import BaseModel

from app.schemas.workflow import (
    Action,
    Ambiguity,
    CollectedValue,
    Condition,
    FieldUpdate,
    Recipient,
    WorkflowState,
    WorkflowStatePatch,
)

T = TypeVar("T", bound=BaseModel)

LIST_FIELDS = {
    "conditions": Condition,
    "actions": Action,
    "recipients": Recipient,
}


def merge_models(base: T, incoming: T) -> T:
    """Deep-merge two models, keeping unset incoming fields from base."""
    merged = _deep_merge_dict(base.model_dump(), incoming.model_dump(exclude_unset=True))
    return type(base).model_validate(merged)


def _deep_merge_dict(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in incoming.items():
        existing = out.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            out[key] = _deep_merge_dict(existing, value)
        else:
            out[key] = value
    return out


def merge_identified_list(
    existing: list[T],
    incoming: list[T],
    *,
    replace: bool,
) -> list[T]:
    if replace:
        return [item.model_copy(deep=True) for item in incoming]

    by_id = {item.id: item for item in existing}
    order = [item.id for item in existing]
    for item in incoming:
        if item.id in by_id:
            by_id[item.id] = merge_models(by_id[item.id], item)
        else:
            by_id[item.id] = item
            order.append(item.id)
    return [by_id[item_id] for item_id in order]


def merge_ambiguities(existing: list[Ambiguity], incoming: list[Ambiguity]) -> list[Ambiguity]:
    by_id = {item.id: item for item in existing}
    order = [item.id for item in existing]
    for item in incoming:
        if item.id in by_id:
            by_id[item.id] = merge_models(by_id[item.id], item)
        else:
            by_id[item.id] = item
            order.append(item.id)
    return [by_id[item_id] for item_id in order]


def parse_path(path: str) -> list[str | int]:
    parts: list[str | int] = []
    for raw in path.split("."):
        if raw.isdigit():
            parts.append(int(raw))
        else:
            parts.append(raw)
    return parts


def set_path(state: WorkflowState, path: str, value: Any) -> WorkflowState:
    data = state.model_dump()
    _set_in_mapping(data, parse_path(path), value)
    return WorkflowState.model_validate(data)


def _set_in_mapping(target: dict[str, Any], parts: list[str | int], value: Any) -> None:
    head, *rest = parts
    if not rest:
        if not isinstance(head, str):
            raise ValueError("Top-level path segments must be field names")
        target[head] = value
        return

    if not isinstance(head, str):
        raise ValueError("Expected a field name in path")

    nxt = rest[0]
    if isinstance(nxt, int):
        items = list(target.get(head) or [])
        while len(items) <= nxt:
            items.append(_blank_list_item(head))
        if len(rest) == 1:
            items[nxt] = value
        else:
            row = items[nxt]
            if not isinstance(row, dict):
                row = _blank_list_item(head)
            _set_in_mapping(row, rest[1:], value)
            items[nxt] = row
        target[head] = items
        return

    child = target.get(head)
    if child is None:
        child = {}
        target[head] = child
    if not isinstance(child, dict):
        raise ValueError(f"Cannot descend into {head!r}")
    _set_in_mapping(child, rest, value)


def _blank_list_item(field: str) -> dict[str, Any]:
    model = LIST_FIELDS.get(field)
    if model is None:
        raise ValueError(f"Unknown list field {field!r}")
    return model().model_dump()


def apply_field_updates(state: WorkflowState, updates: list[FieldUpdate]) -> WorkflowState:
    for update in updates:
        state = set_path(state, update.path, update.value)
    return state


def record_collected(
    state: WorkflowState,
    path: str,
    value: Any,
    utterance_id: str | None,
) -> None:
    if value is None:
        return
    state.collected[path] = CollectedValue(path=path, value=value, utterance_id=utterance_id)


def collect_from_patch(
    state: WorkflowState,
    patch: WorkflowStatePatch,
    utterance_id: str | None,
) -> None:
    dumped = patch.model_dump(exclude_unset=True, exclude={
        "field_updates",
        "resolve_ambiguities",
        "replace_conditions",
        "replace_actions",
        "replace_recipients",
        "remove_condition_ids",
        "remove_action_ids",
        "remove_recipient_ids",
        "ambiguities",
    })
    for path, value in _flatten(dumped):
        record_collected(state, path, value, utterance_id)
    for update in patch.field_updates:
        record_collected(state, update.path, update.value, utterance_id)


def _flatten(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten(value, path))
        return rows
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            path = f"{prefix}.{index}" if prefix else str(index)
            rows.extend(_flatten(value, path))
        return rows
    if payload is None or payload == {} or payload == []:
        return rows
    rows.append((prefix, payload))
    return rows
