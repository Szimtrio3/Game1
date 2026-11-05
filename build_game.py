#!/usr/bin/env python3
"""Build a self-contained, Scratch 3-compatible Chrono Rift project (.sb3).

No third-party packages are needed. The output is a ZIP archive containing the
standard Scratch project.json plus its SVG costume assets.
"""

import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

OUTPUT = Path("chrono-rift.sb3")

# Global variables live on the Stage so every sprite and clone shares them.
GLOBALS = {
    "Mode": "g_mode", "Score": "g_score", "Lives": "g_lives",
    "Wave": "g_wave", "Energy": "g_energy", "Kills": "g_kills",
    "Hurt": "g_hurt", "Shot X": "g_shot_x", "Shot Y": "g_shot_y",
}
MESSAGES = {"shoot": "m_shoot", "hit": "m_hit", "nova": "m_nova"}


@dataclass
class Block:
    opcode: str
    inputs: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)
    next: object = None
    top: bool = False
    x: int = 0
    y: int = 0
    shadow: bool = False


def b(opcode, inputs=None, fields=None, *, top=False, x=40, y=40, shadow=False):
    return Block(opcode, inputs or {}, fields or {}, None, top, x, y, shadow)


def seq(*items):
    items = [item for item in items if item is not None]
    for first, following in zip(items, items[1:]):
        first.next = following
    return items[0] if items else None


def num(value): return ("number", str(value))
def text(value): return ("text", str(value))
def gv(name): return b("data_variable", fields={"VARIABLE": [name, GLOBALS[name]]})
def lv(name, ident): return b("data_variable", fields={"VARIABLE": [name, ident]})
def setv(name, value): return b("data_setvariableto", {"VALUE": value}, {"VARIABLE": [name, GLOBALS[name]]})
def change(name, value): return b("data_changevariableby", {"VALUE": value}, {"VARIABLE": [name, GLOBALS[name]]})
def set_local(name, ident, value): return b("data_setvariableto", {"VALUE": value}, {"VARIABLE": [name, ident]})
def change_local(name, ident, value): return b("data_changevariableby", {"VALUE": value}, {"VARIABLE": [name, ident]})
def add(a, c): return b("operator_add", {"NUM1": a, "NUM2": c})
def sub(a, c): return b("operator_subtract", {"NUM1": a, "NUM2": c})
def mul(a, c): return b("operator_multiply", {"NUM1": a, "NUM2": c})
def lt(a, c): return b("operator_lt", {"OPERAND1": a, "OPERAND2": c})
def gt(a, c): return b("operator_gt", {"OPERAND1": a, "OPERAND2": c})
def eq(a, c): return b("operator_equals", {"OPERAND1": a, "OPERAND2": c})
def and_(a, c): return b("operator_and", {"OPERAND1": a, "OPERAND2": c})
def or_(a, c): return b("operator_or", {"OPERAND1": a, "OPERAND2": c})
def iff(condition, body): return b("control_if", {"CONDITION": condition, "SUBSTACK": body})
def forever(body): return b("control_forever", {"SUBSTACK": body})
def repeat_until(condition, body): return b("control_repeat_until", {"CONDITION": condition, "SUBSTACK": body})
def wait(seconds): return b("control_wait", {"DURATION": seconds})
def random(a, c): return b("operator_random", {"FROM": num(a), "TO": num(c)})
def x_pos(): return b("motion_xposition")
def y_pos(): return b("motion_yposition")
def key_pressed(key_name):
    menu = b("sensing_keyoptions", fields={"KEY_OPTION": [key_name, ""]}, shadow=True)
    return b("sensing_keypressed", {"KEY_OPTION": menu})
def mouse_target():
    menu = b("motion_pointtowards_menu", fields={"TOWARDS": ["_mouse_", ""]}, shadow=True)
    return b("motion_pointtowards", {"TOWARDS": menu})
def target_menu(sprite_name):
    return b("sensing_touchingobjectmenu", fields={"TOUCHINGOBJECTMENU": [sprite_name, ""]}, shadow=True)
def touching(sprite_name):
    return b("sensing_touchingobject", {"TOUCHINGOBJECTMENU": target_menu(sprite_name)})
def broadcast_menu(name):
    return b("event_broadcast_menu", fields={"BROADCAST_OPTION": [name, MESSAGES[name]]}, shadow=True)
