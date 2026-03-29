#!/usr/bin/env python3
"""
Extract Scratch blocks from .sb3/.sprite3 files and output scratch-yaml.

Usage:
    python3 extract.py <file.sb3|file.sprite3|project.json>

No external dependencies — uses only Python standard library.
"""

import hashlib
import json
import os
import sys
import zipfile


# ---------------------------------------------------------------------------
# 1. Orchestration: unzip & prepare project.json
# ---------------------------------------------------------------------------

def get_project_json(filepath):
    """Return (parsed_data, workdir) from a .sb3/.sprite3 zip or a .json file.
    workdir is None for plain .json inputs (output written alongside input)."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".json":
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f), None

    if ext not in (".sb3", ".sprite3"):
        print(f"Error: unsupported extension '{ext}'. Expected .sb3, .sprite3, or .json", file=sys.stderr)
        sys.exit(1)

    # Compute MD5 for cache directory
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    md5hex = md5.hexdigest()

    workdir = os.path.join("/tmp/scratchcode", md5hex)
    os.makedirs(workdir, exist_ok=True)

    # Extract project.json or sprite.json from zip
    # .sb3 files contain project.json; .sprite3 files contain sprite.json
    with zipfile.ZipFile(filepath, "r") as zf:
        names = zf.namelist()
        if "project.json" in names:
            json_name = "project.json"
        elif "sprite.json" in names:
            json_name = "sprite.json"
        else:
            print("Error: neither project.json nor sprite.json found in archive", file=sys.stderr)
            sys.exit(1)
        zf.extract(json_name, workdir)

    json_path = os.path.join(workdir, json_name)
    print(f"Working directory: {workdir}", file=sys.stderr)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # sprite.json is a single target — wrap it to match project.json structure
    if json_name == "sprite.json":
        data = {"targets": [data]}

    return data, workdir


# ---------------------------------------------------------------------------
# 2. Block extraction (faithful port of extract.js)
# ---------------------------------------------------------------------------

def extract_code(project_data):
    targets = []

    for target in project_data.get("targets", []):
        extracted = {
            "name": target["name"],
            "variables": {},
            "lists": [],
            "blocks": [],
        }

        # Variables: { id: [name, value] } -> { name: value }
        raw_vars = target.get("variables", {})
        if raw_vars:
            for name, value in raw_vars.values():
                extracted["variables"][name] = value

        # Lists: { id: [name, [values]] } -> [{ name, items }]
        raw_lists = target.get("lists", {})
        if raw_lists:
            for name, values in raw_lists.values():
                extracted["lists"].append({"name": name, "items": values})

        blocks = target.get("blocks", {})
        comments = target.get("comments", {})

        # blockId -> comment text
        block_comments = {}
        for c in comments.values():
            if c.get("blockId"):
                block_comments[c["blockId"]] = c.get("text", "")

        # -- Helper closures over `blocks` --

        def resolve_primitive(prim):
            ptype, value = prim[0], prim[1]
            if ptype == 12:
                return {"type": "variable", "name": value}
            if ptype == 13:
                return {"type": "list", "name": value}
            if ptype == 11:
                return {"type": "broadcast", "name": value}
            if 4 <= ptype <= 8:
                try:
                    f = float(value)
                    return int(f) if f == int(f) else f
                except (ValueError, TypeError):
                    return value
            return value

        def resolve_shadow_block(block):
            entries = list((block.get("fields") or {}).items())
            if len(entries) == 1:
                return entries[0][1][0]
            if len(entries) > 1:
                return {k: v[0] for k, v in entries}
            return None

        def resolve_input_value(inp):
            primary = inp[1]
            if isinstance(primary, list):
                return resolve_primitive(primary)
            if isinstance(primary, str):
                block = blocks.get(primary)
                if block is None:
                    return None
                if block.get("shadow"):
                    return resolve_shadow_block(block)
                return build_block(primary)  # reporter -> nested block
            return None

        def build_block(block_id):
            block = blocks.get(block_id)
            if not block or block.get("shadow"):
                return None

            params = []
            branches = []

            # procedures_definition: pull proccode + argnames from prototype shadow
            if block["opcode"] == "procedures_definition":
                custom_block_input = (block.get("inputs") or {}).get("custom_block")
                proto_id = custom_block_input[1] if custom_block_input else None
                proto = blocks.get(proto_id) if proto_id else None
                if proto and proto.get("mutation"):
                    mutation = proto["mutation"]
                    params.append(mutation.get("proccode", ""))
                    try:
                        argnames = json.loads(mutation.get("argumentnames", "[]"))
                        params.extend(argnames)
                    except (json.JSONDecodeError, TypeError):
                        pass
                node = {"opcode": block["opcode"]}
                if params:
                    node["params"] = params
                if branches:
                    node["blocks"] = branches
                return node

            # procedures_call: include proccode for readability
            if block["opcode"] == "procedures_call":
                mutation = block.get("mutation")
                if mutation and mutation.get("proccode"):
                    params.append(mutation["proccode"])

            # Field values (e.g. VARIABLE, KEY_OPTION, STOP_OPTION)
            for field_val in (block.get("fields") or {}).values():
                params.append(field_val[0])

            # Input values
            for key, inp in (block.get("inputs") or {}).items():
                if key in ("SUBSTACK", "SUBSTACK2"):
                    sub_id = inp[1]
                    if (
                        sub_id
                        and isinstance(sub_id, str)
                        and blocks.get(sub_id)
                        and not blocks[sub_id].get("shadow")
                    ):
                        branches.append(build_sequence(sub_id))
                    else:
                        branches.append([])
                else:
                    val = resolve_input_value(inp)
                    if val is not None:
                        params.append(val)

            node = {"opcode": block["opcode"]}
            if params:
                node["params"] = params
            if branches:
                node["blocks"] = branches
            return node

        def build_sequence(start_id):
            seq = []
            current_id = start_id
            while current_id:
                node = build_block(current_id)
                if node:
                    seq.append(node)
                blk = blocks.get(current_id)
                current_id = blk.get("next") if blk else None
            return seq

        # Collect top-level scripts
        scripts = []
        for block_id, block in blocks.items():
            if block.get("topLevel") and not block.get("shadow"):
                scripts.append(build_sequence(block_id))
        extracted["blocks"] = scripts

        targets.append(extracted)

    return targets


# ---------------------------------------------------------------------------
# 3. Custom scratch-yaml serializer
# ---------------------------------------------------------------------------

def _needs_quoting(s):
    """Check if a string value needs YAML quoting."""
    if not isinstance(s, str):
        return False
    if s == "":
        return True
    # Looks like a number
    try:
        float(s)
        return True
    except ValueError:
        pass
    # YAML special values
    if s.lower() in ("true", "false", "yes", "no", "null", "~", "on", "off"):
        return True
    # Contains chars that break YAML structure
    for ch in (":", "#", "[", "]", "{", "}", ",", "'", '"', "`", "|", ">", "*", "&", "%", "@"):
        if ch in s:
            return True
    if s.startswith("- ") or s.startswith("? "):
        return True
    return False


def _format_scalar(val):
    """Format a scalar value for YAML output."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return str(int(val)) if val == int(val) else str(val)
    s = str(val)
    if _needs_quoting(s):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _is_simple_param(p):
    """True if param is a simple scalar (not a block dict or typed ref)."""
    return not isinstance(p, dict)


