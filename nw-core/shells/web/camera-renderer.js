import { decode, render } from "./display-list.js";

// Camera's mesh and frame packets are written by CameraRender in Elisa.
const FRAME_MAGIC = 1178818382;
const MESH_MAGIC = 1296258894;
const VERSION = 1;
const FRAME_HEADER = 216;
const PASS_BYTES = 92;
const DRAW_BYTES = 96;
const MESH_HEADER = 20;
const VERTEX_FLOATS = 6;
const MESH_COUNT = 8;
const SHADOW_SIZE = 1024;
const MAX_DRAWS = 302;

function reader(bytes, magic, minimum) {
  if (!(bytes instanceof Uint8Array) || bytes.byteLength < minimum)
    throw new Error("Truncated Camera render packet");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let offset = 0;
  const uint = () => {
    const value = view.getUint32(offset, true);
    offset += 4;
    return value;
  };
  const floats = count => {
    const values = new Float32Array(count);
    for (let i = 0; i < count; i++, offset += 4) {
      values[i] = view.getFloat32(offset, true);
      if (!Number.isFinite(values[i])) throw new Error("Nonfinite Camera render value");
    }
    return values;
  };
  if (uint() !== magic || uint() !== VERSION)
    throw new Error("Unsupported Camera render packet");
  return { uint, floats };
}

export function decodeCameraFrame(bytes) {
  if (bytes.byteLength === 0) return null;
  const { uint, floats } = reader(bytes, FRAME_MAGIC, FRAME_HEADER);
  const width = uint();
  const height = uint();
  const passCount = uint();
  const drawCount = uint();
  if (width < 8 || height < 8 || width > 32768 || height > 32768 ||
      passCount < 1 || passCount > 2 || drawCount < 2 || drawCount > MAX_DRAWS ||
      bytes.byteLength !== FRAME_HEADER + PASS_BYTES * passCount + DRAW_BYTES * drawCount)
    throw new Error("Invalid Camera frame dimensions or counts");
  const [field] = floats(1);
  if (!(field > 0 && field <= 120)) throw new Error("Invalid Camera field size");
  const light = {
    direction: floats(3), colour: floats(3), sky: floats(3), ground: floats(3),
    background: floats(3), clip: floats(16), shadow: floats(16),
  };
  const passes = Array.from({ length: passCount }, () => {
    const x = uint();
    const y = uint();
    const w = uint();
    const h = uint();
    if (w < 8 || h < 8 || x + w > width || y + h > height)
      throw new Error("Invalid Camera viewport");
    return { x, y, width: w, height: h, eye: floats(3), projection: floats(16) };
  });
  const draws = Array.from({ length: drawCount }, () => {
    const mesh = uint();
    const casts = uint();
    if (mesh >= MESH_COUNT || casts > 1) throw new Error("Invalid Camera draw");
    return { mesh, casts: casts === 1, model: floats(16), normalScale: floats(3), colour: floats(3) };
  });
  return { width, height, field, light, passes, draws };
}

export function decodeCameraMesh(bytes, expectedKind) {
  const { uint, floats } = reader(bytes, MESH_MAGIC, MESH_HEADER);
  const kind = uint();
  const vertexCount = uint();
  const indexCount = uint();
  if (kind >= MESH_COUNT || kind !== expectedKind || vertexCount === 0 ||
      indexCount === 0 || indexCount % 3 !== 0 ||
      bytes.byteLength !== MESH_HEADER + 4 * (VERTEX_FLOATS * vertexCount + indexCount))
    throw new Error("Invalid Camera mesh dimensions or counts");
  const vertices = floats(vertexCount * VERTEX_FLOATS);
  const indices = new Uint32Array(indexCount);
  for (let i = 0; i < indexCount; i++) {
    indices[i] = uint();
    if (indices[i] >= vertexCount) throw new Error("Invalid Camera mesh index");
  }
  return { vertices, indices };
}

export async function loadCameraShaders(fetchSource = fetch) {
  const files = ["colour.vert", "colour.frag", "shadow.vert", "shadow.frag"];
  const sources = await Promise.all(files.map(async name => {
    const response = await fetchSource(new URL(`../../res/camera/${name}`, import.meta.url));
    if (!response.ok) throw new Error(`Could not load Camera shader ${name}`);
    return response.text();
  }));
  return { colour: sources.slice(0, 2), shadow: sources.slice(2) };
}