def broadcast(name, wait_for=False):
    opcode = "event_broadcastandwait" if wait_for else "event_broadcast"
    return b(opcode, {"BROADCAST_INPUT": broadcast_menu(name)})
def hat_flag(x=40, y=40): return b("event_whenflagclicked", top=True, x=x, y=y)
def hat_clone(x=40, y=40): return b("control_start_as_clone", top=True, x=x, y=y)
def hat_message(name, x=40, y=40):
    return b("event_whenbroadcastreceived", fields={"BROADCAST_OPTION": [name, MESSAGES[name]]}, top=True, x=x, y=y)
def distance_sq_to_hit():
    dx = sub(gv("Shot X"), x_pos())
    dy = sub(gv("Shot Y"), y_pos())
    return add(mul(dx, dx), mul(dy, dy))
def distance_sq_to_player():
    dx = sub(b("motion_xposition", fields={}), x_pos())
    dy = sub(b("motion_yposition", fields={}), y_pos())
    # The player position is stored globally, avoiding target-coordinate ambiguity.
    dx = sub(gv("Player X"), x_pos())
    dy = sub(gv("Player Y"), y_pos())
    return add(mul(dx, dx), mul(dy, dy))

# Player coordinates are shared for precise enemy targeting and nova range checks.
GLOBALS["Player X"] = "g_player_x"
GLOBALS["Player Y"] = "g_player_y"


def encode_primitive(value):
    kind, raw = value
    return [1, [4 if kind == "number" else 10, raw]]


def serialize_script(root, blocks):
    """Serialize a connected Scratch block graph, preserving parent/next links."""
    counter = [0]

    def visit(node, parent=None):
        if node is None:
            return None
        ident = f"b{counter[0]}"
        counter[0] += 1
        record = {
            "opcode": node.opcode, "next": None, "parent": parent,
            "inputs": {}, "fields": node.fields,
            "shadow": node.shadow, "topLevel": node.top,
        }
        if node.top:
            record["x"], record["y"] = node.x, node.y
        blocks[ident] = record
        for key, value in node.inputs.items():
            if isinstance(value, Block):
                child = visit(value, ident)
                record["inputs"][key] = [1 if value.shadow else 2, child]
            elif key.startswith("SUBSTACK"):
                child = visit(value, ident) if isinstance(value, Block) else None
                record["inputs"][key] = [2, child]
            elif isinstance(value, tuple):
                record["inputs"][key] = encode_primitive(value)
            else:
                raise TypeError(f"Unsupported input {key}: {value!r}")
        if node.next is not None:
            record["next"] = visit(node.next, ident)
        return ident

    visit(root)


def asset(svg):
    content = svg.encode("utf-8")
    digest = hashlib.md5(content).hexdigest()
    return {"name": "costume", "bitmapResolution": 1, "dataFormat": "svg",
            "assetId": digest, "md5ext": digest + ".svg"}, content


# Clean, Scratch-friendly SVGs: simple paths and primitives, no external resources.
BACKDROP_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
<rect width="480" height="360" fill="#080d20"/><circle cx="240" cy="180" r="130" fill="#111944" stroke="#593cff" stroke-width="3"/>
<circle cx="240" cy="180" r="100" fill="none" stroke="#19d9f5" stroke-width="2"/><circle cx="240" cy="180" r="72" fill="#24134c" stroke="#b34cff" stroke-width="3"/>
<g fill="#d9fbff"><circle cx="35" cy="45" r="2"/><circle cx="90" cy="130" r="1.5"/><circle cx="430" cy="65" r="2"/><circle cx="390" cy="280" r="1.5"/><circle cx="55" cy="300" r="2"/><circle cx="180" cy="70" r="1"/><circle cx="325" cy="320" r="1.5"/><circle cx="450" cy="190" r="1"/><circle cx="130" cy="245" r="1"/></g></svg>'''
PLAYER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><path d="M50 5 L82 82 L50 65 L18 82 Z" fill="#20e6ff" stroke="#ffffff" stroke-width="4"/><path d="M50 25 L61 66 L50 59 L39 66 Z" fill="#704cff"/><circle cx="50" cy="50" r="6" fill="#ffffff"/></svg>'''
ENEMY_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><path d="M50 8 L64 32 L92 36 L72 55 L78 85 L50 72 L22 85 L28 55 L8 36 L36 32 Z" fill="#ff426d" stroke="#ffd6e1" stroke-width="4"/><circle cx="40" cy="47" r="5" fill="#ffffff"/><circle cx="60" cy="47" r="5" fill="#ffffff"/></svg>'''
BULLET_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="11" fill="#fff38a" stroke="#ff9e38" stroke-width="4"/></svg>'''


