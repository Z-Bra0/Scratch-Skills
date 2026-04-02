import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/scratch-blocks/scripts/extract.py"
PROJECT_JSON = ROOT / "example/project.json"
BLOCKS_JSON = ROOT / "example/project.blocks.json"


def load_extract_module():
    spec = importlib.util.spec_from_file_location("extract_mod", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_project_data():
    return json.loads(PROJECT_JSON.read_text(encoding="utf-8"))


def test_extract_code_returns_flat_objects():
    extract = load_extract_module()
    objects = extract.extract_code(load_project_data())

    assert [obj["type"] for obj in objects] == ["variable", "list", "script", "script"]
    assert objects[0] == {
        "type": "variable",
        "target": "Stage",
        "name": "my variable",
        "value": 0,
    }
    assert objects[1] == {
        "type": "list",
        "target": "Sprite1",
        "name": "list2",
        "items": ["1", "1"],
    }

    scripts = [obj for obj in objects if obj["type"] == "script" and obj["target"] == "Sprite1"]
    assert len(scripts) == 2
    assert all(isinstance(script["blocks"], list) for script in scripts)


def test_extract_code_keeps_custom_blocks():
    extract = load_extract_module()
    objects = extract.extract_code(load_project_data())
    scripts = [obj["blocks"] for obj in objects if obj["type"] == "script" and obj["target"] == "Sprite1"]
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


def test_to_scratch_json_emits_structured_json():
    extract = load_extract_module()
    objects = extract.extract_code(load_project_data())
    json_text = extract.to_scratch_json(objects)

    assert json.loads(json_text) == objects
    assert '"type": "variable"' in json_text
    assert '"target": "Sprite1"' in json_text
    assert '"opcode": "event_whenflagclicked"' in json_text
    assert '"params": [\n          15\n        ]' in json_text


def test_cli_writes_combined_json_next_to_json(tmp_path):
    project_copy = tmp_path / "project.json"
    project_copy.write_text(PROJECT_JSON.read_text(encoding="utf-8"), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(project_copy)],
        check=True,
        capture_output=True,
        text=True,
    )

    output_path = Path(completed.stdout.strip())
    assert output_path == tmp_path / "project.blocks.json"
    assert output_path.is_file()

    objects = json.loads(output_path.read_text(encoding="utf-8"))
    assert objects[0]["target"] == "Stage"
    assert objects[1]["type"] == "list"


def test_cli_writes_to_explicit_output_path(tmp_path):
    project_copy = tmp_path / "project.json"
    project_copy.write_text(PROJECT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    output_path = tmp_path / "custom" / "result.blocks.json"

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output_path), str(project_copy)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert Path(completed.stdout.strip()) == output_path
    assert output_path.is_file()

    objects = json.loads(output_path.read_text(encoding="utf-8"))
    assert any(obj["target"] == "Sprite1" for obj in objects)


def test_cli_rejects_extracted_blocks_json_input(tmp_path):
    blocks_copy = tmp_path / "project.blocks.json"
    blocks_copy.write_text(BLOCKS_JSON.read_text(encoding="utf-8"), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(blocks_copy)],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "expected Scratch project.json or sprite.json" in completed.stderr
    assert "blocks.json" in completed.stderr


def test_cli_rejects_loose_json_with_noncanonical_name(tmp_path):
    project_copy = tmp_path / "renamed.json"
    project_copy.write_text(PROJECT_JSON.read_text(encoding="utf-8"), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(project_copy)],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "must be named project.json or sprite.json" in completed.stderr


def test_extract_code_ignores_extra_variable_and_list_metadata():
    extract = load_extract_module()
    objects = extract.extract_code(
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

    assert objects == [
        {
            "type": "variable",
            "target": "Sprite1",
            "name": "score",
            "value": 10,
        },
        {
            "type": "list",
            "target": "Sprite1",
            "name": "items",
            "items": ["a", "b"],
        },
    ]


def test_extract_code_emits_empty_script_for_completely_empty_target():
    extract = load_extract_module()
    objects = extract.extract_code(
        {
            "targets": [
                {
                    "name": "EmptySprite",
                    "variables": {},
                    "lists": {},
                    "blocks": {},
                    "comments": {},
                }
            ]
        }
    )

    assert objects == [
        {
            "type": "script",
            "target": "EmptySprite",
            "blocks": [],
        }
    ]
