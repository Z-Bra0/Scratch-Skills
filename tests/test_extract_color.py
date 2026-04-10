import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/scratch-blocks-color/scripts/extract.py"


def load_extract_module():
    spec = importlib.util.spec_from_file_location("extract_color_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_code_ignores_monitor_entries_stored_in_blocks_table():
    extract = load_extract_module()
    objects = extract.extract_code(
        {
            "targets": [
                {
                    "name": "Sprite1",
                    "variables": {"var1": ["score", 10]},
                    "lists": {},
                    "comments": {},
                    "blocks": {
                        "top": {
                            "opcode": "looks_show",
                            "next": None,
                            "parent": None,
                            "inputs": {},
                            "fields": {},
                            "shadow": False,
                            "topLevel": True,
                        },
                        "monitor-var": [12, "score", "var-id", 0, 0],
                        "monitor-list": [13, "items", "list-id", 0, 0],
                    },
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
            "type": "script",
            "target": "Sprite1",
            "blocks": [{"opcode": "looks_show"}],
        },
    ]
