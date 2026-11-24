#!/usr/bin/env python3
"""Compare the pinned original catalog with the reviewed fixture and port menus."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "original-neural-workshop-enhanced"
FIXTURE = ROOT / "nw-core/test/fixtures/task_catalog.json"
CORE_HUB = ROOT / "nw-core/src/taskhub_tasks.elisa"
WEB_SHELL = ROOT / "nw-core/shells/web/index.html"
PYTHON_SHELL = ROOT / "nw-core/shells/python/app.py"
SDL_SHELL = ROOT / "nw-core/shells/sdl3/main.c"
IMPLEMENTATION_PLAN = ROOT / "IMPLEMENTATION_PLAN.md"
sys.path.insert(0, str(ROOT / "nw-core/scripts"))
from generate_task_registry import hub_categories, hub_groups

PYMODULE_EXPORTS = ROOT / "nw-core/src/pymodule_exports.elisa"
WASM_EXPORTS = ROOT / "nw-core/src/wasm/wasm_exports.elisa"
TASKOPTIONS_SOURCE = ORIGINAL / "neural_workshop/ui/taskoptions.py"
GAMESELECT_SOURCE = ORIGINAL / "neural_workshop/ui/gameselect.py"
CONFIGDEFAULTS_SOURCE = ORIGINAL / "neural_workshop/configdefaults.py"


def source_option_value(node: ast.expr, symbols: dict[str, object]):
    """Evaluate the small, data-only expression language used by TaskOptions."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in symbols:
        return symbols[node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [source_option_value(item, symbols) for item in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = source_option_value(node.operand, symbols)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
        left = source_option_value(node.left, symbols)
        right = source_option_value(node.right, symbols)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        return left * right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name == "_" and len(node.args) == 1:
            return source_option_value(node.args[0], symbols)
        args = [source_option_value(arg, symbols) for arg in node.args]
        if name == "range":
            return list(range(*args))
        if name == "tuple" and len(args) == 1:
            return list(args[0])
        if name == "len" and len(args) == 1:
            return len(args[0])
    raise ValueError(f"unsupported source option expression: {ast.dump(node)}")


def source_task_options(revision: str) -> dict[str, dict[str, dict[str, object]]]:
    """Read the pinned UI's declarative option lists without importing pyglet."""
    source = ast.parse(reference_text(TASKOPTIONS_SOURCE, revision))
    specs = {
        statement.targets[0].id: statement.value
        for statement in source.body
        if isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == "TaskSpec"
    }

    symbols: dict[str, object] = {}
    for module_name, constant_name, imported_name in (
        ("marblemaze.py", "GRADES", "_MARBLE_GRADES"),
        ("go.py", "DIFFICULTIES", "_GO_LADDER"),
    ):
        module = ast.parse(reference_text(ORIGINAL / "neural_workshop" / module_name, revision))
        values = assignment(module, constant_name)
        if not isinstance(values, (ast.Tuple, ast.List)):
            raise ValueError(f"{module_name}.{constant_name} must remain a literal sequence")
        symbols[imported_name] = list(range(1, len(values.elts) + 1))

    task_specs = assignment(source, "TASK_SPECS")
    if not isinstance(task_specs, ast.Dict):
        raise ValueError("original TASK_SPECS must remain a literal mapping")

    result: dict[str, dict[str, dict[str, object]]] = {}
    for task_node, spec_node in zip(task_specs.keys, task_specs.values):
        task_id = source_option_value(task_node, symbols)
        if not isinstance(spec_node, ast.Name) or spec_node.id not in specs:
            raise ValueError(f"TASK_SPECS[{task_id!r}] does not reference a TaskSpec")
        spec = specs[spec_node.id]
        option_nodes = next((item.value for item in spec.keywords if item.arg == "options"), None)
        if not isinstance(option_nodes, (ast.Tuple, ast.List)):
            raise ValueError(f"TaskSpec {spec_node.id} must declare a literal option list")

        task_options: dict[str, dict[str, object]] = {}
        for option_node in option_nodes.elts:
            if not isinstance(option_node, ast.Call) or not isinstance(option_node.func, ast.Name) or option_node.func.id != "Option":
                raise ValueError(f"TaskSpec {spec_node.id} contains a non-Option entry")
            if len(option_node.args) < 3:
                raise ValueError(f"TaskSpec {spec_node.id} has an Option without a default")
            key = source_option_value(option_node.args[0], symbols)
            default = source_option_value(option_node.args[2], symbols)
            values_node = next((keyword.value for keyword in option_node.keywords if keyword.arg == "values"), None)
            suffix_node = next((keyword.value for keyword in option_node.keywords if keyword.arg == "suffix"), None)
            if key in task_options:
                raise ValueError(f"TaskSpec {spec_node.id} repeats option {key}")

            if key == "NUMBEROLOGY_LEVEL":
                # current_value() and _build_row() intentionally make this one
                # option an unbounded positive integer despite the placeholder
                # values=(1,) passed to Option.
                schema: dict[str, object] = {
                    "type": "integer", "default": default, "minimum": 1, "maximum": None,
                }
            elif values_node is None:
                if not isinstance(default, bool):
                    raise ValueError(f"Option {key} needs explicit values or a boolean default")
                schema = {"type": "boolean", "default": default}
            else:
                values = source_option_value(values_node, symbols)
                if not isinstance(values, list) or not values or default not in values:
                    raise ValueError(f"Option {key} has invalid values or a missing default")
                sample = values[0]
                if isinstance(sample, bool):
                    value_type = "boolean"
                elif isinstance(sample, int):
                    value_type = "integer"
                elif isinstance(sample, float):
                    value_type = "number"
                elif isinstance(sample, str):
                    value_type = "string"
                else:
                    raise ValueError(f"Option {key} uses an unsupported value type")
                schema = {
                    "type": "enum", "value_type": value_type,
                    "default": default, "values": values,
                }
            if suffix_node is not None:
                schema["suffix"] = source_option_value(suffix_node, symbols)
            task_options[key] = schema
        result[task_id] = task_options
    return result


def source_nback_options(revision: str) -> dict[str, dict[str, object]]:
    """Describe the port-scoped 3D N-Back controls from GameSelect."""
    game_select = ast.parse(reference_text(GAMESELECT_SOURCE, revision))
    trial_values = literal(assignment(game_select, "_TRIAL_MS_VALUES"))
    config_text = reference_text(CONFIGDEFAULTS_SOURCE, revision)
    cube_default_match = re.search(r"^GRID_3D_CUBES = (\d+)\s*$", config_text, re.M)
    if cube_default_match is None:
        raise ValueError("config defaults must retain GRID_3D_CUBES")
    cube_default = int(cube_default_match.group(1))
    cube_values = None
    for node in ast.walk(game_select):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Name) or node.value.func.id != "Cycler":
            continue
        if not any(
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "values"
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "grid_3d_cubes"
            for target in node.targets
        ):
            continue
        values = next((keyword.value for keyword in node.value.keywords if keyword.arg == "values"), None)
        if values is not None:
            cube_values = literal(values)
            break
    if not isinstance(trial_values, list) or not isinstance(cube_values, list):
        raise ValueError("GameSelect must retain literal trial and 3D cube option values")
    return {
        "grid_3d_cubes": {
            "type": "enum", "value_type": "integer",
            "default": cube_default, "values": cube_values,
        },
        "trial_ms": {
            "type": "enum", "value_type": "integer",
            "default": None, "default_policy": "current_mode",
            "values": trial_values,
        },
    }


def assignment(tree: ast.Module, name: str) -> ast.expr:
    for statement in tree.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            if statement.target.id == name:
                return statement.value
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in statement.targets
        ):
            return statement.value
    raise ValueError(f"missing assignment {name}")


