import fs from "fs"; import { fileURLToPath } from "url";
import { instantiateElisa } from "./elisa-wasm-runtime.js";
import { decode } from "./display-list.js";
const w = fileURLToPath(new URL("../../build/nwcore.wasm", import.meta.url));
const { exports: e, instance } = await instantiateElisa(fs.readFileSync(w), { warn: false });
const p = Number(e.nw_frame_alloc(65536n));
for (let i = 0; i < 3; i++) {
  const n = Number(e.nw_frame_write(BigInt(p), 65536n, 5n, 2n, 4n, 0n));
  const cmds = decode(new Uint8Array(instance.exports.memory.buffer, p, n));
  const texts = cmds.filter(c => c.kind === 11 || c.kind === 14).map(c => `${c.ref}+${c.len & 0xffffff}`);
  const box = cmds.find(c => c.kind === 3);
  console.log(`frame ${i}: bytes=${n} cmds=${cmds.length} box.x=${box ? box.a : "?"} textrefs=[${texts}]`);
}