function compile(gl, kind, code) {
  const shader = gl.createShader(kind);
  if (!shader) throw new Error("Could not allocate Camera shader");
  gl.shaderSource(shader, "#version 300 es\nprecision highp float;\n" + code);
  gl.compileShader(shader);
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
  const info = gl.getShaderInfoLog(shader);
  gl.deleteShader(shader);
  throw new Error(`Camera shader compilation failed (${info})`);
}

function link(gl, sources, uniformNames) {
  const program = gl.createProgram();
  if (!program) throw new Error("Could not allocate Camera program");
  const shaders = [];
  try {
    shaders.push(compile(gl, gl.VERTEX_SHADER, sources[0]));
    shaders.push(compile(gl, gl.FRAGMENT_SHADER, sources[1]));
    for (const shader of shaders) gl.attachShader(program, shader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS))
      throw new Error(`Camera program linking failed (${gl.getProgramInfoLog(program)})`);
    const uniforms = Object.fromEntries(uniformNames.map(name => {
      const location = gl.getUniformLocation(program, name);
      if (location === null) throw new Error(`Camera shader is missing ${name}`);
      return [name, location];
    }));
    return { program, uniforms };
  } catch (error) {
    gl.deleteProgram(program);
    throw error;
  } finally {
    for (const shader of shaders) gl.deleteShader(shader);
  }
}

function cameraBytes(api, buffer, capacity, length) {
  if (length < 0n || length > capacity)
    throw new Error(`Camera WASM render packet failed (${length})`);
  return new Uint8Array(api.memory.buffer, Number(buffer), Number(length));
}

export class CameraRenderer {
  constructor(canvas, shaders) {
    this.canvas = canvas;
    const gl = canvas.getContext("webgl2", { alpha: true, antialias: true, depth: true });
    if (!gl) throw new Error("Camera needs WebGL 2");
    this.gl = gl;
    this.meshes = new Map();
    this.field = null;
    this.colour = null;
    this.shadow = null;
    this.shadowDepth = null;
    this.shadowTarget = null;
    this.closed = false;
    try {
      this.colour = link(gl, shaders.colour, ["view_proj", "model", "normal_scale", "light_matrix",
        "tint", "eye", "light_dir", "light_colour", "sky_colour", "ground_colour", "shadow_map", "shadow_texel"]);
      this.shadow = link(gl, shaders.shadow, ["light_clip", "model"]);
      this.createShadowTarget();
    } catch (error) {
      this.dispose();
      throw error;
    }
  }

