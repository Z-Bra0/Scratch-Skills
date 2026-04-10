"""Block layout orchestration and serialization."""

from __future__ import annotations

from typing import Callable

from .catalog import BranchLabelSpec, catalog_entry_for, colours_for, resolve_label
from .config import ANGLE_EXTRA_PAD_X, BLOCK_H, C_INNER_MIN_H, CONTENT_PAD_Y, HAT_H, INNER_INDENT, JsonDict, NOTCH_H, PAD_X, PARAM_MIN_H, PARAM_MIN_W, PARAM_PAD_X, PARAM_PAD_Y, TEXT_X_OFFSET, VARIABLE_MONITOR_BG, VARIABLE_MONITOR_MIN_H, VARIABLE_MONITOR_PAD_X, VARIABLE_MONITOR_PAD_Y, VARIABLE_MONITOR_STROKE, VARIABLE_MONITOR_VALUE_MIN_W, text_width
from .geometry import CORNER_W, _angled_box_d, _bottom_rounded_rect_d, _bowlerhat_d, _c_block_d, _curve_box_d, _fmt, _hat_d, _rect_box_d, _rounded_rect_d, _statement_d, _top_rounded_rect_d
from .inline import (
    _branch_label_fragment,
    _build_centered_monitor_text_layout,
    _build_inline_content_layout,
    _build_list_item_row_layout,
    _build_monitor_text_layout,
    _build_stacked_inline_content,
    _build_variable_value_segment_layout,
    _list_monitor_items,
    _list_monitor_name,
    _monitor_panel,
    _ordered_substacks,
    _serialize_inline_content,
    _svg_group,
    _svg_path,
    _variable_monitor_name,
    _variable_monitor_value,
    block_width,
)
from .models import BlockLayout, BranchLayout, InlineContentLayout, MonitorPanelLayout, RenderFragment


# ============================================================================
# Block Layout Layer
# ============================================================================


