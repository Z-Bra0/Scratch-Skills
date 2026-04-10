"""Scratch-json normalization helpers."""

from __future__ import annotations

from typing import Any

from .config import JsonDict, display_value_text


def _make_state(
    block_type: str,
    *,
    fields: JsonDict | None = None,
    inputs: JsonDict | None = None,
    next_state: JsonDict | None = None,
) -> JsonDict:
    return {
        "type": block_type,
        "fields": fields or {},
        "inputs": inputs or {},
        "next": {"block": next_state} if next_state is not None else {},
    }


def _field_value(state: JsonDict) -> str:
    if not state:
        return "..."
    fields = state.get("fields", {})
    if fields:
        return display_value_text(next(iter(fields.values())))
    return state.get("type", "").split("_")[-1]


def _looks_like_scratch_json(data: list[Any]) -> bool:
    if not data or not all(isinstance(item, dict) for item in data):
        return False
    item_types = {item.get("type") for item in data}
    return item_types <= {"script", "variable", "list"}


def _primitive_state_from_scratch_value(value: Any) -> JsonDict:
    if isinstance(value, dict):
        ref_type = value.get("type")
        name = value.get("name", "")
        if ref_type == "variable":
            return _make_state("data_variable", fields={"VARIABLE": name})
        if ref_type == "list":
            return _make_state("data_listcontents", fields={"LIST": name})
        if ref_type == "broadcast":
            return _make_state("event_broadcast_menu", fields={"BROADCAST_OPTION": name})

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        block_type = "math_whole_number" if isinstance(value, int) and value >= 0 else "math_number"
        return _make_state(block_type, fields={"NUM": str(value)})

    text = "null" if value is None else str(value)
    return _make_state("text", fields={"TEXT": text})


def _scratch_block_to_state(block: JsonDict) -> JsonDict:
    state = _make_state(block.get("opcode", "unknown"))

    for index, value in enumerate(block.get("params", []), start=1):
        key = f"INPUT{index}"
        if isinstance(value, dict) and "opcode" in value:
            state["inputs"][key] = {"block": _scratch_block_to_state(value)}
        else:
            state["inputs"][key] = {"shadow": _primitive_state_from_scratch_value(value)}

    for index, branch in enumerate(block.get("blocks", []), start=1):
        key = "SUBSTACK" if index == 1 else f"SUBSTACK{index}"
        if branch:
            state["inputs"][key] = {"block": _scratch_sequence_to_state(branch)}
        else:
            state["inputs"][key] = {}

    return state


def _scratch_sequence_to_state(blocks: list[JsonDict]) -> JsonDict:
    first_state: JsonDict | None = None
    previous_state: JsonDict | None = None

    for block in blocks:
        current_state = _scratch_block_to_state(block)
        if first_state is None:
            first_state = current_state
        if previous_state is not None:
            previous_state["next"] = {"block": current_state}
        previous_state = current_state

    if first_state is None:
        return _make_state("text", fields={"TEXT": "[empty]"})
    return first_state


def _top_level_object_to_render_state(item: JsonDict) -> JsonDict | None:
    item_type = item.get("type")
    if item_type == "script" and isinstance(item.get("blocks"), list):
        return _scratch_sequence_to_state(item["blocks"])
    if item_type == "variable" and isinstance(item.get("name"), str):
        return _make_state(
            "scratch_variable_monitor",
            fields={
                "TARGET": "" if item.get("target") is None else str(item.get("target")),
                "VARIABLE": item["name"],
                "VALUE": "" if item.get("value") is None else str(item.get("value")),
            },
        )
    if item_type == "list" and isinstance(item.get("name"), str):
        items = item.get("items")
        return _make_state(
            "scratch_list_monitor",
            fields={
                "TARGET": "" if item.get("target") is None else str(item.get("target")),
                "LIST": item["name"],
                "ITEMS": [str(entry) for entry in items] if isinstance(items, list) else [],
            },
        )
    return None


def scratch_json_to_render_states(data: Any) -> list[JsonDict]:
    if not (isinstance(data, list) and _looks_like_scratch_json(data)):
        raise TypeError("Expected scratch-json: a top-level list of scratch-json objects.")
    states: list[JsonDict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        state = _top_level_object_to_render_state(item)
        if state is not None:
            states.append(state)
    return states


def scratch_json_to_states(data: Any) -> list[JsonDict]:
    return [
        state
        for state in scratch_json_to_render_states(data)
        if state.get("type") not in {"scratch_variable_monitor", "scratch_list_monitor"}
    ]
