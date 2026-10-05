import assert from "node:assert/strict";
import { Kind, fillTextRoundedAdvances, render } from "../shells/web/display-list.js";

function canvasFor(widths) {
  const calls = [];
  return {
    calls,
    measureText(glyph) { return {width: widths[glyph]}; },
    fillText(glyph,x,y) { calls.push({glyph,x,y}); },
  };
}

{
  const ctx = canvasFor({A:6.4,B:5.6});
  const width = fillTextRoundedAdvances(ctx,"AB",10,20,
    {align:"center",pixelScale:1.25});
  assert.equal(width,12); // 15 framebuffer pixels after the 1.25 transform
  assert.deepEqual(ctx.calls,[{glyph:"A",x:4,y:20},{glyph:"B",x:10.4,y:20}]);
}
{
  const ctx = canvasFor({A:6.4});
  fillTextRoundedAdvances(ctx,"AA",30,4,{align:"right",pixelScale:1.25});
  assert.deepEqual(ctx.calls,[{glyph:"A",x:17.2,y:4},{glyph:"A",x:23.6,y:4}]);
}
{
  const ctx = canvasFor({"😀":7.1,A:6.4});
  const width = fillTextRoundedAdvances(ctx,"😀A",0,0,{pixelScale:1});
  assert.equal(width,13);
  assert.deepEqual(ctx.calls.map(call=>call.glyph),["😀","A"]);
}
{
  const ctx = canvasFor({A:6.4,B:5.6});
  let transform = null;
  ctx.save = ctx.restore = ctx.translate = ctx.scale = () => {};
  ctx.setTransform = (...values) => { transform=values; };
  ctx.clearRect = () => { ctx.clearedWith=transform; };
  ctx.calls = [];
  ctx.fillStyle = "";
  ctx.textAlign = "";
  ctx.textBaseline = "";
  ctx.font = "";
  const originalFill = ctx.fillText;
  ctx.fillText = function(glyph,x,y) {
    this.calls.push({glyph,x,y,align:this.textAlign,font:this.font,transform});
    originalFill.call(this,glyph,x,y);
  };
  const strokes=[];
  ctx.strokeText=function(glyph,x,y){strokes.push({glyph,x,y,width:this.lineWidth});};
  render(ctx,[{kind:Kind.TEXT,a:456,b:300,c:12,d:0,color:0xffffffff,
    text:"AB",anchor:["center","middle"]}],{width:800,height:600,
    fontFamily:"Courier New",fontScale:4/3,roundGlyphAdvances:true,
    glyphStrokeRatio:0.05});
  assert.deepEqual(ctx.clearedWith,[1,0,0,1,0,0],
    "each frame must clear the complete backing store under identity transform");
  assert.ok(ctx.calls.every(call=>call.align==="left"),
    "per-glyph calls must be left aligned after whole-label centering");
  const scale=Math.min(800/912,600/684);
  const left=ctx.calls[0].x;
  const right=ctx.calls[1].x+Math.round(5.6);
  assert.ok(Math.abs(left+right-800)<1e-9,
    "center anchor must center the physical glyph run in the framebuffer");
  assert.deepEqual(ctx.calls[0].transform,[1,0,0,1,0,0],
    "Marble glyphs must rasterize at physical pixels without an outer scale");
  assert.match(ctx.calls[0].font,/^14\.0350[0-9]*px /,
    "font size must include the final reference-to-framebuffer scale");
  assert.equal(strokes.length,2);
  assert.ok(strokes.every(stroke=>Math.abs(stroke.width-14.0350877193*.05)<1e-9),
    "stroke compensation must scale with physical font size");
}
{
  const ctx = canvasFor({A:6.4});
  let transform = null;
  ctx.save = ctx.restore = ctx.translate = ctx.scale = () => {};
  ctx.setTransform = (...values) => { transform=values; };
  ctx.clearRect = () => {};
  ctx.calls = [];
  ctx.fillStyle = "";
  ctx.textAlign = "";
  ctx.textBaseline = "";
  ctx.font = "";
  ctx.fillText = function(glyph,x,y) { this.calls.push({glyph,x,y}); };
  render(ctx,[{kind:Kind.TEXT,a:456,b:25.08,c:12,d:0,color:0xffffffff,
    text:"A",anchor:["center","middle"]}],{width:800,height:600,
    roundGlyphAdvances:true,textOffsetY:cmd=>cmd.b<40?0:-2.5});
  const scale=Math.min(800/912,600/684);
  assert.ok(Math.abs(ctx.calls[0].y-(600-25.08*scale))<1e-9,
    "per-command vertical correction must reach physical pixel placement");
}
console.log("PASS: Marble text rounds glyph advances in framebuffer pixels");