def make_stage(backdrop):
    variables = {name: [name, 0] for name in GLOBALS}
    variables["Lives"][1] = 5
    variables["Wave"][1] = 1
    broadcasts = dict(MESSAGES)
    return {
        "isStage": True, "name": "Stage", "variables": variables,
        "lists": {}, "broadcasts": broadcasts, "blocks": {}, "comments": {},
        "currentCostume": 0,
        "costumes": [{**backdrop, "name": "Rift Arena", "rotationCenterX": 240, "rotationCenterY": 180}],
        "sounds": [], "volume": 100, "layerOrder": 0,
        "tempo": 60, "videoTransparency": 50, "videoState": "on",
        "textToSpeechLanguage": None,
    }


def make_player(costume):
    local = {"Cooldown": ["p_cooldown", 0]}
    target = {"isStage": False, "name": "Chrono Runner", "variables": local,
              "lists": {}, "broadcasts": {}, "blocks": {}, "comments": {},
              "currentCostume": 0,
              "costumes": [{**costume, "name": "Chrono Runner", "rotationCenterX": 50, "rotationCenterY": 50}],
              "sounds": [], "volume": 100, "layerOrder": 3, "visible": True,
              "x": 0, "y": 0, "size": 55, "direction": 90,
              "draggable": False, "rotationStyle": "all around"}
    script = seq(
        hat_flag(30, 30),
        setv("Mode", text("title")), setv("Score", num(0)), setv("Lives", num(5)),
        setv("Wave", num(1)), setv("Energy", num(0)), setv("Kills", num(0)),
        setv("Hurt", num(0)), setv("Player X", num(0)), setv("Player Y", num(0)),
        set_local("Cooldown", "p_cooldown", num(0)),
        b("motion_gotoxy", {"X": num(0), "Y": num(0)}), b("looks_show"),
        b("looks_say", {"MESSAGE": text("CHRONO RIFT  //  Arrow keys move  •  Mouse fires  •  Q = NOVA  //  Press SPACE")}),
        b("control_wait_until", {"CONDITION": key_pressed("space")}),
        b("looks_say", {"MESSAGE": text("")}), setv("Mode", text("playing")),
        forever(seq(
            iff(eq(gv("Mode"), text("playing")), seq(
                setv("Player X", x_pos()), setv("Player Y", y_pos()),
                mouse_target(),
                iff(key_pressed("up arrow"), b("motion_changeyby", {"DY": num(5)})),
                iff(key_pressed("down arrow"), b("motion_changeyby", {"DY": num(-5)})),
                iff(key_pressed("left arrow"), b("motion_changexby", {"DX": num(-5)})),
                iff(key_pressed("right arrow"), b("motion_changexby", {"DX": num(5)})),
                # Keep the ship inside the arena.
                iff(lt(x_pos(), num(-225)), b("motion_setx", {"X": num(-225)})),
                iff(gt(x_pos(), num(225)), b("motion_setx", {"X": num(225)})),
                iff(lt(y_pos(), num(-165)), b("motion_sety", {"Y": num(-165)})),
                iff(gt(y_pos(), num(165)), b("motion_sety", {"Y": num(165)})),
                iff(gt(lv("Cooldown", "p_cooldown"), num(0)), change_local("Cooldown", "p_cooldown", num(-1))),
                iff(and_(b("sensing_mousedown"), lt(lv("Cooldown", "p_cooldown"), num(1))), seq(
                    broadcast("shoot"), set_local("Cooldown", "p_cooldown", num(9)))),
                iff(and_(key_pressed("q"), gt(gv("Energy"), num(99))), seq(
                    setv("Energy", num(0)), broadcast("nova"))),
                iff(gt(gv("Hurt"), num(0)), change("Hurt", num(-1))),
                iff(gt(gv("Kills"), num(7)), seq(
                    change("Wave", num(1)), setv("Kills", num(0)))),
                iff(gt(gv("Wave"), num(15)), seq(
                    setv("Mode", text("victory")),
                    b("looks_say", {"MESSAGE": text("RIFT STABILIZED!  You saved the timeline.  Green flag to play again.")}))),
                iff(lt(gv("Lives"), num(1)), seq(
                    setv("Mode", text("gameover")),
                    b("looks_say", {"MESSAGE": text("RIFT COLLAPSED  •  Final score is shown above  •  Green flag to retry")}))),
            )),
            wait(num(0.02)),
        )),
    )
    serialize_script(script, target["blocks"])
    return target


