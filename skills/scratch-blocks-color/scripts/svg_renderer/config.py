"""Shared configuration and constants for the grouped Scratch SVG renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]

DROPDOWN_VALUE_TEXT = {
    "_random_": "random position",
    "_mouse_": "mouse-pointer",
    "_myself_": "myself",
    "_stage_": "Stage",
}

CAT_COLOURS: dict[str, dict[str, str]] = {
    "motion": {"p": "#4C97FF", "s": "#4280D7", "t": "#3373CC"},
    "looks": {"p": "#9966FF", "s": "#855CD6", "t": "#774DCB"},
    "sound": {"p": "#CF63CF", "s": "#C94FC9", "t": "#BD42BD"},
    "control": {"p": "#FFAB19", "s": "#EC9C13", "t": "#CF8B17"},
    "events": {"p": "#FFBF00", "s": "#E6AC00", "t": "#CC9900"},
    "sensing": {"p": "#5CB1D6", "s": "#47A8D1", "t": "#2E8EB8"},
    "operators": {"p": "#59C059", "s": "#46B946", "t": "#389438"},
    "data": {"p": "#FF8C1A", "s": "#FF8000", "t": "#DB6E00"},
    "lists": {"p": "#FF661A", "s": "#FF5500", "t": "#E64D00"},
    "procedures": {"p": "#FF6680", "s": "#FF4D6A", "t": "#FF3355"},
    "math": {"p": "#59C059", "s": "#46B946", "t": "#389438"},
    "procedures": {"p": "#FF6680", "s": "#FF4D6A", "t": "#FF3355"},
    "unknown": {"p": "#888888", "s": "#777777", "t": "#666666"},
}
CATEGORY_ALIASES = {"data-lists": "lists", "sounds": "sound", None: "unknown"}

BLOCK_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "BLOCK_CATALOG.json"

RIGHT_TURN_ICON = '<path transform="scale(0.03)" fill="#ffffff" d="m 386.3 160 l -50.3 0 c -17.7 0 -32 14.3 -32 32 s 14.3 32 32 32 l 128 0 c 17.7 0 32 -14.3 32 -32 l 0 -128 c 0 -17.7 -14.3 -32 -32 -32 s -32 14.3 -32 32 l 0 51.2 l -17.6 -17.6 c -87.5 -87.5 -229.3 -87.5 -316.8 0 s -87.5 229.3 0 316.8 s 229.3 87.5 316.8 0 c 12.5 -12.5 12.5 -32.8 0 -45.3 s -32.8 -12.5 -45.3 0 c -62.5 62.5 -163.8 62.5 -226.3 0 s -62.5 -163.8 0 -226.3 s 163.8 -62.5 226.3 0 l 17.2 17.2 z"></path>'
LEFT_TURN_ICON = '<path transform="scale(0.03)" fill="#ffffff" d="m 48.5 224 l -8.5 0 c -13.3 0 -24 -10.7 -24 -24 l 0 -128 c 0 -9.7 5.8 -18.5 14.8 -22.2 s 19.3 -1.7 26.2 5.2 l 41.6 41.6 c 87.6 -86.5 228.7 -86.2 315.8 1 c 87.5 87.5 87.5 229.3 0 316.8 s -229.3 87.5 -316.8 0 c -12.5 -12.5 -12.5 -32.8 0 -45.3 s 32.8 -12.5 45.3 0 c 62.5 62.5 163.8 62.5 226.3 0 s 62.5 -163.8 0 -226.3 c -62.2 -62.2 -162.7 -62.5 -225.3 -1 l 41.1 41.2 c 6.9 6.9 8.9 17.2 5.2 26.2 s -12.5 14.8 -22.2 14.8 l -119.5 0 z"></path>'
FLAG_ICON = '<path transform="scale(0.03)" fill="#4CBF56" d="m 64 32 c 0 -17.7 -14.3 -32 -32 -32 s -32 14.3 -32 32 l 0 32 l 0 304 l 0 112 c 0 17.7 14.3 32 32 32 s 32 -14.3 32 -32 l 0 -128 l 64.3 -16.1 c 41.1 -10.3 84.6 -5.5 122.5 13.4 c 44.2 22.1 95.5 24.8 141.7 7.4 l 34.7 -13 c 12.5 -4.7 20.8 -16.6 20.8 -30 l 0 -247.7 c 0 -23 -24.2 -38 -44.8 -27.7 l -9.6 4.8 c -46.3 23.2 -100.8 23.2 -147.1 0 c -35.1 -17.6 -75.4 -22 -113.5 -12.5 l -69 17.4 l 0 -16 z"></path>'
UP_ICON = '<path transform="scale(0.03)" fill="#ffffff" d="m 350 177.5 c 3.8 -8.8 2 -19 -4.6 -26 l -136 -144 c -4.5 -4.8 -10.8 -7.5 -17.4 -7.5 s -12.9 2.7 -17.4 7.5 l -136 144 c -6.6 7 -8.4 17.2 -4.6 26 s 12.5 14.5 22 14.5 l 88 0 l 0 192 c 0 17.7 -14.3 32 -32 32 l -80 0 c -17.7 0 -32 14.3 -32 32 l 0 32 c 0 17.7 14.3 32 32 32 l 80 0 c 70.7 0 128 -57.3 128 -128 l 0 -192 l 88 0 c 9.6 0 18.2 -5.7 22 -14.5 z"></path>'
ICON_RENDER_SIZE = 14.0
ICON_TOKEN_MAP = {
    "Flag": FLAG_ICON,
    "↱": RIGHT_TURN_ICON,
    "↰": LEFT_TURN_ICON,
    "↺": UP_ICON,
}
ICON_TOKEN_ORDER = ("Flag", "↱", "↰", "↺")
BLOCK_H = 48
C_INNER_MIN_H = 40
FONT_SIZE = 14
HAT_H = 20
INNER_INDENT = 20
NOTCH_H = 8
STACK_GAP = 48
PAD_X = 16
CHAR_W_FACTOR = 6.5 / 11
TEXT_X_OFFSET = 10
SEGMENT_GAP = 6
CONTENT_PAD_Y = 16
PARAM_PAD_X = 10
PARAM_PAD_Y = 6
PARAM_MIN_H = 24
PARAM_MIN_W = 50
ANGLE_EXTRA_PAD_X = 6
LEADING_PARAM_PAD_X = 12
PARAM_TEXT_COLOUR = "#575E75"
DROPDOWN_EXTRA_W = 8
VARIABLE_MONITOR_BG = "#E6F0FF"
VARIABLE_MONITOR_STROKE = "#A8C3E8"
VARIABLE_MONITOR_VALUE_BG = "#FF8D1A"
VARIABLE_MONITOR_VALUE_STROKE = "#DB6E00"
VARIABLE_MONITOR_TEXT = "#000000"
VARIABLE_MONITOR_VALUE_TEXT = "#FFFFFF"
VARIABLE_MONITOR_MIN_H = 32
VARIABLE_MONITOR_PAD_X = 10
VARIABLE_MONITOR_PAD_Y = 8
VARIABLE_MONITOR_VALUE_PAD_X = 10
VARIABLE_MONITOR_VALUE_MIN_W = 40


def text_width(text: str) -> float:
    return len(text) * FONT_SIZE * CHAR_W_FACTOR


def display_value_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return DROPDOWN_VALUE_TEXT.get(text, text)
