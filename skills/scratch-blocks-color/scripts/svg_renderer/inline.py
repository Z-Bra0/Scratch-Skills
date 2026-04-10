"""Inline layout, monitor, and SVG helper functions."""

from __future__ import annotations

import html
import re

from .catalog import BranchLabelSpec, BLOCK_CATALOG, ParamSpec, catalog_entry_for, colours_for, resolve_label
from .config import (
    ANGLE_EXTRA_PAD_X,
    BLOCK_H,
    C_INNER_MIN_H,
    CONTENT_PAD_Y,
    DROPDOWN_EXTRA_W,
    FONT_SIZE,
    HAT_H,
    ICON_RENDER_SIZE,
    ICON_TOKEN_MAP,
    ICON_TOKEN_ORDER,
    INNER_INDENT,
    JsonDict,
    LEADING_PARAM_PAD_X,
    NOTCH_H,
    PAD_X,
    PARAM_MIN_H,
    PARAM_MIN_W,
    PARAM_PAD_X,
    PARAM_PAD_Y,
    PARAM_TEXT_COLOUR,
    SEGMENT_GAP,
    TEXT_X_OFFSET,
    VARIABLE_MONITOR_BG,
    VARIABLE_MONITOR_STROKE,
    VARIABLE_MONITOR_MIN_H,
    VARIABLE_MONITOR_PAD_X,
    VARIABLE_MONITOR_PAD_Y,
    VARIABLE_MONITOR_TEXT,
    VARIABLE_MONITOR_VALUE_BG,
    VARIABLE_MONITOR_VALUE_MIN_W,
    VARIABLE_MONITOR_VALUE_PAD_X,
    VARIABLE_MONITOR_VALUE_STROKE,
    VARIABLE_MONITOR_VALUE_TEXT,
    display_value_text,
    text_width,
)
from .geometry import (
    CORNER_W,
    _angled_box_d,
    _bottom_rounded_rect_d,
    _bowlerhat_d,
    _c_block_d,
    _curve_box_d,
    _fmt,
    _hat_d,
    _rect_box_d,
    _rounded_rect_d,
    _statement_d,
    _top_rounded_rect_d,
)
from .models import (
    BlockLayout,
    BranchLayout,
    InlineContentLayout,
    InlineSegmentLayout,
    MonitorPanelLayout,
    ParamRenderPolicy,
    ProcedureSignatureSpec,
    RenderFragment,
    StackedInlineContentLayout,
)
from .normalize import _field_value


# ============================================================================
# Inline / Helper Layer
# ============================================================================


def _scoped_monitor_name(state: JsonDict, name_key: str) -> str:
    fields = state.get("fields", {})
    name = str(fields.get(name_key, ""))
    target = str(fields.get("TARGET", "")).strip()
    if not target or target == "Stage":
        return name
    return f"{target}: {name}"


def _variable_monitor_name(state: JsonDict) -> str:
    return _scoped_monitor_name(state, "VARIABLE")


def _list_monitor_name(state: JsonDict) -> str:
    return _scoped_monitor_name(state, "LIST")


def _variable_monitor_value(state: JsonDict) -> str:
    return str(state.get("fields", {}).get("VALUE", ""))


def _list_monitor_items(state: JsonDict) -> list[str]:
    items = state.get("fields", {}).get("ITEMS", [])
    if isinstance(items, list):
        return [str(item) for item in items]
    return []


def block_width(label: str) -> float:
    return max(36 * 4, PAD_X * 2 + _tokenized_text_width(label))


def _svg_path(d: str, fill: str, stroke: str, stroke_w: float = 1.0, opacity: float = 1.0) -> str:
    element = f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{_fmt(stroke_w)}"'
    if opacity < 1.0:
        element += f' opacity="{opacity}"'
    return element + "/>"


