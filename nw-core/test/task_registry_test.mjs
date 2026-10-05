import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const webPath = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const catalogPath = fileURLToPath(new URL("./fixtures/task_catalog.json", import.meta.url));
const registryPath = fileURLToPath(new URL("../shells/web/task-registry.js", import.meta.url));
const web = fs.readFileSync(webPath, "utf8");
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
const registrySource = fs.readFileSync(registryPath, "utf8");
const registryModule = await import(`data:text/javascript;base64,${Buffer.from(registrySource).toString("base64")}`);
const { TASK_CATEGORIES: categories, TASK_IDS_BY_CATEGORY: idsByCategory } = registryModule;
assert.equal(catalog.schema_version, 4,
  "the reviewed manifest must carry category metadata, port overrides, and task capabilities");
assert.match(web, /import \{ TASK_CATEGORIES, TASK_IDS_BY_CATEGORY \} from "\.\/task-registry\.js";/,
  "the web menu must consume generated manifest data rather than duplicate it inline");
assert.equal(categories.length, idsByCategory.length,
  "each category's display order must have a corresponding ID row");
assert.deepEqual(catalog.task_capabilities.tetris, {
  required_services: [],
  supported_input: ["keyboard", "pointer"],
  options_schema: {
    starting_rung: { type: "integer", default: 1, minimum: 1, maximum: 8 },
    piece_target: { type: "integer", default: 25, minimum: 1, maximum: 500 },
    queue_size: { type: "integer", default: 5, minimum: 1, maximum: 6 },
  },
}, "Tetris host/input/options capabilities must remain explicit in the manifest");

const catalogCategories = catalog.categories.map((category) => category.id);
const expectedIds = catalogCategories.map((category) => catalog.tasks
  .filter((task) => task.category === category)
  .sort((left, right) => left.position - right.position)
  .map((task) => catalog.port_overrides[task.id]?.id ?? task.id));
assert.equal(categories.length, catalogCategories.length);
for (let category = 0; category < categories.length; category++) {
  assert.equal(categories[category].name, catalog.categories[category].label,
    `menu category label drifted in ${catalogCategories[category]}`);
  assert.equal(categories[category].tasks.length, expectedIds[category].length,
    `menu/catalog task-count mismatch in ${catalogCategories[category]}`);
  assert.deepEqual([...idsByCategory[category]], expectedIds[category],
    `stable menu IDs/order drifted from catalog in ${catalogCategories[category]}`);
  const expectedLabels = catalog.tasks
    .filter((task) => task.category === catalogCategories[category])
    .sort((left, right) => left.position - right.position)
    .map((task) => catalog.port_overrides[task.id]?.label ?? task.label);
  assert.deepEqual([...categories[category].tasks], expectedLabels,
    `visible menu labels drifted from catalog in ${catalogCategories[category]}`);
}

assert.match(web, /function currentTaskId\(\)\s*\{\s*return TASK_IDS_BY_CATEGORY\[taskCategory\]\?\.\[taskSelected\] \?\? "";/,
  "the active menu selection must resolve through stable task identity");
assert.doesNotMatch(web, /taskCategory === \d+\s*&&\s*taskSelected === \d+/,
  "task routing must not dispatch controllers by duplicated category/index pairs");
assert.doesNotMatch(web, /taskSelected === \d+/, 
  "launch routing must not special-case a task by menu index");

console.log("task_registry_test: PASS (generated 45-task menu, IDs/order, overrides, and stable-ID routing)");
