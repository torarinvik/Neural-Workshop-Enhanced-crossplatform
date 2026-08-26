// Does the SHELL's fit rule land the splash where the original put it?
//
//     node shells/web/splash_fit_test.mjs
//
// title_diff.py checks the core side: that the room the core names matches the
// original's. It cannot check the other half, because the fit itself lives in
// the shell -- the core never learns the image's size. This closes that gap by
// applying the shell's rule to the real artwork's dimensions and comparing the
// result against the rectangle measured off the running original.
import { readFile } from "node:fs/promises";
import { instantiateElisa } from "./elisa-wasm-runtime.js";
import { decode, Kind } from "./display-list.js";
const { exports, instance } = await instantiateElisa(await readFile(new URL("../../build/nwcore.wasm", import.meta.url)), { warn: false });
const CAP = 65536, ptr = Number(exports.nw_frame_alloc(BigInt(CAP)));
const len = Number(exports.nw_title_write(BigInt(ptr), BigInt(CAP), 1n, 0n, 0n, 0n));
const fit = decode(new Uint8Array(instance.exports.memory.buffer, ptr, len))
  .find(c => c.kind === Kind.SPRITE_FIT);
if (!fit) { console.log("no sprite_fit command"); process.exit(1); }
const IW = 1254, IH = 1254;                       // res/Logo/logo.png
const scale = Math.min(fit.c / IW, fit.d / IH);   // c,d are the room extent
const w = IW * scale, h = IH * scale;
const got = { x: fit.a - w / 2, y: fit.b - h / 2, w, h };
const want = { x: 298, y: 268, w: 316, h: 316 };  // measured from the original
console.log("room     :", fit.c, "x", fit.d, "centred at", fit.a, fit.b);
console.log("fitted   :", JSON.stringify(got));
console.log("original :", JSON.stringify(want));
const ok = ["x","y","w","h"].every(k => Math.abs(got[k] - want[k]) < 0.01);
console.log(ok ? "MATCH: the shell's fit reproduces the original's placement" : "MISMATCH");
process.exit(ok ? 0 : 1);