def _svg_text(x: float, y: float, text: str, colour: str = "#fff", size: int = FONT_SIZE) -> str:
    safe = html.escape(text)
    return (
        f'<text x="{_fmt(x)}" y="{_fmt(y)}" '
        f'font-family="Helvetica Neue, sans-serif" '
        f'font-size="{size}" fill="{colour}" text-anchor="start" '
        f'dominant-baseline="central">{safe}</text>'
    )


def _svg_text_centered(x: float, y: float, text: str, colour: str = "#fff", size: int = FONT_SIZE) -> str:
    safe = html.escape(text)
    return (
        f'<text x="{_fmt(x)}" y="{_fmt(y)}" '
        f'font-family="Helvetica Neue, sans-serif" '
        f'font-size="{size}" fill="{colour}" text-anchor="middle" '
        f'dominant-baseline="central">{safe}</text>'
    )


def _svg_icon(x: float, y: float, icon_markup: str) -> str:
    translate = f"translate({_fmt(x)} {_fmt(y)})"
    if 'transform="' in icon_markup:
        return icon_markup.replace('transform="', f'transform="{translate} ', 1)
    transform = f'transform="{translate}"'
    if icon_markup.startswith("<path "):
        return icon_markup.replace("<path ", f"<path {transform} ", 1)
    return f'<g {transform}>{icon_markup}</g>'


def _svg_group(x: float, y: float, children: list[str], *, attrs: dict[str, str] | None = None) -> str:
    attr_parts = [f'transform="translate({_fmt(x)} {_fmt(y)})"']
    for key, value in (attrs or {}).items():
        attr_parts.append(f'{key}="{html.escape(value, quote=True)}"')
    attr_text = " ".join(attr_parts)
    inner = "\n    ".join(children)
    return f"<g {attr_text}>\n    {inner}\n  </g>"


def _svg_document(elements: list[str], width: float, height: float) -> str:
    inner = "\n  ".join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{int(width)}" height="{int(height)}" '
        f'style="background:#f9f9f9;font-family:\'Helvetica Neue\',sans-serif">\n'
        f"  {inner}\n"
        f"</svg>"
    )


def _branch_label_fragment(text: str, position: str, width: float, y: float) -> str:
    label_w = _tokenized_text_width(text)
    x = TEXT_X_OFFSET if position != "right" else max(TEXT_X_OFFSET, width - TEXT_X_OFFSET - label_w)
    children, _ = _build_text_children(text, "#fff")
    return _svg_group(x, y - 10.0, list(children))


def _ordered_substacks(inputs: JsonDict) -> list[JsonDict | None]:
    substacks: list[tuple[int, JsonDict | None]] = []
    for key, value in inputs.items():
        if key == "SUBSTACK":
            substacks.append((1, (value or {}).get("block")))
        elif key.startswith("SUBSTACK") and key[8:].isdigit():
            substacks.append((int(key[8:]), (value or {}).get("block")))
    if not substacks:
        return [None]
    substacks.sort(key=lambda item: item[0])
    return [block for _, block in substacks]


def _input_connection(inputs: JsonDict, index: int) -> JsonDict:
    value = inputs.get(f"INPUT{index}")
    return value if isinstance(value, dict) else {}


def _param_fallback_text(spec: ParamSpec) -> str:
    if spec.value is not None:
        return display_value_text(spec.value)
    if spec.type == "boolean":
        return ""
    return "..."


def _is_dropdown_param(spec: ParamSpec) -> bool:
    return spec.type == "dropdown" or spec.type.startswith("dropdown-")


def _is_color_param(spec: ParamSpec) -> bool:
    return spec.type == "color"


def _is_stack_param(spec: ParamSpec) -> bool:
    return spec.type == "input_statement"


def _category_for_state(state: JsonDict) -> str | None:
    block_type = state.get("type", "unknown")
    if block_type in BLOCK_CATALOG:
        return BLOCK_CATALOG[block_type].category
    if block_type.startswith("math_"):
        return "math"
    if block_type.startswith("operator_"):
        return "operators"
    if block_type.startswith("data_variable"):
        return "data"
    if block_type.startswith("data_list"):
        return "lists"
    if block_type.startswith("event_"):
        return "events"
    return None


