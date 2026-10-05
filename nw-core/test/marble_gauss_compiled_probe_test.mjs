import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import {dirname,resolve} from "node:path";
import {pathToFileURL} from "node:url";

assert.equal(process.argv.length,4,"provide private module and original golden JSONL");
const [modulePath,inputPath]=process.argv.slice(2).map(p=>resolve(p));
const module=await(await import(pathToFileURL(modulePath).href)).default();
assert.equal(typeof module.marbleGaussProbe,"function");
const sha=p=>createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const bits=value=>{
  const a=new ArrayBuffer(8);new DataView(a).setFloat64(0,value,false);
  return Buffer.from(a).toString("hex");
};
const counts={captured:0,synthetic:0,rejected:0};
let differences=0;const first=[];
for(const line of fs.readFileSync(inputPath,"utf8").trim().split("\n")){
  const row=JSON.parse(line);
  assert.equal(row.referenceSha256,"9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
  assert.ok(["captured","synthetic"].includes(row.kind));
  assert.ok(row.values.every(v=>typeof v==="number"&&Number.isFinite(v)));
  const output=module.marbleGaussProbe(row.values);
  assert.equal(output.accepted,true,row.label);
  if(bits(output.gauss)!==row.expectedBits||bits(output.cost)!==row.expectedBits){
    differences++;if(first.length<6)first.push({label:row.label,kind:row.kind,
      expected:row.expectedBits,gauss:bits(output.gauss),cost:bits(output.cost)});
  }
  counts[row.kind]++;
}
for(const row of [null,{},true,[],[1],[2,0],[true,0],[1,true],[1,-1],
    [1,513],[1,.5],[1,1],[1,0,0],[1,1,1,1,1,Infinity],[1,1,1,1,1,"1"],
    [1,1,1,1,1,NaN]]){
  assert.equal(module.marbleGaussProbe(row).accepted,false);
  counts.rejected++;
}
console.log(JSON.stringify({schema:"neural-workshop.marble-compiled-gauss.v1",
  runtime:{jsPath:modulePath,jsSha256:sha(modulePath),
    wasmSha256:sha(resolve(dirname(modulePath),"mujoco.wasm"))},
  inputSha256:sha(inputPath),counts,differences,first}));
assert.equal(counts.captured,125);assert.equal(counts.synthetic,1000);
assert.equal(differences,0,"compiled actual Gauss producer differs from original");