def literal(node: ast.expr):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Call) and node.args:
        return literal(node.args[0])
    if isinstance(node, ast.Tuple):
        return tuple(literal(item) for item in node.elts)
    if isinstance(node, ast.List):
        return [literal(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {literal(key): literal(value) for key, value in zip(node.keys, node.values)}
    raise ValueError(f"catalog value is not literal data: {ast.dump(node)}")


def reference_text(path: Path, revision: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ORIGINAL), "show", f"{revision}:{path.relative_to(ORIGINAL)}"],
        encoding="utf-8",
    )


def original_tables(revision: str):
    catalog_tree = ast.parse(reference_text(ORIGINAL / "nwenv/catalog.py", revision))
    ui_tree = ast.parse(reference_text(ORIGINAL / "neural_workshop/ui/taskhub.py", revision))
    catalog = [
        {"id": literal(row.args[0]), "label": literal(row.args[1])}
        for row in assignment(catalog_tree, "CATALOG").elts
    ]
    categories = literal(assignment(ui_tree, "CATEGORIES"))
    tasks = literal(assignment(ui_tree, "TASKS"))
    grouped = []
    for category_id, category_label in categories:
        grouped.append(
            {
                "id": category_id,
                "label": category_label,
                "tasks": [
                    {"id": task_id, "label": label}
                    for task_id, label in tasks[category_id]
                ],
            }
        )
    return catalog, grouped