def _ordered_inline_items(text_segments: list[str], params: list[ParamSpec]) -> list[tuple[str, str | ParamSpec]]:
    items: list[tuple[str, str | ParamSpec]] = []
    limit = min(len(text_segments), len(params))

    for index in range(limit):
        items.append(("text", text_segments[index]))
        items.append(("param", params[index]))

    for text in text_segments[limit:]:
        items.append(("text", text))

    for param in params[limit:]:
        items.append(("param", param))

    return items


def _split_text_tokens(text: str) -> list[tuple[str, str]]:
    if not text:
        return []

    tokens: list[tuple[str, str]] = []
    cursor = 0
    while cursor < len(text):
        matched = False
        for marker in ICON_TOKEN_ORDER:
            if text.startswith(marker, cursor):
                tokens.append(("icon", marker))
                cursor += len(marker)
                matched = True
                break
        if matched:
            continue

        next_icon = len(text)
        for marker in ICON_TOKEN_ORDER:
            index = text.find(marker, cursor)
            if index != -1:
                next_icon = min(next_icon, index)
        tokens.append(("text", text[cursor:next_icon]))
        cursor = next_icon

    return [(kind, value) for kind, value in tokens if value]


def _tokenized_text_width(text: str) -> float:
    width = 0.0
    for kind, value in _split_text_tokens(text):
        if kind == "text":
            width += text_width(value)
        else:
            width += ICON_RENDER_SIZE
    return width


def _build_text_children(text: str, colour: str) -> tuple[tuple[str, ...], float]:
    children: list[str] = []
    cur_x = 0.0
    for kind, value in _split_text_tokens(text):
        if kind == "text":
            children.append(_svg_text(cur_x, 10, value, colour=colour))
            cur_x += text_width(value)
            continue

        children.append(_svg_icon(cur_x, (20.0 - ICON_RENDER_SIZE) / 2, ICON_TOKEN_MAP[value]))
        cur_x += ICON_RENDER_SIZE

    return tuple(children), cur_x


def _param_literal_value(spec: ParamSpec, sub_state: JsonDict | None) -> str | None:
    if isinstance(sub_state, dict):
        fields = sub_state.get("fields", {})
        if fields:
            return _field_value(sub_state)
    return spec.value


def _param_chip_fill(spec: ParamSpec, nested_block: JsonDict | None, parent_fill: str) -> str:
    if _is_dropdown_param(spec):
        return parent_fill
    if _is_color_param(spec):
        literal = _param_literal_value(spec, nested_block)
        if literal:
            return literal
    if isinstance(nested_block, dict):
        category = _category_for_state(nested_block)
        if category is not None:
            return colours_for(category)["p"]
    return "#FFFFFF"


def _param_box_kind(spec: ParamSpec, sub_state: JsonDict | None) -> str:
    if _is_stack_param(spec):
        return "stack"
    if _is_dropdown_param(spec):
        return "rect"
    if isinstance(sub_state, dict):
        entry = catalog_entry_for(sub_state.get("type", "unknown"))
        if "boolean" in entry.shapes:
            return "angle"
        if "round" in entry.shapes:
            return "curve"
    return "angle" if spec.type == "boolean" else "curve"


def _parse_procedure_signature(signature: str) -> tuple[list[str], list[ParamSpec]]:
    if not signature:
        return [], []

    parts = re.split(r"(%[sb])", signature)
    text_segments: list[str] = []
    params: list[ParamSpec] = []

    for index, part in enumerate(parts):
        if index % 2 == 0:
            text_segments.append(part.strip())
            continue

        if part == "%b":
            params.append(ParamSpec(type="boolean"))
        elif part == "%s":
            params.append(ParamSpec(type="string"))

    while text_segments and text_segments[-1] == "":
        text_segments.pop()

    return text_segments, params


