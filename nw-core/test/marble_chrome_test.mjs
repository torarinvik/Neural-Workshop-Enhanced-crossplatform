import assert from "node:assert/strict";
import fs from "node:fs";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { marbleGlyphStrokeRatio, marbleStaticChrome } from "../shells/web/marble-chrome.js";
import { Kind, decode } from "../shells/web/display-list.js";

const status = {kind: Kind.TEXT, a:456, b:622, anchor:["center","top"],
  text:"Press Space"};
const shellSource = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const title = {...status, b:648, text:"Marble Maze"};
const help = {...status, b:26, anchor:["center","middle"], text:"Esc: task menu"};
const other = {...status, a:100};
const marker = {...status, kind:Kind.MARKER};
const commands = [title,status,help,other,marker];
assert.deepEqual(marbleStaticChrome(commands), [title,help,other,marker]);
assert.equal(commands.length,5);
assert.equal(marbleGlyphStrokeRatio(false),0.045,
  "light Marble labels retain the measured native-weight compensation");
assert.equal(marbleGlyphStrokeRatio(true),0,
  "dark Marble labels must not over-thicken their antialiased edges");
assert.match(shellSource,
  /glyphStrokeRatio:[\s\S]*?marbleGlyphStrokeRatio\(dark\(\) !== 0\)/,
  "the live Marble renderer must apply the measured theme-specific text weight");
assert.deepEqual(marbleStaticChrome([{...status,b:621.2999877929688}],800,600), []);
assert.deepEqual(marbleStaticChrome([{...status,b:620}]), [{...status,b:620}]);
for (const text of ["Ready", "Game started", "lost", ""]) {
  assert.deepEqual(marbleStaticChrome([{...status,text}]), []);
}
const wasm = fs.readFileSync(process.env.NWCORE_WASM_PATH ??
  new URL("../build/nwcore.wasm", import.meta.url));
const {exports:e} = await instantiateElisa(wasm, {warn:false});
const capacity = 1048576n;
const pointer = e.nw_frame_alloc(capacity);
let frames = 0;
for (const [width,height] of [[800,600],[912,684],[1280,720],[801,601],
                             [320,240],[1920,1080],[321,241]]) {
  for (const phase of [0,1,2,3]) {
    const length = e.nw_task_game_input_write(pointer,capacity,2n,10n,0n,
      BigInt(phase),0n,0n,0n,0n,-1n,BigInt(width),BigInt(height));
    const commands = decode(new Uint8Array(e.memory.buffer,Number(pointer),Number(length)));
    const slots = commands.filter(c=>c.kind===Kind.TEXT &&
      c.anchor?.[0]==="center" && c.anchor?.[1]==="top");
    assert.equal(slots.length,1,`${width}x${height}, phase ${phase}: status slot`);
    const retained = commands.filter(c=>c!==slots[0]);
    assert.deepEqual(marbleStaticChrome(commands,width,height),retained,
      `${width}x${height}, phase ${phase}: remove only the compiled status`);
    frames++;
  }
}
console.log(`PASS: Marble host owns one live status slot; ${frames} compiled frames preserve other chrome`);
