const WIDTH = 320;
const HEIGHT = 240;
const MAX_SECONDS = 8;
const FRAME_RATE = 15;

export function videoJigsawCrop(sourceWidth, sourceHeight) {
  const scale = Math.max(WIDTH / sourceWidth, HEIGHT / sourceHeight);
  const width = WIDTH / scale;
  const height = HEIGHT / scale;
  return [(sourceWidth - width) / 2, (sourceHeight - height) / 2, width, height];
}

// Sample the same packed RGB offsets as Python's videoclips.difference.
function frameDifference(first, second, pixels) {
  let difference = 0;
  let samples = 0;
  for (let rgb = 0; rgb < pixels * 3; rgb += 97) {
    const rgba = rgb + Math.floor(rgb / 3);
    difference += Math.abs(first[rgba] - second[rgba]);
    samples++;
  }
  return difference / samples;
}

export function videoJigsawFramesDiffer(first, second) {
  return frameDifference(first, second, WIDTH * HEIGHT) >= 4;
}

function waitForVideoEvent(video, event, signal, start) {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(signal.reason);
      return;
    }
    const listeners = new AbortController();
    const options = { once: true, signal: listeners.signal };
    const settle = error => {
      clearTimeout(timeout);
      listeners.abort();
      if (error) reject(error);
      else resolve();
    };
    const timeout = setTimeout(() => settle(new Error("The clip took too long to decode")), 10000);
    video.addEventListener(event, () => settle(), options);
    video.addEventListener("error", () => settle(new Error("The browser could not decode this clip")), options);
    signal.addEventListener("abort", () => settle(signal.reason), options);
    try {
      start();
    } catch (error) {
      settle(error);
    }
  });
}

export function openVideoJigsawClip(file) {
  const video = document.createElement("video");
  const surface = document.createElement("canvas");
  surface.width = WIDTH;
  surface.height = HEIGHT;
  const context = surface.getContext("2d");
  const objectUrl = URL.createObjectURL(file);
  video.muted = true;
  video.playsInline = true;
  video.loop = true;
  const abort = new AbortController();
  const ready = waitForVideoEvent(video, "loadeddata", abort.signal, () => { video.src = objectUrl; });
  const seek = time => Math.abs(video.currentTime - time) < 0.0001
    ? Promise.resolve()
    : waitForVideoEvent(video, "seeked", abort.signal, () => { video.currentTime = time; });
  const drawFrame = () => {
    const crop = videoJigsawCrop(video.videoWidth, video.videoHeight);
    context.drawImage(video, ...crop, 0, 0, WIDTH, HEIGHT);
  };
  let lastFrame = -1;
  return {
    image: surface, width: WIDTH, height: HEIGHT,
    ready,
    async hasMotion() {
      if (!Number.isFinite(video.duration)) return false;
      const frames = Math.round(Math.min(video.duration, MAX_SECONDS) * FRAME_RATE);
      if (frames < 2) throw new Error("The clip contains fewer than two frames");
      const span = Math.floor(frames / 3);
      if (!span) return false;
      let previous = null;
      for (let segment = 0; segment < 3; segment++) {
        await seek(segment * span / FRAME_RATE);
        drawFrame();
        const frame = context.getImageData(0, 0, WIDTH, HEIGHT).data;
        if (previous && !videoJigsawFramesDiffer(previous, frame)) return false;
        previous = frame;
      }
      return true;
    },
    async play() {
      await seek(0);
      drawFrame();
      await video.play();
    },
    capture() {
      if (video.currentTime >= MAX_SECONDS && !video.seeking) {
        video.currentTime = 0;
        return false;
      }
      if (video.readyState < 2 || video.seeking) return false;
      const frame = Math.floor(video.currentTime * FRAME_RATE);
      if (frame === lastFrame) return false;
      drawFrame();
      lastFrame = frame;
      return true;
    },
    close() {
      abort.abort();
      video.pause();
      video.removeAttribute("src");
      video.load();
      URL.revokeObjectURL(objectUrl);
    },
  };
}

const CLIP_WIDTH = 160;
const CLIP_HEIGHT = 120;
const CLIP_RGB_BYTES = CLIP_WIDTH * CLIP_HEIGHT * 3;
const SAMPLE_STRIDE = 97;
const SAMPLES_PER_FRAME = Math.ceil(CLIP_RGB_BYTES / SAMPLE_STRIDE);
const MAX_CLIP_FRAMES = MAX_SECONDS * FRAME_RATE;
const MAX_CLIP_GROUP = 7;

