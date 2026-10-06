// Perspective Marble Maze renderer, ported from neural_workshop.ui.render3d.
// The tray frame remains y-up; the page now presents the same lit, shadowed,
// visibly tilting 3D object instead of replacing it with a plan view.

import { MARBLE } from "./marble-maze.js";

const MAX_HOLES = 96;
const SHADOW_SIZE = 1024;
const MSAA_SAMPLES = 4;
// Keep the numeric ids in lockstep with neural_workshop.ui.render3d.  BRASS
// is not currently selected by Marble Maze, but leaving it out makes this
// shared renderer observably different from the source material contract and
// turns a future collar/fixture draw into the wrong shader branch.
const MATERIAL = Object.freeze({ OAK: 0, STAIN: 1, STEEL: 2, PIT: 3, CUP: 4, BRASS: 5 });
const PINE = [0.80, 0.63, 0.41];
const WALNUT = [0.29, 0.18, 0.11];
const STEEL = [0.86, 0.88, 0.93];
const SAWN = [0.58, 0.44, 0.31];
const GREEN = [0.16, 0.55, 0.30];
const HOLE_WALL_CLEARANCE = MARBLE.RADIUS * 0.80;
const CUP_COLLAR_SCALE = 1.34;

// The generated opening clears walls, but the decorative green annulus is
// wider than that opening and used to disappear beneath nearby wall strips.
// Trim only the collar, retaining the gameplay hole radius and wall clearance.
export function marbleCupCollarOuterRadius(board, hole) {
  let nearestWall = Number.POSITIVE_INFINITY;
  for (const wall of board.walls) {
    const dx = Math.max(wall.x0 - hole.x, 0, hole.x - wall.x1);
    const dy = Math.max(wall.y0 - hole.y, 0, hole.y - wall.y1);
    nearestWall = Math.min(nearestWall, Math.hypot(dx, dy));
  }
  const available = Math.min(hole.radius * CUP_COLLAR_SCALE,
    nearestWall - HOLE_WALL_CLEARANCE);
  return available > hole.radius ? available : null;
}
// The native MarbleMaze replaces Light.span for each tray during on_draw;
// render() below applies that same board-scaled half-extent to the shadow-map
// orthographic box.
const LIGHT = Object.freeze({ direction: [-0.38,0.86,0.34], colour: [1.0,0.97,0.90], sky: [0.76,0.81,0.90], ground: [0.42,0.30,0.19], span: 0.30 });

