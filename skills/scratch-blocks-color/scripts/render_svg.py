"""Public API and CLI for the grouped Scratch SVG renderer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from svg_renderer.catalog import BranchLabelSpec, ParamSpec, catalog_entry_for
from svg_renderer.config import STACK_GAP
from svg_renderer.geometry import _c_block_d, _statement_d
from svg_renderer.inline import (
    _build_inline_content_layout,
    _build_param_segment_layout,
    _ordered_inline_items,
    _param_box_kind,
    _serialize_inline_segment,
    _svg_document,
)
from svg_renderer.layout import GroupBlockRenderer
from svg_renderer.normalize import scratch_json_to_render_states, scratch_json_to_states


def states_to_svg(states: Any, padding: int = 20) -> str:
    renderer = GroupBlockRenderer()
    elements: list[str] = []
    cur_y = float(padding)
    max_x = 0.0
    max_y = 0.0

    for state in scratch_json_to_render_states(states):
        fragment = renderer.render_stack_group(state, float(padding), cur_y)
        elements.append(fragment.markup)
        cur_y += fragment.flow_height + STACK_GAP
        max_x = max(max_x, fragment.bounds_x)
        max_y = max(max_y, fragment.bounds_y)

    width = max_x + padding
    height = max_y + padding
    return _svg_document(elements, width, height)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: render_svg.py <scratch-json.json> [out.svg]", file=sys.stderr)
        return 1

    input_path = Path(argv[1])
    with input_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    svg = states_to_svg(data)

    if len(argv) >= 3:
        output_path = Path(argv[2])
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(svg)
        print(f"Written to {output_path}", file=sys.stderr)
    else:
        digest = hashlib.md5(input_path.read_bytes()).hexdigest()
        output_path = Path("/tmp/scratchcode") / f"{digest}.svg"
        output_path.write_text(svg, encoding="utf-8")
    print(output_path)

    return 0


def _render_param_segment(conn, spec, fill, stroke):
    segment = _build_param_segment_layout(conn, spec, fill, stroke)
    return segment.width, segment.height, _serialize_inline_segment(segment)


__all__ = [
    "states_to_svg",
    "main",
    "ParamSpec",
    "BranchLabelSpec",
    "catalog_entry_for",
    "scratch_json_to_states",
    "_ordered_inline_items",
    "_param_box_kind",
    "_build_inline_content_layout",
    "_render_param_segment",
    "_statement_d",
    "_c_block_d",
]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
