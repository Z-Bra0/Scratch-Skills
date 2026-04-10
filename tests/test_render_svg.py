import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/scratch-blocks-color/scripts/render_svg.py"


def load_render_svg_module():
    spec = importlib.util.spec_from_file_location("render_svg_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def script(blocks, target="Sprite1"):
    return {"type": "script", "target": target, "blocks": blocks}


def svg_size(svg: str) -> tuple[int, int]:
    match = re.search(r'width="(\d+)" height="(\d+)"', svg)
    assert match is not None
    return int(match.group(1)), int(match.group(2))


def test_module_exports_public_entrypoints():
    mod = load_render_svg_module()

    assert callable(mod.states_to_svg)


def test_catalog_entry_parses_shapes_params_and_branch_labels():
    mod = load_render_svg_module()

    entry = mod.catalog_entry_for("control_if_else")

    assert entry.category == "control"
    assert entry.shape == "c_block"
    assert "c-2" in entry.shapes
    assert entry.params == (mod.ParamSpec(type="boolean"),)
    assert entry.branch_labels[0] == mod.BranchLabelSpec(text="else", position="left")


def test_scratch_json_to_states_normalizes_nested_blocks():
    mod = load_render_svg_module()

    states = mod.scratch_json_to_states(
        [
            script(
                [
                    {
                        "opcode": "control_repeat",
                        "params": [3],
                        "blocks": [[{"opcode": "looks_show"}]],
                    }
                ]
            )
        ]
    )

    state = states[0]
    assert state["type"] == "control_repeat"
    assert state["inputs"]["INPUT1"]["shadow"]["fields"]["NUM"] == "3"
    assert state["inputs"]["SUBSTACK"]["block"]["type"] == "looks_show"


def test_ordered_inline_items_appends_remaining_text_segments():
    mod = load_render_svg_module()

    items = mod._ordered_inline_items(["a", "b", "c"], [mod.ParamSpec(type="number")])

    assert items == [
        ("text", "a"),
        ("param", mod.ParamSpec(type="number")),
        ("text", "b"),
        ("text", "c"),
    ]


def test_ordered_inline_items_appends_remaining_params():
    mod = load_render_svg_module()

    items = mod._ordered_inline_items(["a"], [mod.ParamSpec(type="number"), mod.ParamSpec(type="boolean")])

    assert items == [
        ("text", "a"),
        ("param", mod.ParamSpec(type="number")),
        ("param", mod.ParamSpec(type="boolean")),
    ]


def test_param_box_kind_uses_nested_boolean_shapes():
    mod = load_render_svg_module()

    kind = mod._param_box_kind(mod.ParamSpec(type="number"), {"type": "operator_not"})

    assert kind == "angle"


def test_param_box_kind_uses_nested_round_shapes():
    mod = load_render_svg_module()

    kind = mod._param_box_kind(mod.ParamSpec(type="boolean"), {"type": "motion_xposition"})

    assert kind == "curve"


def test_empty_first_text_adds_leading_param_padding():
    mod = load_render_svg_module()

    layout = mod._build_inline_content_layout(
        {"type": "operator_and", "fields": {}, "inputs": {}, "next": {}},
        "#fff",
        "#59C059",
        "#389438",
    )

    assert layout.segments[0].kind == "param"
    assert layout.segments[0].x == 12.0


def test_shadow_backed_round_param_uses_curve_box():
    mod = load_render_svg_module()

    width, height, fragment = mod._render_param_segment(
        {"shadow": {"type": "motion_xposition", "fields": {}, "inputs": {}, "next": {}}},
        mod.ParamSpec(type="number"),
        "#FFAB19",
        "#CF8B17",
    )

    assert width > height
    assert "a 16.0 16.0 0 0 1 0 32.0" in fragment


def test_color_param_uses_literal_fill_value():
    mod = load_render_svg_module()

    _, _, fragment = mod._render_param_segment(
        {"shadow": {"type": "text", "fields": {"TEXT": "#ff00aa"}, "inputs": {}, "next": {}}},
        mod.ParamSpec(type="color"),
        "#5CB1D6",
        "#2E8EB8",
    )

    assert 'fill="#ff00aa"' in fragment
    assert ">#ff00aa</text>" not in fragment


def test_input_statement_params_use_stack_box():
    mod = load_render_svg_module()

    width, height, fragment = mod._render_param_segment(
        {"shadow": {"type": "text", "fields": {"TEXT": "body"}, "inputs": {}, "next": {}}},
        mod.ParamSpec(type="input_statement"),
        "#FF6680",
        "#FF3355",
    )

    assert width > height
    assert "a 4 4 0 0 1 4 -4 h 8.0 c 2 0 3 1" in fragment
    assert "a 16.0 16.0 0 0 1 0 32.0" not in fragment
    assert "l 16.0 16.0" not in fragment


def test_statement_path_uses_v2_style_concave_header_fragment():
    mod = load_render_svg_module()

    d = mod._statement_d(120, True)

    assert d.startswith("m 0.0 4.0 a 4 4 0 0 1 4 -4 h 8.0 c 2 0 3 1")
    assert "c -2 0 -3 1 -4 2" in d
    assert d.endswith("z")


def test_c_block_path_uses_v2_style_branch_fragments():
    mod = load_render_svg_module()

    d = mod._c_block_d(150, [48.0], True)

    assert "a 4 4 0 0 0 -4 4" in d
    assert "c -2 0 -3 1 -4 2" in d
    assert "c 2 0 3 1 4 2" in d
    assert d.endswith("z")


def test_states_to_svg_returns_svg_document():
    mod = load_render_svg_module()

    svg = mod.states_to_svg([script([{"opcode": "looks_show"}])])

    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert '<g transform="translate(20.0 20.0)" data-role="stack">' in svg
    assert 'data-block-type="looks_show"' in svg
    assert 'data-role="content"' in svg
    assert 'transform="translate(10.0 14.0)" data-role="content"' in svg
    assert 'text-anchor="start"' in svg
    assert "show" in svg
    assert "</svg>" in svg


def test_states_to_svg_renders_top_level_variable_monitor():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            {"type": "variable", "target": "Sprite1", "name": "score", "value": 15},
        ]
    )

    assert 'data-block-type="scratch_variable_monitor"' in svg
    assert 'data-shape="variable_monitor"' in svg
    assert 'fill="#E6F0FF"' in svg
    assert 'fill="#FF8D1A"' in svg
    assert 'stroke="#A8C3E8"' in svg
    assert 'stroke="#DB6E00"' in svg
    assert 'fill="#000000"' in svg
    assert '>Sprite1: score</text>' in svg
    assert '>15</text>' in svg
    assert 'a 4 4 0 0 1 4 -4' in svg
    assert 'a 4 4 0 0 1 -4 4' in svg
    assert 'h 32.0 a 4 4 0 0 1 4 4 v 24.0' in svg


