import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import {dirname,resolve} from "node:path";
import {pathToFileURL} from "node:url";

assert.equal(process.argv.length,4,"provide private module and original golden JSONL");
const [modulePath,inputPath]=process.argv.slice(2).map(p=>resolve(p));
const module=await(await import(pathToFileURL(modulePath).href)).default();
assert.equal(typeof module.marbleQCQP2Probe,"function");
const sha=p=>createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const bits=v=>{
  const a=new ArrayBuffer(8);new DataView(a).setFloat64(0,v,false);
  return Buffer.from(a).toString("hex");
};
const counts={captured:0,synthetic:0,rejected:0};let differences=0;const first=[];
for(const line of fs.readFileSync(inputPath,"utf8").trim().split("\n")){
  const row=JSON.parse(line);
  assert.equal(row.referenceSha256,"9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
  assert.ok(["captured","synthetic"].includes(row.kind));
  assert.equal(row.values.length,11);
  assert.ok(row.values.every(v=>typeof v==="number"&&Number.isFinite(v)));
  const actual=module.marbleQCQP2Probe(row.values);
  assert.equal(actual.accepted,true,row.label);
  const raw=Array.from(actual.rawForce,bits);
  if(actual.active!==row.active||JSON.stringify(raw)!==JSON.stringify(row.expectedBits)){
    differences++;if(first.length<6)first.push({label:row.label,kind:row.kind,
      expected:row.expectedBits,actual:raw,expectedActive:row.active,actualActive:actual.active});
  }
  counts[row.kind]++;
}
const good=[1,2,1,1,0,0,1,1,1,1,1];
for(const bad of [null,{},true,[],good.slice(0,10),[2,...good.slice(1)],
    [true,...good.slice(1)],[1,3,...good.slice(2)],[1,2,-1,...good.slice(3)],
    [...good.slice(0,10),0],[...good.slice(0,10),Infinity],
    [...good.slice(0,10),"1"],[...good.slice(0,10),NaN]]){
  assert.equal(module.marbleQCQP2Probe(bad).accepted,false);counts.rejected++;
}
console.log(JSON.stringify({schema:"neural-workshop.marble-compiled-qcqp2.v1",
  runtime:{jsPath:modulePath,jsSha256:sha(modulePath),
    wasmSha256:sha(resolve(dirname(modulePath),"mujoco.wasm"))},
  inputSha256:sha(inputPath),counts,differences,first}));
assert.equal(counts.captured,18);assert.equal(counts.synthetic,1000);
assert.equal(differences,0,"compiled two-tangent kernel differs from actual original");
