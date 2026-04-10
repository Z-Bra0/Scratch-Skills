import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/scratch-blocks-color/scripts/render_ascii.py"


def load_render_module():
    spec = importlib.util.spec_from_file_location("render_ascii_color", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CONNECTOR_CASES = [
    (
        "top",
        0,
        0,
        0,
        12,
        dict(
            prefix_levels=0,
            left_type="DOWN",
            first_span=12,
            middle_type=None,
            second_span=0,
            right_type="END_DOWN",
        ),
        "┌────────────┐",
    ),
    (
        "flat_same_width",
        0,
        12,
        0,
        12,
        dict(
            prefix_levels=0,
            left_type="FLAT",
            first_span=12,
            middle_type=None,
            second_span=0,
            right_type="END_FLAT",
        ),
        "├────────────┤",
    ),
    (
        "flat_b1_long_b2_short",
        0,
        24,
        0,
        8,
        dict(
            prefix_levels=0,
            left_type="FLAT",
            first_span=8,
            middle_type="JOIN_UP",
            second_span=15,
            right_type="END_UP",
        ),
        "├────────┬───────────────┘",
    ),
    (
        "flat_b1_short_b2_long",
        0,
        8,
        0,
        24,
        dict(
            prefix_levels=0,
            left_type="FLAT",
            first_span=8,
            middle_type="JOIN_DOWN",
            second_span=15,
            right_type="END_DOWN",
        ),
        "├────────┴───────────────┐",
    ),
    (
        "down_same_width",
        0,
        12,
        1,
        12,
        dict(
            prefix_levels=1,
            left_type="DOWN",
            first_span=10,
            middle_type="JOIN_DOWN",
            second_span=1,
            right_type="END_DOWN",
        ),
        "│ ┌──────────┴─┐",
    ),
    (
        "down_b1_longer",
        0,
        20,
        1,
        10,
        dict(
            prefix_levels=1,
            left_type="DOWN",
            first_span=10,
            middle_type="JOIN_UP",
            second_span=7,
            right_type="END_UP",
        ),
        "│ ┌──────────┬───────┘",
    ),
    (
        "down_b1_shorter",
        0,
        10,
        1,
        20,
        dict(
            prefix_levels=1,
            left_type="DOWN",
            first_span=8,
            middle_type="JOIN_DOWN",
            second_span=11,
            right_type="END_DOWN",
        ),
        "│ ┌────────┴───────────┐",
    ),
    (
        "up_same_width",
        1,
        12,
        0,
        12,
        dict(
            prefix_levels=1,
            left_type="UP",
            first_span=10,
            middle_type="JOIN_UP",
            second_span=1,
            right_type="END_UP",
        ),
        "│ └──────────┬─┘",
    ),
    (
        "up_b1_longer",
        1,
        20,
        0,
        10,
        dict(
            prefix_levels=1,
            left_type="UP",
            first_span=8,
            middle_type="JOIN_UP",
            second_span=11,
            right_type="END_UP",
        ),
        "│ └────────┬───────────┘",
    ),
    (
        "up_b1_shorter",
        1,
        10,
        0,
        20,
        dict(
            prefix_levels=1,
            left_type="UP",
            first_span=10,
            middle_type="JOIN_DOWN",
            second_span=7,
            right_type="END_DOWN",
        ),
        "│ └──────────┴───────┐",
    ),
    (
        "bottom",
        0,
        12,
        0,
        0,
        dict(
            prefix_levels=0,
            left_type="UP",
            first_span=12,
            middle_type=None,
            second_span=0,
            right_type="END_UP",
        ),
        "└────────────┘",
    ),
]


@pytest.fixture(scope="module")
def render_module():
    return load_render_module()


@pytest.mark.parametrize(
    ("_name", "level1", "width1", "level2", "width2", "expected_spec", "_expected_line"),
    CONNECTOR_CASES,
)
def test_connector_spec(
    render_module, _name, level1, width1, level2, width2, expected_spec, _expected_line
):
    expected_spec = {
        key: getattr(render_module.ConnectorType, value) if key.endswith("_type") and value is not None else value
        for key, value in expected_spec.items()
    }
    assert render_module.connector_spec(level1, width1, level2, width2) == render_module.ConnectorSpec(
        **expected_spec
    )


@pytest.mark.parametrize(
    ("_name", "level1", "width1", "level2", "width2", "_expected_spec", "expected_line"),
    CONNECTOR_CASES,
)
def test_connector_line(render_module, _name, level1, width1, level2, width2, _expected_spec, expected_line):
    assert render_module.connector_line(level1, width1, level2, width2) == expected_line


def test_render_connector_spec_supports_custom_horizontal(render_module):
    spec = render_module.connector_spec(0, 8, 0, 24)
    assert render_module.render_connector_spec(spec, horizontal="=") == "├========┴===============┐"
