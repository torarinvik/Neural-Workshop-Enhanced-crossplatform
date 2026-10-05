import assert from "node:assert/strict";
import {
  RESULT_STORE_KEY,
  RESULT_STORE_VERSION,
  exportResultLedger,
  importResultLedger,
  loadResultLedger,
  upsertResultRecord,
} from "../shells/web/result-store.js";

class MemoryStorage {
  constructor() { this.values = new Map(); }
  getItem(key) { return this.values.has(key) ? this.values.get(key) : null; }
  setItem(key, value) { this.values.set(key, String(value)); }
}

const storage = new MemoryStorage();
const first = { id: "session-1", task: "marble_maze", completed: 1,
  results: [{ trial: 1, scoreWin: true }] };
let result = upsertResultRecord(first, storage);
assert.equal(result.ok, true);
assert.equal(result.replaced, false);
assert.equal(JSON.parse(storage.getItem(RESULT_STORE_KEY)).version, RESULT_STORE_VERSION);

// Replaying the same session updates one record rather than appending a second
// copy. This is the invariant required when a redraw retries a durable write.
result = upsertResultRecord({ ...first, completed: 2,
  results: [...first.results, { trial: 2, scoreWin: false }] }, storage);
assert.equal(result.ok, true);
assert.equal(result.replaced, true);
assert.equal(loadResultLedger(storage).ledger.records.length, 1);
assert.equal(loadResultLedger(storage).ledger.records[0].completed, 2);

const imported = {
  version: 1,
  records: [
    { id: "session-2", task: "count", completed: 1 },
    { id: "session-1", task: "marble_maze", completed: 3 },
  ],
};
result = importResultLedger(JSON.stringify(imported), storage);
assert.equal(result.ok, true);
let loaded = loadResultLedger(storage);
assert.equal(loaded.ledger.records.length, 2);
assert.equal(loaded.ledger.records.find((record) => record.id === "session-1").completed, 3);

const exported = exportResultLedger(storage);
assert.equal(exported.ok, true);
assert.deepEqual(JSON.parse(exported.text), loaded.ledger);

// Invalid imports are rejected before setItem, preserving the old committed
// ledger. A throwing storage must likewise report failure instead of claiming
// that the result was saved.
const beforeInvalid = storage.getItem(RESULT_STORE_KEY);
result = importResultLedger(JSON.stringify({ version: 99, records: [] }), storage);
assert.equal(result.ok, false);
assert.equal(storage.getItem(RESULT_STORE_KEY), beforeInvalid);
const denied = { getItem() { throw new Error("private mode"); }, setItem() {
  throw new Error("private mode");
} };
assert.equal(upsertResultRecord(first, denied).ok, false);

console.log("PASS: transactional result store, import/export, and duplicate-session protection");