def _procedure_signature_spec(state: JsonDict) -> ProcedureSignatureSpec:
    inputs = state.get("inputs", {})
    signature_state = _input_connection(inputs, 1).get("block") or _input_connection(inputs, 1).get("shadow")
    signature = _field_value(signature_state) if isinstance(signature_state, dict) else ""
    text_segments, params = _parse_procedure_signature(signature)
    return ProcedureSignatureSpec(
        text_segments=tuple(text_segments),
        params=tuple(params),
        param_connections=tuple(_input_connection(inputs, index + 2) for index in range(len(params))),
    )


def _build_interleaved_content_layout(
    text_segments: tuple[str, ...] | list[str],
    params: tuple[ParamSpec, ...] | list[ParamSpec],
    param_connections: tuple[JsonDict, ...] | list[JsonDict],
    text_colour: str,
    fill: str,
    stroke: str,
    *,
    leading_pad_on_empty_first_text: bool = False,
    param_fill_override: str | None = None,
) -> InlineContentLayout:
    text_items = list(text_segments)
    param_items = list(params)
    connections = list(param_connections)
    segments: list[InlineSegmentLayout] = []
    param_index = 0

    for kind, item in _ordered_inline_items(text_items, param_items):
        if kind == "text":
            text = str(item)
            if text:
                segments.append(_build_text_segment_layout(text, text_colour))
            continue

        conn = connections[param_index] if param_index < len(connections) else {}
        segments.append(_build_param_segment_layout(conn, item, fill, stroke, param_fill_override=param_fill_override))
        param_index += 1

    leading_pad = 0.0
    if leading_pad_on_empty_first_text and text_items and text_items[0] == "" and param_items:
        leading_pad = LEADING_PARAM_PAD_X

    return _position_segments(segments, leading_pad=leading_pad)


def _build_procedure_call_content_layout(
    state: JsonDict,
    text_colour: str,
    fill: str,
    stroke: str,
) -> InlineContentLayout:
    signature = _procedure_signature_spec(state)
    return _build_interleaved_content_layout(
        signature.text_segments,
        signature.params,
        signature.param_connections,
        text_colour,
        fill,
        stroke,
        leading_pad_on_empty_first_text=True,
    )


def _build_block_signature_segment_layout(
    inner_layout: InlineContentLayout,
    fill: str,
    stroke: str,
) -> InlineSegmentLayout:
    chip_h = max(PARAM_MIN_H, inner_layout.height + PARAM_PAD_Y * 2)
    content_w = max(PARAM_MIN_W, inner_layout.width + PARAM_PAD_X * 2)
    chip_w = max(chip_h, content_w)
    path_d = _statement_d(chip_w, True).replace(_fmt(BLOCK_H - CORNER_W * 2), _fmt(chip_h - CORNER_W * 2), 1)

    children = (
        _svg_path(path_d, fill, stroke, 1.0),
        _svg_group(
            TEXT_X_OFFSET,
            (chip_h - inner_layout.height) / 2,
            _serialize_inline_content(inner_layout),
            attrs={"data-role": "param-content"},
        ),
    )
    return InlineSegmentLayout(
        kind="block",
        width=chip_w,
        height=chip_h,
        x=0.0,
        y=0.0,
        children=(
            _svg_group(0.0, 0.0, list(children), attrs={"data-role": "block-signature"}),
        ),
        attrs={"data-role": "segment"},
    )


def _build_procedure_definition_content_layout(
    state: JsonDict,
    entry,
    text_colour: str,
    fill: str,
    stroke: str,
) -> InlineContentLayout:
    proc_colours = colours_for(entry.category)
    signature_fill = proc_colours["s"]
    signature_param_fill = proc_colours["p"]
    signature = _procedure_signature_spec(state)
    segments: list[InlineSegmentLayout] = []

    for prefix in entry.text:
        if prefix:
            segments.append(_build_text_segment_layout(prefix, text_colour))

    signature_layout = _build_interleaved_content_layout(
        signature.text_segments,
        signature.params,
        signature.param_connections,
        "#fff",
        fill,
        stroke,
        leading_pad_on_empty_first_text=True,
        param_fill_override=signature_param_fill,
    )
    segments.append(_build_block_signature_segment_layout(signature_layout, signature_fill, stroke))
    return _position_segments(segments)


