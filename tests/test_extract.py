import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/scratch-blocks/scripts/extract.py"
PROJECT_JSON = ROOT / "example/project.json"


def load_extract_module():
    spec = importlib.util.spec_from_file_location("extract_mod", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_project_data():
    return json.loads(PROJECT_JSON.read_text(encoding="utf-8"))


def test_extract_code_returns_structured_targets():
    extract = load_extract_module()
    targets = extract.extract_code(load_project_data())

    assert [target["name"] for target in targets] == ["Stage", "Sprite1"]

    stage, sprite = targets
    assert stage["variables"] == {"my variable": 0}
    assert stage["lists"] == []
    assert stage["blocks"] == []

    assert sprite["variables"] == {}
    assert sprite["lists"] == [{"name": "list2", "items": ["1", "1"]}]
    assert isinstance(sprite["blocks"], list)
    assert all(isinstance(script, list) for script in sprite["blocks"])


def test_extract_code_keeps_custom_blocks():
    extract = load_extract_module()
    targets = extract.extract_code(load_project_data())
    sprite = next(target for target in targets if target["name"] == "Sprite1")

    scripts = sprite["blocks"]
    opcodes = [[block["opcode"] for block in script] for script in scripts]

    assert [
        "event_whenflagclicked",
        "motion_turnright",
        "motion_goto",
        "motion_goto",
        "motion_setrotationstyle",
        "procedures_call",
    ] in opcodes
    assert ["procedures_definition", "motion_movesteps", "data_addtolist"] in opcodes

    call_block = next(block for script in scripts for block in script if block["opcode"] == "procedures_call")
    definition_block = next(
        block for script in scripts for block in script if block["opcode"] == "procedures_definition"
    )

    assert call_block["params"] == ["BlockName"]
    assert definition_block["params"] == ["BlockName"]


def test_to_target_yaml_emits_structured_yaml_without_empty_block_fields():
    extract = load_extract_module()
    targets = extract.extract_code(load_project_data())
    stage = next(target for target in targets if target["name"] == "Stage")
    sprite = next(target for target in targets if target["name"] == "Sprite1")
    stage_yaml = extract.to_target_yaml(stage)
    yaml_text = extract.to_target_yaml(sprite)

    assert stage_yaml.startswith("name: Stage\n")
    assert "\n# " not in yaml_text
    assert "variables:\n  my variable: 0\n" in stage_yaml
    assert "lists: []\n" in stage_yaml
    assert "variables: {}\n" in yaml_text
    assert "lists:\n  - name: list2\n    items:\n      - \"1\"\n      - \"1\"\n" in yaml_text
    assert "blocks:\n  - - opcode: event_whenflagclicked\n" in yaml_text
    assert "      params: [15]\n" in yaml_text
    assert "      params: [_random_]\n" in yaml_text
    assert "      params: [_mouse_]\n" in yaml_text
    assert "      params: [\"don't rotate\"]\n" in yaml_text
    assert "      params: [BlockName]\n" in yaml_text
    assert "      params: [list2, \"1\"]\n" in yaml_text
    assert "params: []" not in yaml_text
    assert "\n      blocks: []\n" not in yaml_text


def test_index_yaml_lists_target_names_and_paths():
    extract = load_extract_module()
    index_yaml = extract.to_index_yaml(
        [
            {"name": "Stage", "path": "Stage.yaml"},
            {"name": "Sprite1", "path": "Sprite1.yaml"},
        ]
    )

    assert yaml.safe_load(index_yaml) == [
        {"name": "Stage", "path": "Stage.yaml"},
        {"name": "Sprite1", "path": "Sprite1.yaml"},
    ]


def test_cli_writes_split_target_files_and_index_next_to_json(tmp_path):
    project_copy = tmp_path / "project.json"
    project_copy.write_text(PROJECT_JSON.read_text(encoding="utf-8"), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(project_copy)],
        check=True,
        capture_output=True,
        text=True,
    )

    index_path = Path(completed.stdout.strip())
    out_dir = tmp_path / "project.blocks"
    assert index_path == out_dir / "index.yaml"
    assert index_path.is_file()
    assert (out_dir / "Stage.yaml").is_file()
    assert (out_dir / "Sprite1.yaml").is_file()

    index_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    assert index_data == [
        {"name": "Stage", "path": "Stage.yaml"},
        {"name": "Sprite1", "path": "Sprite1.yaml"},
    ]

    sprite_yaml = (out_dir / "Sprite1.yaml").read_text(encoding="utf-8")
    assert sprite_yaml.startswith("name: Sprite1\n")
    assert "      - \"1\"\n" in sprite_yaml


