"""Shared render models for the grouped Scratch SVG renderer."""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import ParamSpec
from .config import JsonDict


@dataclass(frozen=True)
class RenderFragment:
    markup: str
    flow_height: float
    bounds_x: float
    bounds_y: float


@dataclass(frozen=True)
class InlineSegmentLayout:
    kind: str
    width: float
    height: float
    x: float
    y: float
    children: tuple[str, ...]
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class InlineContentLayout:
    segments: tuple[InlineSegmentLayout, ...]
    width: float
    height: float


@dataclass(frozen=True)
class BranchLayout:
    branch_height: float
    stack_origin: tuple[float, float]
    nested_stack: RenderFragment | None
    label_text: str
    label_position: str
    label_y: float


@dataclass(frozen=True)
class StackedInlineContentLayout:
    children: tuple[str, ...]
    width: float
    height: float


@dataclass(frozen=True)
class MonitorPanelLayout:
    y: float
    width: float
    height: float
    fill: str
    stroke: str
    path_d: str
    content_origin: tuple[float, float]
    content: InlineContentLayout | None = None
    content_children: tuple[str, ...] = ()
    content_role: str = "content"


@dataclass(frozen=True)
class BlockLayout:
    block_type: str
    shape: str
    width: float
    height: float
    flow_height: float
    bounds_x: float
    bounds_y: float
    fill: str
    stroke: str
    path_d: str
    content_origin: tuple[float, float]
    content: InlineContentLayout
    branches: tuple[BranchLayout, ...] = ()
    panels: tuple[MonitorPanelLayout, ...] = ()


@dataclass(frozen=True)
class ParamRenderPolicy:
    box_kind: str
    fill: str
    text_colour: str
    show_text: bool
    show_arrow: bool


@dataclass(frozen=True)
class ProcedureSignatureSpec:
    text_segments: tuple[str, ...]
    params: tuple[ParamSpec, ...]
    param_connections: tuple[JsonDict, ...]

