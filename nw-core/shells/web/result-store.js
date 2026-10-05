// Transactional browser-side result storage shared by the web shell.
//
// localStorage.setItem is atomic at the key level: construct and validate the
// complete replacement string before publishing it, and never clear the old
// value first. Callers receive an explicit {ok:false} result when storage is
// unavailable or malformed so the UI cannot claim that a result was saved.

export const RESULT_STORE_KEY = "neural-workshop.results.v1";
export const RESULT_STORE_VERSION = 1;

function emptyLedger() {
  return { version: RESULT_STORE_VERSION, records: [] };
}

function storageOrNull(storage) {
  if (storage !== undefined) return storage;
  try {
    return globalThis.localStorage ?? null;
  } catch (_error) {
    return null;
  }
}

function validRecord(record) {
  return record !== null && typeof record === "object" &&
    typeof record.id === "string" && record.id.length > 0 && record.id.length <= 160 &&
    typeof record.task === "string" && record.task.length > 0 && record.task.length <= 80;
}

function parseLedger(raw) {
  if (raw === null || raw === "") return emptyLedger();
  const parsed = JSON.parse(raw);
  if (parsed === null || typeof parsed !== "object" ||
      parsed.version !== RESULT_STORE_VERSION || !Array.isArray(parsed.records)) {
    throw new Error("result store has an unsupported format");
  }
  const records = [];
  const ids = new Set();
  for (const record of parsed.records) {
    if (!validRecord(record) || ids.has(record.id)) {
      throw new Error("result store contains an invalid or duplicate record");
    }
    ids.add(record.id);
    // JSON cloning removes accessors/prototypes before a record can be
    // returned to application code or written back to storage.
    records.push(JSON.parse(JSON.stringify(record)));
  }
  return { version: RESULT_STORE_VERSION, records };
}

function serializeLedger(ledger) {
  const checked = parseLedger(JSON.stringify(ledger));
  return JSON.stringify(checked);
}

function unavailable(reason) {
  return { ok: false, ledger: emptyLedger(), error: reason };
}

export function loadResultLedger(storage) {
  const target = storageOrNull(storage);
  if (!target || typeof target.getItem !== "function") {
    return unavailable(new Error("browser result storage is unavailable"));
  }
  try {
    return { ok: true, ledger: parseLedger(target.getItem(RESULT_STORE_KEY)) };
  } catch (error) {
    return unavailable(error);
  }
}

export function saveResultLedger(ledger, storage) {
  const target = storageOrNull(storage);
  if (!target || typeof target.setItem !== "function") {
    return { ok: false, error: new Error("browser result storage is unavailable") };
  }
  try {
    // Serialize and validate before touching storage. If setItem throws, the
    // previous value remains the only committed value at this key.
    const serialized = serializeLedger(ledger);
    target.setItem(RESULT_STORE_KEY, serialized);
    return { ok: true, ledger: JSON.parse(serialized) };
  } catch (error) {
    return { ok: false, error };
  }
}

export function upsertResultRecord(record, storage) {
  if (!validRecord(record)) {
    return { ok: false, error: new Error("result record is missing a valid id or task") };
  }
  const loaded = loadResultLedger(storage);
  if (!loaded.ok) return loaded;
  const records = loaded.ledger.records.filter((item) => item.id !== record.id);
  records.push(JSON.parse(JSON.stringify(record)));
  const saved = saveResultLedger({ version: RESULT_STORE_VERSION, records }, storage);
  return saved.ok ? { ...saved, replaced: loaded.ledger.records.some((item) => item.id === record.id) } : saved;
}

export function exportResultLedger(storage) {
  const loaded = loadResultLedger(storage);
  if (!loaded.ok) return loaded;
  return { ok: true, text: JSON.stringify(loaded.ledger, null, 2), ledger: loaded.ledger };
}

export function importResultLedger(text, storage, { merge = true } = {}) {
  let incoming;
  try {
    incoming = parseLedger(text);
  } catch (error) {
    return { ok: false, error };
  }
  if (!merge) return saveResultLedger(incoming, storage);

  const loaded = loadResultLedger(storage);
  if (!loaded.ok) return loaded;
  const byId = new Map(loaded.ledger.records.map((record) => [record.id, record]));
  for (const record of incoming.records) byId.set(record.id, record);
  return saveResultLedger({
    version: RESULT_STORE_VERSION,
    records: [...byId.values()],
  }, storage);
}
