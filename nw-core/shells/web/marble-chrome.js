import { Kind, REFERENCE_HEIGHT, REFERENCE_WIDTH } from "./display-list.js";

// The host has the live MuJoCo status; the core's board-less scene has only
// placeholder status. Remove just that scene slot, not title/help/verdict.
export function marbleStaticChrome(commands, width = REFERENCE_WIDTH,
                                  height = REFERENCE_HEIGHT) {
  // Geometry truncates layout coordinates before Display normalizes them.
  // Reproduce that order, including odd widths, then the wire's f32 rounding.
  const x = Math.fround(Math.trunc(width / 2) / (width / REFERENCE_WIDTH));
  const y = Math.fround(Math.trunc(height - 62 * height / REFERENCE_HEIGHT) /
                       (height / REFERENCE_HEIGHT));
  return commands.filter(command => !(command.kind === Kind.TEXT &&
    Math.abs(command.a - x) < 0.001 &&
    Math.abs(command.b - y) < 0.001 &&
    command.anchor?.[0] === "center" && command.anchor?.[1] === "top"));
}

// The browser's grayscale text rasterizer needs a slight weight compensation
// against the light native framebuffer, but that same stroke over-brightens
// antialiased edges on the dark framebuffer. Keep the measured treatment
// theme-specific so the shared source geometry stays unchanged.
export function marbleGlyphStrokeRatio(darkTheme) {
  return darkTheme ? 0 : 0.045;
}
