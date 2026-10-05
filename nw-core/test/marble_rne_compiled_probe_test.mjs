import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import {dirname,resolve} from "node:path";
import {pathToFileURL} from "node:url";

assert.equal(process.argv.length,4,"provide private module and original complete-RNE golden JSONL");
const [modulePath,inputPath]=process.argv.slice(2).map(p=>resolve(p));
const module=await(await import(pathToFileURL(modulePath).href)).default();
const controlPath=process.env.NW_RNE_CONTROL_MODULE?resolve(process.env.NW_RNE_CONTROL_MODULE):null;
const control=controlPath?await(await import(pathToFileURL(controlPath).href)).default():null;
const sha=p=>createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const bits=v=>{
  const a=new ArrayBuffer(8);new DataView(a).setFloat64(0,v,false);
  return Buffer.from(a).toString("hex");
};
const fields=["cinert","cvel","cdof","cdof_dot","qvel"];
const counts={captured:0,synthetic:0};const layouts={};let differences=0;const first=[];
const contexts=new Map();
const controlContexts=new Map();let accelerationControlMatches=0;
try{
  for(const line of fs.readFileSync(inputPath,"utf8").trim().split("\n")){
    const row=JSON.parse(line),{model:m,arrays:a}=row.input;
    assert.equal(row.referenceSha256,"9e7724614fb0b3f346758ff4158ef65e7c398f2caa3e9daab41ed210b4ab689c");
    assert.ok(["captured","synthetic"].includes(row.kind));
    const nb=m.body_parentid.length,nv=a.qvel.length;
    assert.ok(nb>0&&nb<=1000&&nv>0&&nv<=512);assert.equal(row.expectedBits.length,nv);
    assert.equal(m.options.enableflags&16,0,"sleep context must be disabled");
    for(const [field,width] of [["cinert",10*nb],["cvel",6*nb],["cdof",6*nv],["cdof_dot",6*nv],["qvel",nv]]){
      assert.equal(a[field].length,width);assert.ok(a[field].every(v=>typeof v==="number"&&Number.isFinite(v)));
    }
    let context=contexts.get(row.xml);
    if(!context){
      const model=module.MjModel.from_xml_string(row.xml);
      context={model,data:new module.MjData(model)};contexts.set(row.xml,context);
    }
    const {model,data}=context;
    assert.equal(model.nbody,nb);assert.equal(model.nv,nv);
    for(const field of ["body_parentid","body_dofadr","body_dofnum"])
      assert.deepEqual(Array.from(model[field]),m[field]);
    model.opt.enableflags=m.options.enableflags;model.opt.disableflags=m.options.disableflags;
    for(let j=0;j<3;j++)model.opt.gravity[j]=m.gravity[j];
    for(const field of fields){
      assert.equal(data[field].length,a[field].length);
      for(let j=0;j<a[field].length;j++)data[field][j]=a[field][j];
      assert.deepEqual(Array.from(data[field]),a[field]);
    }
    // The retained wrapper calls ACTUAL mj_rne after its mirror, then returns
    // its result at this assigned offset. Mirror intermediates are not oracle
    // expectations and cannot make a reconstructed RNE return pass.
    const trace=Array.from(module.marbleRneProjectionTrace(model,data));
    assert.equal(trace.length,36*nb+13*nv);
    const actual=trace.slice(36*nb,36*nb+nv).map(bits);
    if(JSON.stringify(actual)!==JSON.stringify(row.expectedBits)){
      differences++;if(first.length<8)first.push({label:row.label,kind:row.kind,
        expected:row.expectedBits,actual});
    }
    for(const field of fields)assert.deepEqual(Array.from(data[field]),a[field],"RNE input mutated");
    if(control){
      let c=controlContexts.get(row.xml);
      if(!c){const model=control.MjModel.from_xml_string(row.xml);c={model,data:new control.MjData(model)};controlContexts.set(row.xml,c);}
      c.model.opt.enableflags=m.options.enableflags;c.model.opt.disableflags=m.options.disableflags;
      for(let j=0;j<3;j++)c.model.opt.gravity[j]=m.gravity[j];
      for(const field of fields)for(let j=0;j<a[field].length;j++)c.data[field][j]=a[field][j];
      for(let j=0;j<nv;j++){data.qacc[j]=(j%5-2)/(j+1);c.data.qacc[j]=data.qacc[j];}
      module.mj_rne(model,data,1,data.qfrc_bias);
      control.mj_rne(c.model,c.data,1,c.data.qfrc_bias);
      assert.deepEqual(Array.from(data.qfrc_bias,bits),Array.from(c.data.qfrc_bias,bits),"acceleration mode changed from retained control");
      accelerationControlMatches++;
    }
    counts[row.kind]++;layouts[row.layout]=(layouts[row.layout]??0)+1;
  }
}finally{
  for(const {model,data} of contexts.values()){data.delete();model.delete();}
  for(const {model,data} of controlContexts.values()){data.delete();model.delete();}
}
console.log(JSON.stringify({schema:"neural-workshop.marble-compiled-rne.v1",
  runtime:{jsPath:modulePath,jsSha256:sha(modulePath),wasmSha256:sha(resolve(dirname(modulePath),"mujoco.wasm"))},
  inputSha256:sha(inputPath),counts,layouts,differences,first,flagAcceleration:false,
  originalPrivateIntermediatesCaptured:false,
  accelerationControlMatches,accelerationControl:controlPath?{jsSha256:sha(controlPath),wasmSha256:sha(resolve(dirname(controlPath),"mujoco.wasm"))}:null}));
assert.equal(counts.captured,20);assert.equal(counts.synthetic,1000);
assert.equal(differences,0,"actual compiled complete RNE bias returns differ from original");