def test_stage_variable_monitor_keeps_plain_variable_name():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            {"type": "variable", "target": "Stage", "name": "score", "value": 15},
        ]
    )

    assert '>score</text>' in svg
    assert '>Stage: score</text>' not in svg


def test_states_to_svg_renders_top_level_list_monitor():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            {"type": "list", "target": "Apple", "name": "items", "items": ["a", "bb"]},
        ]
    )

    assert 'data-block-type="scratch_list_monitor"' in svg
    assert 'data-shape="list_monitor"' in svg
    assert '>Apple: items</text>' in svg
    assert '>1</text>' in svg
    assert '>2</text>' in svg
    assert '>a</text>' in svg
    assert '>bb</text>' in svg
    assert '>length 2</text>' in svg
    assert 'fill="#FFFFFF"' in svg
    assert 'fill="#E6F0FF"' in svg
    assert 'fill="#FF8D1A"' in svg


def test_states_to_svg_renders_empty_list_monitor():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            {"type": "list", "target": "Stage", "name": "items", "items": []},
        ]
    )

    assert '>items</text>' in svg
    assert '>(empty)</text>' in svg
    assert '>length 0</text>' in svg


def test_renders_hat_and_statement_chain_with_group_transforms():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {"opcode": "event_whenflagclicked"},
                    {"opcode": "motion_movesteps", "params": [10]},
                ]
            )
        ]
    )

    assert 'data-block-type="event_whenflagclicked"' in svg
    assert 'data-shape="hat"' in svg
    assert 'data-block-type="motion_movesteps"' in svg
    assert 'data-shape="statement"' in svg
    assert '<g transform="translate(0.0 68.0)" data-role="block" data-block-type="motion_movesteps"' in svg
    assert 'transform="translate(10.0 34.0)" data-role="content"' in svg
    assert 'transform="translate(10.0 8.0)" data-role="content"' in svg
    assert ">when </text>" in svg
    assert "> clicked</text>" in svg
    assert 'fill="#4CBF56"' in svg
    assert ">move</text>" in svg
    assert ">10</text>" in svg
    assert ">steps</text>" in svg
    assert 'a 16.0 16.0 0 0 1 0 32.0' in svg
    assert 'fill="#FFFFFF"' in svg


