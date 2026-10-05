import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { MarbleMazeRenderer, marbleStageRect } from "../shells/web/marble-maze-renderer.js";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const rendererPath = path.resolve(testDirectory, "../shells/web/marble-maze-renderer.js");
const marbleModulePath = path.resolve(testDirectory, "../shells/web/marble-maze.js");
const shellPath = path.resolve(testDirectory, "../shells/web/index.html");
const rendererSource = fs.readFileSync(rendererPath, "utf8");
const marbleModuleSource = fs.readFileSync(marbleModulePath, "utf8");
const shellSource = fs.readFileSync(shellPath, "utf8");
const marbleFrameStart = shellSource.indexOf("function drawMarbleMazeFrame(");
const marbleFrameEnd = shellSource.indexOf("let monkeyTimer", marbleFrameStart);
assert.ok(marbleFrameStart >= 0 && marbleFrameEnd > marbleFrameStart,
  "Marble browser host must expose a complete frame compositor");
const marbleFrameSource = shellSource.slice(marbleFrameStart, marbleFrameEnd);
const marbleSceneSource = fs.readFileSync(
  path.resolve(testDirectory, "../src/scene_marblemaze.elisa"), "utf8");
const sourceCapturePath = path.resolve(testDirectory, "marble_source_capture.py");
const sourceCaptureSource = fs.readFileSync(sourceCapturePath, "utf8");

assert.match(marbleSceneSource, /sview\("Marble Maze", 0, -1\)/,
  "Marble Elisa scene must own the source title rather than a host duplicate");
