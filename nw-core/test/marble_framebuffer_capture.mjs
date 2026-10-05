// Test-only browser capture. No CSS screenshot, resampling, or pose injection.
export function captureMarbleFramebuffer(canvas, debug, { displayedBackground = false } = {}) {
  if (!debug || debug.testClockFrozen !== true) {
    throw new Error("Marble framebuffer capture requires the frozen test clock");
  }
  const framebuffer = debug.capture?.framebuffer;
  if (!framebuffer || !Number.isSafeInteger(canvas?.width) ||
      !Number.isSafeInteger(canvas?.height) || canvas.width <= 0 ||
      canvas.height <= 0 || framebuffer.width !== canvas.width ||
      framebuffer.height !== canvas.height) {
    throw new Error("canvas dimensions differ from live Marble framebuffer");
  }
  // Snapshot in the same synchronous task as canvas readback, not in a later
  // evaluate call after another input event or animation frame.
  const snapshot = structuredClone(debug);
  let output = canvas;
  let background = null;
  if (displayedBackground) {
    // PNG readback omits CSS backgrounds. Composite explicitly, without
    // changing the source canvas or using CSS dimensions/resampling.
    const doc = canvas.ownerDocument;
    background = doc?.defaultView?.getComputedStyle(canvas).backgroundColor;
    const expected = debug.capture.dark ? "rgb(0, 0, 0)" : "rgb(255, 255, 255)";
    if (background !== expected) {
      throw new Error("displayed Marble background differs from captured theme");
    }
    output = doc.createElement("canvas");
    output.width = canvas.width;
    output.height = canvas.height;
    const context = output.getContext("2d", { alpha: false });
    if (!context) throw new Error("opaque capture context unavailable");
    context.fillStyle = background;
    context.fillRect(0, 0, output.width, output.height);
    context.drawImage(canvas, 0, 0);
  }
  const readback = {
    mode: displayedBackground ? "displayed-background-composite" : "raw",
    background,
    width: canvas.width,
    height: canvas.height,
  };
  snapshot.capture.readback = readback;
  const pngDataUrl = output.toDataURL("image/png");
  if (!pngDataUrl.startsWith("data:image/png;base64,") ||
      pngDataUrl.length <= "data:image/png;base64,".length) {
    throw new Error("canvas did not produce a nonempty PNG capture");
  }
  return { pngDataUrl, debug: snapshot, readback };
}
