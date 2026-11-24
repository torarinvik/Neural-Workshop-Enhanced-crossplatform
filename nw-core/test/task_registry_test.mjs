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
assert.equal(catalog.schema_version, 5,
  "the reviewed manifest must carry source-derived option contracts and host capabilities");
assert.match(web, /import \{ TASK_CATEGORIES, TASK_IDS_BY_CATEGORY \} from "\.\/task-registry\.js";/,
  "the web menu must consume generated manifest data rather than duplicate it inline");
assert.equal(categories.length, idsByCategory.length,
  "each category's display order must have a corresponding ID row");
assert.equal(Object.keys(catalog.task_capabilities).length, 45,
  "every reviewed stable task ID must define a capability record");
assert.equal(Object.values(catalog.task_capabilities)
  .reduce((count, record) => count + Object.keys(record.options_schema).length, 0), 224,
"every source-defined task option and both scoped 3D N-Back controls must be represented");
assert.deepEqual(catalog.task_capabilities.tetris.options_schema.TETRIS_QUEUE, {
  type: "enum", value_type: "integer", default: 5, values: [2, 3, 4, 5, 6],
}, "Tetris queue choices must remain tied to the original settings screen");
assert.deepEqual(catalog.task_capabilities.nback.options_schema.grid_3d_cubes, {
  type: "enum", value_type: "integer", default: 1, values: [1, 2, 3, 4, 5, 6],
}, "3D N-Back cube-count choices must remain explicit in the manifest");

const catalogCategories = [...catalog.categories, ...(catalog.hub_categories ?? [])];
const catalogGroups = new Map(catalogCategories.map(({ id }) => [id, catalog.tasks
  .filter((task) => task.category === id)
  .sort((left, right) => left.position - right.position)]));
for (const task of catalog.hub_additions ?? []) {
  const group = catalogGroups.get(task.category);
  assert.ok(group, `unknown hub category ${task.category}`);
  if (task.after === undefined) {
    assert.equal(group.length, 0, `missing insertion anchor for ${task.id}`);
    group.push(task);
  } else {
    const anchor = group.findIndex(({ id }) => id === task.after);
    assert.ok(anchor >= 0, `missing insertion anchor ${task.after}`);
    group.splice(anchor + 1, 0, task);
  }
}
assert.equal(categories.length, catalogCategories.length);
for (let category = 0; category < categories.length; category++) {
  const { id, label } = catalogCategories[category];
  const group = catalogGroups.get(id);
  assert.equal(categories[category].name, label, `menu category label drifted in ${id}`);
  const expectedIds = group.map((task) => catalog.port_overrides[task.id]?.id ?? task.id);
  assert.deepEqual([...idsByCategory[category]], expectedIds,
    `stable menu IDs/order drifted from catalog in ${id}`);
  const expectedLabels = group.map((task) => catalog.port_overrides[task.id]?.label ?? task.label);
  assert.deepEqual([...categories[category].tasks], expectedLabels,
    `visible menu labels drifted from catalog in ${id}`);
}

assert.match(web, /function currentTaskId\(\)\s*\{\s*return TASK_IDS_BY_CATEGORY\[taskCategory\]\?\.\[taskSelected\] \?\? "";/,
  "the active menu selection must resolve through stable task identity");
assert.doesNotMatch(web, /taskCategory === \d+\s*&&\s*taskSelected === \d+/,
  "task routing must not dispatch controllers by duplicated category/index pairs");
assert.doesNotMatch(web, /taskSelected === \d+/, 
  "launch routing must not special-case a task by menu index");

console.log(`task_registry_test: PASS (generated ${idsByCategory.flat().length}-task menu, IDs/order, overrides, and stable-ID routing)`);