def _build_param_policy(
    spec: ParamSpec,
    sub_state: JsonDict | None,
    nested_block: JsonDict | None,
    parent_fill: str,
    param_fill_override: str | None = None,
) -> ParamRenderPolicy:
    if param_fill_override is not None:
        fill = param_fill_override
    else:
        if _is_color_param(spec):
            fill_source = sub_state if isinstance(sub_state, dict) else None
        else:
            fill_source = nested_block if isinstance(nested_block, dict) else None
        fill = _param_chip_fill(spec, fill_source, parent_fill)
    box_kind = _param_box_kind(spec, sub_state if isinstance(sub_state, dict) else None)
    text_colour = "#fff" if _is_dropdown_param(spec) or _is_color_param(spec) or fill != "#FFFFFF" else PARAM_TEXT_COLOUR
    return ParamRenderPolicy(
        box_kind=box_kind,
        fill=fill,
        text_colour=text_colour,
        show_text=not _is_color_param(spec),
        show_arrow=_is_dropdown_param(spec),
    )


def _build_text_segment_layout(text: str, colour: str, *, role: str = "segment") -> InlineSegmentLayout:
    children, width = _build_text_children(text, colour)
    return InlineSegmentLayout(
        kind="text",
        width=width,
        height=20.0,
        x=0.0,
        y=0.0,
        children=children,
        attrs={"data-role": role},
    )


def _build_variable_value_segment_layout(value: str) -> InlineSegmentLayout:
    text_children, text_w = _build_text_children(value, VARIABLE_MONITOR_VALUE_TEXT)
    chip_h = max(PARAM_MIN_H, 20.0 + PARAM_PAD_Y * 2)
    chip_w = max(chip_h, VARIABLE_MONITOR_VALUE_MIN_W, text_w + VARIABLE_MONITOR_VALUE_PAD_X * 2)
    return _build_fixed_width_value_segment_layout(value, chip_w)


def _build_fixed_width_value_segment_layout(value: str, chip_w: float) -> InlineSegmentLayout:
    text_children, _ = _build_text_children(value, VARIABLE_MONITOR_VALUE_TEXT)
    chip_h = max(PARAM_MIN_H, 20.0 + PARAM_PAD_Y * 2)
    path_d = _rounded_rect_d(0, 0, chip_w, chip_h)
    children = (
        _svg_path(path_d, VARIABLE_MONITOR_VALUE_BG, VARIABLE_MONITOR_VALUE_STROKE, 1.0),
        _svg_group(
            VARIABLE_MONITOR_VALUE_PAD_X,
            (chip_h - 20.0) / 2,
            list(text_children),
            attrs={"data-role": "variable-value-content"},
        ),
    )
    return InlineSegmentLayout(
        kind="value",
        width=chip_w,
        height=chip_h,
        x=0.0,
        y=0.0,
        children=(
            _svg_group(0.0, 0.0, list(children), attrs={"data-role": "variable-value"}),
        ),
        attrs={"data-role": "segment"},
    )


def _build_monitor_text_layout(text: str, colour: str = VARIABLE_MONITOR_TEXT) -> InlineContentLayout:
    segment = _build_text_segment_layout(text, colour)
    return InlineContentLayout((segment,), segment.width, segment.height)


def _build_centered_monitor_text_layout(text: str, width: float, colour: str = VARIABLE_MONITOR_TEXT) -> InlineContentLayout:
    return InlineContentLayout(
        (
            InlineSegmentLayout(
                kind="text",
                width=width,
                height=20.0,
                x=0.0,
                y=0.0,
                children=(_svg_text_centered(width / 2, 10.0, text, colour=colour),),
                attrs={"data-role": "segment"},
            ),
        ),
        width,
        20.0,
    )


