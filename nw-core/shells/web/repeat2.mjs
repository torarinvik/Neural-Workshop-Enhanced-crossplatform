import fs from "fs"; import { fileURLToPath } from "url";
import { instantiateElisa } from "./elisa-wasm-runtime.js";
const w = fileURLToPath(new URL("../../build/nwcore.wasm", import.meta.url));
const { exports: e, instance } = await instantiateElisa(fs.readFileSync(w), { warn: false });
const p = Number(e.nw_frame_alloc(65536n));
for (let i = 0; i < 5; i++) {
  const n = Number(e.nw_frame_write(BigInt(p), 65536n, BigInt(i + 1), 2n, 4n, 0n));
  const b = new Uint8Array(instance.exports.memory.buffer, p, n);
  const dv = new DataView(instance.exports.memory.buffer, p, n);
  const c = dv.getUint32(8, true), pl = dv.getUint32(12, true);
  const pool = new TextDecoder().decode(b.subarray(16 + c*40, 16 + c*40 + pl));
  console.log(`frame ${i}: pages=${instance.exports.memory.buffer.byteLength/65536} pool=${JSON.stringify(pool)}`);
}