def _format_block_lines(block, indent):
    """Return list of YAML lines for a single block at given indent level."""
    prefix = " " * indent
    lines = []

    opcode = block["opcode"]
    params = block.get("params")
    branches = block.get("blocks")

    lines.append(f"{prefix}opcode: {opcode}")

    # params
    if params and all(_is_simple_param(p) for p in params):
        formatted = ", ".join(_format_scalar(p) for p in params)
        lines.append(f"{prefix}params: [{formatted}]")
    elif params:
        lines.append(f"{prefix}params:")
        for p in params:
            if _is_simple_param(p):
                lines.append(f"{prefix}  - {_format_scalar(p)}")
            else:
                # Nested block or typed reference
                sub_lines = _format_dict_inline_or_block(p, indent + 4)
                lines.append(f"{prefix}  - {sub_lines[0].lstrip()}")
                lines.extend(sub_lines[1:])

    # blocks (branches)
    if branches:
        lines.append(f"{prefix}blocks:")
        for branch in branches:
            if not branch:
                lines.append(f"{prefix}  - []")
            else:
                for i, blk in enumerate(branch):
                    blk_lines = _format_block_lines(blk, indent + 6)
                    if i == 0:
                        # First block in branch: "  - - opcode: ..."
                        lines.append(f"{prefix}  - - {blk_lines[0].lstrip()}")
                    else:
                        # Subsequent blocks: "    - opcode: ..."
                        lines.append(f"{prefix}    - {blk_lines[0].lstrip()}")
                    lines.extend(blk_lines[1:])

    return lines