def make_enemy(costume):
    local = {"Enemy HP": ["e_hp", 3]}
    target = {"isStage": False, "name": "Rift Wraith", "variables": local,
              "lists": {}, "broadcasts": {}, "blocks": {}, "comments": {},
              "currentCostume": 0,
              "costumes": [{**costume, "name": "Rift Wraith", "rotationCenterX": 50, "rotationCenterY": 50}],
              "sounds": [], "volume": 100, "layerOrder": 2, "visible": False,
              "x": 0, "y": 0, "size": 55, "direction": 90,
              "draggable": False, "rotationStyle": "all around"}
    spawn = seq(
        hat_flag(430, 30), b("looks_hide"),
        forever(seq(
            iff(eq(gv("Mode"), text("playing")), seq(
                wait(random(0.55, 1.25)),
                b("motion_gotoxy", {"X": random(-220, 220), "Y": random(-160, 160)}),
                b("control_create_clone_of", {"CLONE_OPTION": b("control_create_clone_of_menu", fields={"CLONE_OPTION": ["_myself_", ""]}, shadow=True)}),
            )),
            wait(num(0.02)),
        )),
    )
    clone = seq(
        hat_clone(430, 370), set_local("Enemy HP", "e_hp", add(num(2), gv("Wave"))),
        b("looks_setsize %", {"SIZE": sub(num(65), mul(gv("Wave"), num(1.5)))}),
        b("looks_show"),
        forever(seq(
            iff(eq(gv("Mode"), text("playing")), seq(
                b("motion_pointtowards", {"TOWARDS": b("motion_pointtowards_menu", fields={"TOWARDS": ["Chrono Runner", ""]}, shadow=True)}),
                b("motion_movesteps", {"STEPS": add(num(1.1), mul(gv("Wave"), num(0.12)))}),
                iff(and_(touching("Chrono Runner"), eq(gv("Hurt"), num(0))), seq(
                    change("Lives", num(-1)), setv("Hurt", num(35)))),
                iff(lt(lv("Enemy HP", "e_hp"), num(1)), seq(
                    change("Score", num(10)), change("Kills", num(1)),
                    change("Energy", num(8)), b("control_delete_this_clone"))),
            )),
            iff(eq(gv("Mode"), text("gameover")), b("control_delete_this_clone")),
            iff(eq(gv("Mode"), text("victory")), b("control_delete_this_clone")),
            wait(num(0.02)),
        )),
    )
    hit = seq(
        hat_message("hit", 820, 30),
        iff(and_(eq(gv("Mode"), text("playing")), lt(distance_sq_to_hit(), num(900))),
            change_local("Enemy HP", "e_hp", num(-1))),
    )
    nova = seq(
        hat_message("nova", 820, 230),
        iff(and_(eq(gv("Mode"), text("playing")), lt(distance_sq_to_player(), num(14400))),
            change_local("Enemy HP", "e_hp", num(-5))),
    )
    for root in (spawn, clone, hit, nova):
        serialize_script(root, target["blocks"])
    return target


