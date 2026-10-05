import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import {dirname,resolve} from "node:path";
import {pathToFileURL} from "node:url";

assert.equal(process.argv.length,4,"provide private module and original golden JSONL");
const [modulePath,inputPath]=process.argv.slice(2).map(p=>resolve(p));
const module=await(await import(pathToFileURL(modulePath).href)).default();
assert.equal(typeof module.marbleCostPrimitivesProbe,"function");
const sha=p=>createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const bits=v=>{
  const a=new ArrayBuffer(8);new DataView(a).setFloat64(0,v,false);
  return Buffer.from(a).toString("hex");
};
const counts={captured:0,synthetic:0,rejected:0};
const dimensions={2:0,3:0,5:0};let differences=0;const first=[];
for(const line of fs.readFileSync(inputPath,"utf8").trim().split("\n")){
  const row=JSON.parse(line);
  assert.equal(row.referenceSha256,"9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
  assert.ok(["captured","synthetic"].includes(row.kind));
  const n=row.values[1];assert.ok([2,3,5].includes(n));
  assert.equal(row.values.length,2+n*n+3*n);
  assert.ok(row.values.every(v=>typeof v==="number"&&Number.isFinite(v)));
  const actual=module.marbleCostPrimitivesProbe(row.values);
  assert.equal(actual.accepted,true,row.label);
  const output={quadratic:bits(actual.quadratic),dot:bits(actual.dot)};
  if(Object.keys(output).some(k=>output[k]!==row.expectedBits[k])){
    differences++;if(first.length<8)first.push({label:row.label,kind:row.kind,
      expected:row.expectedBits,actual:output});
  }
  counts[row.kind]++;dimensions[n]++;
}
const good=[1,2,1,2,1,0,0,1,1,2,-1,-2];
for(const bad of [null,{},true,[],good.slice(0,11),[...good,0],
    [2,...good.slice(1)],[true,...good.slice(1)],
    [1,1,...good.slice(2)],[1,4,...good.slice(2)],[1,6,...good.slice(2)],
    [1,2.5,...good.slice(2)],[1,5,...good.slice(2)],
    [...good.slice(0,11),Infinity],[...good.slice(0,11),NaN],
    [...good.slice(0,11),"1"],[...good.slice(0,11),true],Array(43).fill(0)]){
  assert.equal(module.marbleCostPrimitivesProbe(bad).accepted,false);counts.rejected++;
}
console.log(JSON.stringify({schema:"neural-workshop.marble-compiled-cost-primitives.v1",
  runtime:{jsPath:modulePath,jsSha256:sha(modulePath),
    wasmSha256:sha(resolve(dirname(modulePath),"mujoco.wasm"))},
  inputSha256:sha(inputPath),counts,dimensions,differences,first}));
assert.equal(counts.captured,134);assert.equal(counts.synthetic,1000);
assert.equal(differences,0,"actual compiled cost primitives differ from actual original");