assert.match(marbleSceneSource, /put_text\(list, paint, bytes_view\(status\)/,
  "Marble Elisa scene must own the source status text");
assert.match(shellSource,
  /function drawMarbleMaze\(\) \{\s+const game = marbleGame;[\s\S]*?if \(game\) \{\s*drawMarbleMazeFrame\(game\);/,
  "Marble browser host must composite the 3D frame without repainting the source title");
assert.match(shellSource,
  /ctx\.save\(\);\s*ctx\.setTransform\(1, 0, 0, 1, 0, 0\);\s*ctx\.drawImage\(image, x, y, width, height, x, y, width, height\);\s*ctx\.restore\(\);/,
  "Marble framebuffer-pixel composite must bypass display-list scale and Y-flip transforms");
assert.match(shellSource,
  /const params = marbleDebugHooks \? new URLSearchParams\(location\.search\) : null;[\s\S]*?marble-test-canvas-width[\s\S]*?marble-test-canvas-height[\s\S]*?fixedTestSize[\s\S]*?const height = fixedTestSize/,
  "only Marble debug-hook captures may override the logical canvas size");
assert.ok(
  marbleFrameSource.indexOf("ctx.drawImage(image, x, y, width, height, x, y, width, height)") >= 0 &&
  marbleFrameSource.indexOf("marbleText(marbleStatusText(), REFERENCE_WIDTH / 2,") >
    marbleFrameSource.indexOf("ctx.drawImage(image, x, y, width, height, x, y, width, height)"),
  "WebGL Marble frames must paint live physics status after compositing the stage");
assert.match(marbleFrameSource,
  /if \(phase === MARBLE_PHASE\.feedback\) \{\s+const verdict = Number\(state\[MARBLE_INFO\.verdict\]\);\s+marbleText\(marbleStatusText\(\), REFERENCE_WIDTH \/ 2, 60, 17,\s+verdict === 1 \? "#40ff40" : "#ff4040", "center", false,\s+"middle", "system-ui, sans-serif", 1\);/,
  "WebGL Marble feedback must paint source verdict text, typography, and outcome color below the stage");
assert.ok(shellSource.includes(`fontFamily = '"Courier New", monospace'`) &&
  shellSource.includes("${size * MARBLE_TEXT_SCALE * scale}px ${fontFamily}"),
  "Marble text overlay must allow the proportional default face used by source verdict labels");
assert.match(shellSource,
  /const glyphStrokeWidth = fontFamily\.includes\("Courier New"\)[\s\S]*?marbleGlyphStrokeRatio\(dark\(\) !== 0\)/,
  "live Marble overlays must use the measured theme-specific text weight");
assert.doesNotMatch(shellSource,
  /marbleText\("Marble Maze", REFERENCE_WIDTH \/ 2/,
  "Marble title must not be overdrawn by a host-side duplicate");
assert.match(shellSource,
  /const runPhase = marbleInfo\(MARBLE_INFO\.phase\);\s+const runVerdict = marbleInfo\(MARBLE_INFO\.verdict\);\s+marbleReferenceTransform\(\);\s+marbleText\(marbleStatusText\(\), REFERENCE_WIDTH \/ 2, REFERENCE_HEIGHT - 62,/,
  "live Marble status must be drawn in reference space over the static placeholder scene");
assert.match(shellSource, /marble-test-roll.*MARBLE\.MAX_TILT/s,
  "test-only static Marble roll captures must be explicitly bounded");
assert.match(shellSource, /marble-test-pitch.*MARBLE\.MAX_TILT/s,
  "test-only static Marble pitch captures must be explicitly bounded");
assert.match(shellSource,
  /testQuery\.has\("marble-test-state"\)[\s\S]*?numericMarbleFields[\s\S]*?\["rolling", "won", "lost", "done"\][\s\S]*?snapshot\.marbles\.length !== marbleGame\.marbles\.length[\s\S]*?numericMarbleFields\.some/,
  "render-state injection must validate phase/outcome, finite physics fields, and board marble count");
assert.match(shellSource,
  /marble-test-advance-timeout[\s\S]*?Number\(values\[MARBLE_INFO\.trial\]\) === 1/,
  "multi-trial render replay must inject its timeout fixture only on the first generated tray");
assert.match(shellSource,
  /if \(marbleTestAdvanceTimeout\) \{[\s\S]*?MARBLE_ACTION\.score[\s\S]*?recordMarbleResult\(apiReadState\(handle\)\)/,
  "multi-trial timeout replay must commit score and result before the real Space-next action");
assert.match(shellSource,
  /advanceMarbleController\(marbleTestSnapshot\.elapsedMs \/ 1000\)/,
  "rolling capture must synchronize controller time with the injected source pose");
assert.match(shellSource,
  /advanceMarbleControllerToElapsed\(marbleGame\.elapsed\)/,
  "active Marble controller time must follow the authoritative cumulative physics clock");
assert.match(shellSource,
  /function advanceMarbleControllerToElapsed\(elapsedSeconds\)[\s\S]*?Math\.floor\(elapsedMs \+ 1e-9\)[\s\S]*?MARBLE_INFO\.elapsedMs[\s\S]*?targetWholeMs - controllerElapsedMs/,
  "active Marble clock synchronization must preserve source boundaries despite floating-point noise");
assert.match(shellSource,
  /marbleTestSnapshot\.phase !== "rolling"[\s\S]*?MARBLE_ACTION\.syncSettleTime[\s\S]*?MARBLE_ACTION\.report[\s\S]*?recordMarbleResult[\s\S]*?MARBLE_ACTION\.next/,
  "terminal capture replay must use controller settle/report/result/next transitions");
assert.match(sourceCaptureSource,
  /--outcome[\s\S]*?terminal_state = "home" if args\.outcome in \("won", "done"\)[\s\S]*?task\.update\(1\.0 \/ 60\.0\)[\s\S]*?task\._next_trial\(\)/,
  "source terminal captures must use the official update and next-trial paths");
assert.match(shellSource,
  /wx, wy, wz, qw, qx, qy, qz,[\s\S]*?wx, wy, wz, qw, qx, qy, qz,/,
  "Marble capture diagnostics must expose angular velocity and the rolling quaternion");
assert.match(sourceCaptureSource,
  /--move[\s\S]*?action="append"[\s\S]*?--move-frames[\s\S]*?task\.held\.update\(args\.move\)[\s\S]*?task\.update\(1\.0 \/ 60\.0\)/,
  "source screenshot capture must replay concurrent held axes for a deterministic rolling pose");
assert.match(sourceCaptureSource,
  /"inputReplay": \([\s\S]*?"held": sorted\(set\(args\.move\)\)[\s\S]*?"heldFrames": args\.move_frames/,
  "source screenshot manifest must declare the exact held-key replay used to reach its pose");
assert.match(sourceCaptureSource,
  /--release-frames[\s\S]*?task\.held\.clear\(\)[\s\S]*?range\(args\.release_frames\)[\s\S]*?task\.update\(1\.0 \/ 60\.0\)/,
  "source interaction fixture must advance after the real held input has been released");
assert.match(sourceCaptureSource,
  /--move-stage[\s\S]*?parse_move_stages\(args\.move_stage\)[\s\S]*?task\.held\.clear\(\)[\s\S]*?task\.held\.update\(stage\["held"\]\)[\s\S]*?range\(stage\["frames"\]\)[\s\S]*?task\.update\(1\.0 \/ 60\.0\)/,
  "source screenshot fixture must replay ordered held-key and neutral stages frame by frame");
assert.match(sourceCaptureSource,
  /"inputReplay": \([\s\S]*?\{"stages": move_stages\}/,
  "source screenshot manifest must preserve the full staged input schedule");
assert.match(sourceCaptureSource,
  /--restart-after-move[\s\S]*?task\.restart\(\)[\s\S]*?range\(args\.post_restart_frames\)[\s\S]*?task\.update\(1\.0 \/ 60\.0\)/,
  "source interaction fixture must exercise the real restart path and post-restart frames");
assert.match(sourceCaptureSource,
  /def float32_abi_value\(value: float\)[\s\S]*?struct\.unpack\("=f", struct\.pack\("=f", float\(value\)\)\)/,
  "interaction parity fixture must round geometry with the actual Float32 ABI encoding");
assert.match(sourceCaptureSource,
  /--board-abi-f32[\s\S]*?task\.tray = float32_abi_tray\(task\.tray\)[\s\S]*?task\.sim = marble_source\.Simulation\(task\.tray\)[\s\S]*?grain_seed = task\.stage\.grain_seed[\s\S]*?task\._build_scene\(\)[\s\S]*?task\.stage\.grain_seed = grain_seed[\s\S]*?"boardGeometryPrecision": "wasm-f32-roundtrip"/,
  "Float32 interaction fixtures must rebuild source physics/rendering without changing the board RNG identity");
assert.match(shellSource,
  /if \(marbleTestFreezeClock\) \{\s+Object\.defineProperty\(window\.__nw, "marbleTestStepFixedFrame"/,
  "fixed-frame replay control must be hidden unless the explicit frozen test clock is active");
assert.match(shellSource,
  /function marbleTick\(now, generation, forcedTestDt = null\)[\s\S]*?forcedTestDt !== null \? forcedTestDt/,
  "deterministic replay must override only the test tick delta, leaving live RAF timing intact");
assert.match(shellSource,
  /function marbleTestStepFixedFrame\(\)[\s\S]*?cancelAnimationFrame\(marbleFrameHandle\)[\s\S]*?marbleTick\(performance\.now\(\), marbleLifecycleGeneration, 1 \/ 60\)[\s\S]*?cancelAnimationFrame\(marbleFrameHandle\)/,
  "a replay frame must cancel live RAFs around exactly one source-sized physics/controller tick");
assert.match(sourceCaptureSource,
  /--outcome.*next-trial[\s\S]*?feedback_deadline = task\.until[\s\S]*?task\.update\(0\.0\)[\s\S]*?task\.trial != 2/,
  "source multi-trial capture must use the timeout feedback deadline and create tray two through update()");
assert.match(sourceCaptureSource,
  /--theme.*choices=\("light", "dark"\)[\s\S]*?state\.cfg\.BLACK_BACKGROUND = args\.theme == "dark"[\s\S]*?"theme": args\.theme/,
  "source screenshot capture must set and attest the requested UI theme");
assert.match(sourceCaptureSource,
  /window\.switch_to\(\)[\s\S]*?clear_colour = 0\.0 if args\.theme == "dark" else 1\.0[\s\S]*?gl\.glClearColor\(clear_colour, clear_colour, clear_colour, 1\.0\)/,
  "source screenshot capture must initialize the window clear colour for its requested theme");
assert.match(sourceCaptureSource,
  /"points": list\(geometry\.point_size\(\)\)[\s\S]*?"layoutPixels": list\(geometry\.pixel_size\(\)\)[\s\S]*?"framebuffer": \[int\(width\), int\(height\)\][\s\S]*?"scale": float\(window\.scale\)/,
  "source capture manifest must distinguish points, layout pixels, framebuffer pixels, and scale");

assert.match(shellSource, /CORE_WASM_LOAD_TIMEOUT_MS = 15000/,
  "web shell core loading must have a bounded timeout");
assert.match(shellSource, /core-wasm-timeout-ms/,
  "core-load timeout override must be available only through the test hook");
assert.match(shellSource, /coreWasmLoadTimeoutMs/,
  "web shell must use the selected bounded core-load timeout");
assert.match(shellSource, /new AbortController\(\)/,
  "web shell core loading must abort a stalled fetch when supported");
assert.match(shellSource, /WASM core load timed out after \$\{coreWasmLoadTimeoutMs\}ms/,
  "web shell must report a core-load timeout instead of remaining at loading");
assert.match(shellSource, /if \(location\.protocol === "file:"\)/,
  "web shell must distinguish file-URL setup errors from served HTTP failures");
assert.match(shellSource, /if \(coreWasmTimer !== null\) clearTimeout\(coreWasmTimer\)/,
  "web shell core-load timeout must be cleared after success or failure");
assert.match(shellSource, /const MARBLE_MAX_SETTLE_MS = 600050;/,
  "Marble host must allow the source's final 50 ms settlement overshoot");
assert.match(shellSource,
  /const settleMs = Math\.max\(0, Math\.min\(MARBLE_MAX_SETTLE_MS,/,
  "physical Marble settlement must preserve the bounded overshoot");

function assertRect(actual, expected, label) {
  assert.deepEqual(actual, expected, `${label} stage rectangle`);
}

// The default native window is 912x684 logical pixels.  These values are the
// exact _stage_rect result used by the original Python renderer.
assertRect(marbleStageRect(912, 684),
  { x: 27, bottom: 179, width: 857, top: 596, height: 417 },
  "standard-DPI");

// Exercise the same framebuffer geometry when a DPR-1 browser has a standard
// 912x684 CSS canvas, and at the source window's 640x480-point minimum on a
// Retina display (1280x960 drawing-surface pixels).
assertRect(marbleStageRect(1280, 960),
  { x: 38, bottom: 248, width: 1203, top: 836, height: 588 },
  "source-minimum-retina-framebuffer");
assertRect(marbleStageRect(760, 570),
  { x: 22, bottom: 151, width: 714, top: 496, height: 345 },
  "responsive-DPR-1-canvas");

// Pyglet lays out in drawing-surface pixels, so the browser must match its
// floor operations against the Retina framebuffer rather than CSS pixels.
assertRect(marbleStageRect(1604, 1203, 2),
  { x: 48, bottom: 309, width: 1507, top: 1048, height: 739 },
  "Retina-DPI");
assertRect(marbleStageRect(1520, 1140),
  { x: 45, bottom: 293, width: 1428, top: 993, height: 700 },
  "height-constrained-retina");

assertRect(marbleStageRect(1604, 1203, 0),
  { x: 48, bottom: 309, width: 1507, top: 1048, height: 739 },
  "invalid-DPI-fallback");

assert.match(rendererSource, /getContext\("webgl2",\{alpha:true,antialias:false/,
  "Marble renderer must request WebGL2 without implementation-defined default MSAA");
assert.match(rendererSource, /webglcontextlost/,
  "Marble renderer must listen for WebGL context loss");
assert.match(rendererSource, /webglcontextrestored/,
  "Marble renderer must listen for WebGL context restoration");
assert.match(rendererSource, /event\.preventDefault\(\)/,
  "Marble renderer must allow the browser to restore a lost context");
assert.match(rendererSource, /this\.contextLost\|\|!this\.gl\|\|this\.gl\.isContextLost\(\)/,
  "Marble renderer must avoid issuing draw calls while the context is lost");
assert.match(rendererSource, /resourcesInvalid/,
  "Marble renderer must invalidate pre-loss handles for safe disposal");
assert.match(rendererSource, /catch\(error\)\{\s*\/\/ A renderer that never became usable/, 
  "Marble renderer construction must dispose partially allocated resources");
assert.match(rendererSource, /this\.dispose\(\);\s*throw error;/,
  "Marble renderer construction must report failures only after partial cleanup");
assert.match(rendererSource, /this\.shadowTexture=null;this\.shadowFbo=null/,
  "Marble renderer must initialize WebGL ownership slots before construction");
assert.match(rendererSource, /image\.decoding="async"/,
  "Marble map loads must use the browser's asynchronous decode path explicitly");
assert.match(rendererSource, /onTexturesSettled/,
  "Marble renderer must expose completion of the asynchronous map batch");
assert.match(rendererSource, /this\.texturesSettled=true/,
  "Marble renderer must record when every map has loaded or failed");
assert.match(rendererSource, /texParameteri\(gl\.TEXTURE_2D,gl\.TEXTURE_MIN_FILTER,gl\.LINEAR\)/,
  "Marble map placeholders must remain complete before their image upload");
assert.match(rendererSource, /!this\.gl\|\|this\.resourcesInvalid\|\|gl\.isContextLost\(\)/,
  "Marble texture uploads must not use pre-loss handles after restoration");
assert.match(rendererSource, /const canDelete=!this\.resourcesInvalid&&!gl\.isContextLost\(\)/,
  "Marble renderer must not delete stale WebGL handles after context loss");
assert.match(rendererSource, /renderbufferStorageMultisample\(gl\.RENDERBUFFER,MSAA_SAMPLES,gl\.RGBA8/,
  "Marble renderer must use explicit four-sample RGBA8 storage");
assert.match(rendererSource, /renderbufferStorageMultisample\(gl\.RENDERBUFFER,MSAA_SAMPLES,gl\.DEPTH_COMPONENT24/,
  "Marble renderer must use explicit four-sample depth storage");
assert.match(rendererSource,
  /getRenderbufferParameter\(gl\.RENDERBUFFER,gl\.RENDERBUFFER_SAMPLES\)[\s\S]*?colourSampleCount!==MSAA_SAMPLES\|\|depthSampleCount!==MSAA_SAMPLES[\s\S]*?this\.sampleCount=colourSampleCount/,
  "Marble renderer must measure and enforce actual four-sample colour/depth storage");
assert.match(rendererSource, /ground:\s*\[0\.42,0\.30,0\.19\], span:\s*0\.30/,
  "Marble renderer must retain the source Light default");
assert.match(rendererSource, /BRASS:\s*5/,
  "Marble renderer must retain the source BRASS material id");
assert.match(rendererSource, /uMaterial==5\)\{gloss=96\.0;specStrength=0\.55;ambientStrength=0\.35;\}/,
  "Marble renderer must retain the source BRASS shader branch");
assert.match(rendererSource, /_draw\(mesh,model,material,tint,cut=false,pass="colour",normalScale=\[1,1,1\]\)/,
  "Marble draw calls must retain the source normal-scale contract");
assert.match(rendererSource, /uniform3fv\(u\.uNormalScale,normalScale\)/,
  "Marble colour draws must upload the source normal scale");
assert.match(rendererSource, /makeLightMatrices\(Math\.max\(this\.board\.width,this\.board\.depth\)\*0\.78\)/,
  "Marble renderer must apply the source's board-scaled shadow span");
assert.match(rendererSource,
  /if\(!game\)return;const b=this\.board,halfW=b\.width\/2,halfD=b\.depth\/2;\s*for\(const marble of game\.marbles\)/,
  "Marble renderer must submit live marbles to both colour and depth passes so they cast contact shadows");
assert.match(rendererSource, /blitFramebuffer\(0,0,viewWidth,viewHeight,0,0,viewWidth,viewHeight,gl\.COLOR_BUFFER_BIT,gl\.NEAREST\)/,
  "Marble renderer must resolve the multisample target exactly once");
assert.match(rendererSource, /bindFramebuffer\(gl\.FRAMEBUFFER,null\);gl\.disable\(gl\.DEPTH_TEST\);gl\.disable\(gl\.BLEND\);\s+gl\.viewport\(left,bottom,viewWidth,viewHeight\);gl\.useProgram\(this\.compositeProgram\)/,
  "Marble compositor must disable scene depth and blending before the full-screen resolve draw");
assert.match(rendererSource, /gl\.enable\(gl\.DEPTH_TEST\);gl\.depthFunc\(gl\.LESS\);gl\.disable\(gl\.CULL_FACE\);\n\s+gl\.disable\(gl\.BLEND\);gl\.enable\(gl\.SAMPLE_ALPHA_TO_COVERAGE\)/,
  "Marble colour pass must restore depth and alpha-to-coverage state");
assert.match(rendererSource, /marbleStageRect\(width,height\)/,
  "Marble renderer must lay out the native stage in framebuffer-pixel coordinates");
assert.match(rendererSource, /if\(this\.board===board\)\{this\.grainSeed=Number\(grainSeed\);return;\}/,
  "Marble renderer must refresh the grain input even when a board object is reused");
assert.match(rendererSource, /this\.captureCamera=\{eye:Array\.from\(camera\.eye\),viewProj:Array\.from\(camera\.viewProj\),aspect:viewWidth\/viewHeight\}/,
  "Marble renderer capture diagnostics must record the camera actually used to draw");
assert.match(rendererSource, /gl\.depthMask\(true\);gl\.disable\(gl\.SCISSOR_TEST\)/,
  "Marble renderer must restore the depth write mask after compositing");
assert.match(rendererSource, /gl\.enable\(gl\.BLEND\);gl\.blendFunc\(gl\.SRC_ALPHA,gl\.ONE_MINUS_SRC_ALPHA\)/,
  "Marble renderer must restore the native source-over blend state for UI");
assert.match(rendererSource, /gl\.disable\(gl\.CULL_FACE\);gl\.viewport\(0,0,width,height\);const clearBackground=dark\?0:1;gl\.clearColor\(clearBackground,clearBackground,clearBackground,1\)/,
  "Marble renderer must restore the full framebuffer viewport and theme clear colour");
assert.match(rendererSource, /texImage2D\(gl\.TEXTURE_2D,0,gl\.RGBA8,gl\.RGBA,gl\.UNSIGNED_BYTE,image\)/,
  "Marble texture uploads must use the source renderer's explicit RGBA8 format");
assert.match(rendererSource, /gl\.pixelStorei\(gl\.UNPACK_FLIP_Y_WEBGL,false\);\s*gl\.pixelStorei\(gl\.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl\.BROWSER_DEFAULT_WEBGL\)/,
  "Marble texture uploads must restore WebGL unpack state after asynchronous upload");
assert.match(rendererSource, /_restoreState\(width,height,dark\)/,
  "Marble renderer must centralize the native post-render state restoration");
assert.match(rendererSource, /try\{[\s\S]*return this\.canvas;\n    \}finally\{this\._restoreState\(width,height,dark\);\}/,
  "Marble renderer must restore the WebGL state even when a render pass throws");
assert.equal(
  (rendererSource.match(/this\._drawScene\(game,frame,"colour"\);/g) ?? []).length,
  1,
  "Marble renderer must submit the native colour pass exactly once per frame",
);

const marbleKeyStart = shellSource.lastIndexOf("    if (isMarbleTask()) {");
const marbleKeyEnd = shellSource.indexOf("    if (isCountTask()) {", marbleKeyStart);
assert.ok(marbleKeyStart >= 0 && marbleKeyEnd > marbleKeyStart,
  "Marble keyboard handler must remain discoverable in the browser shell");
const marbleKeyBlock = shellSource.slice(marbleKeyStart, marbleKeyEnd);
assert.match(marbleKeyBlock, /if \(key === API_KEY\.space &&/,
  "Marble result reset must be gated on Space");
assert.doesNotMatch(marbleKeyBlock, /if \(key === API_KEY\.enter &&/,
  "ignored Enter must not reset Marble run statistics");
const launchStart = shellSource.indexOf("function launchTask()");
const launchEnd = shellSource.indexOf("function setScreen(next)", launchStart);
assert.ok(launchStart >= 0 && launchEnd > launchStart,
  "Marble launch lifecycle must remain discoverable in the browser shell");
const launchBlock = shellSource.slice(launchStart, launchEnd);
assert.match(launchBlock,
  /if \(isMarbleTask\(\)\) \{\s*destroyMarbleRun\(\);\s*ensureMarbleRun\(\);\s*\}/,
  "Marble task launch must create only the READY controller");
assert.doesNotMatch(launchBlock,
  /if \(isMarbleTask\(\)\) \{[\s\S]*?ensureMarbleBoard\(\)/,
  "Marble launch must not deal or build a tray before Space");
assert.match(shellSource,
  /if \(phase === MARBLE_PHASE\.preparing \|\| phase === MARBLE_PHASE\.running\) \{\s*ensureMarbleBoard\(\);/,
  "Marble Space start must lazily complete the board handshake for both first and later trays");
assert.match(shellSource, /if \(!game\) \{\s*if \(phase === MARBLE_PHASE\.ready\) return "Press Space to start";/,
  "Marble READY rendering must not require a prematurely constructed game");
const applyOptionsStart = shellSource.indexOf("function applyMarbleOptions()");
const applyOptionsEnd = shellSource.indexOf("function cancelMarbleOptions()", applyOptionsStart);
assert.ok(applyOptionsStart >= 0 && applyOptionsEnd > applyOptionsStart,
  "Marble options apply lifecycle must remain discoverable in the browser shell");
const applyOptionsBlock = shellSource.slice(applyOptionsStart, applyOptionsEnd);
assert.doesNotMatch(applyOptionsBlock,
  /if \(returnTo === "task"[\s\S]*?ensureMarbleBoard\(\)/,
  "Marble options apply must return to READY without eagerly rebuilding a tray");
assert.match(shellSource, /function apiApplyMarbleOptions\(handle, options\)/,
  "Marble options apply must have a controller-level reset entry point");
assert.match(applyOptionsBlock, /apiApplyMarbleOptions\(marbleRunHandle, nextOptions\)/,
  "Marble options apply must update the live controller in place");
assert.match(applyOptionsBlock, /clearMarbleGame\(\);\s*resetMarbleRunStats\(\);/,
  "Marble options apply must dispose host physics without destroying the controller RNG");
assert.doesNotMatch(applyOptionsBlock, /destroyMarbleRun\(\);/,
  "Marble options apply must not recreate the controller and rewind its RNG");
assert.match(shellSource, /async function toggleMarbleFullscreen\(\)/,
  "Marble must retain the native F11 fullscreen action when the browser delivers it");
assert.match(shellSource, /event\.key === "F11"/,
  "Marble keyboard handling must recognize the native F11 shortcut");
assert.match(shellSource, /document\.documentElement\.requestFullscreen\(\)/,
  "Marble fullscreen must use the guarded browser Fullscreen API");
assert.match(shellSource, /document\.addEventListener\("fullscreenchange"/,
  "Marble fullscreen changes must refit and redraw the stage");
assert.match(shellSource, /function ensureMarbleRenderer\(\)/,
  "Marble renderer must be created on demand for a live task");
assert.match(shellSource, /function marbleRendererState\(\)/,
  "Marble renderer diagnostics must expose an explicit capability state");
assert.match(shellSource, /rendererNote = marbleGame \? ` · renderer \$\{marbleRendererState\(\)\}`/,
  "Marble status must identify the active 3D renderer or its fallback");
assert.match(shellSource, /rendererError: marbleRendererError \|\| null/,
  "Marble debug diagnostics must retain the renderer failure cause");
for (const expression of [
  "board: marbleGame?.board ? {", "width: marbleGame.board.width,",
  "walls: marbleGame.board.walls.map", "holes: marbleGame.board.holes.map",
  "starts: marbleGame.board.starts.map", "home: { ...marbleGame.board.home }",
]) {
  assert.ok(shellSource.includes(expression),
    `Marble debug capture must expose generated geometry expression: ${expression}`);
}
assert.match(shellSource, /renderer\.onTexturesSettled = \(\) =>/,
  "Marble shell must redraw when asynchronous material loading settles");
assert.match(shellSource, /function disposeMarbleRenderer\(\)/,
  "Marble renderer must have an explicit task-exit disposal path");
assert.match(shellSource, /let marblePhysicsCleanup = null/,
  "Marble shell must retain a failed native cleanup owner for retry");
assert.match(shellSource, /pendingPhysicsCleanup: marblePhysicsCleanup !== null/,
  "Marble diagnostics must expose pending native cleanup without leaking the object");
assert.match(shellSource, /cannot replace a MuJoCo engine after cleanup failed/,
  "Marble shell must not allocate a replacement engine over a failed cleanup");
assert.match(shellSource, /marbleRendererRecovery/,
  "Marble shell must retain a lost renderer until restoration or task exit");
assert.match(shellSource, /Marble Maze 3D renderer recovery failed/,
  "Marble shell must report renderer recovery failure");
assert.match(shellSource, /marble-test-hooks/,
  "Marble renderer integration hooks must be opt-in and query-gated");
assert.match(shellSource,
  /const marbleTestFreezeClock = marbleDebugHooks &&[\s\S]*?marble-test-freeze-clock/,
  "deterministic Marble capture clock must only be enabled by test hooks");
assert.match(shellSource, /const dt = forcedTestDt !== null \? forcedTestDt : marbleTestFreezeClock \? 0/,
  "frozen capture clock must stop both controller and physics simulation time");
assert.match(shellSource, /testClockFrozen: marbleTestFreezeClock/,
  "Marble capture diagnostics must expose whether the test clock is frozen");
assert.match(shellSource, /function applyMarbleTestOptionOverrides\(options\)/,
  "Marble lifecycle acceptance options must have an explicit test-only override helper");
assert.match(shellSource, /wrapMarbleOptionNote\(marbleOptionNote\(\), 96\)/,
  "Marble options notes must wrap inside the native menu panel width");
assert.match(shellSource, /marbleText\(line, REFERENCE_WIDTH \/ 2, 240 - index \* 12, 10/,
  "Marble options notes must leave the native footer clear at every rung");
assert.match(shellSource, /if \(!marbleDebugHooks\) return options;/,
  "Marble test option overrides must not affect ordinary production URLs");
assert.match(shellSource, /marble-test-trials/,
  "Marble headed lifecycle tests must be able to select a deterministic trial count");
assert.match(shellSource, /marble-test-adaptive/,
  "Marble headed lifecycle tests must be able to select adaptation explicitly");
assert.match(shellSource, /Object\.defineProperty\(window\.__nw, "marbleRunStats"/,
  "Marble test hooks must expose the opt-in result ledger");
assert.match(shellSource, /resourceStats: typeof globalThis\.__NW_MARBLE_MUJOCO_RESOURCE_STATS__ === "function"/,
  "Marble headed lifecycle tests must expose native resource counts behind the test hook");
assert.match(shellSource, /controllerElapsedMs/,
  "Marble result records must retain the common-controller clock");
assert.match(shellSource, /grainSeed: marbleRunHandle === 0n \? null :[\s\S]*?nw_api_v1_marble_grain_seed/,
  "Marble capture diagnostics must expose the actual grain seed");
assert.match(shellSource, /camera: marbleRenderer\.captureCamera/,
  "Marble capture diagnostics must expose the last rendered camera trace");
assert.match(shellSource, /materialState: marbleRenderer\.texturesSettled/,
  "Marble capture diagnostics must expose material-map settlement");
assert.match(shellSource, /timedOut/,
  "Marble result records must distinguish timeout from verdict");
assert.match(shellSource, /scoreWin: controllerScoreWin === 1/,
  "Marble result records must preserve the controller's source score() rule");
assert.match(shellSource, /homeMarbles: marbleRunStats\.homeMarbles/,
  "Marble result records must retain the source home-marble aggregate");
assert.match(shellSource, /seconds: marbleRunStats\.seconds/,
  "Marble result records must retain the source elapsed-seconds aggregate");
assert.match(shellSource, /best_rung: marbleRunStats\.bestRung/,
  "Marble result records must expose source score() field names");
assert.match(shellSource, /Math\.trunc\(marbleRunStats\.results\.reduce\(/,
  "Marble elapsed-second scoring must truncate the complete run total");
assert.match(shellSource, /result-store\.js/,
  "browser results must use the shared transactional result store");
assert.match(shellSource, /id="results-export"/,
  "browser results must expose an explicit export action");
assert.match(shellSource, /id="results-import"/,
  "browser results must expose an explicit import action");
assert.match(shellSource, /upsertResultRecord\(marbleResultRecord\(\)\)/,
  "Marble must upsert one durable record per run rather than append on redraw");
assert.match(shellSource, /marbleRunStats\.persistence = "unavailable"/,
  "Marble must surface storage denial instead of claiming persistence");
assert.match(shellSource, /marbleFeedbackKind\(game, verdict, boardSeconds\)/,
  "Marble feedback must use the shared source-order outcome classifier");
assert.match(marbleModuleSource, /if \(!game\?\.settled && Number\(game\?\.elapsed\) >= Number\(boardSeconds\)\)/,
  "Marble feedback must honor physical settlement before the timeout clock");
assert.match(shellSource, /logicalWidth: fittedLogicalWidth, logicalHeight: fittedLogicalHeight/,
  "Marble renderer must receive the fitted logical canvas dimensions");
assert.match(shellSource, /function destroyMarbleRun\(\)/,
  "Marble task lifecycle must retain an explicit controller disposal path");
assert.match(shellSource, /let marbleFeedbackLastWallMs = null/,
  "Marble feedback must retain the source wall-clock deadline separately");
assert.match(shellSource,
  /const feedbackDeltaMs = marbleTestFreezeFeedback\s*\? 0 : Math\.max\(0, now - marbleFeedbackLastWallMs\)/,
  "Marble feedback must use wall-clock time except for the explicit frozen capture hook");
assert.match(shellSource, /marbleFeedbackLastWallMs = null;\s*\n  marbleClockRemainderMs = 0/,
  "Marble feedback deadline must be cleared with the host lifecycle");
assert.match(shellSource, /window\.addEventListener\("blur", \(\) => \{\n  releaseMarbleInput\(\);/,
  "Marble must release held input when the window loses focus");
assert.match(shellSource, /document\.addEventListener\("visibilitychange", \(\) => \{\n  if \(document\.hidden\) releaseMarbleInput\(\);/,
  "Marble must release held input when the document becomes hidden");
assert.match(shellSource, /MuJoCo WASM unavailable; using the Marble Maze fallback solver/,
  "MuJoCo load rejection must be labeled as fallback physics");
assert.match(shellSource, /id="marble-retry"/,
  "MuJoCo load rejection must expose a dedicated retry control");
assert.match(shellSource, /async function retryMarblePhysics\(\)/,
  "Marble physics retry must be an explicit asynchronous operation");
assert.match(shellSource, /function marblePhysicsRunActive\(\)/,
  "Marble physics retry must distinguish a READY controller from active physics");
assert.match(shellSource, /return Number\(apiReadState\(marbleRunHandle\)\[MARBLE_INFO\.phase\]\) !== MARBLE_PHASE\.ready/,
  "Marble physics retry must remain blocked after the board-less READY interval");
assert.match(shellSource, /marblePhysicsRunActive\(\)\) return;/,
  "Marble physics retry must not hot-swap an active simulation");
assert.match(shellSource, /Object\.defineProperty\(window\.__nw, "marblePhysicsEngine"/,
  "Marble engine diagnostics must remain live after a retry");
assert.match(shellSource, /Retry Marble physics/,
  "Marble retry control must use an explicit physics label");
assert.match(shellSource, /marblePhysicsRetryFailed/,
  "Marble must retain an explicit retry-failure state");
assert.match(shellSource, /marblePhysicsRetryFailed \? " · retry failed"/,
  "Marble status must distinguish a failed retry from an available first retry");
assert.match(shellSource, /marble-force-retry-failure/,
  "Marble retry failure coverage must be opt-in and query-gated");
assert.match(shellSource, /marble-force-renderer-failure/,
  "Marble renderer fallback coverage must be opt-in and query-gated");
assert.match(shellSource, /forced Marble Maze WebGL renderer failure for lifecycle testing/,
  "Marble lifecycle tests must be able to exercise the labeled renderer fallback path");
assert.match(shellSource, /forceMarbleFallback = marbleDebugHooks &&/,
  "Marble fallback injection must be restricted to opt-in test hooks");
assert.match(shellSource, /forced Marble Maze fallback for lifecycle testing/,
  "Marble lifecycle tests must be able to exercise the labeled fallback path");

// Exercise the constructor's real cleanup boundary with a minimal WebGL2
// double.  Static regexes protect the source shape, but only an injected
// framebuffer failure can prove that every resource allocated before the
// failure is actually deleted before the error escapes to the shell.
{
  const deleted = {
    shaders: 0,
    programs: 0,
    textures: 0,
    framebuffers: 0,
    buffers: 0,
    vertexArrays: 0,
  };
  let nextHandle = 0;
  const handle = (kind) => ({ kind, id: ++nextHandle });
  const gl = {
    VERTEX_SHADER: 1, FRAGMENT_SHADER: 2, COMPILE_STATUS: 3,
    LINK_STATUS: 4, ARRAY_BUFFER: 5, ELEMENT_ARRAY_BUFFER: 6,
    STATIC_DRAW: 7, TEXTURE_2D: 8, RGBA8: 9, RGBA: 10,
    UNSIGNED_BYTE: 11, TEXTURE_MIN_FILTER: 12, TEXTURE_MAG_FILTER: 13,
    LINEAR: 14, TEXTURE_WRAP_S: 15, TEXTURE_WRAP_T: 16,
    REPEAT: 17, CLAMP_TO_EDGE: 18, FRAMEBUFFER: 19,
    RENDERBUFFER: 20, DEPTH_COMPONENT24: 21, DEPTH_COMPONENT: 22,
    UNSIGNED_INT: 23, DEPTH_ATTACHMENT: 24, NONE: 25,
    FRAMEBUFFER_COMPLETE: 26, FRAMEBUFFER_INCOMPLETE_ATTACHMENT: 27,
    TEXTURE0: 28,
    createShader: (type) => handle(`shader-${type}`),
    shaderSource() {}, compileShader() {},
    getShaderParameter: () => true, getShaderInfoLog: () => "",
    deleteShader: () => { deleted.shaders += 1; },
    createProgram: () => handle("program"), attachShader() {}, linkProgram() {},
    getProgramParameter: () => true, getProgramInfoLog: () => "",
    deleteProgram: () => { deleted.programs += 1; },
    getUniformLocation: (_program, name) => ({ name }),
    createVertexArray: () => handle("vertex-array"),
    bindVertexArray() {}, deleteVertexArray: () => { deleted.vertexArrays += 1; },
    createBuffer: () => handle("buffer"), bindBuffer() {}, bufferData() {},
    enableVertexAttribArray() {}, vertexAttribPointer() {},
    deleteBuffer: () => { deleted.buffers += 1; },
    createTexture: () => handle("texture"), bindTexture() {}, texImage2D() {},
    texParameteri() {}, deleteTexture: () => { deleted.textures += 1; },
    createFramebuffer: () => handle("framebuffer"), bindFramebuffer() {},
    framebufferTexture2D() {}, drawBuffers() {}, readBuffer() {},
    checkFramebufferStatus: () => gl.FRAMEBUFFER_INCOMPLETE_ATTACHMENT,
    deleteFramebuffer: () => { deleted.framebuffers += 1; },
    isContextLost: () => false,
  };
  const canvas = {
    getContext: () => gl,
    addEventListener() {},
    removeEventListener() {},
  };
  const previousDocument = globalThis.document;
  globalThis.document = { createElement: () => canvas };
  try {
    assert.throws(
      () => new MarbleMazeRenderer(),
      /Marble Maze shadow framebuffer is incomplete/,
      "constructor must rethrow the injected capability error",
    );
  } finally {
    if (previousDocument === undefined) delete globalThis.document;
    else globalThis.document = previousDocument;
  }
  assert.equal(deleted.shaders, 6,
    "all compiled shader objects must be released on constructor failure");
  assert.equal(deleted.programs, 3,
    "all linked programs must be released on constructor failure");
  assert.equal(deleted.textures, 1,
    "the partially allocated shadow texture must be released");
  assert.equal(deleted.framebuffers, 1,
    "the partially allocated shadow framebuffer must be released");
  assert.equal(deleted.buffers, 1,
    "the composite buffer must be released");
  assert.equal(deleted.vertexArrays, 1,
    "the composite vertex array must be released");
}

console.log("PASS: Marble renderer stage, framebuffer, state, and key contracts");