class GroupBlockRenderer:
    def __init__(self) -> None:
        self._shape_builders: dict[str, Callable[[JsonDict, InlineContentLayout, float, str, str], BlockLayout]] = {
            "statement": self._layout_statement_block,
            "end": self._layout_end_block,
            "hat": self._layout_hat_block,
            "bowlerhat": self._layout_bowlerhat_block,
            "variable_monitor": self._layout_variable_monitor_block,
            "list_monitor": self._layout_list_monitor_block,
            "reporter_round": self._layout_reporter_round_block,
            "reporter_boolean": self._layout_reporter_boolean_block,
            "c_block": self._layout_c_block,
            "c_end": self._layout_c_end_block,
        }

    def render_stack_group(self, state: JsonDict, x: float, y: float) -> RenderFragment:
        children: list[str] = []
        cur_y = 0.0
        max_x = 0.0
        max_y = 0.0
        cur_state: JsonDict | None = state

        while cur_state:
            fragment = self.render_block_group(cur_state, 0.0, cur_y)
            children.append(fragment.markup)
            cur_y += fragment.flow_height
            max_x = max(max_x, fragment.bounds_x)
            max_y = max(max_y, fragment.bounds_y)
            cur_state = (cur_state.get("next") or {}).get("block")

        return RenderFragment(
            markup=_svg_group(x, y, children, attrs={"data-role": "stack"}),
            flow_height=cur_y,
            bounds_x=x + max_x,
            bounds_y=y + max_y,
        )

    def render_block_group(self, state: JsonDict, x: float, y: float) -> RenderFragment:
        layout = self._layout_block(state)
        return self._serialize_block_layout(layout, x, y)

    def _layout_block(self, state: JsonDict) -> BlockLayout:
        block_type = state.get("type", "unknown")
        fields = state.get("fields", {})
        inputs = state.get("inputs", {})
        entry = catalog_entry_for(block_type)
        colours = colours_for(entry.category)
        content = _build_inline_content_layout(state, "#fff", colours["p"], colours["t"])
        if entry.shape in {"variable_monitor", "list_monitor"}:
            width = TEXT_X_OFFSET + content.width + VARIABLE_MONITOR_PAD_X
        else:
            width = max(block_width(resolve_label(block_type, fields, inputs)), TEXT_X_OFFSET + content.width + PAD_X)
        builder = self._shape_builders.get(entry.shape, self._layout_statement_block)
        return builder(state, content, width, colours["p"], colours["t"])

    def _layout_statement_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        return self._layout_statement_family(state, content, width, fill, stroke, "statement")

    def _layout_end_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        return self._layout_statement_family(state, content, width, fill, stroke, "end")

    def _layout_statement_family(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
        render_shape: str,
    ) -> BlockLayout:
        has_next = render_shape == "statement"
        body_h = max(BLOCK_H, content.height + CONTENT_PAD_Y)
        path_d = _statement_d(width, has_next).replace(_fmt(BLOCK_H - CORNER_W * 2), _fmt(body_h - CORNER_W * 2), 1)
        extra = NOTCH_H if has_next else 0.0
        return BlockLayout(
            block_type=state.get("type", "unknown"),
            shape=render_shape,
            width=width,
            height=body_h,
            flow_height=body_h,
            bounds_x=width,
            bounds_y=body_h + extra,
            fill=fill,
            stroke=stroke,
            path_d=path_d,
            content_origin=(TEXT_X_OFFSET, (body_h - content.height) / 2),
            content=content,
        )

    def _layout_hat_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        body_h = max(BLOCK_H, content.height + CONTENT_PAD_Y)
        path_d = _hat_d(width).replace(_fmt(BLOCK_H - CORNER_W * 2), _fmt(body_h - CORNER_W * 2), 1)
        return BlockLayout(
            block_type=state.get("type", "unknown"),
            shape="hat",
            width=width,
            height=HAT_H + body_h,
            flow_height=HAT_H + body_h,
            bounds_x=width,
            bounds_y=HAT_H + body_h + NOTCH_H,
            fill=fill,
            stroke=stroke,
            path_d=path_d,
            content_origin=(TEXT_X_OFFSET, HAT_H + (body_h - content.height) / 2),
            content=content,
        )

    def _layout_bowlerhat_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        body_h = max(BLOCK_H, content.height + CONTENT_PAD_Y)
        path_d = _bowlerhat_d(width).replace(_fmt(BLOCK_H - CORNER_W * 2), _fmt(body_h - CORNER_W * 2), 1)
        return BlockLayout(
            block_type=state.get("type", "unknown"),
            shape="bowlerhat",
            width=width,
            height=HAT_H + body_h,
            flow_height=HAT_H + body_h,
            bounds_x=width,
            bounds_y=HAT_H + body_h + NOTCH_H,
            fill=fill,
            stroke=stroke,
            path_d=path_d,
            content_origin=(TEXT_X_OFFSET, -5.0),
            content=content,
        )

    def _layout_reporter_round_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        return self._layout_reporter_family(state, content, fill, stroke, "reporter_round")

    def _layout_reporter_boolean_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        return self._layout_reporter_family(state, content, fill, stroke, "reporter_boolean")

    def _layout_reporter_family(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        fill: str,
        stroke: str,
        render_shape: str,
    ) -> BlockLayout:
        body_h = max(PARAM_MIN_H, content.height + PARAM_PAD_Y * 2)
        content_w = max(PARAM_MIN_W, content.width + PARAM_PAD_X * 2)
        if render_shape == "reporter_boolean":
            content_w += ANGLE_EXTRA_PAD_X * 2
        chip_w = max(body_h, content_w)
        if render_shape == "reporter_boolean":
            path_d = _angled_box_d(0, 0, chip_w - body_h, body_h)
        else:
            path_d = _curve_box_d(0, 0, chip_w - body_h, body_h)
        return BlockLayout(
            block_type=state.get("type", "unknown"),
            shape=render_shape,
            width=chip_w,
            height=body_h,
            flow_height=body_h,
            bounds_x=chip_w,
            bounds_y=body_h,
            fill=fill,
            stroke=stroke,
            path_d=path_d,
            content_origin=(PARAM_PAD_X, (body_h - content.height) / 2),
            content=content,
        )

    def _layout_variable_monitor_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        del fill, stroke
        body_h = max(VARIABLE_MONITOR_MIN_H, content.height + VARIABLE_MONITOR_PAD_Y * 2)
        body_w = max(width, TEXT_X_OFFSET + content.width + VARIABLE_MONITOR_PAD_X)
        path_d = _rounded_rect_d(0, 0, body_w, body_h)
        return BlockLayout(
            block_type=state.get("type", "unknown"),
            shape="variable_monitor",
            width=body_w,
            height=body_h,
            flow_height=body_h,
            bounds_x=body_w,
            bounds_y=body_h,
            fill=VARIABLE_MONITOR_BG,
            stroke=VARIABLE_MONITOR_STROKE,
            path_d=path_d,
            content_origin=(TEXT_X_OFFSET, (body_h - content.height) / 2),
            content=content,
            panels=(
                _monitor_panel(
                    0.0,
                    body_w,
                    body_h,
                    VARIABLE_MONITOR_BG,
                    VARIABLE_MONITOR_STROKE,
                    path_d,
                    content=content,
                ),
            ),
        )

    def _layout_list_monitor_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        del content, width, fill, stroke
        title = _list_monitor_name(state)
        items = _list_monitor_items(state)
        footer = f"length {len(items)}"

        title_width = text_width(title)
        footer_width = text_width(footer)
        if items:
            index_w = text_width("00")
            value_w = max(
                max((_build_variable_value_segment_layout(value).width for value in items), default=VARIABLE_MONITOR_VALUE_MIN_W),
                VARIABLE_MONITOR_VALUE_MIN_W,
            )
            rows = [
                _build_list_item_row_layout(index, value, index_w=index_w, value_w=value_w)
                for index, value in enumerate(items, start=1)
            ]
        else:
            rows = [_build_monitor_text_layout("(empty)")]
        rows_layout = _build_stacked_inline_content(rows, role="list-item")

        panel_width = max(
            title_width,
            rows_layout.width,
            footer_width,
        ) + TEXT_X_OFFSET * 2
        title_layout = _build_centered_monitor_text_layout(title, panel_width - TEXT_X_OFFSET * 2)
        footer_layout = _build_centered_monitor_text_layout(footer, panel_width - TEXT_X_OFFSET * 2)
        top_h = max(VARIABLE_MONITOR_MIN_H, 20.0 + VARIABLE_MONITOR_PAD_Y * 2)
        middle_h = max(VARIABLE_MONITOR_MIN_H, rows_layout.height + VARIABLE_MONITOR_PAD_Y * 2)
        bottom_h = max(VARIABLE_MONITOR_MIN_H, 20.0 + VARIABLE_MONITOR_PAD_Y * 2)

        return BlockLayout(
            block_type=state.get("type", "unknown"),
            shape="list_monitor",
            width=panel_width,
            height=top_h + middle_h + bottom_h,
            flow_height=top_h + middle_h + bottom_h,
            bounds_x=panel_width,
            bounds_y=top_h + middle_h + bottom_h,
            fill="",
            stroke="",
            path_d="",
            content_origin=(0.0, 0.0),
            content=InlineContentLayout(segments=(), width=0.0, height=20.0),
            panels=(
                _monitor_panel(
                    0.0,
                    panel_width,
                    top_h,
                    "#FFFFFF",
                    VARIABLE_MONITOR_STROKE,
                    _top_rounded_rect_d(0.0, 0.0, panel_width, top_h),
                    content=title_layout,
                ),
                _monitor_panel(
                    top_h,
                    panel_width,
                    middle_h,
                    VARIABLE_MONITOR_BG,
                    VARIABLE_MONITOR_STROKE,
                    _rect_box_d(0.0, 0.0, panel_width, middle_h),
                    content_children=rows_layout.children,
                    content_role="list-items",
                    content_origin=(TEXT_X_OFFSET, VARIABLE_MONITOR_PAD_Y),
                ),
                _monitor_panel(
                    top_h + middle_h,
                    panel_width,
                    bottom_h,
                    "#FFFFFF",
                    VARIABLE_MONITOR_STROKE,
                    _bottom_rounded_rect_d(0.0, 0.0, panel_width, bottom_h),
                    content=footer_layout,
                    content_origin=(TEXT_X_OFFSET, (bottom_h - footer_layout.height) / 2),
                ),
            ),
        )

    def _layout_c_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        return self._layout_c_family(state, content, width, fill, stroke, "c_block")

    def _layout_c_end_block(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
    ) -> BlockLayout:
        return self._layout_c_family(state, content, width, fill, stroke, "c_end")

    def _layout_c_family(
        self,
        state: JsonDict,
        content: InlineContentLayout,
        width: float,
        fill: str,
        stroke: str,
        render_shape: str,
    ) -> BlockLayout:
        inputs = state.get("inputs", {})
        entry = catalog_entry_for(state.get("type", "unknown"))
        has_next = render_shape == "c_block"
        branch_states = _ordered_substacks(inputs)
        branch_labels = list(entry.branch_labels)
        while len(branch_states) < len(branch_labels):
            branch_states.append(None)

        header_h = max(BLOCK_H, content.height + CONTENT_PAD_Y)
        footer_height = BLOCK_H / 2
        branch_gap_h = BLOCK_H

        branch_fragments: list[RenderFragment | None] = []
        branch_heights: list[float] = []
        for sub_state in branch_states:
            if sub_state:
                nested = self.render_stack_group(sub_state, 0.0, 0.0)
                branch_fragments.append(nested)
                branch_heights.append(max(C_INNER_MIN_H, nested.flow_height))
            else:
                branch_fragments.append(None)
                branch_heights.append(C_INNER_MIN_H)

        path_d = _c_block_d(width, branch_heights, has_next).replace(_fmt(BLOCK_H - CORNER_W * 2), _fmt(header_h - CORNER_W * 2), 1)

        branch_layouts: list[BranchLayout] = []
        branch_y = float(header_h)
        separator_y = float(header_h)
        max_x = width
        max_y = 0.0

        for index, (branch_height, nested) in enumerate(zip(branch_heights, branch_fragments)):
            cavity_y = branch_y + NOTCH_H
            cavity_h = max(0.0, branch_height - NOTCH_H * 2)
            max_y = max(max_y, cavity_y + cavity_h)
            if nested is not None:
                max_x = max(max_x, INNER_INDENT + nested.bounds_x)
                max_y = max(max_y, branch_y + nested.bounds_y)

            label = branch_labels[index] if index < len(branch_labels) else BranchLabelSpec(text="", position="left")
            band_height = branch_gap_h if index < len(branch_heights) - 1 else footer_height
            branch_layouts.append(
                BranchLayout(
                    branch_height=branch_height,
                    stack_origin=(INNER_INDENT, branch_y),
                    nested_stack=nested,
                    label_text=label.text.strip(),
                    label_position=label.position,
                    label_y=separator_y + branch_height + band_height / 2,
                )
            )

            branch_y += branch_height + (branch_gap_h if index < len(branch_heights) - 1 else 0.0)
            separator_y += branch_height + (branch_gap_h if index < len(branch_heights) - 1 else 0.0)

        total_height = header_h + sum(branch_heights) + max(0, len(branch_heights) - 1) * branch_gap_h + footer_height
        max_y = max(max_y, total_height + (NOTCH_H if has_next else 0.0))

        return BlockLayout(
            block_type=state.get("type", "unknown"),
            shape=render_shape,
            width=width,
            height=total_height,
            flow_height=total_height,
            bounds_x=max_x,
            bounds_y=max_y,
            fill=fill,
            stroke=stroke,
            path_d=path_d,
            content_origin=(TEXT_X_OFFSET, (header_h - content.height) / 2),
            content=content,
            branches=tuple(branch_layouts),
        )

    def _serialize_block_layout(self, layout: BlockLayout, x: float, y: float) -> RenderFragment:
        if layout.panels:
            children: list[str] = []
            for panel in layout.panels:
                panel_children = [_svg_path(panel.path_d, panel.fill, panel.stroke)]
                if panel.content is not None:
                    panel_children.append(
                        _svg_group(
                            panel.content_origin[0],
                            panel.content_origin[1],
                            _serialize_inline_content(panel.content),
                            attrs={"data-role": panel.content_role},
                        )
                    )
                elif panel.content_children:
                    panel_children.append(
                        _svg_group(
                            panel.content_origin[0],
                            panel.content_origin[1],
                            list(panel.content_children),
                            attrs={"data-role": panel.content_role},
                        )
                    )
                children.append(_svg_group(0.0, panel.y, panel_children, attrs={"data-role": "panel"}))
        else:
            children = [
                _svg_path(layout.path_d, layout.fill, layout.stroke),
                _svg_group(
                    layout.content_origin[0],
                    layout.content_origin[1],
                    _serialize_inline_content(layout.content),
                    attrs={"data-role": "content"},
                ),
            ]

        for branch in layout.branches:
            if branch.nested_stack is not None:
                children.append(
                    _svg_group(
                        branch.stack_origin[0],
                        branch.stack_origin[1],
                        [branch.nested_stack.markup],
                        attrs={"data-role": "stack"},
                    )
                )
            if branch.label_text:
                children.append(
                    _branch_label_fragment(branch.label_text, branch.label_position, layout.width - CORNER_W, branch.label_y)
                )

        markup = _svg_group(
            x,
            y,
            children,
            attrs={
                "data-role": "block",
                "data-block-type": layout.block_type,
                "data-shape": layout.shape,
            },
        )
        return RenderFragment(
            markup=markup,
            flow_height=layout.flow_height,
            bounds_x=x + layout.bounds_x,
            bounds_y=y + layout.bounds_y,
        )