def _format_dict_inline_or_block(d, indent):
    """Format a dict that's either a nested block or a typed reference."""
    prefix = " " * indent
    if "opcode" in d:
        return _format_block_lines(d, indent)
    elif "type" in d:
        # Typed reference: { type: variable, name: score }
        return [f"{prefix}type: {d['type']}", f"{prefix}name: {_format_scalar(d['name'])}"]
    else:
        # Generic dict (multi-field shadow, rare)
        lines = []
        for k, v in d.items():
            lines.append(f"{prefix}{k}: {_format_scalar(v)}")
        return lines


def _format_mapping(mapping, indent):
    prefix = " " * indent
    lines = []
    for key, value in mapping.items():
        lines.append(f"{prefix}{key}: {_format_scalar(value)}")
    return lines


def _format_scalar_list(values, indent):
    prefix = " " * indent
    return [f"{prefix}- {_format_scalar(value)}" for value in values]


def _format_lists(lists, indent):
    prefix = " " * indent
    lines = []
    for item in lists:
        lines.append(f"{prefix}- name: {_format_scalar(item['name'])}")
        entries = item.get("items", [])
        if entries:
            lines.append(f"{prefix}  items:")
            lines.extend(_format_scalar_list(entries, indent + 4))
        else:
            lines.append(f"{prefix}  items: []")
    return lines


def _format_script_lines(script, indent):
    prefix = " " * indent
    if not script:
        return [f"{prefix}- []"]

    lines = []
    for i, block in enumerate(script):
        blk_lines = _format_block_lines(block, indent + 4)
        marker = "- -" if i == 0 else "  -"
        lines.append(f"{prefix}{marker} {blk_lines[0].lstrip()}")
        lines.extend(blk_lines[1:])
    return lines


def to_scratch_yaml(targets):
    """Convert extracted target data to scratch-yaml string."""
    all_lines = []

    for target in targets:
        if all_lines:
            all_lines.append("")
        all_lines.append(f"- name: {_format_scalar(target['name'])}")
        variables = target.get("variables", {})
        if variables:
            all_lines.append("  variables:")
            all_lines.extend(_format_mapping(variables, 4))
        else:
            all_lines.append("  variables: {}")

        lists = target.get("lists", [])
        if lists:
            all_lines.append("  lists:")
            all_lines.extend(_format_lists(lists, 4))
        else:
            all_lines.append("  lists: []")

        scripts = target.get("blocks", [])
        if not scripts:
            all_lines.append("  blocks: []")
            continue

        all_lines.append("  blocks:")
        for script in scripts:
            all_lines.extend(_format_script_lines(script, 4))

    return "\n".join(all_lines) + "\n"


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract.py <file.sb3|file.sprite3|project.json>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    project_data, workdir = get_project_json(filepath)
    extracted = extract_code(project_data)
    yaml_content = to_scratch_yaml(extracted)

    # Write output file into workdir (or alongside .json input)
    if workdir:
        out_path = os.path.join(workdir, "blocks.yaml")
    else:
        base = os.path.splitext(filepath)[0]
        out_path = base + ".blocks.yaml"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    # Print the output file path so callers know where to find it
    print(out_path)


if __name__ == "__main__":
    main()
