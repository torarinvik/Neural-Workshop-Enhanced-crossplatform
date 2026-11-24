/* Playwright CLI run-code callback. Open the web shell with
 * marble-test-hooks=1 and marble-test-freeze-clock=1 before running it. */
async function replayMarbleFrameArchive(page) {
  await page.reload();
  await page.waitForFunction(() => window.__nw?.marbleDebug && window.__nw.createPublicFrameArchive);
  await page.keyboard.press("Enter");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowUp");
  await page.waitForFunction(() => document.getElementById("status").textContent.includes("Attention · Marble Maze"));
  await page.keyboard.press("Enter");
  await page.keyboard.press("Space");
  await page.waitForFunction(() => window.__nw.marbleDebug.board && window.__nw.marbleRenderer?.viewport);

  return page.evaluate(async () => {
    const runtime = window.__nw;
    const renderer = runtime.marbleRenderer;
    if (runtime.marblePhysicsEngine !== "mujoco" || runtime.marbleDebug.renderer !== "webgl2") {
      throw new Error("Expected the MuJoCo run and the WebGL2 renderer");
    }

    const { x, y, width, height } = renderer.viewport;
    const stage = document.createElement("canvas");
    stage.width = width;
    stage.height = height;
    const ctx = stage.getContext("2d");
    ctx.drawImage(renderer.canvas, x, y, width, height, 0, 0, width, height);
    const source = ctx.getImageData(0, 0, width, height).data;
    const archive = runtime.createPublicFrameArchive();
    const frame = archive.capture();
    const stored = archive.get(frame.digest);
    const digestBytes = await crypto.subtle.digest("SHA-256", stored);
    const digest = Array.from(new Uint8Array(digestBytes), byte => byte.toString(16).padStart(2, "0")).join("");
    if (digest !== frame.digest) throw new Error("Archived bytes do not match the frame digest");

    const colors = new Set();
    let compared = 0;
    for (let row = 8; row < height - 8; row += 11) {
      for (let col = 8; col < width - 8; col += 13) {
        const input = (row * width + col) * 4;
        if (source[input + 3] !== 255) continue;
        const output = ((y + row) * frame.width + x + col) * 4;
        for (let channel = 0; channel < 4; channel++) {
          if (source[input + channel] !== stored[output + channel]) {
            throw new Error(`Archived Marble stage differs at (${col}, ${row})`);
          }
        }
        colors.add(source.slice(input, input + 3).join(","));
        compared++;
      }
    }
    if (compared < 100 || colors.size < 20) throw new Error("Archived stage has too few rendered colors");
    return { compared, colors: colors.size, digest };
  });
}
