#!/usr/bin/env python3
"""Render scratch-yaml into boxed ASCII art with stream-based v4 connectors."""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

LVL_PREFIX = "│ "
BLOCK_CATALOG_PATH = Path(__file__).resolve().parents[1] / "references" / "BLOCK_CATALOG.yaml"


def load_block_catalog() -> dict[str, dict]:
    with BLOCK_CATALOG_PATH.open(encoding="utf-8") as f:
        blocks = yaml.safe_load(f) or []
    return {
        block["opcode"]: block
        for block in blocks
        if isinstance(block, dict) and isinstance(block.get("opcode"), str)
    }


BLOCK_CATALOG = load_block_catalog()


@dataclass
class Item:
    width: int
    level: int
    content: str = ""


def parse_args():
    parser = argparse.ArgumentParser(prog="render_ascii.py")
    parser.add_argument("file", nargs="?", default="-", help="scratch-yaml file path or - for stdin")
    parser.add_argument("--yaml", help="scratch-yaml text to render directly")
    parser.add_argument("--targets", nargs="+", metavar="NAME", help="only render these target names")
    return parser.parse_args()


def read_input(path: str, yaml_text: str | None = None) -> str:
    if yaml_text is not None:
        return yaml_text
    if path != "-":
        if not os.path.isfile(path):
            raise SystemExit(f"Error: file not found: {path}")
        with open(path, encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Usage: python3 render_ascii.py [blocks.yaml|-] [--yaml TEXT] [--targets NAME ...]")


def parse_targets(text: str, base_dir: Path | None = None) -> list[tuple[str, list[dict]]]:
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
    if isinstance(data, dict):
        return [(data.get("name", "Unnamed"), data.get("blocks", []) or [])]
    if not isinstance(data, list):
        raise SystemExit("Expected scratch-yaml to be a target object or top-level list of targets")

    if all(isinstance(target, dict) and isinstance(target.get("path"), str) for target in data):
        if base_dir is None:
            raise SystemExit("Cannot resolve scratch-yaml index paths without a base directory")
        targets = []
        for target in data:
            name = target.get("name", "Unnamed")
            target_path = base_dir / target["path"]
            with target_path.open(encoding="utf-8") as f:
                target_data = yaml.safe_load(f.read()) or {}
            if not isinstance(target_data, dict):
                raise SystemExit(f"Expected target file to contain one target object: {target_path}")
            scripts = target_data.get("blocks", []) or []
            targets.append((name, scripts))
        return targets

    targets = []
    for target in data:
        if not isinstance(target, dict):
            continue
        name = target.get("name", "Unnamed")
        scripts = target.get("blocks", []) or []
        targets.append((name, scripts))
    return targets


def humanize(opcode: str, params: list | None = None) -> str:
    params = params or []
    block = BLOCK_CATALOG.get(opcode)
    if not isinstance(block, dict):
        if not params:
            return opcode
        formatted = ", ".join(format_param_value(param) for param in params)
        return f"{opcode} ({formatted})"

    texts = block.get("text")
    if not isinstance(texts, list):
        texts = [opcode]
    param_specs = block.get("params")
    if not isinstance(param_specs, list):
        param_specs = []

    parts: list[str] = []
    count = max(len(texts), len(params), len(param_specs))
    for i in range(count):
        if i < len(texts) and isinstance(texts[i], str) and texts[i]:
            parts.append(texts[i])
        if i < len(params) or i < len(param_specs):
            raw_value = params[i] if i < len(params) else None
            param_spec = param_specs[i] if i < len(param_specs) and isinstance(param_specs[i], dict) else {}
            param_type = str(param_spec.get("type", ""))
            if raw_value is None:
                if "value" in param_spec:
                    raw_value = param_spec["value"]
                elif param_type == "boolean":
                    parts.append("<>")
                    continue
                elif param_type.startswith("dropdown"):
                    parts.append("[ ▼]")
                    continue
                else:
                    parts.append("()")
                    continue
            value = format_param_value(raw_value)
            if isinstance(raw_value, bool) or param_type == "boolean":
                parts.append(f"<{value}>")
            elif param_type.startswith("dropdown"):
                parts.append(f"[{value} ▼]")
            else:
                parts.append(f"({value})")

    return " ".join(parts) if parts else opcode


def format_param_value(value) -> str:
    if isinstance(value, dict) and "opcode" in value:
        return humanize(value["opcode"], value.get("params", []))
    if isinstance(value, dict) and value.get("type") in {"variable", "list", "broadcast"}:
        return str(value["name"])
    return "true" if value is True else "false" if value is False else str(value)


def get_num_branches(block_spec: dict) -> int:
    if not block_spec:
        return 0
    shapes = block_spec.get("shapes")
    if "c-1" in shapes:
        return 1
    elif "c-2" in shapes:
        return 2
    return 0


def flatten_sequence(blocks: list[dict], level: int = 0) -> list[Item]:
    items: list[Item] = []
    for block in blocks:
        text = humanize(block['opcode'], block.get('params', []))
        text = f" {text} "
        width = len(text)
        items.append(Item(width, level, text))

        block_spec = BLOCK_CATALOG.get(block["opcode"])
        nested_blocks = block.get("blocks")
        num_branch = get_num_branches(block_spec)
        if not nested_blocks and num_branch == 0:
            continue
        if not nested_blocks:
            nested_blocks = []
        num_missed_branches = num_branch - len(nested_blocks)
        if num_missed_branches > 0:
            nested_blocks.extend([[] for _ in range(num_missed_branches)])

        nested_level = level + 1
        branch_labels = block_spec.get("branch_labels", []) if block_spec else []
        for i, branch in enumerate(nested_blocks):
            if len(branch) == 0:
                items.append(Item(0, nested_level, ""))
            else:
                items.extend(flatten_sequence(branch, nested_level))
            branch_label = branch_labels[i] if i < len(branch_labels) else None
            label_content = None
            if branch_label:
                pos = branch_label.get("position", "left")
                label_text = branch_label["text"]
                diff = width - len(label_text) - 1
                if label_text and diff > 0:
                    if pos == "left":
                        label_content = " " + label_text + " " * diff
                    else:
                        label_content = " " * diff + label_text + " "
            items.append(Item(width, level, label_content))
    return items


def connector_line(level1: int, width1: int, level2: int, width2: int) -> str:
    if abs(level2 - level1) > 1:
        raise ValueError("levels can only stay the same or move by 1")
    if width1 < 0 or width2 < 0 or (width1 == 0 and width2 == 0):
        raise ValueError("widths must be positive")

    if level1 == 0 and width1 == 0:
        return "┌" + "─" * width2 + "┐"
    elif level2 == 0 and width2 == 0:
        return "└" + "─" * width1 + "┘"

    delta_level = level2 - level1
    num_prefix = 0
    if delta_level == 0:
        num_prefix = level1
    else:
        num_prefix = min(level1, level2) + 1
    prefix = LVL_PREFIX * num_prefix
    real_width1 = width1 + level1 * len(LVL_PREFIX)
    real_width2 = width2 + level2 * len(LVL_PREFIX)

    if delta_level == 1:
        left = "┌"
    elif delta_level == -1:
        left = "└"
    else:
        left = "├"

    if width1 != 0 and real_width1 < real_width2:
        middle = "┴"
    elif width2 != 0 and real_width1 > real_width2:
        middle = "┬"
    else:
        middle = ""

    span1 = "─" * (min(real_width1, real_width2) - len(prefix))
    span2 = "─" * (abs(real_width1 - real_width2) - len(middle))

    if real_width1 < real_width2:
        right = "┐"
    elif real_width1 > real_width2:
        right = "┘"
    else:
        right = "┤"

    return prefix + left + span1 + middle + span2 + right


def content_line(level: int, content: str) -> str:
    prefix = LVL_PREFIX * level
    if content:
        return prefix + "│" + content + "│"
    else:
        return prefix + "│"


def render_items(items: list[Item]) -> list[str]:
    if not items:
        return []
    lines = [connector_line(0, 0, 0, items[0].width)]
    for i, item in enumerate(items):
        if item.content is not None:
            inner = item.content.ljust(max(item.width, 0))
            lines.append(content_line(item.level, inner))
        next_width = (items[i + 1].width) if i + 1 < len(items) else 0
        next_level = items[i + 1].level if i + 1 < len(items) else 0
        lines.append(connector_line(item.level, item.width, next_level, next_width))
    return lines


def render(text: str, targets: list[str] | None = None, base_dir: Path | None = None) -> str:
    out = []
    for name, scripts in parse_targets(text, base_dir):
        if targets and name not in targets:
            continue
        out.append(f"# {name}")
        if not scripts:
            out.extend(["(no scripts)", ""])
            continue
        for i, script in enumerate(scripts, 1):
            out.extend([f"[script {i}]", *render_items(flatten_sequence(script)), ""])
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    args = parse_args()
    base_dir = None
    if args.yaml is None and args.file != "-":
        base_dir = Path(args.file).resolve().parent
    sys.stdout.write(render(read_input(args.file, args.yaml), args.targets, base_dir))
