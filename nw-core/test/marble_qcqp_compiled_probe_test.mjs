// Private complete generic kernel probe; no production or browser mutations.
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import {dirname,resolve} from "node:path";
import {pathToFileURL} from "node:url";

assert.equal(process.argv.length,4,"provide private module and original golden JSONL");
const [moduleFile,inputFile]=process.argv.slice(2).map(p=>resolve(p));
const module=await(await import(pathToFileURL(moduleFile).href)).default();
assert.equal(typeof module.marbleQCQP5Probe,"function");
const sha=p=>createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const bits=v=>{
  const buffer=new ArrayBuffer(8);
  new DataView(buffer).setFloat64(0,v,false);
  return Buffer.from(buffer).toString("hex");
};
const counts={captured:0,synthetic:0,rejected:0};
let differences=0;
const first=[];
for(const line of fs.readFileSync(inputFile,"utf8").trim().split("\n")){
  const row=JSON.parse(line);
  assert.equal(row.referenceSha256,"9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
  assert.ok(["captured","synthetic"].includes(row.kind));
  assert.equal(row.values.length,38);
  assert.ok(row.values.every(v=>typeof v==="number"&&Number.isFinite(v)));
  const actual=module.marbleQCQP5Probe(row.values);
  assert.equal(actual.accepted,true,row.label);
  const actualBits=Array.from(actual.rawForce,bits);
  if(actual.active!==row.active||JSON.stringify(actualBits)!==JSON.stringify(row.expectedBits)){
    differences++;
    if(first.length<8)first.push({label:row.label,kind:row.kind,expected:row.expectedBits,
      actual:actualBits,expectedActive:row.active,actualActive:actual.active});
  }
  counts[row.kind]++;
}
const good=[1,5,1,...Array(25).fill(0),...Array(5).fill(0),...Array(5).fill(1)];
for(const bad of [[],[1],null,{},true,good.slice(0,37),[2,...good.slice(1)],
  [1,4,...good.slice(2)],[1,5,-1,...good.slice(3)],[true,...good.slice(1)],
  [...good.slice(0,37),0],[...good.slice(0,37),Infinity],
  [...good.slice(0,37),"1"]]){
  assert.equal(module.marbleQCQP5Probe(bad).accepted,false);
  counts.rejected++;
}
console.log(JSON.stringify({schema:"neural-workshop.marble-compiled-qcqp.v1",
  runtime:{jsPath:moduleFile,jsSha256:sha(moduleFile),
    wasmSha256:sha(resolve(dirname(moduleFile),"mujoco.wasm"))},
  inputSha256:sha(inputFile),counts,differences,first}));
assert.equal(counts.captured,114);
assert.equal(counts.synthetic,1000);
assert.equal(differences,0,"compiled generic kernel differs from actual original");
