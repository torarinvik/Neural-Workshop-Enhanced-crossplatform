const MIN_RECORDINGS = 300;
const MAX_WAV_BYTES = 4 * 1024 * 1024;

export function tunerRecordingBank(index, files) {
  const byRow = new Map();
  for (const file of files) {
    const match = /^(\d{7})\.wav$/.exec(file.name);
    if (!match) continue;
    const path = file.webkitRelativePath?.split("/") ?? [];
    if (path.length > 2 && path.at(-2).toLowerCase() !== "esc50") continue;
    if (file.size > 0 && file.size <= MAX_WAV_BYTES) byRow.set(Number(match[1]), file);
  }
  const entries = new Map();
  for (const line of index.split(/\r?\n/)) {
    if (line.startsWith("#") || !line.trim()) continue;
    const fields = line.split("\t");
    const [row, label, from, to, sounding, db] = fields.map(Number);
    if (fields.length !== 6 || fields.some(field => !field.trim()) ||
        ![row, label, from, to].every(Number.isSafeInteger) ||
        ![sounding, db].every(Number.isFinite) ||
        row < 0 || row >= 2000 || label < 0 || label >= 50 || from < 0 || to > 60000) {
      throw new Error("Invalid ESC-50 index");
    }
    const file = byRow.get(row);
    if (file && to / 1000 - from / 1000 >= 1 && sounding >= 0.45 && db >= -42) {
      entries.set(row, { file, label, from, to });
    }
  }
  return new Map([...entries].sort(([a], [b]) => a - b));
}

export function attachTunerRecordings(api, handle, bank) {
  if (bank.size < MIN_RECORDINGS) return;
  for (const [row, entry] of bank) {
    if (api.nw_tuner_recording_add(handle, BigInt(row), BigInt(entry.label),
        BigInt(entry.from), BigInt(entry.to)) !== 1n) {
      throw new Error("Could not register the Tuner recordings");
    }
  }
}

export async function loadTunerRecordings(api, handle, bank, current, now) {
  const stations = Number(api.nw_api_v1_tuner_info(handle, 6n));
  const rows = new Map();
  let pointer = 0n;
  try {
    for (let position = -1; position < stations; position++) {
      if (!current()) return;
      const row = Number(api.nw_tuner_recording_row(handle, BigInt(position)));
      const entry = bank.get(row);
      if (!entry) throw new Error("Missing Tuner recording metadata");
      if (!rows.has(row)) {
        try {
          const bytes = await entry.file.arrayBuffer();
          rows.set(row, bytes.byteLength <= MAX_WAV_BYTES ? bytes : new ArrayBuffer(0));
        } catch (_error) {
          rows.set(row, new ArrayBuffer(0));
        }
      }
      if (!current()) return;
      const bytes = rows.get(row);
      if (bytes.byteLength > 0) {
        if (!pointer) pointer = api.nw_frame_alloc(BigInt(MAX_WAV_BYTES));
        if (!pointer) throw new Error("Could not allocate recording buffer");
        new Uint8Array(api.memory.buffer, Number(pointer), bytes.byteLength).set(new Uint8Array(bytes));
      }
      if (api.nw_tuner_recording_load(handle, BigInt(position), pointer, BigInt(bytes.byteLength),
          BigInt(entry.from), BigInt(entry.to), now()) !== 1n) {
        throw new Error("Could not load the Tuner recording");
      }
    }
  } finally {
    if (pointer) api.nw_frame_free(pointer);
  }
}
