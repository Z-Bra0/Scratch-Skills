import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = ROOT / "skills/scratch-blocks/scripts/render_ascii.py"
OUTPUT_SPRITE_YAML = ROOT / "output/sprite.yaml"


def load_render_module():
    spec = importlib.util.spec_from_file_location("render_ascii_viewer", RENDER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalize_multiline(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


RENDER_CASES = {
    "flat_same_length": (
        """
        - name: Sprite1
          blocks:
            - - opcode: looks_show
              - opcode: looks_hide
        """,
        """
        # Sprite1
        [script 1]
        ┌──────┐
        │ show │
        ├──────┤
        │ hide │
        └──────┘
        """,
    ),
    "flat_b1_long_b2_short": (
        """
        - name: Sprite1
          blocks:
            - - opcode: event_whenkeypressed
                params: [space]
              - opcode: looks_show
        """,
        """
        # Sprite1
        [script 1]
        ┌────────────────────────────┐
        │ when [space ▼] key pressed │
        ├──────┬─────────────────────┘
        │ show │
        └──────┘
        """,
    ),
    "flat_b1_short_b2_long": (
        """
        - name: Sprite1
          blocks:
            - - opcode: looks_show
              - opcode: event_whenkeypressed
                params: [space]
        """,
        """
        # Sprite1
        [script 1]
        ┌──────┐
        │ show │
        ├──────┴─────────────────────┐
        │ when [space ▼] key pressed │
        └────────────────────────────┘
        """,
    ),
    "same_length": (
        """
        - name: Sprite1
          blocks:
            - - opcode: control_repeat
                params: [10]
                blocks:
                  - - opcode: looks_say
                      params: [hi]
        """,
        """
        # Sprite1
        [script 1]
        ┌─────────────┐
        │ repeat (10) │
        │ ┌──────────┬┘
        │ │ say (hi) │
        │ └──────────┴┐
        │           ↺ │
        └─────────────┘
        """,
    ),
    "parent_longer_child_shorter": (
        """
        - name: Sprite1
          blocks:
            - - opcode: control_repeat
                params: [100000]
                blocks:
                  - - opcode: looks_say
                      params: [hi]
        """,
        """
        # Sprite1
        [script 1]
        ┌─────────────────┐
        │ repeat (100000) │
        │ ┌──────────┬────┘
        │ │ say (hi) │
        │ └──────────┴────┐
        │               ↺ │
        └─────────────────┘
        """,
    ),
    "parent_shorter_child_longer": (
        """
        - name: Sprite1
          blocks:
            - - opcode: control_repeat
                params: [1]
                blocks:
                  - - opcode: looks_say
                      params: [this is a much longer nested message]
        """,
        """
        # Sprite1
        [script 1]
        ┌────────────┐
        │ repeat (1) │
        │ ┌──────────┴─────────────────────────────────┐
        │ │ say (this is a much longer nested message) │
        │ └──────────┬─────────────────────────────────┘
        │          ↺ │
        └────────────┘
        """,
    ),
    "nested_shorter_than_following_block": (
        """
        - name: Sprite1
          blocks:
            - - opcode: control_repeat
                params: [3]
                blocks:
                  - - opcode: looks_say
                      params: [hi]
              - opcode: motion_movesteps
                params: [99999]
        """,
        """
        # Sprite1
        [script 1]
        ┌────────────┐
        │ repeat (3) │
        │ ┌──────────┤
        │ │ say (hi) │
        │ └──────────┤
        │          ↺ │
        ├────────────┴───────┐
        │ move (99999) steps │
        └────────────────────┘
        """,
    ),
    "nested_longer_than_following_block": (
        """
        - name: Sprite1
          blocks:
            - - opcode: control_repeat
                params: [3]
                blocks:
                  - - opcode: looks_say
                      params: [this nested block is much longer]
              - opcode: motion_movesteps
                params: [1]
        """,
        """
        # Sprite1
        [script 1]
        ┌────────────┐
        │ repeat (3) │
        │ ┌──────────┴─────────────────────────────┐
        │ │ say (this nested block is much longer) │
        │ └──────────┬─────────────────────────────┘
        │          ↺ │
        ├────────────┴───┐
        │ move (1) steps │
        └────────────────┘
        """,
    ),
    "empty_nested_branch": (
        """
        - name: Sprite1
          blocks:
            - - opcode: control_repeat
                params: [3]
                blocks:
                  - []
        """,
        """
        # Sprite1
        [script 1]
        ┌────────────┐
        │ repeat (3) │
        │ ┌──────────┘
        │ │
        │ └──────────┐
        │          ↺ │
        └────────────┘
        """,
    ),
    "empty_nested_branch_from_c_block_metadata": (
        """
        - name: Sprite1
          blocks:
            - - opcode: control_repeat
                params: [3]
        """,
        """
        # Sprite1
        [script 1]
        ┌────────────┐
        │ repeat (3) │
        │ ┌──────────┘
        │ │
        │ └──────────┐
        │          ↺ │
        └────────────┘
        """,
    ),
}


CONNECTOR_CASES = [
    ("top", 0, 0, 0, 12, "┌────────────┐"),
    ("flat_same_width", 0, 12, 0, 12, "├────────────┤"),
    ("flat_b1_long_b2_short", 0, 24, 0, 8, "├────────┬───────────────┘"),
    ("flat_b1_short_b2_long", 0, 8, 0, 24, "├────────┴───────────────┐"),
    ("down_same_width", 0, 12, 1, 12, "│ ┌──────────┴─┐"),
    ("down_b1_longer", 0, 20, 1, 10, "│ ┌──────────┬───────┘"),
    ("down_b1_shorter", 0, 10, 1, 20, "│ ┌────────┴───────────┐"),
    ("up_same_width", 1, 12, 0, 12, "│ └──────────┬─┘"),
    ("up_b1_longer", 1, 20, 0, 10, "│ └────────┬───────────┘"),
    ("up_b1_shorter", 1, 10, 0, 20, "│ └──────────┴───────┐"),
    ("bottom", 0, 12, 0, 0, "└────────────┘"),
]


CONTENT_LINE_CASES = [
    ("level_0", 0, " content1 ", "│ content1 │"),
    ("level_1", 1, " content2 ", "│ │ content2 │"),
    ("level_2", 2, " content3 ", "│ │ │ content3 │"),
]


HUMANIZE_CASES = [
    ("dropdown_runtime", "event_whenkeypressed", ["space"], "when [space ▼] key pressed"),
    ("numeric_runtime", "motion_movesteps", [10], "move (10) steps"),
    ("numeric_placeholder", "control_wait", [], "wait (1) seconds"),
    ("dropdown_placeholder", "motion_setrotationstyle", [], "set rotation style [left-right ▼]"),
    ("boolean_declared", "operator_and", ["lhs", "rhs"], "<lhs> and <rhs>"),
    ("boolean_missing", "operator_not", [], "not <>"),
    (
        "nested_reporter",
        "motion_turnleft",
        [
            {
                "opcode": "operator_add",
                "params": [
                    {"opcode": "operator_random", "params": [1, 10]},
                    {"opcode": "operator_mathop", "params": ["abs", 5]},
                ],
            }
        ],
        "turn ↰ ((pick random (1) to (10)) + ([abs ▼] of (5))) degrees",
    ),
]


@pytest.fixture(scope="module")
def render_module():
    return load_render_module()


@pytest.mark.parametrize(
    ("_name", "level1", "width1", "level2", "width2", "expected"),
    CONNECTOR_CASES,
)
def test_connector_line(render_module, _name, level1, width1, level2, width2, expected):
    assert render_module.connector_line(level1, width1, level2, width2) == expected


@pytest.mark.parametrize(("_name", "level", "content", "expected"), CONTENT_LINE_CASES)
def test_content_line(render_module, _name, level, content, expected):
    assert render_module.content_line(level, content) == expected


@pytest.mark.parametrize(("name", "opcode", "params", "expected"), HUMANIZE_CASES)
def test_humanize_cases(render_module, name, opcode, params, expected):
    assert render_module.humanize(opcode, params) == expected


@pytest.mark.parametrize(("name", "source_expected"), RENDER_CASES.items())
def test_render_cases(render_module, name, source_expected):
    source, expected = source_expected
    assert render_module.render(normalize_multiline(source)) == normalize_multiline(expected)


def test_render_shows_missing_boolean_placeholder(render_module):
    source = normalize_multiline(
        """
        - name: Sprite1
          blocks:
            - - opcode: control_wait_until
                params:
                  - opcode: operator_and
                    params:
                      - opcode: sensing_keypressed
                        params: [space]
                      - opcode: operator_not
        """
    )
    expected = normalize_multiline(
        """
        # Sprite1
        [script 1]
        ┌────────────────────────────────────────────────────┐
        │ wait until <<key [space ▼] pressed?> and <not <>>> │
        └────────────────────────────────────────────────────┘
        """
    )

    assert render_module.render(source) == expected


def test_render_unknown_nested_opcode_falls_back_without_crashing(render_module):
    source = normalize_multiline(
        """
        - name: Sprite1
          blocks:
            - - opcode: custom_parent
                blocks:
                  - - opcode: custom_child
        """
    )
    expected = normalize_multiline(
        """
        # Sprite1
        [script 1]
        ┌───────────────┐
        │ custom_parent │
        │ ┌─────────────┴┐
        │ │ custom_child │
        │ └─────────────┬┘
        └───────────────┘
        """
    )

    assert render_module.render(source) == expected


def test_render_fixture_output_sprite_yaml(render_module):
    expected = normalize_multiline(
        """
        # Sprite1
        [script 1]
        ┌───────────────────────────────────────────────────────────────┐
        │ turn ↰ ((pick random (1) to (10)) + ([abs ▼] of (5))) degrees │
        └───────────────────────────────────────────────────────────────┘

        [script 2]
        ┌────────────────────────────────────────────────────┐
        │ wait until <<key [space ▼] pressed?> and <not <>>> │
        └────────────────────────────────────────────────────┘
        """
    )

    assert render_module.render(OUTPUT_SPRITE_YAML.read_text(encoding="utf-8")) == expected


def test_render_cli_reads_index_yaml_and_target_files(tmp_path):
    index_path = tmp_path / "index.yaml"
    stage_path = tmp_path / "Stage.yaml"
    sprite_path = tmp_path / "Sprite1.yaml"

    index_path.write_text(
        normalize_multiline(
            """
            - name: Stage
              path: Stage.yaml
            - name: Sprite1
              path: Sprite1.yaml
            """
        ),
        encoding="utf-8",
    )
    stage_path.write_text(
        normalize_multiline(
            """
            name: Stage
            variables: {}
            lists: []
            blocks: []
            """
        ),
        encoding="utf-8",
    )
    sprite_path.write_text(
        normalize_multiline(
            """
            name: Sprite1
            variables: {}
            lists: []
            blocks:
              - - opcode: motion_movesteps
                  params: [10]
            """
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(RENDER_SCRIPT), str(index_path), "--targets", "Sprite1"],
        capture_output=True,
        check=True,
        text=True,
    )

    assert completed.stdout == normalize_multiline(
        """
        # Sprite1
        [script 1]
        ┌─────────────────┐
        │ move (10) steps │
        └─────────────────┘
        """
    )
