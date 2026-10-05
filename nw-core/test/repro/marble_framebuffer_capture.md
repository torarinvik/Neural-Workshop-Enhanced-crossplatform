# Browser framebuffer capture

Use `test/marble_framebuffer_capture.mjs` after navigating and independently
replaying the requested state through ordinary keys. Serve `nw-core` over
HTTP; enable `marble-test-hooks=1&marble-test-freeze-clock=1`. This helper
does not start a game, replace physics, inject a source pose, or advance time.

In a browser evaluation, import the helper from the served test directory:

```javascript
const { captureMarbleFramebuffer } = await import('/test/marble_framebuffer_capture.mjs');
const capture = captureMarbleFramebuffer(
  document.getElementById('screen'), window.__nw.marbleDebug,
  { displayedBackground: true });
```

Save `capture.pngDataUrl` as a PNG through a browser download and save
`capture.debug` as JSON. The helper composites the transparent canvas readback
against the verified light/dark CSS background at framebuffer resolution; the
readback mode, background, and dimensions are bound into the debug snapshot.
Do not fetch fresh debug state in a later evaluation:
both outputs must originate from this same returned capture. The test clock
must stay frozen while saving. Use unique paths under `output/playwright`.
Do not crop, rescale, or replace this capture with an element screenshot. Raw
mode remains available for low-level diagnostics, but is not the recommended
cross-shell image input; the comparator composites such legacy browser PNGs
against the synchronized theme background before measuring them.
Element screenshots can include fractional CSS-position rounding: the
800x600 logical test produced a1600x1202 screenshot for a1600x1200 framebuffer.

Then run `marble_browser_pair_metadata.py` against the independently captured
original source metadata, followed by `marble_render_pair_test.py` with
`--require-synchronized --require-scene-state`. A raw PNG is not itself proof
of source parity. Pixel limits require review; absent limits the comparator
must remain diagnostic-only. Record candidate JS/WASM identities separately.

Portable tests cover frozen-clock enforcement, dimensions, independent
snapshot ownership, explicit PNG encoding, nonempty output, and invalid
metadata failing before readback. They do not qualify browser PNG encoding
or any new rendered scene. Actual browser integration passed2026-10-03:
rung16/800x600 logical,30 east-held and12 released frames. Paired raw PNG
and same-task debug snapshot pass source scene/camera qualification;
`output/playwright/mm-helper-800x600-release-render-diagnostic.json` records
the diagnostic-only comparison. Browser PNG matches the previous independent
raw framebuffer capture byte-for-byte. This does not qualify every phase/DPR.