def test_renders_end_block_group():
    mod = load_render_svg_module()

    svg = mod.states_to_svg([script([{"opcode": "control_stop", "params": ["all"]}])])

    assert 'data-block-type="control_stop"' in svg
    assert 'data-shape="end"' in svg
    assert ">stop</text>" in svg
    assert ">all</text>" in svg
    assert ">▼</text>" in svg
    assert 'v 32.0 h -' in svg


def test_renders_c_block_with_nested_stack_group():
    mod = load_render_svg_module()
    data = [
        script(
            [
                {
                    "opcode": "control_repeat",
                    "params": [3],
                    "blocks": [[{"opcode": "looks_say", "params": ["hi"]}]],
                }
            ]
        )
    ]

    svg = mod.states_to_svg(data)

    assert 'data-block-type="control_repeat"' in svg
    assert 'data-shape="c_block"' in svg
    assert 'transform="translate(20.0 48.0)" data-role="stack"' in svg
    assert 'data-block-type="looks_say"' in svg
    assert ">repeat</text>" in svg
    assert ">3</text>" in svg
    assert ">say</text>" in svg
    assert ">hi</text>" in svg


def test_c_block_renders_right_aligned_branch_label():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "control_repeat",
                        "params": [3],
                        "blocks": [[{"opcode": "looks_say", "params": ["hi"]}]],
                    }
                ]
            )
        ]
    )

    assert 'd="m 350 177.5' in svg
    assert '<g transform="translate(116.0 98.0)">' in svg


def test_c_end_block_uses_flat_footer():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "control_forever",
                        "blocks": [[{"opcode": "looks_show"}]],
                    }
                ]
            )
        ]
    )

    assert 'data-block-type="control_forever"' in svg
    assert 'data-shape="c_end"' in svg
    assert 'h -144.0 a 4 4 0 0 1 -4 -4 z' in svg


def test_c_block_renders_left_aligned_else_branch_label():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "control_if_else",
                        "params": [{"opcode": "operator_not"}],
                        "blocks": [
                            [{"opcode": "looks_show"}],
                            [{"opcode": "looks_say", "params": ["hi"]}],
                        ],
                    }
                ]
            )
        ]
    )

    assert 'data-block-type="control_if_else"' in svg
    assert ">else</text>" in svg
    assert '<g transform="translate(10.0 122.0)">' in svg


def test_c_block_uses_branch_labels_to_preserve_empty_second_branch():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "control_if_else",
                        "params": [{"opcode": "operator_not"}],
                        "blocks": [[{"opcode": "looks_show"}]],
                    }
                ]
            )
        ]
    )

    assert 'data-block-type="control_if_else"' in svg
    assert svg.count('data-role="stack"') >= 2
    assert ">else</text>" in svg
    width, height = svg_size(svg)
    assert width >= 220
    assert height >= 260


def test_tall_if_else_condition_keeps_second_branch_aligned():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "control_if_else",
                        "params": [
                            {
                                "opcode": "operator_gt",
                                "params": [
                                    {"opcode": "operator_random", "params": [1, 10]},
                                    "50",
                                ],
                            }
                        ],
                        "blocks": [
                            [
                                {
                                    "opcode": "control_if",
                                    "params": [
                                        {
                                            "opcode": "operator_and",
                                            "params": [
                                                {"opcode": "sensing_touchingcolor", "params": ["#b2e670"]},
                                                {"opcode": "operator_contains", "params": ["apple", "a"]},
                                            ],
                                        }
                                    ],
                                    "blocks": [[{"opcode": "looks_switchcostumeto", "params": ["costume2"]}]],
                                }
                            ],
                            [[{"opcode": "looks_say", "params": ["Hello!"]}][0]],
                        ],
                    }
                ]
            )
        ]
    )

    assert 'data-block-type="looks_say"' in svg
    assert 'transform="translate(20.0 264.0)" data-role="stack"' in svg
    assert '<g transform="translate(10.0 230.0)">' in svg


def test_turn_text_uses_right_turn_icon():
    mod = load_render_svg_module()

    svg = mod.states_to_svg([script([{"opcode": "motion_turnright", "params": [15]}])])

    assert ">turn </text>" in svg
    assert 'd="m 386.3 160' in svg
    assert ">↱</text>" not in svg


def test_rejects_non_list_inputs():
    mod = load_render_svg_module()

    try:
        mod.states_to_svg({"type": "looks_show", "fields": {}, "inputs": {}, "next": {}})
    except TypeError as exc:
        assert "Expected scratch-json" in str(exc)
    else:
        raise AssertionError("expected invalid top-level input to be rejected")


