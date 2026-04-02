import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = ROOT / "skills/scratch-blocks/scripts/render_ascii.py"
EXAMPLE_SPRITE_JSON = ROOT / "example/sprite.json"
EXAMPLE_SPRITE_ASCII = ROOT / "example/sprite.ascii.txt"


def load_render_module():
    spec = importlib.util.spec_from_file_location("render_ascii_viewer", RENDER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalize_multiline(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


def to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def script(blocks, target="Sprite1"):
    return {"type": "script", "target": target, "blocks": blocks}


RENDER_CASES = {
    "flat_same_length": (
        [script([{"opcode": "looks_show"}, {"opcode": "looks_hide"}])],
        """
        # Sprite1
        ┌──────┐
        │ show │
        ├──────┤
        │ hide │
        └──────┘
        """,
    ),
    "same_length": (
        [
            script(
                [
                    {
                        "opcode": "control_repeat",
                        "params": [10],
                        "blocks": [[{"opcode": "looks_say", "params": ["hi"]}]],
                    }
                ]
            )
        ],
        """
        # Sprite1
        ┌─────────────┐
        │ repeat (10) │
        │ ┌──────────┬┘
        │ │ say (hi) │
        │ └──────────┴┐
        │           ↺ │
        └─────────────┘
        """,
    ),
    "parent_shorter_child_longer": (
        [
            script(
                [
                    {
                        "opcode": "control_repeat",
                        "params": [1],
                        "blocks": [[{"opcode": "looks_say", "params": ["this is a much longer nested message"]}]],
                    }
                ]
            )
        ],
        """
        # Sprite1
        ┌────────────┐
        │ repeat (1) │
        │ ┌──────────┴─────────────────────────────────┐
        │ │ say (this is a much longer nested message) │
        │ └──────────┬─────────────────────────────────┘
        │          ↺ │
        └────────────┘
        """,
    ),
    "nested_longer_than_following_block": (
        [
            script(
                [
                    {
                        "opcode": "control_repeat",
                        "params": [3],
                        "blocks": [[{"opcode": "looks_say", "params": ["this nested block is much longer"]}]],
                    },
                    {"opcode": "motion_movesteps", "params": [1]},
                ]
            )
        ],
        """
        # Sprite1
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
    "empty_nested_branch_from_c_block_metadata": (
        [script([{"opcode": "control_repeat", "params": [3]}])],
        """
        # Sprite1
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
    assert render_module.render(to_json(source)) == normalize_multiline(expected)


def test_render_shows_missing_boolean_placeholder(render_module):
    source = to_json(
        [
            script(
                [
                    {
                        "opcode": "control_wait_until",
                        "params": [
                            {
                                "opcode": "operator_and",
                                "params": [
                                    {"opcode": "sensing_keypressed", "params": ["space"]},
                                    {"opcode": "operator_not"},
                                ],
                            }
                        ],
                    }
                ]
            )
        ]
    )
    expected = normalize_multiline(
        """
        # Sprite1
        ┌────────────────────────────────────────────────────┐
        │ wait until <<key [space ▼] pressed?> and <not <>>> │
        └────────────────────────────────────────────────────┘
        """
    )

    assert render_module.render(source) == expected


def test_render_unknown_nested_opcode_falls_back_without_crashing(render_module):
    source = to_json(
        [
            script(
                [
                    {
                        "opcode": "custom_parent",
                        "blocks": [[{"opcode": "custom_child"}]],
                    }
                ]
            )
        ]
    )
    expected = normalize_multiline(
        """
        # Sprite1
        ┌───────────────┐
        │ custom_parent │
        │ ┌─────────────┴┐
        │ │ custom_child │
        │ └─────────────┬┘
        └───────────────┘
        """
    )

    assert render_module.render(source) == expected


def test_parse_targets_shows_helpful_json_error(render_module):
    with pytest.raises(SystemExit, match=r"Invalid scratch-json at line 1, column \d+"):
        render_module.parse_targets('[{"type":"script","target":"Sprite1",]')


def test_parse_targets_rejects_top_level_non_list(render_module):
    with pytest.raises(SystemExit, match="Expected scratch-json: a top-level list of objects"):
        render_module.parse_targets('{"type":"script","target":"Sprite1","blocks":[]}')


def test_parse_targets_detects_raw_project_json(render_module):
    with pytest.raises(SystemExit, match="Got raw Scratch project.json instead. Run extract.py first."):
        render_module.parse_targets('{"targets":[]}')


def test_parse_targets_accepts_empty_top_level_list(render_module):
    assert render_module.parse_targets("[]") == []


def test_parse_targets_expands_variables_and_lists_into_synthetic_targets(render_module):
    source = to_json(
        [
            {"type": "variable", "target": "Sprite1", "name": "score", "value": 15},
            {"type": "variable", "target": "Sprite1", "name": "level", "value": 160},
            {"type": "list", "target": "Sprite1", "name": "items", "items": [1, 20, 3]},
            {"type": "script", "target": "Sprite1", "blocks": []},
        ]
    )

    targets = render_module.parse_targets(source)
    assert [(target.owner_name, target.display_name, target.scripts) for target in targets] == [
        (
            "Sprite1",
            "Sprite1 Variables",
            [
                [
                    {"opcode": "custom_text", "params": ["score     "]},
                    {"opcode": "custom_text", "params": ["15        "]},
                ],
                [
                    {"opcode": "custom_text", "params": ["level     "]},
                    {"opcode": "custom_text", "params": ["160       "]},
                ],
            ],
        ),
        (
            "Sprite1",
            "Sprite1 Lists",
            [
                [
                    {"opcode": "custom_text", "params": ["items     "]},
                    {"opcode": "custom_text", "params": ["• 1       "]},
                    {"opcode": "custom_text", "params": ["• 20      "]},
                    {"opcode": "custom_text", "params": ["• 3       "]},
                ]
            ],
        ),
        ("Sprite1", "Sprite1", [[]]),
    ]


def test_parse_targets_rejects_duplicate_variable(render_module):
    source = to_json(
        [
            {"type": "variable", "target": "Sprite1", "name": "score", "value": 1},
            {"type": "variable", "target": "Sprite1", "name": "score", "value": 2},
        ]
    )

    with pytest.raises(SystemExit, match="Duplicate variable 'score' for target 'Sprite1'"):
        render_module.parse_targets(source)


def test_parse_targets_rejects_invalid_script_blocks(render_module):
    source = to_json(
        [
            {"type": "script", "target": "Sprite1", "blocks": [{"opcode": "looks_show"}, 1]},
        ]
    )

    with pytest.raises(SystemExit, match="Expected each block to be an object with an 'opcode' field"):
        render_module.parse_targets(source)


def test_render_expands_variables_and_lists_into_synthetic_targets(render_module):
    source = to_json(
        [
            {"type": "variable", "target": "Sprite1", "name": "score", "value": 15},
            {"type": "list", "target": "Sprite1", "name": "items", "items": [1, 20]},
            {"type": "script", "target": "Sprite1", "blocks": []},
        ]
    )
    expected = normalize_multiline(
        """
        # Sprite1 Variables
        ┌────────────┐
        │ score      │
        ├────────────┤
        │ 15         │
        └────────────┘

        # Sprite1 Lists
        ┌────────────┐
        │ items      │
        ├────────────┤
        │ • 1        │
        ├────────────┤
        │ • 20       │
        └────────────┘

        # Sprite1
        (no scripts)
        """
    )

    assert render_module.render(source) == expected


def test_render_targets_filter_keeps_target_variables_and_lists(render_module):
    source = to_json(
        [
            {"type": "variable", "target": "Sprite1", "name": "score", "value": 10},
            {"type": "list", "target": "Sprite1", "name": "items", "items": [1]},
            {"type": "script", "target": "Sprite1", "blocks": []},
            {"type": "variable", "target": "Sprite2", "name": "score", "value": 20},
            {"type": "list", "target": "Sprite2", "name": "items", "items": [2]},
            {"type": "script", "target": "Sprite2", "blocks": []},
        ]
    )
    expected = normalize_multiline(
        """
        # Sprite1 Variables
        ┌────────────┐
        │ score      │
        ├────────────┤
        │ 10         │
        └────────────┘

        # Sprite1 Lists
        ┌────────────┐
        │ items      │
        ├────────────┤
        │ • 1        │
        └────────────┘

        # Sprite1
        (no scripts)
        """
    )

    assert render_module.render(source, targets=["Sprite1"]) == expected


def test_render_fixture_output_sprite_json(render_module):
    expected = EXAMPLE_SPRITE_ASCII.read_text(encoding="utf-8")
    assert render_module.render(EXAMPLE_SPRITE_JSON.read_text(encoding="utf-8")) == expected


def test_render_cli_accepts_json_argument():
    completed = subprocess.run(
        [
            sys.executable,
            str(RENDER_SCRIPT),
            "--json",
            '[{"type":"script","target":"Sprite1","blocks":[{"opcode":"motion_movesteps","params":[10]}]}]',
        ],
        capture_output=True,
        check=True,
        text=True,
    )

    assert "# Sprite1\n" in completed.stdout
    assert "move (10) steps" in completed.stdout


def test_render_cli_shows_helpful_json_error_for_bad_input():
    completed = subprocess.run(
        [
            sys.executable,
            str(RENDER_SCRIPT),
            "--json",
            '[{"type":"script","target":"Sprite1","blocks":[{"opcode":"motion_movesteps"}]',
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "Invalid scratch-json" in completed.stderr
