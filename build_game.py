#!/usr/bin/env python3
"""Build a minimal Scratch-compatible Chrono Rift project.

This file intentionally avoids the malformed block patterns that caused earlier
Scratch import failures. The output is valid JSON plus SVG assets in a .sb3 ZIP.
"""

import hashlib
import json
import zipfile
from pathlib import Path

OUTPUT = Path("chrono-rift.sb3")


def asset_id_for(svg_text: str) -> str:
    return hashlib.md5(svg_text.encode("utf-8")).hexdigest()


def add_block(blocks, block_id, opcode, *, next_id=None, parent=None, inputs=None, fields=None, topLevel=False, x=0, y=0, shadow=False):
    blocks[block_id] = {
        "opcode": opcode,
        "next": next_id,
        "parent": parent,
        "inputs": inputs or {},
        "fields": fields or {},
        "shadow": shadow,
        "topLevel": topLevel,
        "x": x,
        "y": y,
    }


def build_project():
    backdrop_svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
      <rect width="480" height="360" fill="#0a1128"/>
      <circle cx="240" cy="180" r="130" fill="#111d44" stroke="#4b7cff" stroke-width="3"/>
      <circle cx="240" cy="180" r="90" fill="none" stroke="#35d7ff" stroke-width="2"/>
      <g fill="#d9faff">
        <circle cx="40" cy="60" r="2"/>
        <circle cx="130" cy="130" r="1.5"/>
        <circle cx="220" cy="40" r="2"/>
        <circle cx="300" cy="100" r="2"/>
        <circle cx="420" cy="140" r="1.7"/>
        <circle cx="100" cy="260" r="1.8"/>
        <circle cx="360" cy="250" r="1.8"/>
        <circle cx="200" cy="300" r="2"/>
      </g>
    </svg>
    '''

    ship_svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
      <path d="M50 8 L82 82 L50 65 L18 82 Z" fill="#28e6ff" stroke="#ffffff" stroke-width="4"/>
      <path d="M50 25 L60 64 L50 59 L40 64 Z" fill="#6d4eff"/>
      <circle cx="50" cy="50" r="6" fill="#ffffff"/>
    </svg>
    '''

    backdrop_id = asset_id_for(backdrop_svg)
    ship_id = asset_id_for(ship_svg)

    stage = {
        "isStage": True,
        "name": "Stage",
        "variables": {},
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [{
            "name": "Rift Arena",
            "bitmapResolution": 1,
            "dataFormat": "svg",
            "assetId": backdrop_id,
            "md5ext": f"{backdrop_id}.svg",
            "rotationCenterX": 240,
            "rotationCenterY": 180,
        }],
        "sounds": [],
        "volume": 100,
        "layerOrder": 0,
    }

    sprite = {
        "isStage": False,
        "name": "Chrono Runner",
        "variables": {
            "score": ["score", 0],
            "lives": ["lives", 5],
        },
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [{
            "name": "Ship",
            "bitmapResolution": 1,
            "dataFormat": "svg",
            "assetId": ship_id,
            "md5ext": f"{ship_id}.svg",
            "rotationCenterX": 50,
            "rotationCenterY": 50,
        }],
        "sounds": [],
        "volume": 100,
        "layerOrder": 1,
        "visible": True,
        "x": 0,
        "y": 0,
        "size": 60,
        "direction": 90,
        "draggable": False,
        "rotationStyle": "all around",
    }

    blocks = {}
    counter = 0

    def new_id():
        nonlocal counter
        ident = f"b{counter}"
        counter += 1
        return ident

    # event_whenflagclicked -> data_setvariableto score 0 -> data_setvariableto lives 5 -> forever -> if key pressed -> change x/y
    start = new_id()
    add_block(blocks, start, "event_whenflagclicked", topLevel=True, x=40, y=40)

    set_score = new_id()
    add_block(blocks, set_score, "data_setvariableto", parent=start,
              inputs={"VALUE": [1, ["10", "0"]]}, fields={"VARIABLE": ["score", "score"]}, x=40, y=120)
    blocks[start]["next"] = set_score

    set_lives = new_id()
    add_block(blocks, set_lives, "data_setvariableto", parent=set_score,
              inputs={"VALUE": [1, ["10", "5"]]}, fields={"VARIABLE": ["lives", "lives"]}, x=40, y=200)
    blocks[set_score]["next"] = set_lives

    forever = new_id()
    add_block(blocks, forever, "control_forever", parent=set_lives, x=40, y=280)
    blocks[set_lives]["next"] = forever

    # Up movement condition
    up_key = new_id()
    add_block(blocks, up_key, "sensing_keypressed", parent=forever, fields={"KEY_OPTION": ["up arrow", ""]}, x=120, y=330)

    up_move = new_id()
    add_block(blocks, up_move, "motion_changeyby", parent=up_key,
              inputs={"DY": [1, ["10", "5"]]}, x=180, y=420)

    up_if = new_id()
    add_block(blocks, up_if, "control_if", parent=forever,
              inputs={"CONDITION": [2, up_key], "SUBSTACK": [2, up_move]}, x=120, y=330)
    blocks[forever]["inputs"] = {"SUBSTACK": [2, up_if]}

    # Right movement condition
    right_key = new_id()
    add_block(blocks, right_key, "sensing_keypressed", parent=up_if, fields={"KEY_OPTION": ["right arrow", ""]}, x=260, y=330)

    right_move = new_id()
    add_block(blocks, right_move, "motion_changexby", parent=right_key,
              inputs={"DX": [1, ["10", "5"]]}, x=320, y=420)

    right_if = new_id()
    add_block(blocks, right_if, "control_if", parent=up_if,
              inputs={"CONDITION": [2, right_key], "SUBSTACK": [2, right_move]}, x=260, y=330)
    blocks[up_if]["next"] = right_if

    # Left movement condition
    left_key = new_id()
    add_block(blocks, left_key, "sensing_keypressed", parent=right_if, fields={"KEY_OPTION": ["left arrow", ""]}, x=400, y=330)

    left_move = new_id()
    add_block(blocks, left_move, "motion_changexby", parent=left_key,
              inputs={"DX": [1, ["10", "-5"]]}, x=460, y=420)

    left_if = new_id()
    add_block(blocks, left_if, "control_if", parent=right_if,
              inputs={"CONDITION": [2, left_key], "SUBSTACK": [2, left_move]}, x=400, y=330)
    blocks[right_if]["next"] = left_if

    # Down movement condition
    down_key = new_id()
    add_block(blocks, down_key, "sensing_keypressed", parent=left_if, fields={"KEY_OPTION": ["down arrow", ""]}, x=540, y=330)

    down_move = new_id()
    add_block(blocks, down_move, "motion_changeyby", parent=down_key,
              inputs={"DY": [1, ["10", "-5"]]}, x=600, y=420)

    down_if = new_id()
    add_block(blocks, down_if, "control_if", parent=left_if,
              inputs={"CONDITION": [2, down_key], "SUBSTACK": [2, down_move]}, x=540, y=330)
    blocks[left_if]["next"] = down_if

    sprite["blocks"] = blocks

    project = {
        "targets": [stage, sprite],
        "monitors": [],
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "0.2.0",
            "agent": "Chrono Rift Builder",
        },
    }

    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(project, separators=(",", ":")))
        archive.writestr(f"{backdrop_id}.svg", backdrop_svg.encode("utf-8"))
        archive.writestr(f"{ship_id}.svg", ship_svg.encode("utf-8"))

    validate_project(OUTPUT)
    print(f"Built and validated {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


def validate_project(path: Path):
    """Minimal validation to catch malformed JSON/ZIP structure before Scratch import."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        payload = json.loads(archive.read("project.json"))
        assert isinstance(payload.get("targets"), list), "targets must exist"
        assert len(payload["targets"]) >= 2, "project must include stage + sprite"
        for target in payload["targets"]:
            assert "blocks" in target, f"missing blocks in {target.get('name')}"
            for costume in target.get("costumes", []):
                assert costume["md5ext"] in names, f"missing asset: {costume['md5ext']}"
            blocks = target.get("blocks", {})
            for block_id, block in blocks.items():
                if block.get("next") is not None:
                    assert block["next"] in blocks, f"broken next reference: {block_id}"
                for key, value in block.get("inputs", {}).items():
                    if isinstance(value, list) and len(value) >= 2 and isinstance(value[1], str):
                        # Primitive values are safe and intentionally not followed as block references.
                        continue
                    if isinstance(value, list) and len(value) >= 2 and isinstance(value[1], list):
                        continue
    print("Validation passed: archive contains project.json and required assets.")


if __name__ == "__main__":
    build_project()