def test_empty_script_does_not_crash():
    mod = load_render_svg_module()

    svg = mod.states_to_svg([script([])])

    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert 'data-block-type="text"' in svg
    assert ">[empty]</text>" in svg


def test_round_reporter_blocks_render_as_curve_groups():
    mod = load_render_svg_module()

    svg = mod.states_to_svg([script([{"opcode": "motion_xposition"}])])

    assert 'data-block-type="motion_xposition"' in svg
    assert 'data-shape="reporter_round"' in svg
    assert "x position" in svg
    assert 'a 16.0 16.0 0 0 1 0 32.0' in svg


def test_boolean_reporter_blocks_render_as_angle_groups():
    mod = load_render_svg_module()

    svg = mod.states_to_svg([script([{"opcode": "operator_not"}])])

    assert 'data-block-type="operator_not"' in svg
    assert 'data-shape="reporter_boolean"' in svg
    assert 'l 16.0 16.0 l -16.0 16.0' in svg


def test_boolean_params_use_angled_box_and_nested_params_increase_height():
    mod = load_render_svg_module()

    nested_svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "control_wait_until",
                        "params": [
                            {
                                "opcode": "operator_and",
                                "params": [
                                    {"opcode": "sensing_touchingobject", "params": ["mouse-pointer"]},
                                    {"opcode": "operator_not"},
                                ],
                            }
                        ],
                    }
                ]
            )
        ]
    )
    simple_svg = mod.states_to_svg([script([{"opcode": "control_wait_until", "params": [{"opcode": "operator_not"}]}])])
    nested_width, nested_height = svg_size(nested_svg)
    simple_width, simple_height = svg_size(simple_svg)

    assert 'l 28.0 28.0 l -28.0 28.0' in nested_svg
    assert "mouse-pointer" in nested_svg
    assert ">and</text>" in nested_svg
    assert nested_width > simple_width
    assert nested_height > simple_height
    assert 'fill="#59C059"' in simple_svg


def test_procedure_definition_parses_signature_into_text_and_params():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "procedures_definition",
                        "params": ["block name %s label text %b", "number or text", "boolean"],
                    }
                ]
            )
        ]
    )

    assert 'data-block-type="procedures_definition"' in svg
    assert 'data-shape="bowlerhat"' in svg
    assert ">define</text>" in svg
    assert ">block name</text>" in svg
    assert ">label text</text>" in svg
    assert ">number or text</text>" in svg
    assert ">boolean</text>" in svg
    assert "a 20 20 0 0 1 20 -20" in svg
    assert "c 25 -22 71 -22 96 0" not in svg
    assert 'transform="translate(10.0 -5.0)" data-role="content"' in svg
    assert 'data-role="block-signature"' in svg
    assert svg.count('data-role="param"') >= 2
    assert 'fill="#FF6680"' in svg
    assert 'fill="#FF4D6A"' in svg


def test_procedure_call_parses_signature_and_uses_nested_param_shapes():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {
                        "opcode": "procedures_call",
                        "params": [
                            "block name %s label text %b",
                            {"opcode": "looks_size"},
                            {"opcode": "operator_contains", "params": ["apple", "a"]},
                        ],
                    }
                ]
            )
        ]
    )

    assert 'data-block-type="procedures_call"' in svg
    assert 'data-shape="statement"' in svg
    assert ">block name</text>" in svg
    assert ">label text</text>" in svg
    assert ">size</text>" in svg
    assert ">contains</text>" in svg
    assert 'a 16.0 16.0 0 0 1 0 32.0' in svg
    assert 'l 22.0 22.0 l -22.0 22.0' in svg


def test_dropdown_tokens_render_with_friendly_display_text():
    mod = load_render_svg_module()

    svg = mod.states_to_svg(
        [
            script(
                [
                    {"opcode": "sensing_touchingobject", "params": ["_mouse_"]},
                    {"opcode": "motion_goto", "params": ["_random_"]},
                ]
            )
        ]
    )

    assert "mouse-pointer" in svg
    assert "random position" in svg
    assert "_mouse_" not in svg
    assert "_random_" not in svg


def test_cli_writes_svg_to_explicit_output_path(tmp_path):
    input_path = tmp_path / "scratch.json"
    output_path = tmp_path / "out.svg"
    input_path.write_text(json.dumps([script([{"opcode": "looks_show"}])]), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(input_path), str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.is_file()
    assert "Written to" in completed.stderr
    assert 'data-block-type="looks_show"' in output_path.read_text(encoding="utf-8")
