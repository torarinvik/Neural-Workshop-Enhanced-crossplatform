// Read-only helper localization on existing public compiled bindings.
import assert from "node:assert/strict";
import fs from "node:fs";
import {resolve,dirname} from "node:path";
import {pathToFileURL} from "node:url";
import {createHash} from "node:crypto";
const [modulePath,inputPath]=process.argv.slice(2).map(p=>resolve(p));
assert.ok(modulePath && inputPath,"provide private module and original JSON");
const module=await(await import(pathToFileURL(modulePath).href)).default();
const golden=JSON.parse(fs.readFileSync(inputPath,"utf8"));
assert.equal(golden.referenceSha256,"9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
const bits=v=>{const b=Buffer.alloc(8);b.writeDoubleBE(v);return b.toString("hex");};
const decode=v=>Buffer.from(v,"hex").readDoubleBE();
const model=module.MjModel.from_xml_string('<mujoco><worldbody><body><freejoint/><geom size=".1"/></body></worldbody></mujoco>');
const data=new module.MjData(model);
const counts={integrate:0,normalize3:0,normalize3Length:0,normalize4:0,axisAngle:0,sine:0,cosine:0,multiply:0};
const capturedCounts=Object.fromEntries(Object.keys(counts).map(k=>[k,0]));
const first={};
function compare(name,row,actual,expected){
  const values=Array.from(actual,bits);
  if(JSON.stringify(values)!==JSON.stringify(expected)){
    counts[name]++;
    if(row.label.startsWith("event"))capturedCounts[name]++;
    first[name]??={label:row.label,actual:values,expected};
  }
}
try{
  for(const row of golden.results){
    assert.equal(row.q.length,4);assert.equal(row.v.length,3);
    assert.ok([...row.q,...row.v,row.dt].every(Number.isFinite));
    const out=data.qpos.subarray(0,4);
    out.set(row.q);module.mju_quatIntegrate(out,row.v,row.dt);
    compare("integrate",row,out,row.originalBits);
    out.set(row.v);const norm=module.mju_normalize3(out.subarray(0,3));
    compare("normalize3Length",row,[norm],row.normBits);
    compare("normalize3",row,out.subarray(0,3),row.axisBits);
    out.set(row.q);module.mju_normalize4(out);
    compare("normalize4",row,out,row.normalizedBits);
    module.mju_axisAngle2Quat(out,row.axisBits.map(decode),decode(row.angleBits[0]));
    compare("axisAngle",row,out,row.rotationBits);
    if(row.sineBits && row.cosineBits){
      module.mju_axisAngle2Quat(out,[1,0,0],decode(row.angleBits[0]));
      compare("sine",row,[out[1]],row.sineBits);
      compare("cosine",row,[out[0]],row.cosineBits);
    }
    module.mju_mulQuat(out,row.normalizedBits.map(decode),row.rotationBits.map(decode));
    compare("multiply",row,out,row.originalBits);
  }
}finally{data.delete();model.delete();}
console.log(JSON.stringify({schema:"neural-workshop.marble-quaternion-helper-localization.v1",calls:golden.results.length,
  runtimeJsSha256:createHash("sha256").update(fs.readFileSync(modulePath)).digest("hex"),
  runtimeWasmSha256:createHash("sha256").update(fs.readFileSync(resolve(dirname(modulePath),"mujoco.wasm"))).digest("hex"),
  counts,capturedCounts,first,ordinaryTrajectoryAcceptance:false,promoted:false},null,2));
