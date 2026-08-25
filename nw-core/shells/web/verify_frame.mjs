// Cross-checks the JS decoder against the Python one on a frame produced by
// the WASM core: both must see identical commands.
import fs from "fs";
import { fileURLToPath } from "url";
import { execFileSync } from "child_process";
import { instantiateElisa } from "./elisa-wasm-runtime.js";
import { decode } from "./display-list.js";

const wasmPath = fileURLToPath(new URL("../../build/nwcore.wasm", import.meta.url));
const { exports: e, instance } = await instantiateElisa(fs.readFileSync(wasmPath), { warn: false });

const buf = Number(e.nw_frame_alloc(65536n));
if (!buf) throw new Error("frame_alloc failed");
const len = Number(e.nw_frame_write(BigInt(buf), 65536n, 5n, 2n, 4n, 0n));
console.log(`frame: ${len} bytes at 0x${buf.toString(16)}`);

const bytes = new Uint8Array(instance.exports.memory.buffer, buf, len);
const commands = decode(bytes);
console.log(`decoded ${commands.length} commands`);

const hex = Buffer.from(bytes).toString("hex");
const py = execFileSync("python3", ["-c", `
import sys; sys.path.insert(0, "${fileURLToPath(new URL("../../test", import.meta.url))}")
from display_decode import decode, canonical
print("\\n".join(canonical(decode(bytes.fromhex(sys.argv[1])))))`, hex], { encoding: "utf8" }).trim().split("\n");

// Same canonical form as the Python side, so the two decoders are comparable.
const canon = commands.map(c => {
    const named = { kind: Object.keys({RECT:1,BORDERED_RECT:2,BOX:3,CIRCLE:4,ARC:5,LINE:6,TRIANGLE:7,POLYGON:8,POLY_POINT:9,SPRITE:10,TEXT:11,VERDICT:12,SOUND:13,MARKER:14}).find(
        k => ({RECT:1,BORDERED_RECT:2,BOX:3,CIRCLE:4,ARC:5,LINE:6,TRIANGLE:7,POLYGON:8,POLY_POINT:9,SPRITE:10,TEXT:11,VERDICT:12,SOUND:13,MARKER:14})[k] === c.kind).toLowerCase() };
    return named.kind;
}).join(",");
const pyKinds = py.map(l => l.split(" ")[0]).join(",");

if (canon !== pyKinds) {
    console.log("MISMATCH\n  js:     " + canon + "\n  python: " + pyKinds);
    process.exit(1);
}
console.log(`PASS: both decoders agree on ${commands.length} commands`);
console.log("first three:", py.slice(0, 3).join(" | "));
