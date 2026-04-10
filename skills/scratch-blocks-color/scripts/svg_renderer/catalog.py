"""Catalog parsing and block spec helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from .config import BLOCK_CATALOG_PATH, CAT_COLOURS, CATEGORY_ALIASES, JsonDict, display_value_text
from .normalize import _field_value


@dataclass(frozen=True)
class ParamSpec:
    type: str
    value: str | None = None


@dataclass(frozen=True)
class BranchLabelSpec:
    text: str
    position: str = "left"


@dataclass(frozen=True)
class BlockCatalogEntry:
    category: str
    shapes: tuple[str, ...]
    shape: str
    text: tuple[str, ...]
    param_count: int
    params: tuple[ParamSpec, ...]
    branch_labels: tuple[BranchLabelSpec, ...]


UNKNOWN_CATALOG_ENTRY = BlockCatalogEntry(
    category="unknown",
    shapes=(),
    shape="statement",
    text=(),
    param_count=0,
    params=(),
    branch_labels=(),
)

SYNTHETIC_CATALOG_ENTRIES = {
    "scratch_variable_monitor": BlockCatalogEntry(
        category="data",
        shapes=("monitor", "rect"),
        shape="variable_monitor",
        text=(),
        param_count=0,
        params=(),
        branch_labels=(),
    ),
    "scratch_list_monitor": BlockCatalogEntry(
        category="lists",
        shapes=("monitor", "list"),
        shape="list_monitor",
        text=(),
        param_count=0,
        params=(),
        branch_labels=(),
    ),
    "data_variable": BlockCatalogEntry(
        category="data",
        shapes=("reporter", "round"),
        shape="reporter_round",
        text=(),
        param_count=0,
        params=(),
        branch_labels=(),
    ),
    "data_listcontents": BlockCatalogEntry(
        category="lists",
        shapes=("reporter", "round"),
        shape="reporter_round",
        text=(),
        param_count=0,
        params=(),
        branch_labels=(),
    ),
}


def _shape_from_catalog_entry(entry: JsonDict) -> str:
    shapes = entry.get("shapes", [])

    if "bowlerhat" in shapes:
        return "bowlerhat"
    if "hat" in shapes:
        return "hat"
    if "c-block" in shapes:
        return "c_end" if "end" in shapes else "c_block"
    if "reporter" in shapes and "boolean" in shapes:
        return "reporter_boolean"
    if "reporter" in shapes:
        return "reporter_round"
    if "end" in shapes:
        return "end"
    return "statement"


def _load_block_catalog() -> dict[str, BlockCatalogEntry]:
    entries = json.loads(BLOCK_CATALOG_PATH.read_text(encoding="utf-8"))
    catalog: dict[str, BlockCatalogEntry] = {}

    for entry in entries:
        opcode = entry["opcode"]
        catalog[opcode] = BlockCatalogEntry(
            category=entry.get("category", "unknown"),
            shapes=tuple(str(shape) for shape in entry.get("shapes", [])),
            shape=_shape_from_catalog_entry(entry),
            text=tuple(entry.get("text", [])),
            param_count=len(entry.get("params", [])),
            params=tuple(
                ParamSpec(
                    type=str(item.get("type", "")),
                    value=None if item.get("value") is None else str(item.get("value")),
                )
                for item in entry.get("params", [])
                if isinstance(item, dict)
            ),
            branch_labels=tuple(
                BranchLabelSpec(
                    text=str(item.get("text", "")),
                    position=str(item.get("position", "left")),
                )
                for item in entry.get("branch_labels", [])
                if isinstance(item, dict)
            ),
        )

    return catalog


BLOCK_CATALOG = _load_block_catalog()


def catalog_entry_for(block_type: str) -> BlockCatalogEntry:
    if block_type in SYNTHETIC_CATALOG_ENTRIES:
        return SYNTHETIC_CATALOG_ENTRIES[block_type]
    return BLOCK_CATALOG.get(block_type, UNKNOWN_CATALOG_ENTRY)


def colours_for(category: str | None) -> dict[str, str]:
    normalized = CATEGORY_ALIASES.get(category, category)
    return CAT_COLOURS.get(normalized, CAT_COLOURS["unknown"])


def _display_value(value: Any) -> str:
    if isinstance(value, (list, tuple)) and value:
        return display_value_text(value[0])
    return display_value_text(value)


def _ordered_param_values(fields: JsonDict, inputs: JsonDict) -> list[str]:
    values: list[str] = []

    for value in fields.values():
        values.append(_display_value(value))

    for conn in inputs.values():
        sub = conn.get("block") or conn.get("shadow")
        values.append(f"[{_field_value(sub)}]" if sub else "[…]")

    return values


def resolve_label(block_type: str, fields: JsonDict, inputs: JsonDict) -> str:
    entry = BLOCK_CATALOG.get(block_type)
    if entry is None:
        return block_type.replace("_", " ")

    text_segments = list(entry.text)
    values = _ordered_param_values(fields, inputs)
    param_count = entry.param_count

    if len(values) < param_count:
        values.extend(["[…]"] * (param_count - len(values)))
    else:
        values = values[:param_count]

    if not text_segments and not values:
        return block_type.replace("_", " ")

    parts: list[str] = []
    max_len = max(len(text_segments), len(values))
    for idx in range(max_len):
        if idx < len(text_segments) and text_segments[idx]:
            parts.append(text_segments[idx])
        if idx < len(values):
            parts.append(values[idx])

    return " ".join(part for part in parts if part).strip()
