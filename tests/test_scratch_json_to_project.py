import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONVERTER = ROOT / "tools/scratch_json_to_project.py"
EXTRACTOR = ROOT / "skills/scratch-blocks/scripts/extract.py"
MYBLOCKS = ROOT / "example/myblocks.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_convert_preserves_procedure_call_arguments_round_trip():
    converter = load_module(CONVERTER, "scratch_json_to_project")
    extractor = load_module(EXTRACTOR, "scratch_extract")

    scratch_objects = json.loads(MYBLOCKS.read_text(encoding="utf-8"))
    project = converter.convert_scratch_json_to_project(scratch_objects)

    target = next(item for item in project["targets"] if item["name"] == "Amon")
    call_block = next(block for block in target["blocks"].values() if block["opcode"] == "procedures_call")

    assert json.loads(call_block["mutation"]["argumentids"]) == ["arg0", "arg1"]
    assert list(call_block["inputs"]) == ["arg0", "arg1"]

    round_tripped = extractor.extract_code(project)
    call_script = next(
        obj["blocks"]
        for obj in round_tripped
        if obj["type"] == "script" and any(block["opcode"] == "procedures_call" for block in obj["blocks"])
    )
    call = next(block for block in call_script if block["opcode"] == "procedures_call")

    assert call["params"] == [
        "block name %s label text %b",
        {"opcode": "looks_size"},
        {"opcode": "operator_contains", "params": ["apple", "a"]},
    ]