def _build_fixed_width_text_segment_layout(text: str, colour: str, width: float) -> InlineSegmentLayout:
    children, _ = _build_text_children(text, colour)
    return InlineSegmentLayout(
        kind="text",
        width=width,
        height=20.0,
        x=0.0,
        y=0.0,
        children=children,
        attrs={"data-role": "segment"},
    )


def _build_list_item_row_layout(index: int, value: str, *, index_w: float, value_w: float) -> InlineContentLayout:
    return _position_segments(
        [
            _build_fixed_width_text_segment_layout(str(index), VARIABLE_MONITOR_TEXT, index_w),
            _build_fixed_width_value_segment_layout(value, value_w),
        ]
    )


def _build_stacked_inline_content(
    layouts: list[InlineContentLayout],
    *,
    role: str,
    gap: float = SEGMENT_GAP,
) -> StackedInlineContentLayout:
    children: list[str] = []
    cur_y = 0.0
    max_w = 0.0
    for layout in layouts:
        children.append(_svg_group(0.0, cur_y, _serialize_inline_content(layout), attrs={"data-role": role}))
        cur_y += layout.height + gap
        max_w = max(max_w, layout.width)
    total_h = max(0.0, cur_y - gap) if layouts else 0.0
    return StackedInlineContentLayout(tuple(children), max_w, total_h)


def _monitor_panel(
    y: float,
    width: float,
    height: float,
    fill: str,
    stroke: str,
    path_d: str,
    *,
    content: InlineContentLayout | None = None,
    content_children: tuple[str, ...] = (),
    content_role: str = "content",
    content_origin: tuple[float, float] | None = None,
) -> MonitorPanelLayout:
    if content_origin is None:
        content_h = content.height if content is not None else 20.0
        content_origin = (TEXT_X_OFFSET, (height - content_h) / 2)
    return MonitorPanelLayout(
        y=y,
        width=width,
        height=height,
        fill=fill,
        stroke=stroke,
        path_d=path_d,
        content_origin=content_origin,
        content=content,
        content_children=content_children,
        content_role=content_role,
    )


def _position_segments(segments: list[InlineSegmentLayout], leading_pad: float = 0.0) -> InlineContentLayout:
    max_h = max((segment.height for segment in segments), default=20.0)
    cur_x = leading_pad
    positioned: list[InlineSegmentLayout] = []

    for segment in segments:
        positioned.append(
            InlineSegmentLayout(
                kind=segment.kind,
                width=segment.width,
                height=segment.height,
                x=cur_x,
                y=(max_h - segment.height) / 2,
                children=segment.children,
                attrs=segment.attrs,
            )
        )
        cur_x += segment.width + SEGMENT_GAP

    total_width = max(0.0, cur_x - SEGMENT_GAP)
    return InlineContentLayout(tuple(positioned), total_width, max_h)


def _serialize_inline_segment(segment: InlineSegmentLayout) -> str:
    return _svg_group(segment.x, segment.y, list(segment.children), attrs=segment.attrs)


def _serialize_inline_content(layout: InlineContentLayout) -> list[str]:
    return [_serialize_inline_segment(segment) for segment in layout.segments]


def _append_dropdown_arrow(layout: InlineContentLayout, colour: str) -> InlineContentLayout:
    arrow_segment = InlineSegmentLayout(
        kind="arrow",
        width=text_width("▼"),
        height=20.0,
        x=layout.width + SEGMENT_GAP,
        y=(layout.height - 20.0) / 2,
        children=(_svg_text(0, 10, "▼", colour=colour),),
        attrs={"data-role": "param-arrow"},
    )
    return InlineContentLayout(
        segments=layout.segments + (arrow_segment,),
        width=layout.width + SEGMENT_GAP + arrow_segment.width,
        height=layout.height,
    )


