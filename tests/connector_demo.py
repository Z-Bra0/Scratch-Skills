#!/usr/bin/env python3
"""Prototype connector renderer based only on two box levels and widths."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "scratch-blocks", "scripts"))
from render_ascii import connector_line, content_line


CASES = [
    ("top", 0, 0, 0, 12),
    ("flat_same_width", 0, 12, 0, 12),
    ("flat_b1_long_b2_short", 0, 24, 0, 8),
    ("flat_b1_short_b2_long", 0, 8, 0, 24),
    ("down_same_width", 0, 12, 1, 12),
    ("down_same_width_off_-1", 0, 12, 1, 11),
    ("down_same_width_off_-2", 0, 12, 1, 10),
    ("down_same_width_level_1_to_2", 1, 12, 2, 12),
    ("down_b1_longer", 0, 20, 1, 10),
    ("down_b1_shorter", 0, 10, 1, 20),
    ("up_same_width", 1, 12, 0, 12),
    ("up_same_width_off_-1", 1, 12, 0, 11),
    ("up_same_width_off_-2", 1, 12, 0, 10),
    ("up_same_width_level_2_to_1", 2, 12, 1, 12),
    ("up_b1_longer", 1, 20, 0, 10),
    ("up_b1_shorter", 1, 10, 0, 20),
    ("bottom", 0, 12, 0, 0),
]

CONTENT_LINE_CASES = [
    ("level 0", 0, "content1"),
    ("level 1", 1, "content2"),
    ("level 2", 2, "content3"),
]

def main():
    for name, level1, width1, level2, width2 in CASES:
        print(f"=== {name} ===")
        print(f"b1: level={level1}, width={width1}")
        print(f"b2: level={level2}, width={width2}")
        print(connector_line(level1, width1, level2, width2))
        print()

    for name, level, content in CONTENT_LINE_CASES:
        print(f"=== {name} ===")
        print(content_line(level, content))
        print()


if __name__ == "__main__":
    main()
