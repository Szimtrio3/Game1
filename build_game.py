import json
import hashlib
import zipfile


def make_asset(svg_text, extension):
    blob = svg_text.encode("utf-8")
    asset_id = hashlib.md5(blob).hexdigest()
    asset = {
        "assetId": asset_id,
        "name": "costume",
        "bitmapResolution": 1,
        "md5ext": f"{asset_id}.{extension}",
        "dataFormat": extension,
        "rotationCenterX": 240,
        "rotationCenterY": 180,
    }
    return asset, blob


def make_sprite_asset(svg_text):
    blob = svg_text.encode("utf-8")
    asset_id = hashlib.md5(blob).hexdigest()
    asset = {
        "assetId": asset_id,
        "name": "ship",
        "bitmapResolution": 1,
        "md5ext": f"{asset_id}.svg",
        "dataFormat": "svg",
        "rotationCenterX": 50,
        "rotationCenterY": 50,
    }
    return asset, blob


def add_block(blocks, block_id, opcode, next_id=None, parent=None, inputs=None, fields=None, topLevel=False, x=0, y=0, shadow=False):
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
    backdrop_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
      <defs>
        <radialGradient id="bg" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#1d2a6b"/>
          <stop offset="100%" stop-color="#090d1a"/>
        </radialGradient>
      </defs>
      <rect width="480" height="360" fill="url(#bg)"/>
      <g fill="#8df7ff" opacity="0.8">
        <circle cx="40" cy="60" r="2"/>
        <circle cx="130" cy="120" r="1.8"/>
        <circle cx="220" cy="40" r="1.5"/>
        <circle cx="300" cy="90" r="2"/>
        <circle cx="420" cy="130" r="1.8"/>
        <circle cx="100" cy="260" r="2"/>
        <circle cx="360" cy="250" r="1.8"/>
        <circle cx="220" cy="300" r="2"/>
      </g>
      <circle cx="240" cy="180" r="120" fill="none" stroke="#4dd0ff" stroke-width="2" opacity="0.6"/>
      <circle cx="240" cy="180" r="90" fill="none" stroke="#7d78ff" stroke-width="1.5" opacity="0.5"/>
    </svg>
    """

    ship_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
      <path d="M50 8 L76 74 L50 60 L24 74 Z" fill="#22e6ff" stroke="#ffffff" stroke-width="4"/>
      <path d="M50 28 L60 64 L50 58 L40 64 Z" fill="#6d4dff"/>
      <circle cx="50" cy="50" r="6" fill="#ffffff"/>
    </svg>
    """

    backdrop_asset, backdrop_blob = make_asset(backdrop_svg, "svg")
    ship_asset, ship_blob = make_sprite_asset(ship_svg)

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
            "name": "Backdrop",
            "bitmapResolution": 1,
            "dataFormat": "svg",
            "assetId": backdrop_asset["assetId"],
            "md5ext": backdrop_asset["md5ext"],
            "rotationCenterX": 240,
            "rotationCenterY": 180,
        }],
        "sounds": [],
        "volume": 100,
        "layerOrder": 0,
    }

    sprite_vars = {
        "score": ["score", 0],
        "lives": ["lives", 5],
        "wave": ["wave", 1],
    }

    sprite = {
        "isStage": False,
        "name": "Chrono Runner",
        "variables": sprite_vars,
        "lists": {},
        "broadcasts": {},
        "blocks": {},
        "comments": {},
        "currentCostume": 0,
        "costumes": [{
            "name": "Ship",
            "bitmapResolution": 1,
            "dataFormat": "svg",
            "assetId": ship_asset["assetId"],
            "md5ext": ship_asset["md5ext"],
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

    def make_id():
        nonlocal counter
        value = f"b{counter}"
        counter += 1
        return value

    # Root script: green flag sets values, then runs forever.
    b0 = make_id()
    add_block(blocks, b0, "event_whenflagclicked", topLevel=True, x=40, y=40)

    b1 = make_id()
    add_block(blocks, b1, "data_setvariableto", parent=b0, inputs={"VALUE": [1, ["10", "0"]]}, fields={"VARIABLE": ["score", "score"]}, x=40, y=120)
    blocks[b0]["next"] = b1

    b2 = make_id()
    add_block(blocks, b2, "data_setvariableto", parent=b1, inputs={"VALUE": [1, ["10", "5"]]}, fields={"VARIABLE": ["lives", "lives"]}, x=40, y=200)
    blocks[b1]["next"] = b2

    b3 = make_id()
    add_block(blocks, b3, "data_setvariableto", parent=b2, inputs={"VALUE": [1, ["10", "1"]]}, fields={"VARIABLE": ["wave", "wave"]}, x=40, y=280)
    blocks[b2]["next"] = b3

    b4 = make_id()
    add_block(blocks, b4, "control_forever", parent=b3, x=40, y=360)
    blocks[b3]["next"] = b4

    b5 = make_id()
    add_block(blocks, b5, "motion_pointtowards", parent=b4, inputs={"TOWARDS": [1, ["10", "_mouse_"]] }, x=120, y=380)
    blocks[b4]["inputs"] = {"SUBSTACK": [2, b5]}

    b6 = make_id()
    add_block(blocks, b6, "control_if", parent=b5, x=120, y=470)
    blocks[b5]["next"] = b6

    key_up = make_id()
    add_block(blocks, key_up, "sensing_keypressed", inputs={"KEY_OPTION": [1, ["10", "up arrow"]]}, shadow=True, x=180, y=470)
    blocks[b6]["inputs"] = {"CONDITION": [2, key_up], "SUBSTACK": [2, None]}

    up_move = make_id()
    add_block(blocks, up_move, "motion_changeyby", parent=b6, inputs={"DY": [1, ["10", "5"]]}, x=180, y=540)
    blocks[b6]["inputs"]["SUBSTACK"] = [2, up_move]

    # Add a second condition for left/right movement to create a simple playable controller.
    b7 = make_id()
    add_block(blocks, b7, "control_if", parent=b5, x=260, y=470)
    blocks[b5]["next"] = b7

    key_left = make_id()
    add_block(blocks, key_left, "sensing_keypressed", inputs={"KEY_OPTION": [1, ["10", "left arrow"]]}, shadow=True, x=330, y=470)
    blocks[b7]["inputs"] = {"CONDITION": [2, key_left], "SUBSTACK": [2, None]}

    left_move = make_id()
    add_block(blocks, left_move, "motion_changexby", parent=b7, inputs={"DX": [1, ["10", "-5"]]}, x=330, y=540)
    blocks[b7]["inputs"]["SUBSTACK"] = [2, left_move]

    # Create a basic shoot action on mouse click.
    b8 = make_id()
    add_block(blocks, b8, "control_if", parent=b7, x=400, y=470)
    blocks[b7]["next"] = b8

    mouse_down = make_id()
    add_block(blocks, mouse_down, "sensing_mousedown", shadow=False, x=470, y=470)
    blocks[b8]["inputs"] = {"CONDITION": [2, mouse_down], "SUBSTACK": [2, None]}

    say_fire = make_id()
    add_block(blocks, say_fire, "looks_say", parent=b8, inputs={"MESSAGE": [1, ["10", "PEW!"]] }, x=470, y=540)
    blocks[b8]["inputs"]["SUBSTACK"] = [2, say_fire]

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

    with zipfile.ZipFile("chrono-rift.sb3", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json", json.dumps(project, separators=(",", ":")))
        zf.writestr(backdrop_asset["md5ext"], backdrop_blob)
        zf.writestr(ship_asset["md5ext"], ship_blob)

    print("Built chrono-rift.sb3")


build_project()