def _build_inline_content_layout(state: JsonDict, text_colour: str, fill: str, stroke: str) -> InlineContentLayout:
    block_type = state.get("type", "unknown")
    entry = catalog_entry_for(block_type)
    if block_type == "scratch_variable_monitor":
        return _position_segments(
            [
                _build_text_segment_layout(_variable_monitor_name(state), VARIABLE_MONITOR_TEXT),
                _build_variable_value_segment_layout(_variable_monitor_value(state)),
            ]
        )
    if block_type == "procedures_definition":
        return _build_procedure_definition_content_layout(state, entry, text_colour, fill, stroke)

    if block_type == "procedures_call":
        return _build_procedure_call_content_layout(state, text_colour, fill, stroke)

    text_segments = list(entry.text)
    params = list(entry.params)
    fields = state.get("fields", {})
    inputs = state.get("inputs", {})

    if not text_segments and not params:
        label = _field_value(state) if fields else resolve_label(block_type, fields, inputs)
        return InlineContentLayout(( _build_text_segment_layout(label, text_colour), ), text_width(label), 20.0)

    return _build_interleaved_content_layout(
        text_segments,
        params,
        [_input_connection(inputs, index + 1) for index in range(len(params))],
        text_colour,
        fill,
        stroke,
        leading_pad_on_empty_first_text=True,
    )


def _build_param_segment_layout(
    conn: JsonDict,
    spec: ParamSpec,
    parent_fill: str,
    stroke: str,
    *,
    param_fill_override: str | None = None,
) -> InlineSegmentLayout:
    nested_block = conn.get("block")
    sub_state = nested_block or conn.get("shadow")
    policy = _build_param_policy(
        spec,
        sub_state if isinstance(sub_state, dict) else None,
        nested_block if isinstance(nested_block, dict) else None,
        parent_fill,
        param_fill_override=param_fill_override,
    )

    if policy.show_text and isinstance(sub_state, dict):
        inner_layout = _build_inline_content_layout(sub_state, policy.text_colour, policy.fill, stroke)
    elif policy.show_text:
        fallback = _param_fallback_text(spec)
        if fallback:
            inner_layout = InlineContentLayout(
                segments=(_build_text_segment_layout(fallback, policy.text_colour),),
                width=text_width(fallback),
                height=20.0,
            )
        else:
            inner_layout = InlineContentLayout(segments=(), width=0.0, height=20.0)
    else:
        inner_layout = InlineContentLayout(segments=(), width=0.0, height=20.0)

    if policy.show_arrow:
        inner_layout = _append_dropdown_arrow(inner_layout, "#fff")

    chip_h = max(PARAM_MIN_H, inner_layout.height + PARAM_PAD_Y * 2)
    content_w = max(PARAM_MIN_W, inner_layout.width + PARAM_PAD_X * 2)
    if policy.show_arrow:
        content_w += DROPDOWN_EXTRA_W
    if policy.box_kind == "angle":
        content_w += ANGLE_EXTRA_PAD_X * 2
    chip_w = max(chip_h, content_w)

    if policy.box_kind == "angle":
        path_d = _angled_box_d(0, 0, chip_w - chip_h, chip_h)
    elif policy.box_kind == "stack":
        path_d = _statement_d(chip_w, False).replace(_fmt(BLOCK_H - CORNER_W * 2), _fmt(chip_h - CORNER_W * 2), 1)
    elif policy.box_kind == "rect":
        path_d = _rect_box_d(0, 0, chip_w, chip_h)
    else:
        path_d = _curve_box_d(0, 0, chip_w - chip_h, chip_h)

    content_x = TEXT_X_OFFSET if policy.box_kind == "stack" else PARAM_PAD_X
    children = (
        _svg_path(path_d, policy.fill, stroke, 1.0),
        _svg_group(
            content_x,
            (chip_h - inner_layout.height) / 2,
            _serialize_inline_content(inner_layout),
            attrs={"data-role": "param-content"},
        ),
    )
    return InlineSegmentLayout(
        kind="param",
        width=chip_w,
        height=chip_h,
        x=0.0,
        y=0.0,
        children=(
            _svg_group(0.0, 0.0, list(children), attrs={"data-role": "param"}),
        ),
        attrs={"data-role": "segment"},
    )
