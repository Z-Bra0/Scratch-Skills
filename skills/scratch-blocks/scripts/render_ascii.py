#!/usr/bin/env python3
"""Render scratch-yaml into boxed ASCII art with stream-based v4 connectors."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import yaml

LABELS = {
    "control_forever": "forever",
    "control_if": "if",
    "control_if_else": "if else",
    "control_repeat": "repeat",
    "control_wait": "wait",
    "data_showvariable": "show variable",
    "event_whenflagclicked": "when flag clicked",
    "event_whenkeypressed": "when key pressed",
    "looks_hide": "hide",
    "looks_say": "say",
    "looks_show": "show",
    "motion_changexby": "change x by",
    "motion_changeyby": "change y by",
    "motion_glideto": "glide to",
    "motion_goto": "go to",
    "motion_movesteps": "move",
    "motion_setx": "set x to",
    "motion_sety": "set y to",
    "motion_turnleft": "turn left",
    "motion_turnright": "turn right",
    "motion_xposition": "x position",
    "motion_yposition": "y position",
    "pen_clear": "clear",
    "pen_penDown": "pen down",
    "sensing_answer": "answer",
    "sensing_keypressed": "key pressed?",
}


@dataclass
class Item:
    kind: str
    width: int
    level: int
    content: str = ""


def read_input() -> str:
    if len(sys.argv) > 2:
        raise SystemExit("Usage: python3 render_ascii.py [blocks.yaml|-]")
    if len(sys.argv) == 2 and sys.argv[1] != "-":
        path = sys.argv[1]
        if not os.path.isfile(path):
            raise SystemExit(f"Error: file not found: {path}")
        with open(path, encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Usage: python3 render_ascii.py [blocks.yaml|-]")


def parse_targets(text: str) -> list[tuple[str, list[dict]]]:
    stripped = text.lstrip()
    if stripped.startswith("# "):
        targets, name, body = [], None, []
        for line in text.splitlines():
            if line.startswith("# ") and not line.startswith(("# Variables:", "# List:")):
                if name is not None:
                    targets.append((name, yaml.safe_load("\n".join(body)) or []))
                name, body = line[2:].strip(), []
            elif name is not None and not line.startswith(("# Variables:", "# List:")):
                body.append(line)
        if name is not None:
            targets.append((name, yaml.safe_load("\n".join(body)) or []))
        return targets

    data = yaml.safe_load(text) or []
    if not isinstance(data, list):
        raise SystemExit("Expected scratch-yaml to be a top-level list of targets")

    targets = []
    for target in data:
        if not isinstance(target, dict):
            continue
        name = target.get("name", "Unnamed")
        scripts = target.get("blocks", []) or []
        targets.append((name, scripts))
    return targets


def humanize(opcode: str) -> str:
    return LABELS.get(opcode, opcode.split("_", 1)[-1].replace("_", " "))


def block_text(block: dict) -> str:
    def item(value) -> str:
        if isinstance(value, dict) and "opcode" in value:
            return block_text(value)
        if isinstance(value, dict) and value.get("type") in {"variable", "list", "broadcast"}:
            return str(value["name"])
        return "true" if value is True else "false" if value is False else str(value)

    params = ", ".join(item(v) for v in block.get("params", []))
    label = humanize(block["opcode"])
    return label if not params else f"{label} ({params})"


def total_width(text: str) -> int:
    return len(text) + 4


def flatten_sequence(blocks: list[dict], level: int = 0) -> list[Item]:
    items: list[Item] = []
    for block in blocks:
        text = block_text(block)
        width = total_width(text)
        items.append(Item("block", width, level, text))

        branches = list(block.get("blocks", []))
        for idx in range(len(branches)):
            branch = branches[idx] if idx < len(branches) else []
            nested_level = level + 1
            local_width = max(width - len(guide(nested_level)), 4)
            if branch:
                items.extend(flatten_sequence(branch, nested_level))
            else:
                items.append(Item("blank", local_width, nested_level, ""))
            items.append(Item("close", local_width, nested_level, ""))
    return items


def guide(level: int) -> str:
    return "┃ " * level


def top_line(width: int) -> str:
    return f"┏{'━' * (width - 2)}┓"


def bottom_line(width: int) -> str:
    return f"┗{'━' * (width - 2)}┛"


def draw_connector(width: int, level: int, next_width: int, next_level: int) -> str:
    prefix = guide(next_level)
    if width == 0:
        return prefix + top_line(next_width)
    if next_width == 0:
        return prefix + bottom_line(width)

    if next_level == level + 1:
        available = max(width - len(prefix), 0)
        if next_width == width:
            body = top_line(next_width)
        elif next_width < width:
            tail = max(available - next_width - 1, 0)
            body = top_line(next_width) + ("━" * tail) + "┛"
        else:
            left = max(available - 2, 0)
            right = max(next_width - available - 1, 0)
            body = "┏" + ("━" * left) + "┛" + ("━" * right) + "┓"
        return prefix + body

    if next_level == level - 1:
        available = max(next_width - len(guide(level)), 0)
        if width == next_width:
            return prefix + ("━" * next_width)
        if width < next_width:
            tail = max(available - width - 1, 0)
            bridge = "┛" + ("━" * max(width - 2, 0)) + "┓"
            return prefix + bridge + ("━" * tail)
        left = max(available - 2, 0)
        right = max(width - available - 1, 0)
        return prefix + "┓" + ("━" * left) + "┛" + ("━" * right)

    if next_width == width:
        return prefix + ("━" * width)
    if next_width > width:
        return prefix + f"┛{'━' * (next_width - 2)}┓"
    return prefix + f"┓{'━' * (width - 2)}┛"


def draw_content(item: Item) -> str | None:
    if item.kind == "close":
        return None
    inner = item.content.ljust(max(item.width - 4, 1))
    return guide(item.level) + f"┃ {inner} ┃"


def render_items(items: list[Item]) -> list[str]:
    if not items:
        return []
    lines = [draw_connector(0, 0, items[0].width, items[0].level)]
    for i, item in enumerate(items):
        content = draw_content(item)
        if content is not None:
            lines.append(content)
        next_width = items[i + 1].width if i + 1 < len(items) else 0
        next_level = items[i + 1].level if i + 1 < len(items) else 0
        lines.append(draw_connector(item.width, item.level, next_width, next_level))
    return lines


def render(text: str) -> str:
    out = []
    for name, scripts in parse_targets(text):
        out.append(f"# {name}")
        if not scripts:
            out.extend(["(no scripts)", ""])
            continue
        for i, script in enumerate(scripts, 1):
            out.extend([f"[script {i}]", *render_items(flatten_sequence(script)), ""])
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    sys.stdout.write(render(read_input()))
