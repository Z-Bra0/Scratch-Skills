"""Geometry and path helpers for grouped Scratch SVG rendering."""

from __future__ import annotations

from .config import BLOCK_H, HAT_H, INNER_INDENT

CORNER_PREFIX = "a 4 4 0"
CORNER_TL = f"{CORNER_PREFIX} 0 1 4 -4"
CORNER_TR = f"{CORNER_PREFIX} 0 1 4 4"
CORNER_BL = f"{CORNER_PREFIX} 0 1 -4 -4"
CORNER_BR = f"{CORNER_PREFIX} 0 1 -4 4"
CORNER_BR_REV = f"{CORNER_PREFIX} 0 0 -4 4"
CORNER_TR_REV = f"{CORNER_PREFIX} 0 0 4 4"
CORNER_W = 4
CORNER_BOWLER_W = 20

CONCAVE_L = "c 2 0 3 1 4 2 l 4 4 c 1 1 2 2 4 2 h 12 c 2 0 3 -1 4 -2 l 4 -4 c 1 -1 2 -2 4 -2"
CONCAVE_R = "c -2 0 -3 1 -4 2 l -4 4 c -1 1 -2 2 -4 2 h -12 c -2 0 -3 -1 -4 -2 l -4 -4 c -1 -1 -2 -2 -4 -2"
CONCAVE_W = 36
PATH_END = "z"

HAT = "c 25 -22 71 -22 96 0"
HAT_W = 96
BRANCH_W_OFFSET = INNER_INDENT


def _fmt(value: float) -> str:
    return f"{value:.1f}"


def _v_bar(height: float) -> str:
    return f"v {_fmt(height)}"


def _h_bar(width: float) -> str:
    return f"h {_fmt(width)}"


def _pos(x: float, y: float) -> str:
    return f"m {_fmt(x)} {_fmt(y)}"


def _header_w_hat(width: float) -> str:
    bar = _h_bar(max(0.0, width - HAT_W + CORNER_W))
    return f"{HAT} {bar} {CORNER_TR}"


def _header_w_concave(width: float, reverse: bool = False) -> str:
    bar1_w = 8.0
    bar1 = _h_bar(bar1_w)
    bar2 = _h_bar(width - CONCAVE_W - bar1_w)
    prefix = CORNER_TR_REV if reverse else CORNER_TL
    return f"{prefix} {bar1} {CONCAVE_L} {bar2} {CORNER_TR}"


def _header_w_bowlerhat(width: float) -> str:
    bar = _h_bar(width)
    return f"a 20 20 0 0 1 20 -20 {bar} a 20 20 0 0 1 20 20"


def _footer_w_convex(width: float, reverse: bool = False) -> str:
    bar2_w = 8.0
    bar1 = _h_bar(-(width - CONCAVE_W - bar2_w))
    bar2 = _h_bar(-bar2_w)
    postfix = CORNER_BR_REV if reverse else CORNER_BL
    return f"{CORNER_BR} {bar1} {CONCAVE_R} {bar2} {postfix}"


def _footer_w_flat_line(width: float) -> str:
    return f"{CORNER_BR} {_h_bar(-width)} {CORNER_BL}"


def _statement_d(width: float, has_next: bool) -> str:
    footer = _footer_w_convex(width) if has_next else _footer_w_flat_line(width)
    dots = [
        _pos(0.0, CORNER_W),
        _header_w_concave(width),
        _v_bar(BLOCK_H - CORNER_W * 2),
        footer,
        PATH_END,
    ]
    return " ".join(dots)


def _hat_d(width: float) -> str:
    dots = [
        _pos(0.0, HAT_H),
        _header_w_hat(width),
        _v_bar(BLOCK_H - CORNER_W * 2),
        _footer_w_convex(width),
        PATH_END,
    ]
    return " ".join(dots)


def _bowlerhat_d(width: float) -> str:
    dots = [
        _pos(0, 0),
        _header_w_bowlerhat(width - CORNER_BOWLER_W * 2),
        _v_bar(BLOCK_H),
        _footer_w_convex(width - CORNER_W * 2),
        PATH_END,
    ]
    return " ".join(dots)