async function decodeClipFrames(file, signal, frameLimit, consume) {
  const video = document.createElement("video");
  const objectUrl = URL.createObjectURL(file);
  video.muted = true;
  video.playsInline = true;

  try {
    await waitForVideoEvent(video, "loadeddata", signal, () => { video.src = objectUrl; });
    const count = Math.round(Math.min(video.duration, MAX_SECONDS) * FRAME_RATE);
    const limit = frameLimit(count);
    if (!Number.isInteger(limit) || limit < 1 || limit > MAX_CLIP_FRAMES)
      throw new Error("The clip is too short for this cut");
    const crop = videoJigsawCrop(video.videoWidth, video.videoHeight);
    const frames = [];
    for (let frame = 0; frame < limit; frame++) {
      signal.throwIfAborted();
      const time = Math.min(frame / FRAME_RATE, Math.max(0, video.duration - 0.0001));
      if (Math.abs(time - video.currentTime) >= 0.0001) {
        await waitForVideoEvent(video, "seeked", signal, () => { video.currentTime = time; });
      }
      const surface = document.createElement("canvas");
      surface.width = CLIP_WIDTH;
      surface.height = CLIP_HEIGHT;
      const context = surface.getContext("2d");
      context.drawImage(video, ...crop, 0, 0, CLIP_WIDTH, CLIP_HEIGHT);
      frames.push(surface);
      consume(context, frame);
    }
    return { frames, count };
  } finally {
    video.removeAttribute("src");
    video.load();
    URL.revokeObjectURL(objectUrl);
  }
}

export async function openVideoSequenceClip(file, pieces, signal) {
  let span = 0;
  let previous = null;
  let motion = 255;
  const decoded = await decodeClipFrames(file, signal, count => {
    span = Math.floor(count / pieces);
    return span * pieces;
  }, (context, frame) => {
    if (frame % span !== 0) return;
    const pixels = context.getImageData(0, 0, CLIP_WIDTH, CLIP_HEIGHT).data;
    if (previous) motion = Math.min(motion, frameDifference(previous, pixels, CLIP_WIDTH * CLIP_HEIGHT));
    previous = pixels;
  });
  return { ...decoded, motion };
}

export async function openWhatNextClip(file, signal) {
  let samples;
  const { frames } = await decodeClipFrames(file, signal, count => {
    if (Number.isInteger(count) && count >= 1 && count <= MAX_CLIP_FRAMES)
      samples = new Uint8Array(count * SAMPLES_PER_FRAME);
    return count;
  }, (context, frame) => {
    const pixels = context.getImageData(0, 0, CLIP_WIDTH, CLIP_HEIGHT).data;
    let at = frame * SAMPLES_PER_FRAME;
    for (let rgb = 0; rgb < CLIP_RGB_BYTES; rgb += SAMPLE_STRIDE) {
      samples[at++] = pixels[rgb + Math.floor(rgb / 3)];
    }
  });
  return { frames, samples };
}

export function encodeWhatNextGroup(clips) {
  if (!Array.isArray(clips) || clips.length < 1 || clips.length > MAX_CLIP_GROUP)
    throw new Error("Invalid What Happens Next clip count");
  let length = 1 + clips.length;
  for (const { frames, samples } of clips) {
    if (!Array.isArray(frames) || frames.length < 1 || frames.length > MAX_CLIP_FRAMES ||
        !(samples instanceof Uint8Array) || samples.length !== frames.length * SAMPLES_PER_FRAME)
      throw new Error("Invalid What Happens Next clip frames");
    length += samples.length;
  }
  const packet = new Uint8Array(length);
  packet[0] = clips.length;
  let offset = 1 + clips.length;
  for (const [index, clip] of clips.entries()) {
    packet[1 + index] = clip.frames.length;
    packet.set(clip.samples, offset);
    offset += clip.samples.length;
  }
  return packet;
}

export function loadWhatNextGroup(api, handle, clips, timestamp, sequence) {
  const packet = encodeWhatNextGroup(clips);
  const length = BigInt(packet.length);
  const pointer = api.nw_frame_alloc(length);
  if (pointer <= 0n) throw new Error("Could not allocate What Happens Next clip samples");
  try {
    new Uint8Array(api.memory.buffer, Number(pointer), packet.length).set(packet);
    return api.nw_what_next_load(handle, pointer, length, timestamp, sequence);
  } finally {
    api.nw_frame_free(pointer);
  }
}
