import fs from "fs"; import { fileURLToPath } from "url";
import { load } from "../../build/nwcore.js";
const w = fileURLToPath(new URL("../../build/nwcore.wasm", import.meta.url));
const core = await load(fs.readFileSync(w));
// Plain numbers at the call site: the wrapper converts.
console.log("msToTicks(250, 100)      =", core.msToTicks(250, 100));
console.log("crabBack(3, 2)           =", core.crabBack(3, 2));
console.log("intervalAdjustStep(600)  =", core.intervalAdjustStep(600));
console.log("phaseField(2200,500,120,100,0) =", core.phaseField(2200, 500, 120, 100, 0));