def _branch_d(width: float, inner_height: float) -> str:
    branch_width = width - BRANCH_W_OFFSET
    dots = [
        _v_bar(BLOCK_H - CORNER_W * 2),
        _footer_w_convex(branch_width, reverse=True),
        _v_bar(inner_height - CORNER_W * 2),
        _header_w_concave(branch_width, reverse=True),
    ]
    return " ".join(dots)


def _c_block_d(width: float, branch_heights: list[float], has_next: bool) -> str:
    footer_height = BLOCK_H / 2
    footer = _footer_w_convex(width) if has_next else _footer_w_flat_line(width)
    dots = [_pos(0.0, CORNER_W), _header_w_concave(width)]
    for inner_height in branch_heights:
        dots.append(_branch_d(width, inner_height))
    dots.extend([_v_bar(footer_height - CORNER_W * 2), footer, PATH_END])
    return " ".join(dots)


def _curve_box_d(x: float, y: float, width: float, height: float) -> str:
    curve_w = height / 2
    curve_r = f"a {_fmt(curve_w)} {_fmt(curve_w)} 0 0 1 0 {_fmt(height)}"
    curve_l = f"a {_fmt(curve_w)} {_fmt(curve_w)} 0 0 1 0 {_fmt(-height)}"
    dots = [_pos(x, y), _pos(x + curve_w, y), _h_bar(width), curve_r, _h_bar(-width), curve_l, PATH_END]
    return " ".join(dots)


def curve_box(x: float, y: float, width: float, height: float) -> str:
    return f'<path d="{_curve_box_d(x, y, width, height)}"/>'


def _angled_box_d(x: float, y: float, width: float, height: float) -> str:
    half = height / 2
    dots = [
        _pos(x, y),
        _pos(x + half, y),
        _h_bar(width),
        f"l {_fmt(half)} {_fmt(half)}",
        f"l {_fmt(-half)} {_fmt(half)}",
        _h_bar(-width),
        f"l {_fmt(-half)} {_fmt(-half)}",
        f"l {_fmt(half)} {_fmt(-half)}",
        PATH_END,
    ]
    return " ".join(dots)


def angled_box(x: float, y: float, width: float, height: float) -> str:
    return f'<path d="{_angled_box_d(x, y, width, height)}"/>'


def _rect_box_d(x: float, y: float, width: float, height: float) -> str:
    dots = [
        _pos(x, y),
        _h_bar(width),
        _v_bar(height),
        _h_bar(-width),
        _v_bar(-height),
        PATH_END,
    ]
    return " ".join(dots)


def _rounded_rect_d(x: float, y: float, width: float, height: float) -> str:
    inner_w = max(0.0, width - CORNER_W * 2)
    inner_h = max(0.0, height - CORNER_W * 2)
    dots = [
        _pos(x, y + CORNER_W),
        CORNER_TL,
        _h_bar(inner_w),
        CORNER_TR,
        _v_bar(inner_h),
        CORNER_BR,
        _h_bar(-inner_w),
        CORNER_BL,
        _v_bar(-inner_h),
        PATH_END,
    ]
    return " ".join(dots)


def _top_rounded_rect_d(x: float, y: float, width: float, height: float) -> str:
    inner_w = max(0.0, width - CORNER_W * 2)
    side_h = max(0.0, height - CORNER_W)
    dots = [
        _pos(x, y + CORNER_W),
        CORNER_TL,
        _h_bar(inner_w),
        CORNER_TR,
        _v_bar(side_h),
        _h_bar(-width),
        _v_bar(-side_h),
        PATH_END,
    ]
    return " ".join(dots)


def _bottom_rounded_rect_d(x: float, y: float, width: float, height: float) -> str:
    inner_w = max(0.0, width - CORNER_W * 2)
    side_h = max(0.0, height - CORNER_W)
    dots = [
        _pos(x, y),
        _h_bar(width),
        _v_bar(side_h),
        CORNER_BR,
        _h_bar(-inner_w),
        CORNER_BL,
        _v_bar(-side_h),
        PATH_END,
    ]
    return " ".join(dots)


def rect_box(x: float, y: float, width: float, height: float) -> str:
    return f'<path d="{_rect_box_d(x, y, width, height)}"/>'