def parse_core_menu():
    source = CORE_HUB.read_text()
    categories: dict[int, str] = {}
    tasks: dict[int, dict[int, str]] = {}
    function = ""
    current_category = None
    current_task = None
    for line in source.splitlines():
        if line.startswith("    def "):
            function = line.strip().split("(", 1)[0][4:]
            current_category = None
            current_task = None
            continue
        if function == "category_name":
            match = re.match(r"\s{8}(?:if|elif) which == (\d+):", line)
            if match:
                current_task = int(match.group(1))
            label = re.match(r'\s{12}return "([^"]*)"', line)
            if label and current_task is not None and label.group(1):
                categories[current_task] = label.group(1)
        elif function == "task_name":
            match = re.match(r"\s{8}(?:if|elif) category == (\d+):", line)
            if match:
                current_category = int(match.group(1))
                tasks[current_category] = {}
                current_task = None
                continue
            match = re.match(r"\s{12}(?:if|elif) which == (\d+)(?: and has_(?:signals|fold_it|beliefs))?:", line)
            if match:
                current_task = int(match.group(1))
                continue
            label = re.match(r'\s{16}return "([^"]*)"', line)
            if label and label.group(1) and current_category is not None and current_task is not None:
                tasks[current_category][current_task] = label.group(1)
    # Some controllers are available only in the newer hosts. Include their
    # conditional insertions when auditing the full task hub.
    for name, category, position in reversed(re.findall(
        r'^        return "([^"]+)" if (?:has_video_sequence|has_hidden_rule|has_hidden_wiring|has_triage|has_delay|has_stop_switch|has_hold_it|has_notebook|has_where_was_it|has_which_is_nearer|has_same_or_mirror|has_point_of_view|has_inside_or_out|has_touching|has_crossings|has_time_it|has_balance|has_juggler|has_lander|has_beat|has_glider|has_catch|has_echo_cave|has_drone_hoops|has_field_manual|has_safecracker|has_stagehand|has_loading_dock|has_gunslinger|has_potters_wheel|has_railyard|has_airtraffic|has_escort|has_sokobanlive|has_kitchen|has_crane|has_ferry|has_docking|has_rover|has_unicycle|has_morning_round|has_heavier|has_full_stop|has_missing_word|has_proofreader|has_figures_of_speech|has_crazy_cog|has_camera|has_what_next|has_falls) and category == (\d+) and (?:source|index|position|self_control_index|hold_index|perception_index) == (\d+)(?: and has_camera)?(?: and has_what_next)?(?: \+ \(1 if has_(?:railyard|airtraffic|escort|sokobanlive|kitchen|crane|ferry|docking|rover) else 0\))*$',
        source, re.M,
    )):
        cards = tasks.get(int(category), {})
        ordered = [cards[index] for index in range(len(cards))]
        ordered.insert(int(position), name)
        tasks[int(category)] = dict(enumerate(ordered))
    cipher_card = re.search(r'^        return "([^"]+)" if has_cipher_abyss and category == 4', source, re.M)
    if cipher_card:
        cards = list(tasks[4].values())
        cards.insert(cards.index("Crazy Cog") + 1, cipher_card.group(1))
        tasks[4] = dict(enumerate(cards))
    conductor_card = re.search(r'^        return "([^"]+)" if has_conductor and category == 2', source, re.M)
    if conductor_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Potter's Wheel") + 1, conductor_card.group(1))
        tasks[2] = dict(enumerate(cards))
    tightrope_card = re.search(r'^        return "([^"]+)" if has_tightrope and category == 2', source, re.M)
    if tightrope_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Conductor") + 1, tightrope_card.group(1))
        tasks[2] = dict(enumerate(cards))
    sign_painter_card = re.search(r'^        return "([^"]+)" if has_sign_painter and category == 2', source, re.M)
    if sign_painter_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Tightrope") + 1, sign_painter_card.group(1))
        tasks[2] = dict(enumerate(cards))
    bartender_card = re.search(r'^        return "([^"]+)" if has_bartender and category == 2', source, re.M)
    if bartender_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Sign Painter") + 1, bartender_card.group(1))
        tasks[2] = dict(enumerate(cards))
    lock_pick_card = re.search(r'^        return "([^"]+)" if has_lock_pick and category == 2', source, re.M)
    if lock_pick_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Bartender") + 1, lock_pick_card.group(1))
        tasks[2] = dict(enumerate(cards))
    air_hockey_card = re.search(r'^        return "([^"]+)" if has_air_hockey and category == 2', source, re.M)
    if air_hockey_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Lock Pick") + 1, air_hockey_card.group(1))
        tasks[2] = dict(enumerate(cards))
    semaphore_card = re.search(r'^        return "([^"]+)" if has_semaphore and category == 2', source, re.M)
    if semaphore_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Air Hockey") + 1, semaphore_card.group(1))
        tasks[2] = dict(enumerate(cards))
    shadow_puppets_card = re.search(r'^        return "([^"]+)" if has_shadow_puppets and category == 2', source, re.M)
    if shadow_puppets_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Semaphore") + 1, shadow_puppets_card.group(1))
        tasks[2] = dict(enumerate(cards))
    night_watch_card = re.search(r'^        return "([^"]+)" if has_night_watch and category == 2', source, re.M)
    if night_watch_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Shadow Puppets") + 1, night_watch_card.group(1))
        tasks[2] = dict(enumerate(cards))
    kerbside_card = re.search(r'^        return "([^"]+)" if has_kerbside and category == 2', source, re.M)
    if kerbside_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Night Watch") + 1, kerbside_card.group(1))
        tasks[2] = dict(enumerate(cards))
    steadicam_card = re.search(r'^        return "([^"]+)" if has_steadicam and category == 2', source, re.M)
    if steadicam_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Kerbside") + 1, steadicam_card.group(1))
        tasks[2] = dict(enumerate(cards))
    free_kick_card = re.search(r'^        return "([^"]+)" if has_free_kick and category == 2', source, re.M)
    if free_kick_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Steadicam") + 1, free_kick_card.group(1))
        tasks[2] = dict(enumerate(cards))
    glove_card = re.search(r'^        return "([^"]+)" if has_glove and category == 2', source, re.M)
    if glove_card:
        cards = list(tasks[2].values())
        cards.insert(cards.index("Free Kick") + 1, glove_card.group(1))
        tasks[2] = dict(enumerate(cards))
    motion_card = re.search(
        r'if has_sfm and category == 3:\n            return "([^"]+)" if falls_index == sfm_card',
        source,
    )
    if motion_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Which Is Nearer?") + 1, motion_card.group(1))
        tasks[3] = dict(enumerate(cards))
    drshape_card = re.search(r'return "([^"]+)" if perception_index == drshape_card', source)
    if drshape_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Point of View") + 1, drshape_card.group(1))
        tasks[3] = dict(enumerate(cards))
    tuner_card = re.search(r'return "([^"]+)" if (?:has_tuner and )?perception_index == tuner_card', source)
    if tuner_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Time It") + 1, tuner_card.group(1))
        tasks[3] = dict(enumerate(cards))
    shadow_play_card = re.search(
        r'return "([^"]+)" if has_shadow_play and perception_index == shadow_play_card', source,
    )
    if shadow_play_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Tuner") + 1, shadow_play_card.group(1))
        tasks[3] = dict(enumerate(cards))
    captcha_card = re.search(
        r'return "([^"]+)" if has_captcha and perception_index == captcha_card', source,
    )
    if captcha_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Shadow Play") + 1, captcha_card.group(1))
        tasks[3] = dict(enumerate(cards))
    by_ear_card = re.search(
        r'return "([^"]+)" if has_by_ear and perception_index == by_ear_card', source,
    )
    if by_ear_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Captcha") + 1, by_ear_card.group(1))
        tasks[3] = dict(enumerate(cards))
    piano_tuner_card = re.search(
        r'return "([^"]+)" if has_piano_tuner and perception_index == piano_tuner_card', source,
    )
    if piano_tuner_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("By Ear") + 1, piano_tuner_card.group(1))
        tasks[3] = dict(enumerate(cards))
    cricket_hunt_card = re.search(
        r'return "([^"]+)" if has_cricket_hunt and perception_index == cricket_hunt_card', source,
    )
    if cricket_hunt_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Piano Tuner") + 1, cricket_hunt_card.group(1))
        tasks[3] = dict(enumerate(cards))
    claw_machine_card = re.search(
        r'return "([^"]+)" if has_claw_machine and perception_index == claw_machine_card', source,
    )
    if claw_machine_card:
        cards = list(tasks[3].values())
        cards.insert(cards.index("Cricket Hunt") + 1, claw_machine_card.group(1))
        tasks[3] = dict(enumerate(cards))
    decisions = re.search(r'^        if category == 7:\n((?: {12}[^\n]+\n)+)', source, re.M)
    if decisions:
        # This comparison is against the web registry. A shared scene may
        # already support a card on SDL before its WASM selector ships.
        web_exports = WASM_EXPORTS.read_text()
        cards = [
            label for label, feature in re.findall(r'return "([^"]+)" if has_(\w+)', decisions.group(1))
            if f"export fn nw_api_v1_task_{feature}(" in web_exports
        ]
        tasks[7] = dict(enumerate(cards))
    # The tabs after Decisions name each card by its position.
    for name, category, position in re.findall(
        r'^        return "([^"]+)" if has_\w+ and category == (8|9|10|11) and position == (\d+)$', source, re.M,
    ):
        tasks.setdefault(int(category), {})[int(position)] = name
    return categories, tasks