def make_bullet(costume):
    target = {"isStage": False, "name": "Nova Bolt", "variables": {},
              "lists": {}, "broadcasts": {}, "blocks": {}, "comments": {},
              "currentCostume": 0,
              "costumes": [{**costume, "name": "Nova Bolt", "rotationCenterX": 16, "rotationCenterY": 16}],
              "sounds": [], "volume": 100, "layerOrder": 1, "visible": False,
              "x": 0, "y": 0, "size": 45, "direction": 90,
              "draggable": False, "rotationStyle": "all around"}
    root = seq(
        hat_flag(30, 760), b("looks_hide"),
        b("event_whenbroadcastreceived", fields={"BROADCAST_OPTION": ["shoot", MESSAGES["shoot"]]}, top=True, x=250, y=760),
        b("looks_hide"),
    )
    # Broadcast handler is a separate top-level script: a hidden original fires clones.
    fire = seq(
        hat_message("shoot", 250, 760),
        b("motion_gotoxy", {"X": gv("Player X"), "Y": gv("Player Y")}),
        b("motion_pointtowards", {"TOWARDS": b("motion_pointtowards_menu", fields={"TOWARDS": ["_mouse_", ""]}, shadow=True)}),
        b("control_create_clone_of", {"CLONE_OPTION": b("control_create_clone_of_menu", fields={"CLONE_OPTION": ["_myself_", ""]}, shadow=True)}),
    )
    clone = seq(
        hat_clone(500, 30), b("looks_show"), b("looks_setsize %", {"SIZE": num(42)}),
        repeat_until(or_(b("sensing_touchingobject", {"TOUCHINGOBJECTMENU": b("sensing_touchingobjectmenu", fields={"TOUCHINGOBJECTMENU": ["edge", ""]}, shadow=True)}), touching("Rift Wraith")), seq(
            b("motion_movesteps", {"STEPS": num(12)}),
            iff(touching("Rift Wraith"), seq(
                setv("Shot X", x_pos()), setv("Shot Y", y_pos()),
                broadcast("hit", wait_for=True), b("control_delete_this_clone"))),
        )),
        b("control_delete_this_clone"),
    )
    for script in (root, fire, clone):
        serialize_script(script, target["blocks"])
    return target


def build_project():
    backdrop, backdrop_blob = asset(BACKDROP_SVG)
    player_costume, player_blob = asset(PLAYER_SVG)
    enemy_costume, enemy_blob = asset(ENEMY_SVG)
    bullet_costume, bullet_blob = asset(BULLET_SVG)
    stage = make_stage(backdrop)
    targets = [stage, make_player(player_costume), make_enemy(enemy_costume), make_bullet(bullet_costume)]
    monitors = []
    for name, x, y in (("Score", 8, 8), ("Lives", 8, 30), ("Wave", 8, 52), ("Energy", 8, 74)):
        monitors.append({"id": GLOBALS[name], "mode": "default", "opcode": "data_variable",
                         "params": {"VARIABLE": GLOBALS[name]}, "spriteName": None,
                         "value": 0, "width": 110, "height": 18, "x": x, "y": y,
                         "visible": True, "sliderMin": 0, "sliderMax": 100, "isDiscrete": True})
    project = {"targets": targets, "monitors": monitors, "extensions": [],
               "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "Chrono Rift SB3 Builder"}}
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(project, separators=(",", ":")))
        for item, content in ((backdrop, backdrop_blob), (player_costume, player_blob),
                              (enemy_costume, enemy_blob), (bullet_costume, bullet_blob)):
            archive.writestr(item["md5ext"], content)
    validate_project(OUTPUT)
    print(f"Created and validated {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


def validate_project(path):
    """Catch malformed ZIP/JSON, missing assets and broken block references before upload."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        project = json.loads(archive.read("project.json"))
        assert len(project["targets"]) == 4, "Expected Stage and three game sprites"
        for target in project["targets"]:
            for costume in target["costumes"]:
                assert costume["md5ext"] in names, f"Missing costume asset: {costume['md5ext']}"
            blocks = target["blocks"]
            for block_id, block in blocks.items():
                if block["next"] is not None:
                    assert block["next"] in blocks, f"Broken next block from {block_id}"
                for input_value in block["inputs"].values():
                    if isinstance(input_value, list) and len(input_value) > 1 and isinstance(input_value[1], str):
                        assert input_value[1] in blocks, f"Broken input block from {block_id}: {input_value[1]}"
                    elif isinstance(input_value, list) and len(input_value) > 1 and input_value[1] is not None:
                        if isinstance(input_value[1], list):
                            continue  # Primitive shadow values such as numbers and text.
                        assert input_value[1] in blocks, f"Broken substack from {block_id}"
        assert "Chrono Runner" in [target["name"] for target in project["targets"]]
        assert "Rift Wraith" in [target["name"] for target in project["targets"]]


if __name__ == "__main__":
    build_project()