  createShadowTarget() {
    const gl = this.gl;
    this.shadowDepth = gl.createTexture();
    this.shadowTarget = gl.createFramebuffer();
    if (!this.shadowDepth || !this.shadowTarget) throw new Error("Could not allocate Camera shadow map");
    gl.bindTexture(gl.TEXTURE_2D, this.shadowDepth);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.DEPTH_COMPONENT24, SHADOW_SIZE, SHADOW_SIZE, 0,
      gl.DEPTH_COMPONENT, gl.UNSIGNED_INT, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.shadowTarget);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, this.shadowDepth, 0);
    gl.drawBuffers([gl.NONE]);
    gl.readBuffer(gl.NONE);
    const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    if (status !== gl.FRAMEBUFFER_COMPLETE) throw new Error("Incomplete Camera shadow framebuffer");
  }

  mesh(kind, field, readMesh) {
    const cached = this.meshes.get(kind);
    if (cached) return cached;
    const gl = this.gl;
    const { vertices, indices } = decodeCameraMesh(readMesh(kind, field), kind);
    const mesh = { array: gl.createVertexArray(), position: gl.createBuffer(),
      elements: gl.createBuffer(), count: indices.length };
    if (!mesh.array || !mesh.position || !mesh.elements) {
      this.deleteMesh(mesh);
      throw new Error("Could not allocate Camera mesh");
    }
    gl.bindVertexArray(mesh.array);
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh.position);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 24, 0);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 3, gl.FLOAT, false, 24, 12);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.elements);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
    gl.bindVertexArray(null);
    this.meshes.set(kind, mesh);
    return mesh;
  }

  deleteMesh(mesh) {
    const gl = this.gl;
    gl.deleteVertexArray(mesh.array);
    gl.deleteBuffer(mesh.position);
    gl.deleteBuffer(mesh.elements);
  }

  renderRun(api, handle, buffer, capacity, width, height) {
    const frame = decodeCameraFrame(cameraBytes(api, buffer, capacity, api.nw_camera_frame(
      handle, buffer, capacity, BigInt(width), BigInt(height))));
    if (!frame) return null;
    return this.render(frame, (kind, field) => cameraBytes(api, buffer, capacity,
      api.nw_camera_mesh(buffer, capacity, BigInt(kind), field)));
  }

  renderTask(ctx, api, handle, buffer, capacity, dark) {
    const { width, height } = ctx.canvas;
    const chrome = decode(cameraBytes(api, buffer, capacity, api.nw_camera_chrome(
      handle, buffer, capacity, dark ? 1n : 0n, BigInt(width), BigInt(height))));
    const sceneImage = this.renderRun(api, handle, buffer, capacity, width, height);
    return render(ctx, chrome, {
      width, height, referenceWidth: width, referenceHeight: height, sceneImage,
    });
  }

  render(frame, readMesh) {
    if (this.closed || this.gl.isContextLost()) throw new Error("Camera renderer is unavailable");
    const gl = this.gl;
    if (this.canvas.width !== frame.width) this.canvas.width = frame.width;
    if (this.canvas.height !== frame.height) this.canvas.height = frame.height;
    if (this.field !== frame.field) {
      for (const kind of [6, 7]) {
        const ground = this.meshes.get(kind);
        if (ground) this.deleteMesh(ground);
        this.meshes.delete(kind);
      }
      this.field = frame.field;
    }
    const instances = frame.draws.map(draw => ({ draw, mesh: this.mesh(draw.mesh, frame.field, readMesh) }));
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);
    gl.disable(gl.CULL_FACE);
    gl.disable(gl.SCISSOR_TEST);
    gl.depthMask(true);
    gl.depthFunc(gl.LESS);
    gl.clearDepth(1);

    gl.bindFramebuffer(gl.FRAMEBUFFER, this.shadowTarget);
    gl.viewport(0, 0, SHADOW_SIZE, SHADOW_SIZE);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    gl.useProgram(this.shadow.program);
    const shadow = this.shadow.uniforms;
    gl.uniformMatrix4fv(shadow.light_clip, false, frame.light.clip);
    for (const { draw, mesh } of instances) {
      if (draw.casts) {
        gl.uniformMatrix4fv(shadow.model, false, draw.model);
        this.draw(mesh);
      }
    }

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, frame.width, frame.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.SCISSOR_TEST);
    gl.useProgram(this.colour.program);
    const colour = this.colour.uniforms;
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.shadowDepth);
    gl.uniform1i(colour.shadow_map, 0);
    gl.uniform1f(colour.shadow_texel, 1 / SHADOW_SIZE);
    gl.uniformMatrix4fv(colour.light_matrix, false, frame.light.shadow);
    gl.uniform3fv(colour.light_dir, frame.light.direction);
    gl.uniform3fv(colour.light_colour, frame.light.colour);
    gl.uniform3fv(colour.sky_colour, frame.light.sky);
    gl.uniform3fv(colour.ground_colour, frame.light.ground);
    gl.clearColor(...frame.light.background, 1);
    for (const pass of frame.passes) {
      const bounds = [pass.x, pass.y, pass.width, pass.height];
      gl.viewport(...bounds);
      gl.scissor(...bounds);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.uniformMatrix4fv(colour.view_proj, false, pass.projection);
      gl.uniform3fv(colour.eye, pass.eye);
      for (const { draw, mesh } of instances) {
        gl.uniformMatrix4fv(colour.model, false, draw.model);
        gl.uniform3fv(colour.normal_scale, draw.normalScale);
        gl.uniform3fv(colour.tint, draw.colour);
        this.draw(mesh);
      }
    }
    gl.disable(gl.SCISSOR_TEST);
    gl.bindVertexArray(null);
    gl.useProgram(null);
    return this.canvas;
  }

  draw(mesh) {
    const gl = this.gl;
    gl.bindVertexArray(mesh.array);
    gl.drawElements(gl.TRIANGLES, mesh.count, gl.UNSIGNED_INT, 0);
  }

  dispose() {
    if (this.closed) return;
    this.closed = true;
    const gl = this.gl;
    for (const mesh of this.meshes.values()) this.deleteMesh(mesh);
    this.meshes.clear();
    if (this.colour) gl.deleteProgram(this.colour.program);
    if (this.shadow) gl.deleteProgram(this.shadow.program);
    gl.deleteTexture(this.shadowDepth);
    gl.deleteFramebuffer(this.shadowTarget);
  }
}