def parse_web_menu(fixture):
    source = WEB_SHELL.read_text()
    if 'import { TASK_CATEGORIES, TASK_IDS_BY_CATEGORY } from "./task-registry.js";' not in source:
        raise ValueError("browser menu must import its generated task registry")
    subprocess.run(
        [sys.executable, str(ROOT / "nw-core/scripts/generate_task_registry.py"), "--check"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    overrides = fixture["port_overrides"]
    return [
        {
            "label": category["label"],
            "tasks": [overrides.get(task["id"], {}).get("label", task["label"]) for task in tasks],
        }
        for category, tasks in zip(hub_categories(fixture), hub_groups(fixture))
    ]


def parse_plan_anchors():
    source = IMPLEMENTATION_PLAN.read_text()
    headings = list(re.finditer(r"^### GAME-\d{3} — [^\n]+\n", source, re.M))
    result = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        section = source[heading.end():end]
        stable_id = re.search(r"^\*\*Stable task ID:\*\* `([^`]+)`\.", section, re.M)
        kernel_line = re.search(
            r"^\*\*Existing kernel anchors?:\*\*(.*)$", section, re.M
        )
        scene_line = re.search(
            r"^\*\*Existing scene anchors?:\*\*(.*)$", section, re.M
        )
        if stable_id is None or kernel_line is None or scene_line is None:
            raise ValueError(f"incomplete source anchors in {heading.group(0).strip()}")
        task_id = stable_id.group(1)
        if task_id in result:
            raise ValueError(f"duplicate plan task ID: {task_id}")
        kernels = re.findall(r"`(nw-core/[^`]+)`", kernel_line.group(1))
        scenes = re.findall(r"`(nw-core/[^`]+)`", scene_line.group(1))
        if not kernels or not scenes:
            raise ValueError(f"missing kernel or scene file mapping for {task_id}")
        result[task_id] = {"kernels": kernels, "scenes": scenes}
    return result


def audit_runtime_coverage(fixture, task_ids):
    coverage = fixture.get("runtime_coverage")
    if not isinstance(coverage, dict) or set(coverage) != {"default", "overrides"}:
        raise ValueError("fixture runtime_coverage must contain default and overrides")
    default = coverage["default"]
    overrides = coverage["overrides"]
    if not isinstance(overrides, dict):
        raise ValueError("runtime_coverage overrides must be an object")
    unknown = set(overrides) - set(task_ids)
    if unknown:
        raise ValueError(f"runtime coverage contains unknown task IDs: {sorted(unknown)}")

    export_source = WASM_EXPORTS.read_text()
    exports = set(re.findall(r"^export fn ([A-Za-z_][A-Za-z0-9_]*)\(", export_source, re.M))
    selector_exports = {name for name in exports if name.startswith("nw_api_v1_task_")}
    mapped_selectors: set[str] = set()
    for task_id in task_ids:
        row = overrides.get(task_id, default)
        row_exports = row.get("wasm_exports") if isinstance(row, dict) else None
        if not isinstance(row_exports, list):
            continue
        if len(row_exports) != len(set(row_exports)):
            raise ValueError(f"duplicate WASM export mapping for {task_id}")
        mapped_selectors.update(
            name for name in row_exports if isinstance(name, str) and name.startswith("nw_api_v1_task_")
        )
        if row.get("hosts", {}).get("web") in {"stateful_controller", "physics_prototype"}:
            has_task_selector = any(
                name.startswith("nw_api_v1_task_") or name == "nw_api_v1_tetris_task_id"
                for name in row_exports
            )
            if not has_task_selector:
                raise ValueError(f"web runtime capability for {task_id} lacks its task selector export")
    if mapped_selectors != selector_exports:
        raise ValueError(
            "reviewed task-to-WASM selector map is not exact: "
            f"unmapped={sorted(selector_exports - mapped_selectors)}, "
            f"unknown={sorted(mapped_selectors - selector_exports)}"
        )
    mapped_v1_exports = set(default.get("wasm_exports", []))
    for row in overrides.values():
        mapped_v1_exports.update(
            name for name in row.get("wasm_exports", [])
            if isinstance(name, str) and name.startswith("nw_api_v1_")
        )
    mapped_v1_exports = {name for name in mapped_v1_exports if name.startswith("nw_api_v1_")}
    global_v1_exports = {"nw_api_v1_abi_version", "nw_api_v1_drain_effects"}
    task_v1_exports = {name for name in exports if name.startswith("nw_api_v1_")} - global_v1_exports
    if mapped_v1_exports != task_v1_exports:
        raise ValueError(
            "reviewed task-to-WASM v1 export map is not exact: "
            f"unmapped={sorted(task_v1_exports - mapped_v1_exports)}, "
            f"unknown={sorted(mapped_v1_exports - task_v1_exports)}"
        )
    required_nback3d_exports = {
        "nw_api_v1_task_nback_3d",
        "nw_api_v1_nback3d_info",
        "nw_api_v1_create",
        "nw_api_v1_render",
    }
    if missing := required_nback3d_exports - exports:
        raise ValueError(f"3D N-Back runtime exports are missing: {sorted(missing)}")
    forbidden_nback_paths = (
        r'^include ".*/scene_nback\.elisa"$',
        r'^include ".*/scene_batch\.elisa"$',
        r'^include ".*/scene_menu\.elisa"$',
        r'^include ".*/scene_menu_screen\.elisa"$',
        r'^export fn nw_(?:crab_back|frame_write|session_frame_write|batch_write|menu_write|menu_state_write)\(',
    )
    for pattern in forbidden_nback_paths:
        if re.search(pattern, export_source, re.M):
            raise ValueError(f"WASM source includes a non-3D N-Back route: {pattern}")

    allowed_host_status = {
        "web": {"stateless_frame_only", "stateful_controller", "physics_prototype"},
        "python": {"not_integrated", "stateful_controller"},
        "sdl3": {"not_integrated", "stateful_controller"},
    }
    for task_id in task_ids:
        row = overrides.get(task_id, default)
        if not isinstance(row, dict):
            raise ValueError(f"runtime coverage is not an object for {task_id}")
        controller = row.get("controller")
        modules = row.get("controller_modules")
        if controller is not None:
            modules = [controller, *modules] if isinstance(modules, list) else [controller]
        elif modules != []:
            raise ValueError(f"controller_modules require a controller for {task_id}")
        for module in modules or []:
            if not isinstance(module, str) or not (ROOT / module).is_file():
                raise ValueError(f"missing controller module for {task_id}: {module}")
        row_exports = row.get("wasm_exports")
        if not isinstance(row_exports, list) or not row_exports:
            raise ValueError(f"missing wasm export map for {task_id}")
        missing_exports = set(row_exports) - exports
        if missing_exports:
            raise ValueError(f"unknown WASM exports for {task_id}: {sorted(missing_exports)}")
        hosts = row.get("hosts")
        if not isinstance(hosts, dict) or set(hosts) != set(allowed_host_status):
            raise ValueError(f"host capability map must name web, python, and sdl3 for {task_id}")
        for host, status in hosts.items():
            if status not in allowed_host_status[host]:
                raise ValueError(f"invalid {host} support state for {task_id}: {status}")
        if any(status == "stateful_controller" for status in hosts.values()) and not controller:
            raise ValueError(f"stateful host capability for {task_id} requires an explicit controller module")


def audit_task_capabilities(fixture, task_ids):
    capabilities = fixture.get("task_capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError("task_capabilities must be an object")
    unknown = set(capabilities) - set(task_ids)
    if unknown:
        raise ValueError(f"capabilities contain unknown task IDs: {sorted(unknown)}")
    missing = set(task_ids) - set(capabilities)
    if missing:
        raise ValueError(f"capabilities are missing task IDs: {sorted(missing)}")

    expected_options = source_task_options(fixture["reference_revision"])
    expected_options["nback"] = source_nback_options(fixture["reference_revision"])
    if set(expected_options) != set(task_ids):
        raise ValueError(
            "source option contracts do not match the reviewed catalog: "
            f"missing={sorted(set(task_ids) - set(expected_options))}, "
            f"unknown={sorted(set(expected_options) - set(task_ids))}"
        )

    allowed_inputs = {"keyboard", "pointer", "text", "audio", "gamepad", "touch"}
    for task_id, record in capabilities.items():
        if not isinstance(record, dict) or set(record) != {
            "required_services", "supported_input", "options_schema"
        }:
            raise ValueError(f"capability record for {task_id} must define services, input, and options")
        services = record["required_services"]
        inputs = record["supported_input"]
        options = record["options_schema"]
        if not isinstance(services, list) or any(not isinstance(value, str) or not value for value in services):
            raise ValueError(f"required_services must be non-empty strings for {task_id}")
        if not isinstance(inputs, list) or not inputs or not set(inputs) <= allowed_inputs:
            raise ValueError(f"supported_input is missing or invalid for {task_id}")
        if not isinstance(options, dict):
            raise ValueError(f"options_schema must be an object for {task_id}")
        if options != expected_options[task_id]:
            raise ValueError(
                f"options_schema for {task_id} differs from the pinned source; "
                "review the source changes and update the catalog deliberately"
            )
        for name, option in options.items():
            if not isinstance(name, str) or not isinstance(option, dict):
                raise ValueError(f"invalid option schema for {task_id}.{name}")
            option_type = option.get("type")
            if option_type == "boolean":
                if set(option) != {"type", "default"} or not isinstance(option.get("default"), bool):
                    raise ValueError(f"invalid boolean option for {task_id}.{name}")
            elif option_type == "integer":
                if set(option) != {"type", "default", "minimum", "maximum"}:
                    raise ValueError(f"invalid integer option for {task_id}.{name}")
                default, minimum, maximum = option["default"], option["minimum"], option["maximum"]
                if any(not isinstance(value, int) or isinstance(value, bool)
                       for value in (default, minimum)):
                    raise ValueError(f"integer option bounds/default missing for {task_id}.{name}")
                if maximum is not None and (not isinstance(maximum, int) or isinstance(maximum, bool)):
                    raise ValueError(f"integer option maximum is invalid for {task_id}.{name}")
                if minimum > default or (maximum is not None and default > maximum):
                    raise ValueError(f"option default outside bounds for {task_id}.{name}")
            elif option_type == "enum":
                allowed_fields = {"type", "value_type", "default", "values", "suffix", "default_policy"}
                if set(option) - allowed_fields or not {"type", "value_type", "default", "values"} <= set(option):
                    raise ValueError(f"invalid enum option fields for {task_id}.{name}")
                values = option["values"]
                value_type = option["value_type"]
                if value_type not in {"boolean", "integer", "number", "string"} or not isinstance(values, list) or not values:
                    raise ValueError(f"invalid enum values for {task_id}.{name}")
                if option.get("default_policy") == "current_mode":
                    if option["default"] is not None:
                        raise ValueError(f"dynamic default must be null for {task_id}.{name}")
                elif option.get("default_policy") is not None or option["default"] not in values:
                    raise ValueError(f"enum default is invalid for {task_id}.{name}")
                for value in values:
                    valid = (
                        isinstance(value, bool) if value_type == "boolean" else
                        isinstance(value, int) and not isinstance(value, bool) if value_type == "integer" else
                        isinstance(value, (int, float)) and not isinstance(value, bool) if value_type == "number" else
                        isinstance(value, str)
                    )
                    if not valid:
                        raise ValueError(f"enum value has the wrong type for {task_id}.{name}")
                if "suffix" in option and not isinstance(option["suffix"], str):
                    raise ValueError(f"enum suffix must be text for {task_id}.{name}")
            else:
                raise ValueError(f"unsupported option type for {task_id}.{name}")


def main() -> int:
    fixture = json.loads(FIXTURE.read_text())
    if fixture.get("schema_version") != 5:
        raise ValueError("task fixture schema version must be 5")
    original_catalog, original_groups = original_tables(fixture["reference_revision"])
    rows = fixture["tasks"]
    ids = [row["id"] for row in rows]
    if len(rows) != 45 or len(set(ids)) != len(ids):
        raise ValueError(f"fixture must contain 45 unique stable IDs, found {len(rows)} rows")
    expected = [
        {"id": task["id"], "label": task["label"], "category": group["id"], "position": position}
        for group in original_groups
        for position, task in enumerate(group["tasks"])
    ]
    if rows != expected:
        raise ValueError("reviewed fixture does not exactly match original task IDs, labels, categories, and order")
    if fixture.get("categories") != [
        {"id": group["id"], "label": group["label"]} for group in original_groups
    ]:
        raise ValueError("reviewed category labels/order differ from the pinned original task hub")
    if fixture.get("port_overrides") != {"nback": {"id": "nback_3d", "label": "3D N-Back"}}:
        raise ValueError("port overrides must explicitly preserve the 3D-only N-Back boundary")
    if [(row["id"], row["label"]) for row in original_catalog] != [
        (row["id"], row["label"]) for row in rows
    ]:
        raise ValueError("original nwenv catalog differs from the reviewed task fixture")

    plan_anchors = parse_plan_anchors()
    if set(plan_anchors) != set(ids):
        raise ValueError("per-game plan sections do not map every reviewed task ID exactly once")
    for task_id, anchors in plan_anchors.items():
        for path in [*anchors["kernels"], *anchors["scenes"]]:
            if not (ROOT / path).is_file():
                raise ValueError(f"missing plan anchor for {task_id}: {path}")
    audit_runtime_coverage(fixture, [*ids, *(row["id"] for row in fixture["hub_additions"])])
    audit_task_capabilities(fixture, ids)

    core_categories, core_tasks = parse_core_menu()
    web_groups = parse_web_menu(fixture)
    expected_categories = [group["label"] for group in hub_categories(fixture)]
    # The frozen reference keeps the stable task id/label pair `nback` for
    # catalog comparison. The port deliberately narrows that one visible
    # capability to the 3D face-pattern/cube task; all other N-Back variants
    # stay in the original application and must not appear in a port shell.
    overrides = fixture["port_overrides"]
    expected_groups = [[
        overrides.get(task["id"], {}).get("label", task["label"])
        for task in group
    ] for group in hub_groups(fixture)]
    actual_core_categories = [core_categories.get(index) for index in range(len(expected_categories))]
    actual_core_groups = [
        [core_tasks.get(index, {}).get(position) for position in range(len(core_tasks.get(index, {})))]
        for index, group in enumerate(expected_groups)
    ]
    actual_web_categories = [group["label"] for group in web_groups]
    actual_web_groups = [group["tasks"] for group in web_groups]
    if actual_core_categories != expected_categories or actual_core_groups != expected_groups:
        raise ValueError("Elisa task hub labels/order differ from the pinned original task catalog")
    if actual_web_categories != expected_categories or actual_web_groups != expected_groups:
        raise ValueError("browser task hub labels/order differ from the pinned original task catalog")

    shell_sources = {
        "browser": WEB_SHELL.read_text(),
        "python": PYTHON_SHELL.read_text(),
        "sdl3": SDL_SHELL.read_text(),
        "python ABI": PYMODULE_EXPORTS.read_text(),
    }
    forbidden_port_paths = {
        "browser": {
            "legacy Mode button": re.compile(r'id=["\']screen-menu["\']'),
            "legacy menu screen": re.compile(r'screen\s*[!=]==?\s*["\']menu["\']'),
            "legacy menu transition": re.compile(r'setScreen\(["\']menu["\']\)'),
            "legacy menu export": re.compile(r'\bnw_menu_state_write\b'),
            "generic session preview export": re.compile(r'\bsessionFrame\b'),
            "non-3D preview title": re.compile(r'Dual N-Back'),
        },
        "python": {
            "generic session preview": re.compile(
                r'\b(?:nback_frame|nback_session_frame|batch_frame|menu_frame|menu_state_frame)\b'
            ),
            "generic preview class": re.compile(r'\b(?:MenuSession|BatchSession|Session)\b'),
            "generic mode argument": re.compile(r'--(?:nback|mode)\b'),
            "non-3D preview title": re.compile(r'Dual N-Back'),
        },
        "sdl3": {
            "generic session ABI": re.compile(
                r'\bnw_(?:frame_write|session_frame_write|batch_write)\b'
            ),
            "non-3D preview title": re.compile(r'Dual N-Back'),
        },
        "python ABI": {
            "generic session export": re.compile(
                r'^\s*fn\s+(?:nback_frame|nback_session_frame|batch_frame|menu_frame|menu_state_frame)\b',
                re.M,
            ),
        },
    }
    for shell, patterns in forbidden_port_paths.items():
        source = shell_sources[shell]
        for description, pattern in patterns.items():
            if pattern.search(source):
                raise ValueError(f"{shell} port exposes {description}")

    # The WASM source still contains legacy display helpers for the independent
    # source-parity sweeps. They are intentionally not counted as a production
    # host surface; the browser never routes to them and this audit guards that
    # distinction above.

    print(
        f"PASS: {len(rows)} stable task IDs; original, Elisa, and browser menus, "
        "controller/export map, host capabilities, and 224 source option records match"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
