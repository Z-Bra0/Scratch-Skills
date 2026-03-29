#!/usr/bin/env python3
"""Parse Scratch block metadata from an exported block reference HTML file."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_content(node: ET.Element) -> str:
    return "".join(node.itertext()).replace("\xa0", " ").strip()


def parse_blocks(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8").replace("&nbsp;", "&#160;")
    wrapped = f'<root xmlns:xlink="http://www.w3.org/1999/xlink">{raw}</root>'
    root = ET.fromstring(wrapped)

    blocks = []
    for node in root.iter():
        if local_name(node.tag) != "g":
            continue
        classes = (node.get("class") or "").split()
        if "blocklyDraggable" not in classes:
            continue

        texts = [
            text_content(child)
            for child in node.iter()
            if local_name(child.tag) == "text" and text_content(child)
        ]

        blocks.append(
            {
                "id": node.get("data-id"),
                "shapes": node.get("data-shapes"),
                "category": node.get("data-category"),
                "text": texts[0] if len(texts) == 1 else texts,
            }
        )
    return blocks


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 tools/parse_block_ref.py <block_ref.html>")
    path = Path(sys.argv[1])
    json.dump(parse_blocks(path), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
