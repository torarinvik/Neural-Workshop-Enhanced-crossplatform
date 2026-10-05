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
PYMODULE_EXPORTS = ROOT / "nw-core/src/pymodule_exports.elisa"
WASM_EXPORTS = ROOT / "nw-core/src/wasm/wasm_exports.elisa"


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


def original_tables():
    catalog_tree = ast.parse((ORIGINAL / "nwenv/catalog.py").read_text())
    ui_tree = ast.parse((ORIGINAL / "neural_workshop/ui/taskhub.py").read_text())
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
            match = re.match(r"\s{12}(?:if|elif) which == (\d+):", line)
            if match:
                current_task = int(match.group(1))
                continue
            label = re.match(r'\s{16}return "([^"]*)"', line)
            if label and label.group(1) and current_category is not None and current_task is not None:
                tasks[current_category][current_task] = label.group(1)
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
            "tasks": [
                overrides.get(task["id"], {}).get("label", task["label"])
                for task in sorted(
                    (row for row in fixture["tasks"] if row["category"] == category["id"]),
                    key=lambda row: row["position"],
                )
            ],
        }
        for category in fixture["categories"]
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
        for name, option in options.items():
            if not isinstance(name, str) or not isinstance(option, dict):
                raise ValueError(f"invalid option schema for {task_id}.{name}")
            if option.get("type") != "integer":
                raise ValueError(f"unsupported option type for {task_id}.{name}")
            default = option.get("default")
            minimum = option.get("minimum")
            maximum = option.get("maximum")
            if any(not isinstance(value, int) or isinstance(value, bool)
                   for value in (default, minimum, maximum)):
                raise ValueError(f"integer option bounds/default missing for {task_id}.{name}")
            if minimum > default or default > maximum:
                raise ValueError(f"option default outside bounds for {task_id}.{name}")


def main() -> int:
    fixture = json.loads(FIXTURE.read_text())
    if fixture.get("schema_version") != 4:
        raise ValueError("task fixture schema version must be 4")
    revision = subprocess.check_output(
        ["git", "-C", str(ORIGINAL), "-c", "core.hooksPath=/dev/null", "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if revision != fixture["reference_revision"]:
        raise ValueError(
            f"reference revision is {revision}, fixture pins {fixture['reference_revision']}; review and update deliberately"
        )

    original_catalog, original_groups = original_tables()
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
    audit_runtime_coverage(fixture, ids)
    audit_task_capabilities(fixture, ids)

    core_categories, core_tasks = parse_core_menu()
    web_groups = parse_web_menu(fixture)
    expected_categories = [group["label"] for group in original_groups]
    # The frozen reference keeps the stable task id/label pair `nback` for
    # catalog comparison. The port deliberately narrows that one visible
    # capability to the 3D face-pattern/cube task; all other N-Back variants
    # stay in the original application and must not appear in a port shell.
    overrides = fixture["port_overrides"]
    expected_groups = [[
        overrides.get(task["id"], {}).get("label", task["label"])
        for task in group["tasks"]
    ] for group in original_groups]
    actual_core_categories = [core_categories.get(index) for index in range(len(expected_categories))]
    actual_core_groups = [
        [core_tasks.get(index, {}).get(position) for position in range(len(group))]
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
        "kernel/scene anchors, controller/export map, and host capabilities match"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