def test_cli_writes_to_explicit_output_path(tmp_path):
    project_copy = tmp_path / "project.json"
    project_copy.write_text(PROJECT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    output_path = tmp_path / "custom" / "result.blocks.yaml"

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output_path), str(project_copy)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert Path(completed.stdout.strip()) == output_path
    assert output_path.is_file()

    yaml_text = output_path.read_text(encoding="utf-8")
    assert yaml_text.startswith("- name: Stage\n")
    assert "- name: Sprite1\n" in yaml_text


def test_to_target_yaml_serializes_list_items():
    extract = load_extract_module()
    yaml_text = extract.to_target_yaml(
        {
            "name": "Sprite1",
            "variables": {},
            "lists": [{"name": "list2", "items": ["1", "2"]}],
            "blocks": [],
        }
    )

    assert "lists:\n  - name: list2\n    items:\n      - \"1\"\n      - \"2\"\n" in yaml_text


def test_extract_code_ignores_extra_variable_and_list_metadata():
    extract = load_extract_module()
    targets = extract.extract_code(
        {
            "targets": [
                {
                    "name": "Sprite1",
                    "variables": {"var1": ["score", 10, True]},
                    "lists": {"list1": ["items", ["a", "b"], 123]},
                    "blocks": {},
                    "comments": {},
                }
            ]
        }
    )

    assert targets == [
        {
            "name": "Sprite1",
            "variables": {"score": 10},
            "lists": [{"name": "items", "items": ["a", "b"]}],
            "blocks": [],
        }
    ]


def test_unique_target_filename_sanitizes_and_deduplicates():
    extract = load_extract_module()
    used = set()

    first = extract.unique_target_filename("Mouse/1", used)
    second = extract.unique_target_filename("Mouse:1", used)

    assert first == "Mouse_1.yaml"
    assert second == "Mouse_1_2.yaml"


def test_unique_target_filename_deduplicates_case_insensitively():
    extract = load_extract_module()
    used = set()

    first = extract.unique_target_filename("Sprite", used)
    second = extract.unique_target_filename("sprite", used)

    assert first == "Sprite.yaml"
    assert second == "sprite_2.yaml"


def test_unique_target_filename_avoids_reserved_index_name():
    extract = load_extract_module()
    used = {"index.yaml"}

    assert extract.unique_target_filename("index", used) == "index_2.yaml"


def test_render_ascii_accepts_single_target_object():
    render_path = ROOT / "skills/scratch-blocks/scripts/render_ascii.py"
    completed = subprocess.run(
        [sys.executable, str(render_path), "-"],
        input="name: Sprite1\nvariables: {}\nlists: []\nblocks:\n  - - opcode: motion_movesteps\n      params: [10]\n",
        capture_output=True,
        check=True,
        text=True,
    )

    assert "# Sprite1\n" in completed.stdout
    assert "move (10)" in completed.stdout


def test_render_ascii_accepts_yaml_argument():
    render_path = ROOT / "skills/scratch-blocks/scripts/render_ascii.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(render_path),
            "--yaml",
            "name: Sprite1\nvariables: {}\nlists: []\nblocks:\n  - - opcode: motion_movesteps\n      params: [10]\n",
        ],
        capture_output=True,
        check=True,
        text=True,
    )

    assert "# Sprite1\n" in completed.stdout
    assert "move (10)" in completed.stdout


def test_cli_split_output_avoids_case_insensitive_collisions(tmp_path):
    project_path = tmp_path / "project.json"
    project_path.write_text(
        json.dumps(
            {
                "targets": [
                    {"name": "Sprite", "variables": {}, "lists": {}, "blocks": {}, "comments": {}},
                    {"name": "sprite", "variables": {}, "lists": {}, "blocks": {}, "comments": {}},
                ]
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(project_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    index_path = Path(completed.stdout.strip())
    index_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))

    assert index_data == [
        {"name": "Sprite", "path": "Sprite.yaml"},
        {"name": "sprite", "path": "sprite_2.yaml"},
    ]
    assert (index_path.parent / "Sprite.yaml").is_file()
    assert (index_path.parent / "sprite_2.yaml").is_file()


def test_cli_split_output_reserves_index_yaml_name(tmp_path):
    project_path = tmp_path / "project.json"
    project_path.write_text(
        json.dumps(
            {
                "targets": [
                    {"name": "index", "variables": {}, "lists": {}, "blocks": {}, "comments": {}},
                ]
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(project_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    index_path = Path(completed.stdout.strip())
    index_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))

    assert index_path.name == "index.yaml"
    assert index_data == [{"name": "index", "path": "index_2.yaml"}]
    assert (index_path.parent / "index_2.yaml").is_file()
