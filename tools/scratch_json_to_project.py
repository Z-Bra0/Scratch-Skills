#!/usr/bin/env python3
"""
Build a standalone Scratch project.json from extracted scratch-json.

The output is synthetic: it reconstructs targets, variables, lists, blocks,
monitors, and minimal target metadata directly from scratch-json without
reading an original project.json.

Usage:
    python3 tools/scratch_json_to_project.py path/to/project.blocks.json
    python3 tools/scratch_json_to_project.py path/to/project.blocks.json path/to/output.project.json
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any


INPUT_NAME_OVERRIDES = {
    "motion_movesteps": ["STEPS"],
    "motion_turnright": ["DEGREES"],
    "motion_turnleft": ["DEGREES"],
    "motion_goto": ["TO"],
    "motion_glideto": ["SECS", "TO"],
    "motion_glidesecstoxy": ["SECS", "X", "Y"],
    "motion_pointindirection": ["DIRECTION"],
    "motion_pointtowards": ["TOWARDS"],
    "motion_changexby": ["DX"],
    "motion_setx": ["X"],
    "motion_changeyby": ["DY"],
    "motion_sety": ["Y"],
    "control_wait": ["DURATION"],
    "control_repeat": ["TIMES"],
    "control_repeat_until": ["CONDITION"],
    "control_while": ["CONDITION"],
    "control_if": ["CONDITION"],
    "control_if_else": ["CONDITION"],
    "control_wait_until": ["CONDITION"],
    "operator_add": ["NUM1", "NUM2"],
    "operator_subtract": ["NUM1", "NUM2"],
    "operator_multiply": ["NUM1", "NUM2"],
    "operator_divide": ["NUM1", "NUM2"],
    "operator_gt": ["OPERAND1", "OPERAND2"],
    "operator_lt": ["OPERAND1", "OPERAND2"],
    "operator_equals": ["OPERAND1", "OPERAND2"],
    "data_addtolist": ["LIST", "ITEM"],
}

FIELD_NAME_OVERRIDES = {
    "motion_setrotationstyle": ["STYLE"],
}

MENU_SHADOWS = {
    ("motion_goto", "TO"): ("motion_goto_menu", "TO"),
}

SUBSTACK_NAMES = {
    "control_repeat": ["SUBSTACK"],
    "control_forever": ["SUBSTACK"],
    "control_repeat_until": ["SUBSTACK"],
    "control_if": ["SUBSTACK"],
    "control_if_else": ["SUBSTACK", "SUBSTACK2"],
}


def stable_id(prefix: str, parts: list[str]) -> str:
    text = ":".join([prefix] + parts)
    return re.sub(r"[^A-Za-z0-9:_-]", "_", text)


def is_reference(value: Any) -> bool:
    return isinstance(value, dict) and value.get("type") in {"variable", "list", "broadcast"} and "name" in value


def primitive_tuple_from_value(value: Any) -> list[Any]:
    if is_reference(value):
        if value["type"] == "variable":
            return [12, value["name"]]
        if value["type"] == "list":
            return [13, value["name"]]
        return [11, value["name"]]

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [4, str(value)]

    if isinstance(value, bool):
        return [10, str(value)]

    if value is None:
        return [10, "null"]

    return [10, str(value)]


def make_literal_shadow(parent_id: str, shadow_id: str, field_name: str, value: Any) -> dict[str, Any]:
    return {
        "opcode": "text",
        "next": None,
        "parent": parent_id,
        "inputs": {},
        "fields": {
            field_name: [str(value), None],
        },
        "shadow": True,
        "topLevel": False,
    }


def resolve_shadow_primitive(primitive: list[Any]) -> Any:
    ptype = int(primitive[0])
    raw = primitive[1]

    if ptype == 12:
        return {"type": "variable", "name": str(raw)}
    if ptype == 13:
        return {"type": "list", "name": str(raw)}
    if ptype == 11:
        return {"type": "broadcast", "name": str(raw)}
    if 4 <= ptype <= 8:
        number = float(raw)
        return int(number) if number.is_integer() else number
    if raw is None:
        return None
    return str(raw)


def resolve_shadow_value(block: dict[str, Any]) -> Any:
    fields = block.get("fields") or {}
    entries = list(fields.items())
    if len(entries) == 1:
        return entries[0][1][0]
    if len(entries) > 1:
        return {key: value[0] for key, value in entries}
    return None


def build_scratch_block_from_project(target: dict[str, Any], block_id: str) -> dict[str, Any] | None:
    blocks = target.get("blocks", {})
    block = blocks.get(block_id)

    if not block or block.get("shadow"):
        return None

    if block["opcode"] == "procedures_definition":
        custom_input = (block.get("inputs") or {}).get("custom_block")
        prototype_id = custom_input[1] if custom_input and isinstance(custom_input[1], str) else None
        prototype = blocks.get(prototype_id) if prototype_id else None
        params: list[Any] = []

        if prototype and prototype.get("mutation"):
            mutation = prototype["mutation"]
            params.append(mutation.get("proccode", ""))
            try:
                names = json.loads(mutation.get("argumentnames", "[]"))
                if isinstance(names, list):
                    params.extend(str(name) for name in names)
            except (TypeError, json.JSONDecodeError):
                pass

        node = {"opcode": block["opcode"]}
        if params:
            node["params"] = params
        return node

    params: list[Any] = []
    branches: list[list[dict[str, Any]]] = []

    if block["opcode"] == "procedures_call" and block.get("mutation", {}).get("proccode"):
        params.append(block["mutation"]["proccode"])

    for field_name, field_value in (block.get("fields") or {}).items():
        if block["opcode"] == "data_addtolist" and field_name == "LIST":
            params.append(field_value[0])
        elif block["opcode"] == "motion_setrotationstyle" and field_name == "STYLE":
            params.append(field_value[0])

    for input_name, raw_input in (block.get("inputs") or {}).items():
        primary = raw_input[1]

        if input_name in ("SUBSTACK", "SUBSTACK2"):
            if isinstance(primary, str) and blocks.get(primary) and not blocks[primary].get("shadow"):
                branches.append(build_scratch_sequence_from_project(target, primary))
            else:
                branches.append([])
            continue

        if isinstance(primary, list):
            params.append(resolve_shadow_primitive(primary))
            continue

        if isinstance(primary, str):
            child = blocks.get(primary)
            if not child:
                continue

            if child.get("shadow"):
                params.append(resolve_shadow_value(child))
                continue

            nested = build_scratch_block_from_project(target, primary)
            if nested is not None:
                params.append(nested)

    node = {"opcode": block["opcode"]}
    if params:
        node["params"] = params
    if branches:
        node["blocks"] = branches
    return node


def build_scratch_sequence_from_project(target: dict[str, Any], start_id: str) -> list[dict[str, Any]]:
    blocks = target.get("blocks", {})
    sequence: list[dict[str, Any]] = []
    current_id: str | None = start_id

    while current_id:
        block = build_scratch_block_from_project(target, current_id)
        if block:
            sequence.append(block)
        current = blocks.get(current_id)
        current_id = current.get("next") if current else None

    return sequence


@dataclass
class BuildContext:
    target_name: str
    variable_ids_by_name: dict[str, str]
    list_ids_by_name: dict[str, str]
    next_id: int = 1

    def alloc(self, opcode: str) -> str:
        block_id = stable_id("block", [self.target_name, str(self.next_id), opcode])
        self.next_id += 1
        return block_id


def create_project_block(opcode: str, parent: str | None, top_level: bool) -> dict[str, Any]:
    return {
        "opcode": opcode,
        "next": None,
        "parent": parent,
        "inputs": {},
        "fields": {},
        "shadow": False,
        "topLevel": top_level,
    }


def attach_shadow_or_nested(
    context: BuildContext,
    blocks: dict[str, dict[str, Any]],
    parent_id: str,
    parent_block: dict[str, Any],
    input_name: str,
    value: Any,
) -> None:
    if isinstance(value, dict) and "opcode" in value:
        child_id = build_block_tree(context, blocks, value, parent_id, False, None, None)
        parent_block["inputs"][input_name] = [1, child_id]
        return

    menu_shadow = MENU_SHADOWS.get((parent_block["opcode"], input_name))
    if menu_shadow:
        shadow_opcode, field_name = menu_shadow
        shadow_id = context.alloc(shadow_opcode)
        blocks[shadow_id] = {
            "opcode": shadow_opcode,
            "next": None,
            "parent": parent_id,
            "inputs": {},
            "fields": {
                field_name: [str(value), None],
            },
            "shadow": True,
            "topLevel": False,
        }
        parent_block["inputs"][input_name] = [1, shadow_id]
        return

    parent_block["inputs"][input_name] = [1, primitive_tuple_from_value(value)]


def assign_param(
    context: BuildContext,
    blocks: dict[str, dict[str, Any]],
    block_id: str,
    project_block: dict[str, Any],
    opcode: str,
    index: int,
    value: Any,
) -> None:
    field_names = FIELD_NAME_OVERRIDES.get(opcode, [])
    if index < len(field_names):
        field_name = field_names[index]
        project_block["fields"][field_name] = [str(value), None]
        return

    input_names = INPUT_NAME_OVERRIDES.get(opcode, [])
    if index < len(input_names):
        input_name = input_names[index]
        if opcode == "data_addtolist" and input_name == "LIST":
            list_name = str(value)
            project_block["fields"]["LIST"] = [list_name, context.list_ids_by_name.get(list_name)]
            return
        attach_shadow_or_nested(context, blocks, block_id, project_block, input_name, value)
        return

    fallback_name = f"INPUT{index + 1}"
    attach_shadow_or_nested(context, blocks, block_id, project_block, fallback_name, value)


def attach_substacks(
    context: BuildContext,
    blocks: dict[str, dict[str, Any]],
    block_id: str,
    project_block: dict[str, Any],
    opcode: str,
    branches: list[list[dict[str, Any]]],
) -> None:
    input_names = SUBSTACK_NAMES.get(opcode, [])

    for index, branch in enumerate(branches):
        input_name = input_names[index] if index < len(input_names) else f"SUBSTACK{index + 1}"
        if branch:
            first_id = build_sequence(context, blocks, branch, block_id, False, None, None)
            project_block["inputs"][input_name] = [2, first_id]
        else:
            project_block["inputs"][input_name] = [2, None]


def build_block_tree(
    context: BuildContext,
    blocks: dict[str, dict[str, Any]],
    block: dict[str, Any],
    parent: str | None,
    top_level: bool,
    x: int | None,
    y: int | None,
) -> str:
    block_id = context.alloc(block["opcode"])
    project_block = create_project_block(block["opcode"], parent, top_level)
    blocks[block_id] = project_block

    if top_level:
        project_block["x"] = x
        project_block["y"] = y

    params = block.get("params") or []

    if block["opcode"] == "procedures_definition":
        proccode = str(params[0]) if params else ""
        argument_names = [str(value) for value in params[1:]]
        prototype_id = context.alloc("procedures_prototype")
        blocks[prototype_id] = {
            "opcode": "procedures_prototype",
            "next": None,
            "parent": block_id,
            "inputs": {},
            "fields": {},
            "shadow": True,
            "topLevel": False,
            "mutation": {
                "tagName": "mutation",
                "children": [],
                "proccode": proccode,
                "argumentids": json.dumps([f"arg{index}" for index in range(len(argument_names))]),
                "argumentnames": json.dumps(argument_names),
                "argumentdefaults": json.dumps(["" for _ in argument_names]),
                "warp": "false",
            },
        }
        project_block["inputs"]["custom_block"] = [1, prototype_id]
        return block_id

    if block["opcode"] == "procedures_call":
        argument_ids = [f"arg{index}" for index in range(max(len(params) - 1, 0))]
        project_block["mutation"] = {
            "tagName": "mutation",
            "children": [],
            "proccode": str(params[0]) if params else "",
            "argumentids": json.dumps(argument_ids),
            "warp": "false",
        }
        for index, value in enumerate(params[1:]):
            attach_shadow_or_nested(context, blocks, block_id, project_block, argument_ids[index], value)
        return block_id

    for index, value in enumerate(params):
        assign_param(context, blocks, block_id, project_block, block["opcode"], index, value)

    branches = block.get("blocks") or []
    if branches:
        attach_substacks(context, blocks, block_id, project_block, block["opcode"], branches)

    return block_id


def build_sequence(
    context: BuildContext,
    blocks: dict[str, dict[str, Any]],
    sequence: list[dict[str, Any]],
    parent: str | None,
    top_level: bool,
    x: int | None,
    y: int | None,
) -> str | None:
    previous_id: str | None = None
    first_id: str | None = None

    for index, block in enumerate(sequence):
        current_id = build_block_tree(
            context,
            blocks,
            block,
            parent if index == 0 else previous_id,
            top_level and index == 0,
            x if index == 0 else None,
            y if index == 0 else None,
        )

        if first_id is None:
            first_id = current_id

        if previous_id is not None:
            blocks[previous_id]["next"] = current_id

        previous_id = current_id

    return first_id


def default_stage() -> dict[str, Any]:
    return {
        "isStage": True,
        "name": "Stage",
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [],
        "sounds": [],
        "volume": 100,
        "layerOrder": 0,
        "tempo": 60,
        "videoTransparency": 50,
        "videoState": "on",
        "textToSpeechLanguage": None,
    }


def default_sprite(name: str, layer_order: int) -> dict[str, Any]:
    return {
        "isStage": False,
        "name": name,
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [],
        "sounds": [],
        "volume": 100,
        "layerOrder": layer_order,
        "visible": True,
        "x": 0,
        "y": 0,
        "size": 100,
        "direction": 90,
        "draggable": False,
        "rotationStyle": "all around",
    }


def target_names_from_objects(objects: list[dict[str, Any]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    if any(obj.get("target") == "Stage" for obj in objects):
        ordered.append("Stage")
        seen.add("Stage")

    for obj in objects:
        target_name = obj["target"]
        if target_name not in seen:
            ordered.append(target_name)
            seen.add(target_name)

    if "Stage" not in seen:
        ordered.insert(0, "Stage")

    return ordered


def build_targets(scratch_objects: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    objects_by_target: dict[str, list[dict[str, Any]]] = {}
    for obj in scratch_objects:
        objects_by_target.setdefault(obj["target"], []).append(obj)

    targets: list[dict[str, Any]] = []
    list_monitors: list[dict[str, Any]] = []
    layer_order = 0

    for target_index, target_name in enumerate(target_names_from_objects(scratch_objects)):
        target_objects = objects_by_target.get(target_name, [])
        is_stage = target_name == "Stage"
        target = default_stage() if is_stage else default_sprite(target_name, layer_order)
        layer_order += 0 if is_stage else 1

        variable_ids_by_name: dict[str, str] = {}
        list_ids_by_name: dict[str, str] = {}

        for obj in target_objects:
            if obj["type"] == "variable":
                var_id = stable_id("var", [target_name, obj["name"]])
                variable_ids_by_name[obj["name"]] = var_id
                target["variables"][var_id] = [obj["name"], obj["value"]]
            elif obj["type"] == "list":
                list_id = stable_id("list", [target_name, obj["name"]])
                list_ids_by_name[obj["name"]] = list_id
                target["lists"][list_id] = [obj["name"], obj["items"]]
                list_monitors.append(
                    {
                        "id": list_id,
                        "mode": "list",
                        "opcode": "data_listcontents",
                        "params": {
                            "LIST": obj["name"],
                        },
                        "spriteName": None if is_stage else target_name,
                        "value": obj["items"],
                        "width": 0,
                        "height": 0,
                        "x": 12 + 160 * len(list_monitors),
                        "y": 8,
                        "visible": True,
                    }
                )

        context = BuildContext(target_name, variable_ids_by_name, list_ids_by_name)
        script_index = 0
        for obj in target_objects:
            if obj["type"] != "script" or not obj["blocks"]:
                continue

            x = 48 + script_index * 260
            y = 64 + script_index * 120
            build_sequence(context, target["blocks"], obj["blocks"], None, True, x, y)
            script_index += 1

        targets.append(target)

    return targets, list_monitors


def convert_scratch_json_to_project(scratch_objects: list[dict[str, Any]]) -> dict[str, Any]:
    targets, list_monitors = build_targets(scratch_objects)
    return {
        "targets": targets,
        "monitors": list_monitors,
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "12.7.0",
            "agent": "",
        },
    }


def infer_output_path(scratch_json_path: str) -> str:
    if scratch_json_path.endswith(".blocks.json"):
        stem = scratch_json_path[: -len(".blocks.json")]
        return stem + ".project.json"

    directory = os.path.dirname(os.path.abspath(scratch_json_path))
    filename = os.path.basename(scratch_json_path)
    name, _sep, _ext = filename.rpartition(".")
    base = name or filename
    return os.path.join(directory, base + ".project.json")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: python3 tools/scratch_json_to_project.py path/to/project.blocks.json [output.project.json]",
            file=sys.stderr,
        )
        return 1

    scratch_json_path = argv[1]
    output_path = argv[2] if len(argv) > 2 else infer_output_path(scratch_json_path)

    if not os.path.isfile(scratch_json_path):
        print(f"Error: scratch-json file not found: {scratch_json_path}", file=sys.stderr)
        return 1

    with open(scratch_json_path, "r", encoding="utf-8") as handle:
        scratch_objects = json.load(handle)

    project = convert_scratch_json_to_project(scratch_objects)

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(project, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(os.path.abspath(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
