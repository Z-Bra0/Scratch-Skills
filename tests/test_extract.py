import importlib.util
import json
import subprocess
import sys
from pathlib import Path


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


def test_to_scratch_yaml_emits_structured_yaml_without_empty_block_fields():
    extract = load_extract_module()
    yaml_text = extract.to_scratch_yaml(extract.extract_code(load_project_data()))

    assert yaml_text.startswith("- name: Stage\n")
    assert "\n# " not in yaml_text
    assert "  variables:\n    my variable: 0\n" in yaml_text
    assert "  lists: []\n" in yaml_text
    assert "  variables: {}\n" in yaml_text
    assert "  lists:\n    - name: list2\n      items:\n        - \"1\"\n        - \"1\"\n" in yaml_text
    assert "  blocks:\n    - - opcode: event_whenflagclicked\n" in yaml_text
    assert "        params: [15]\n" in yaml_text
    assert "        params: [_random_]\n" in yaml_text
    assert "        params: [_mouse_]\n" in yaml_text
    assert "        params: [\"don't rotate\"]\n" in yaml_text
    assert "        params: [BlockName]\n" in yaml_text
    assert "        params: [list2, \"1\"]\n" in yaml_text
    assert "params: []" not in yaml_text
    assert "\n        blocks: []\n" not in yaml_text


def test_cli_writes_blocks_yaml_next_to_json(tmp_path):
    project_copy = tmp_path / "project.json"
    project_copy.write_text(PROJECT_JSON.read_text(encoding="utf-8"), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(project_copy)],
        check=True,
        capture_output=True,
        text=True,
    )

    out_path = Path(completed.stdout.strip())
    assert out_path == tmp_path / "project.blocks.yaml"
    assert out_path.is_file()

    yaml_text = out_path.read_text(encoding="utf-8")
    assert yaml_text.startswith("- name: Stage\n")
    assert "- name: Sprite1\n" in yaml_text


def test_to_scratch_yaml_serializes_list_items():
    extract = load_extract_module()
    yaml_text = extract.to_scratch_yaml(
        [
            {
                "name": "Sprite1",
                "variables": {},
                "lists": [{"name": "list2", "items": ["1", "2"]}],
                "blocks": [],
            }
        ]
    )

    assert "  lists:\n    - name: list2\n      items:\n        - \"1\"\n        - \"2\"\n" in yaml_text