const VERTEX_SHADER = `#version 300 es
precision highp float;
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
uniform mat4 uViewProj;
uniform mat4 uModel;
uniform vec3 uNormalScale;
uniform mat4 uLightMatrix;
out vec3 vWorld;
out vec3 vNormal;
out vec3 vLocal;
out vec4 vShadow;
void main(){
  vec4 world=uModel*vec4(position,1.0);
  vWorld=world.xyz; vNormal=mat3(uModel)*(normal*uNormalScale); vLocal=position;
  vShadow=uLightMatrix*world; gl_Position=uViewProj*world;
}`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;
precision highp int;
in vec3 vWorld; in vec3 vNormal; in vec3 vLocal; in vec4 vShadow;
uniform int uMaterial; uniform vec3 uTint; uniform vec3 uEye;
uniform vec3 uLightDir; uniform vec3 uLightColour; uniform vec3 uSkyColour; uniform vec3 uGroundColour;
uniform sampler2D uShadowMap; uniform float uShadowTexel; uniform int uShadows;
uniform sampler2D uMarbleColour; uniform sampler2D uMarbleRough; uniform sampler2D uMarbleNormal;
uniform int uMarbleMaps; uniform mat4 uModel;
uniform int uHoleCount; uniform vec4 uHoles[96]; uniform int uCutHoles; uniform float uGrainSeed;
out vec4 frag;
float hash3(vec3 p){return fract(sin(dot(p,vec3(17.13,91.7,47.31)))*43758.5453);}
float noise3(vec3 p){
  vec3 i=floor(p),f=fract(p); f=f*f*(3.0-2.0*f);
  float n000=hash3(i),n100=hash3(i+vec3(1,0,0)),n010=hash3(i+vec3(0,1,0)),n110=hash3(i+vec3(1,1,0));
  float n001=hash3(i+vec3(0,0,1)),n101=hash3(i+vec3(1,0,1)),n011=hash3(i+vec3(0,1,1)),n111=hash3(i+vec3(1,1,1));
  return mix(mix(mix(n000,n100,f.x),mix(n010,n110,f.x),f.y),mix(mix(n001,n101,f.x),mix(n011,n111,f.x),f.y),f.z);
}
float fbm(vec3 p){return 0.5*noise3(p)+0.25*noise3(p*2.03)+0.155*noise3(p*4.01)+0.075*noise3(p*8.05);}
vec3 timber(vec3 base,vec3 dark){
  vec3 p=vLocal; vec2 about=vec2(p.x+0.16+uGrainSeed*0.05,p.y+0.19);
  float ring=length(about)*190.0+9.0*fbm(p*vec3(4.0,4.0,1.6))+2.2*fbm(p*vec3(17.0,17.0,6.0));
  float band=fract(ring),grain=smoothstep(0.24,0.44,band)*(1.0-smoothstep(0.52,0.80,band));
  float fibre=fbm(p*vec3(380.0,380.0,30.0))-0.5,blotch=fbm(p*vec3(9.0,9.0,3.5))-0.5;
  return clamp(mix(base,dark,clamp(grain*0.52+blotch*0.24+0.09,0.0,1.0))*(1.0+fibre*0.12),0.0,1.0);
}
float shadowed(vec3 n,vec3 l){
  if(uShadows==0||vShadow.w<=0.0)return 1.0;
  vec3 c=vShadow.xyz/vShadow.w;
  if(c.x<0.0||c.x>1.0||c.y<0.0||c.y>1.0||c.z>1.0)return 1.0;
  float slope=clamp(1.0-dot(n,l),0.0,1.0),bias=0.0009+0.0042*slope*slope,lit=0.0;
  for(int j=-1;j<=1;++j)for(int i=-1;i<=1;++i){
    float nearest=texture(uShadowMap,c.xy+vec2(float(i),float(j))*uShadowTexel).r;
    lit+=(c.z-bias<=nearest)?1.0:0.0;
  }
  return lit/9.0;
}
vec3 environment(vec3 dir){
  float up=dir.y;
  vec3 above=mix(uSkyColour*0.28,uSkyColour*0.78,clamp(up*1.8,0.0,1.0));
  vec3 below=uGroundColour*(0.20+0.58*clamp(-up*2.4,0.0,1.0));
  return mix(below,above,smoothstep(-0.035,0.035,up));
}
void main(){
  float coverage=1.0;
  if(uCutHoles==1){
    float edge=1e9;
    for(int i=0;i<96;++i){if(i>=uHoleCount)break;edge=min(edge,length(vLocal.xz-uHoles[i].xy)-uHoles[i].z);}
    float fade=max(fwidth(edge),1e-6);coverage=clamp(edge/fade+0.5,0.0,1.0);if(coverage<=0.0)discard;
  }
  vec3 n=normalize(vNormal),view=normalize(uEye-vWorld);if(!gl_FrontFacing)n=-n;
  vec3 l=normalize(uLightDir),halfWay=normalize(l+view);
  float ndl=max(dot(n,l),0.0),lit=shadowed(n,l);vec3 ambient=mix(uGroundColour,uSkyColour,n.y*0.5+0.5);
  vec3 albedo=uTint;float gloss=24.0,specStrength=0.10,ambientStrength=0.42;
  if(uMaterial==0){albedo=timber(uTint,uTint*vec3(0.55,0.44,0.34));gloss=40.0;specStrength=0.16;}
  else if(uMaterial==1){albedo=timber(uTint,uTint*vec3(0.42,0.36,0.32));gloss=28.0;specStrength=0.11;}
  else if(uMaterial==4){gloss=60.0;specStrength=0.22;ambientStrength=0.5;}
  else if(uMaterial==5){gloss=96.0;specStrength=0.55;ambientStrength=0.35;}
  else if(uMaterial==3){
    float depth=clamp(1.0+vLocal.y*26.0,0.0,1.0),side=max(dot(n,l),0.0);
    vec3 wall=uTint*(0.05+0.10*ambient+0.92*side)*depth*depth;frag=vec4(clamp(wall,0.0,1.0),coverage);return;
  } else if(uMaterial==2){
    vec3 ball=normalize(vLocal),bumped=n,shine=uTint;float polish=1.0;
    if(uMarbleMaps==1){
      vec2 uv=vec2(atan(ball.z,ball.x)*0.1591549+0.5,acos(clamp(ball.y,-1.0,1.0))*0.3183099);
      float grain=dot(texture(uMarbleColour,uv).rgb,vec3(0.299,0.587,0.114));shine=uTint*(0.70+0.88*grain);
      polish=1.0-texture(uMarbleRough,uv).g;
      vec3 across=normalize(vec3(-ball.z,0.0,ball.x)+vec3(1e-6,0.0,0.0)),down=cross(ball,across);
      vec3 bump=texture(uMarbleNormal,uv).xyz*2.0-1.0,local=normalize(across*bump.x+down*bump.y+ball*bump.z);
      bumped=normalize(mat3(uModel)*mix(ball,local,0.22));
    }else{float mottle=fbm(vLocal*640.0)-0.5;shine=uTint*(1.0+mottle*0.22);}
    vec3 bounce=reflect(-view,bumped),mirrored=environment(bounce);
    float tight=mix(26.0,190.0,polish),lamp=pow(max(dot(bounce,l),0.0),tight),sheen=pow(max(dot(bounce,l),0.0),9.0);
    float fresnel=0.05+0.95*pow(1.0-max(dot(bumped,view),0.0),5.0);
    vec3 colour=shine*mirrored*(0.34+0.66*lit)+uLightColour*lamp*(1.4+1.4*polish)*lit+uLightColour*sheen*0.14*lit+uSkyColour*fresnel*0.16;
    frag=vec4(clamp(colour,0.0,1.0),coverage);return;
  }
  float spec=pow(max(dot(n,halfWay),0.0),gloss)*specStrength;
  vec3 colour=albedo*(ambient*ambientStrength+uLightColour*ndl*lit*0.85)+uLightColour*spec*lit;
  frag=vec4(clamp(colour,0.0,1.0),coverage);
}`;

const DEPTH_VERTEX_SHADER = `#version 300 es
precision highp float;
layout(location=0) in vec3 position;
uniform mat4 uLightClip; uniform mat4 uModel;
out vec3 vLocal;
void main(){vLocal=position;gl_Position=uLightClip*uModel*vec4(position,1.0);}`;
const DEPTH_FRAGMENT_SHADER = `#version 300 es
precision highp float; precision highp int;
in vec3 vLocal; uniform int uHoleCount; uniform vec4 uHoles[96]; uniform int uCutHoles;
void main(){if(uCutHoles==1)for(int i=0;i<96;++i){if(i>=uHoleCount)break;if(length(vLocal.xz-uHoles[i].xy)<uHoles[i].z)discard;}}`;

const COMPOSITE_VERTEX_SHADER = `#version 300 es
precision highp float;
layout(location=0) in vec2 position;
out vec2 vUv;
void main(){vUv=position*0.5+0.5;gl_Position=vec4(position,0.0,1.0);}`;
const COMPOSITE_FRAGMENT_SHADER = `#version 300 es
precision highp float;
in vec2 vUv; uniform sampler2D uScene; out vec4 frag;
void main(){frag=texture(uScene,vUv);}`;

function identity(){return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);}
function multiply(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o;}
function translation(x,y,z){const o=identity();o[12]=x;o[13]=y;o[14]=z;return o;}
function rotateX(a){const c=Math.cos(a),s=Math.sin(a);return new Float32Array([1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1]);}
function rotateZ(a){const c=Math.cos(a),s=Math.sin(a);return new Float32Array([c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1]);}
function quaternionMatrix(w,x,y,z){
  const xx=x*x,yy=y*y,zz=z*z,xy=x*y,xz=x*z,yz=y*z,wx=w*x,wy=w*y,wz=w*z;
  const m=new Float32Array([1-2*(yy+zz),2*(xy+wz),2*(xz-wy),0,2*(xy-wz),1-2*(xx+zz),2*(yz+wx),0,2*(xz+wy),2*(yz-wx),1-2*(xx+yy),0,0,0,0,1]);
  const o=new Float32Array(16);for(let r=0;r<4;r++)for(let c=0;c<4;c++)o[c*4+r]=m[r*4+c];return o;
}
function normalize(v){const n=Math.hypot(v[0],v[1],v[2])||1;return[v[0]/n,v[1]/n,v[2]/n];}
function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
function cross(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
function lookAt(eye,target,up){
  const z=normalize([eye[0]-target[0],eye[1]-target[1],eye[2]-target[2]]),x=normalize(cross(up,z)),y=cross(z,x);
  return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);
}
function perspective(aspect,near,far,fovDegrees){const f=1/Math.tan(fovDegrees*Math.PI/360),nf=1/(near-far);return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*nf,-1,0,0,2*far*near*nf,0]);}
function orthographic(span,near,far){const nf=1/(near-far);return new Float32Array([1/span,0,0,0,0,1/span,0,0,0,0,2*nf,0,0,0,(far+near)*nf,1]);}
function makeLightMatrices(span){
  const eye=LIGHT.direction.map(v=>v*span*2.2),up=Math.abs(LIGHT.direction[1])>0.98?[0,0,1]:[0,1,0];
  const clip=multiply(orthographic(span,0.01,span*5),lookAt(eye,[0,0,0],up));
  const bias=new Float32Array([0.5,0,0,0,0,0.5,0,0,0,0,0.5,0,0.5,0.5,0.5,1]);
  return{clip,texture:multiply(bias,clip)};
}
function makeCamera(board,aspect){
  const elevation=47*Math.PI/180,fov=36*Math.PI/180,halfV=Math.tan(fov/2),halfH=halfV*Math.max(aspect,0.35);
  const spanX=board.width*0.5*1.30,spanZ=board.depth*0.5*1.30*Math.sin(elevation);
  const distance=Math.max(spanX/halfH,spanZ/halfV)+board.depth*0.25,eye=[0,Math.sin(elevation)*distance,Math.cos(elevation)*distance];
  return{eye,viewProj:multiply(perspective(aspect,0.02,12,36),lookAt(eye,[0,0,0],[0,1,0]))};
}

// Pyglet's pixel_size() is already in drawing-surface pixels, including on
// Retina displays. Match _stage_rect() in that coordinate space: floor the
// source proportions and 8-pixel verdict-band clearance against the actual
// framebuffer dimensions. Flooring in CSS/logical pixels first drifts by one
// pixel for some scaled viewport sizes. Keep this pure so the native source
// rectangle is testable without creating a WebGL context.
export function marbleStageRect(width, height) {
  const pixelWidth = Math.max(1, Math.trunc(width));
  const pixelHeight = Math.max(1, Math.trunc(height));
  const bottomMargin = Math.trunc(58 * pixelHeight / 684);
  const bandCeiling = pixelHeight - Math.trunc(pixelHeight * 0.75);
  const bottom = Math.max(bottomMargin, bandCeiling + 8);
  const top = Math.trunc(pixelHeight - 88 * pixelHeight / 684);
  const stageHeight = Math.max(48, top - bottom);
  return {
    x: Math.trunc(pixelWidth * 0.03),
    bottom,
    width: Math.trunc(pixelWidth * 0.94),
    top,
    height: stageHeight,
  };
}

class Builder{
  constructor(){this.positions=[];this.normals=[];this.indices=[];}
  face(points,normal){const base=this.positions.length/3;for(const p of points){this.positions.push(...p);this.normals.push(...normal);}this.indices.push(base,base+1,base+2,base,base+2,base+3);}
  box(x0,y0,z0,x1,y1,z1){
    this.face([[x0,y1,z1],[x1,y1,z1],[x1,y1,z0],[x0,y1,z0]],[0,1,0]);this.face([[x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1]],[0,-1,0]);
    this.face([[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]],[0,0,1]);this.face([[x1,y0,z0],[x0,y0,z0],[x0,y1,z0],[x1,y1,z0]],[0,0,-1]);
    this.face([[x1,y0,z1],[x1,y0,z0],[x1,y1,z0],[x1,y1,z1]],[1,0,0]);this.face([[x0,y0,z0],[x0,y0,z1],[x0,y1,z1],[x0,y1,z0]],[-1,0,0]);
  }
  tube(cx,cz,radius,top,bottom,segments=22,floorDisc=true){
    const base=this.positions.length/3;
    for(let i=0;i<segments;i++){const a=2*Math.PI*i/segments,nx=Math.cos(a),nz=Math.sin(a),x=cx+nx*radius,z=cz+nz*radius;this.positions.push(x,top,z,x,bottom,z);this.normals.push(-nx,0,-nz,-nx,0,-nz);}
    for(let i=0;i<segments;i++){const a=base+i*2,b=base+((i+1)%segments)*2;this.indices.push(a,b,b+1,a,b+1,a+1);}
    if(floorDisc){const centre=this.positions.length/3;this.positions.push(cx,bottom,cz);this.normals.push(0,1,0);const rim=this.positions.length/3;
      for(let i=0;i<segments;i++){const a=2*Math.PI*i/segments;this.positions.push(cx+Math.cos(a)*radius,bottom,cz+Math.sin(a)*radius);this.normals.push(0,1,0);}
      for(let i=0;i<segments;i++)this.indices.push(centre,rim+i,rim+(i+1)%segments);}
  }
  ring(cx,cz,inner,outer,y,segments=30){const base=this.positions.length/3;
    for(let i=0;i<segments;i++){const a=2*Math.PI*i/segments,c=Math.cos(a),s=Math.sin(a);this.positions.push(cx+c*inner,y,cz+s*inner,cx+c*outer,y,cz+s*outer);this.normals.push(0,1,0,0,1,0);}
    for(let i=0;i<segments;i++){const a=base+i*2,b=base+((i+1)%segments)*2;this.indices.push(a,a+1,b+1,a,b+1,b);}}
  sphere(radius,rings=26,segments=34){const base=this.positions.length/3;
    for(let ring=0;ring<=rings;ring++){const phi=Math.PI*ring/rings,y=Math.cos(phi),r=Math.sin(phi);for(let step=0;step<=segments;step++){const theta=2*Math.PI*step/segments,nx=r*Math.cos(theta),nz=r*Math.sin(theta);this.positions.push(nx*radius,y*radius,nz*radius);this.normals.push(nx,y,nz);}}
    for(let ring=0;ring<rings;ring++)for(let step=0;step<segments;step++){const a=base+ring*(segments+1)+step,b=a+segments+1;this.indices.push(a,b,b+1,a,b+1,a+1);}}
}

function compile(gl,type,source){const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)){const e=gl.getShaderInfoLog(shader);gl.deleteShader(shader);throw new Error(`Marble Maze shader compile failed: ${e}`);}return shader;}
function makeProgram(gl,vs,fs){const p=gl.createProgram(),v=compile(gl,gl.VERTEX_SHADER,vs),f=compile(gl,gl.FRAGMENT_SHADER,fs);gl.attachShader(p,v);gl.attachShader(p,f);gl.linkProgram(p);gl.deleteShader(v);gl.deleteShader(f);if(!gl.getProgramParameter(p,gl.LINK_STATUS)){const e=gl.getProgramInfoLog(p);gl.deleteProgram(p);throw new Error(`Marble Maze shader link failed: ${e}`);}return p;}
function uploadMesh(gl,b){if(!b.indices.length)return null;const vao=gl.createVertexArray();gl.bindVertexArray(vao);
  const pos=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,pos);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(b.positions),gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.FLOAT,false,0,0);
  const norm=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,norm);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(b.normals),gl.STATIC_DRAW);gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,3,gl.FLOAT,false,0,0);
  const elements=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,elements);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(b.indices),gl.STATIC_DRAW);gl.bindVertexArray(null);return{vao,pos,norm,elements,count:b.indices.length};}
function deleteMesh(gl,m){if(!m)return;gl.deleteBuffer(m.pos);gl.deleteBuffer(m.norm);gl.deleteBuffer(m.elements);gl.deleteVertexArray(m.vao);}

export class MarbleMazeRenderer{
  constructor(){
    this.canvas=document.createElement("canvas");
    this.contextLost=false;
    this.resourcesInvalid=false;
    this.onContextLost=null;
    this.onContextRestored=null;
    this.onTexturesSettled=null;
    this._contextLostHandler=(event)=>{
      event.preventDefault();
      this.contextLost=true;
      this.resourcesInvalid=true;
      if(this.onContextLost)this.onContextLost(event);
    };
    this._contextRestoredHandler=()=>{
      this.contextLost=false;
      if(this.onContextRestored)this.onContextRestored();
    };
    // Initialize every ownership slot before any WebGL call. Construction
    // can fail while a shader, shadow target, or resolve target is only
    // partially allocated; keeping null slots makes the catch path below
    // able to dispose that prefix without guessing which stage completed.
    this.gl=null;this.colourProgram=null;this.depthProgram=null;this.compositeProgram=null;
    this.dynamicMeshes=[];this.meshes=null;this.board=null;this.holes=[];this.marbleTextures=[];
    this.captureCamera=null;
    this.marbleMapsLoaded=0;this.marbleMapsSettled=0;this.texturesSettled=false;this.marbleMapsFailed=false;this.ballMesh=null;
    this.colourFbo=null;this.colourColourRb=null;this.colourDepthRb=null;this.resolveFbo=null;this.resolveTexture=null;this.resolveSize=[0,0];this.sampleCount=0;
    this.shadowTexture=null;this.shadowFbo=null;this.compositeScene=null;this.compositeVao=null;this.compositeBuffer=null;
    this.canvas.addEventListener("webglcontextlost",this._contextLostHandler,false);
    this.canvas.addEventListener("webglcontextrestored",this._contextRestoredHandler,false);
    try{
      // The native renderer owns a four-sample offscreen target and resolves
      // it explicitly. Do not also request an implementation-defined default
      // framebuffer MSAA target: that would make edge coverage depend on the
      // browser/GPU pair and would apply a second, different resolve.
      this.gl=this.canvas.getContext("webgl2",{alpha:true,antialias:false,depth:true,premultipliedAlpha:false,preserveDrawingBuffer:true});
      if(!this.gl)throw new Error("WebGL 2 is required for the original Marble Maze 3D view");
      const gl=this.gl;this.colourProgram=makeProgram(gl,VERTEX_SHADER,FRAGMENT_SHADER);this.depthProgram=makeProgram(gl,DEPTH_VERTEX_SHADER,DEPTH_FRAGMENT_SHADER);this.compositeProgram=makeProgram(gl,COMPOSITE_VERTEX_SHADER,COMPOSITE_FRAGMENT_SHADER);
      this.compositeScene=gl.getUniformLocation(this.compositeProgram,"uScene");
      this.compositeVao=gl.createVertexArray();this.compositeBuffer=gl.createBuffer();
      gl.bindVertexArray(this.compositeVao);gl.bindBuffer(gl.ARRAY_BUFFER,this.compositeBuffer);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,1,1,-1,-1,1,1,-1,1]),gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);gl.bindVertexArray(null);
      this._createShadowTarget();this._loadMarbleMaps();this._cacheUniforms();
    }catch(error){
      // A renderer that never became usable still owns every resource
      // allocated before the failure. Dispose that prefix before reporting
      // the capability error to the shell; otherwise repeated task opens can
      // leak shader/texture/framebuffer handles while showing the fallback.
      this.dispose();
      throw error;
    }
  }
  _cacheUniforms(){const gl=this.gl;this.colourUniforms=Object.fromEntries(["uViewProj","uModel","uNormalScale","uLightMatrix","uMaterial","uTint","uEye","uLightDir","uLightColour","uSkyColour","uGroundColour","uShadowMap","uShadowTexel","uShadows","uMarbleColour","uMarbleRough","uMarbleNormal","uMarbleMaps","uHoleCount","uHoles","uCutHoles","uGrainSeed"].map(n=>[n,gl.getUniformLocation(this.colourProgram,n)]));
    this.depthUniforms=Object.fromEntries(["uLightClip","uModel","uHoleCount","uHoles","uCutHoles"].map(n=>[n,gl.getUniformLocation(this.depthProgram,n)]));}
  _createShadowTarget(){const gl=this.gl;this.shadowTexture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.shadowTexture);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.DEPTH_COMPONENT24,SHADOW_SIZE,SHADOW_SIZE,0,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    this.shadowFbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowFbo);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,this.shadowTexture,0);gl.drawBuffers([gl.NONE]);gl.readBuffer(gl.NONE);
    if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw new Error("Marble Maze shadow framebuffer is incomplete");gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.bindTexture(gl.TEXTURE_2D,null);}
  _dropColourTarget(){const gl=this.gl;if(!gl)return;
    if(this.colourFbo)gl.deleteFramebuffer(this.colourFbo);if(this.colourColourRb)gl.deleteRenderbuffer(this.colourColourRb);if(this.colourDepthRb)gl.deleteRenderbuffer(this.colourDepthRb);
    if(this.resolveFbo)gl.deleteFramebuffer(this.resolveFbo);if(this.resolveTexture)gl.deleteTexture(this.resolveTexture);
    this.colourFbo=null;this.colourColourRb=null;this.colourDepthRb=null;this.resolveFbo=null;this.resolveTexture=null;this.resolveSize=[0,0];this.sampleCount=0;}
  _ensureColourTarget(width,height){const gl=this.gl;if(this.resolveSize[0]===width&&this.resolveSize[1]===height)return;
    this._dropColourTarget();
    try{
      this.colourFbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,this.colourFbo);
      this.colourColourRb=gl.createRenderbuffer();gl.bindRenderbuffer(gl.RENDERBUFFER,this.colourColourRb);
      gl.renderbufferStorageMultisample(gl.RENDERBUFFER,MSAA_SAMPLES,gl.RGBA8,width,height);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.RENDERBUFFER,this.colourColourRb);
      this.colourDepthRb=gl.createRenderbuffer();gl.bindRenderbuffer(gl.RENDERBUFFER,this.colourDepthRb);
      gl.renderbufferStorageMultisample(gl.RENDERBUFFER,MSAA_SAMPLES,gl.DEPTH_COMPONENT24,width,height);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.RENDERBUFFER,this.colourDepthRb);
      gl.bindRenderbuffer(gl.RENDERBUFFER,this.colourColourRb);
      const colourSampleCount=gl.getRenderbufferParameter(gl.RENDERBUFFER,gl.RENDERBUFFER_SAMPLES);
      gl.bindRenderbuffer(gl.RENDERBUFFER,this.colourDepthRb);
      const depthSampleCount=gl.getRenderbufferParameter(gl.RENDERBUFFER,gl.RENDERBUFFER_SAMPLES);
      if(colourSampleCount!==MSAA_SAMPLES||depthSampleCount!==MSAA_SAMPLES)throw new Error(`Marble Maze requires ${MSAA_SAMPLES}x MSAA (colour=${colourSampleCount}, depth=${depthSampleCount})`);
      this.sampleCount=colourSampleCount;
      if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw new Error("Marble Maze multisample framebuffer is incomplete");
      this.resolveFbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,this.resolveFbo);
      this.resolveTexture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.resolveTexture);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,width,height,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,this.resolveTexture,0);
      if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw new Error("Marble Maze resolve framebuffer is incomplete");
      this.resolveSize=[width,height];
    }catch(error){this._dropColourTarget();throw error;}
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.bindRenderbuffer(gl.RENDERBUFFER,null);gl.bindTexture(gl.TEXTURE_2D,null);}
  _loadMarbleMaps(){const gl=this.gl;this.marbleTextures=["marble_colour.png","marble_rough.png","marble_normal.png"].map(name=>{
    const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
    // Keep the placeholder complete while the preloaded image crosses the
    // browser event loop. The native renderer has all maps before its first
    // colour pass; a complete neutral texture avoids a transient black
    // sampler result when the browser is still decoding a cached PNG.
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([128,128,128,255]));
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    const settle=()=>{this.marbleMapsSettled++;if(this.marbleMapsSettled===3){this.texturesSettled=true;if(this.onTexturesSettled)this.onTexturesSettled();}};
    const image=new Image();image.decoding="async";image.fetchPriority="high";image.onload=()=>{
      if(!this.gl||this.resourcesInvalid||gl.isContextLost()){settle();return;}
      let uploaded=false;
      try{
        gl.bindTexture(gl.TEXTURE_2D,texture);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
        gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.NONE);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
        gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,gl.RGBA,gl.UNSIGNED_BYTE,image);
        gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
        gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
        uploaded=true;
      }catch(error){this.marbleMapsFailed=true;}
      finally{
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);
        gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.BROWSER_DEFAULT_WEBGL);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
        gl.bindTexture(gl.TEXTURE_2D,null);
      }
      if(uploaded)this.marbleMapsLoaded++;
      settle();
    };image.onerror=()=>{this.marbleMapsFailed=true;settle();};
    image.src=new URL(`../../res/marblemaze/${name}`,import.meta.url).href;return texture;});}
  setBoard(board,grainSeed=0){if(this.board===board){this.grainSeed=Number(grainSeed);return;}const gl=this.gl;for(const m of this.dynamicMeshes)deleteMesh(gl,m);this.dynamicMeshes=[];this.board=board;
    const halfW=board.width/2,halfD=board.depth/2,wx=x=>x-halfW,wz=y=>halfD-y;
    const body=new Builder();body.box(-halfW,-0.013,-halfD,halfW,0,halfD);
    const frame=new Builder(),rail=0.016,railHigh=Math.max(0.020,board.height*1.25),slab=0.013;
    frame.box(-halfW-rail,-slab,-halfD-rail,halfW+rail,railHigh,-halfD);frame.box(-halfW-rail,-slab,halfD,halfW+rail,railHigh,halfD+rail);frame.box(-halfW-rail,-slab,-halfD,-halfW,railHigh,halfD);frame.box(halfW,-slab,-halfD,halfW+rail,railHigh,halfD);
    const walls=new Builder();for(const w of board.walls)walls.box(wx(w.x0),0,wz(w.y1),wx(w.x1),board.height,wz(w.y0));
    const pits=new Builder(),cups=new Builder(),collar=new Builder();for(const h of board.holes){(h.home?cups:pits).tube(wx(h.x),wz(h.y),h.radius,0,-0.032);if(h.home){const outer=marbleCupCollarOuterRadius(board,h);if(outer!==null)collar.ring(wx(h.x),wz(h.y),h.radius,outer,0.0006);}}
    const ball=new Builder();ball.sphere(0.0075);this.meshes={body:uploadMesh(gl,body),frame:uploadMesh(gl,frame),walls:uploadMesh(gl,walls),pits:uploadMesh(gl,pits),cups:uploadMesh(gl,cups),collar:uploadMesh(gl,collar)};
    if(!this.ballMesh)this.ballMesh=uploadMesh(gl,ball);for(const m of Object.values(this.meshes))if(m)this.dynamicMeshes.push(m);
    this.holes=board.holes.slice(0,MAX_HOLES).map(h=>[wx(h.x),wz(h.y),h.radius,h.home?1:0]);
    this.grainSeed=Number(grainSeed);
  }
  _draw(mesh,model,material,tint,cut=false,pass="colour",normalScale=[1,1,1]){
    if(!mesh)return;const gl=this.gl,u=pass==="depth"?this.depthUniforms:this.colourUniforms,p=pass==="depth"?this.depthProgram:this.colourProgram;
    gl.useProgram(p);gl.uniformMatrix4fv(u.uModel,false,model);
    if(pass==="depth")gl.uniform1i(u.uCutHoles,cut?1:0);
    else{gl.uniform3fv(u.uNormalScale,normalScale);gl.uniform1i(u.uMaterial,material);gl.uniform3fv(u.uTint,tint);gl.uniform1i(u.uCutHoles,cut?1:0);}
    gl.bindVertexArray(mesh.vao);gl.drawElements(gl.TRIANGLES,mesh.count,gl.UNSIGNED_INT,0);
  }
  _drawScene(game,frame,pass){const m=this.meshes;
    this._draw(m.body,frame,MATERIAL.OAK,PINE,true,pass);this._draw(m.frame,frame,MATERIAL.OAK,PINE,false,pass);this._draw(m.walls,frame,MATERIAL.STAIN,WALNUT,false,pass);
    if(pass!=="depth"){this._draw(m.pits,frame,MATERIAL.PIT,SAWN,false,pass);this._draw(m.cups,frame,MATERIAL.PIT,[0.24,0.44,0.29],false,pass);this._draw(m.collar,frame,MATERIAL.CUP,GREEN,false,pass);}
    if(!game)return;const b=this.board,halfW=b.width/2,halfD=b.depth/2;
    for(const marble of game.marbles){if(marble.state==="home"||marble.state==="lost")continue;
      const spin=quaternionMatrix(marble.qw,-marble.qx,-marble.qz,marble.qy),model=multiply(multiply(frame,translation(marble.x-halfW,marble.z,halfD-marble.y)),spin);
      this._draw(this.ballMesh,model,MATERIAL.STEEL,STEEL,false,pass);}
  }
  _restoreState(width,height,dark){const gl=this.gl;if(!gl)return;
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.bindRenderbuffer(gl.RENDERBUFFER,null);
    for(let unit=3;unit>=0;unit--){gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,null);}
    gl.activeTexture(gl.TEXTURE0);gl.useProgram(null);gl.bindVertexArray(null);gl.depthMask(true);gl.disable(gl.SCISSOR_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.disable(gl.SAMPLE_ALPHA_TO_COVERAGE);gl.disable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);gl.viewport(0,0,width,height);const clearBackground=dark?0:1;gl.clearColor(clearBackground,clearBackground,clearBackground,1);
  }
  render(game,{width,height,logicalWidth=null,logicalHeight=null,dark=false,shadows=true,grainSeed=0}={}){
    if(!game?.board||this.contextLost||!this.gl||this.gl.isContextLost())return null;this.setBoard(game.board,grainSeed);const gl=this.gl;
    if(this.canvas.width!==width||this.canvas.height!==height){this.canvas.width=width;this.canvas.height=height;}
    // Match MarbleMaze._stage_rect in the framebuffer's pixel coordinate space.
    const stage=marbleStageRect(width,height);
    const {x:left,bottom, width:viewWidth, top, height:viewHeight}=stage;
    this.viewport={x:left,y:height-top,width:viewWidth,height:viewHeight};
    try{
      this._ensureColourTarget(viewWidth,viewHeight);
      const camera=makeCamera(this.board,viewWidth/viewHeight),frame=multiply(rotateX(game.pitch),rotateZ(-game.roll)),light=makeLightMatrices(Math.max(this.board.width,this.board.depth)*0.78);
      this.captureCamera={eye:Array.from(camera.eye),viewProj:Array.from(camera.viewProj),aspect:viewWidth/viewHeight};
      const holeData=new Float32Array(MAX_HOLES*4);this.holes.forEach((v,i)=>holeData.set(v,i*4));
      gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowFbo);gl.viewport(0,0,SHADOW_SIZE,SHADOW_SIZE);gl.clearDepth(1);gl.clear(gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LESS);gl.disable(gl.BLEND);gl.disable(gl.CULL_FACE);
      if(shadows){const u=this.depthUniforms;gl.useProgram(this.depthProgram);gl.uniformMatrix4fv(u.uLightClip,false,light.clip);gl.uniform1i(u.uHoleCount,this.holes.length);gl.uniform4fv(u.uHoles,holeData);this._drawScene(game,frame,"depth");}
      // Clear the browser's default target only as the destination canvas
      // hygiene pass. The scene itself is rendered into the explicit target
      // below, whose dimensions equal the native stage rectangle.
      gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.disable(gl.SCISSOR_TEST);gl.viewport(0,0,width,height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      gl.bindFramebuffer(gl.FRAMEBUFFER,this.colourFbo);gl.viewport(0,0,viewWidth,viewHeight);
      const bg=dark?[0.055,0.055,0.065]:[0.90,0.905,0.925];gl.clearColor(bg[0],bg[1],bg[2],1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      // This is the native Stage._colour_pass: explicit four-sample storage,
      // no blending, and alpha-to-coverage for the fractional hole rim.
      // Set depth state here as well as in the shadow pass. Shadows are an
      // option, so a no-shadow frame follows a previous frame's cleanup with
      // depth testing disabled; relying on the shadow pass made overlapping
      // walls/marbles draw in submission order whenever shadows were off.
      gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LESS);gl.disable(gl.CULL_FACE);
      gl.disable(gl.BLEND);gl.enable(gl.SAMPLE_ALPHA_TO_COVERAGE);const u=this.colourUniforms;gl.useProgram(this.colourProgram);
      gl.uniformMatrix4fv(u.uViewProj,false,camera.viewProj);gl.uniformMatrix4fv(u.uLightMatrix,false,light.texture);gl.uniform3fv(u.uEye,camera.eye);gl.uniform3fv(u.uLightDir,LIGHT.direction);gl.uniform3fv(u.uLightColour,LIGHT.colour);gl.uniform3fv(u.uSkyColour,LIGHT.sky);gl.uniform3fv(u.uGroundColour,LIGHT.ground);
      gl.uniform1f(u.uShadowTexel,1/SHADOW_SIZE);gl.uniform1i(u.uShadows,shadows?1:0);gl.uniform1i(u.uHoleCount,this.holes.length);gl.uniform4fv(u.uHoles,holeData);gl.uniform1f(u.uGrainSeed,this.grainSeed);
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,this.shadowTexture);gl.uniform1i(u.uShadowMap,0);
      const mapUniforms=[u.uMarbleColour,u.uMarbleRough,u.uMarbleNormal];for(let i=0;i<3;i++){gl.activeTexture(gl.TEXTURE1+i);gl.bindTexture(gl.TEXTURE_2D,this.marbleTextures[i]);gl.uniform1i(mapUniforms[i],i+1);}
      gl.uniform1i(u.uMarbleMaps,this.marbleMapsLoaded===3&&!this.marbleMapsFailed?1:0);this._drawScene(game,frame,"colour");
      // Resolve exactly once, then composite the resolved texture into the
      // stage rectangle just as the native renderer does. Keeping the resolve
      // texture makes the browser path's filtering and edge treatment explicit
      // instead of inheriting them from drawImage or a browser canvas policy.
      gl.bindFramebuffer(gl.READ_FRAMEBUFFER,this.colourFbo);gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER,this.resolveFbo);
      gl.blitFramebuffer(0,0,viewWidth,viewHeight,0,0,viewWidth,viewHeight,gl.COLOR_BUFFER_BIT,gl.NEAREST);
      // The native Stage._blit disables depth before drawing the resolved
      // full-screen quad.  The colour pass necessarily leaves depth testing
      // enabled, but the compositor is not scene geometry and must not be
      // rejected by whatever depth value the destination framebuffer holds.
      gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);
      gl.viewport(left,bottom,viewWidth,viewHeight);gl.useProgram(this.compositeProgram);
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,this.resolveTexture);gl.uniform1i(this.compositeScene,0);
      gl.bindVertexArray(this.compositeVao);gl.drawArrays(gl.TRIANGLES,0,6);
      return this.canvas;
    }finally{this._restoreState(width,height,dark);}
  }
  dispose(){
    const gl=this.gl;
    if(this.canvas){
      this.canvas.removeEventListener("webglcontextlost",this._contextLostHandler,false);
      this.canvas.removeEventListener("webglcontextrestored",this._contextRestoredHandler,false);
    }
    this.onContextLost=null;this.onContextRestored=null;this.onTexturesSettled=null;
    if(!gl)return;
    // Once a context has been lost, every pre-loss handle is invalid even if
    // the browser has already restored the context. Calling delete* on those
    // stale names produces INVALID_OPERATION warnings and cannot reclaim the
    // old context's resources; let the browser discard them and only clear our
    // JavaScript references.
    const canDelete=!this.resourcesInvalid&&!gl.isContextLost();
    if(canDelete){
      for(const m of this.dynamicMeshes)deleteMesh(gl,m);deleteMesh(gl,this.ballMesh);
      this._dropColourTarget();for(const t of this.marbleTextures)if(t)gl.deleteTexture(t);
      if(this.shadowTexture)gl.deleteTexture(this.shadowTexture);if(this.shadowFbo)gl.deleteFramebuffer(this.shadowFbo);
      if(this.colourProgram)gl.deleteProgram(this.colourProgram);if(this.depthProgram)gl.deleteProgram(this.depthProgram);if(this.compositeProgram)gl.deleteProgram(this.compositeProgram);
      if(this.compositeBuffer)gl.deleteBuffer(this.compositeBuffer);if(this.compositeVao)gl.deleteVertexArray(this.compositeVao);
    }
    this.dynamicMeshes=[];this.ballMesh=null;this.colourFbo=null;this.colourColourRb=null;this.colourDepthRb=null;this.resolveFbo=null;this.resolveTexture=null;this.resolveSize=[0,0];this.marbleTextures=[];this.shadowTexture=null;this.shadowFbo=null;this.colourProgram=null;this.depthProgram=null;this.compositeProgram=null;this.compositeBuffer=null;this.compositeVao=null;this.gl=null;}
}
