import {
  BLEND_WIDTH_RANGE,
  FRAME_RATE_RANGE,
  SMOOTHING_WINDOW_RANGE,
  THRESHOLD_RANGE,
} from "./validation";

/** The explanation behind each setting's info button. Problems the user must act on are not here: they stay inline. */
export const windowSizeHelp = "Larger windows separate low notes better but blur changes over time.";

export const frameRateHelp = `${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`;

export const colormapHelp =
  "How each tile is colored: its color is the color of the chosen scale at how strong its own note is, quiet notes at the start of the scale and the loudest note of the file at the end, so the same strength always gets the same color. Summer: green to yellow. Autumn: red to yellow. Hot: dark red through red and yellow to white. Cool: cyan to magenta.";

export const thresholdHelp = `A note whose volume is below the threshold is drawn black. The threshold is a share of the loudest note in the whole file: ${THRESHOLD_RANGE.min} (the left end) is off, and ${THRESHOLD_RANGE.max} (the right end) is ${THRESHOLD_RANGE.max}% of the loudest note. Louder notes are never changed.`;

export const imageTypeHelp =
  "Tiles: the picture is a grid of flat colored tiles with hard edges. Blended tiles: the same grid and colors, but the colors of neighboring tiles fade into each other across the edges between them. Contour: the same grid of notes drawn as a filled contour map, bands of color that flow from one note to the next, from the start of the colormap for silence to its end for the loudest note of the file.";

export const blendWidthHelp = `Number from ${BLEND_WIDTH_RANGE.min} to ${BLEND_WIDTH_RANGE.max}. How far the fade reaches on each side of an edge between two tiles, as a percentage of a tile's width: larger values give wider, softer fades and smaller ones sharper edges. Only used by Blended tiles.`;

export const smoothingHelp =
  "0 is no smoothing. Otherwise each frame is averaged with the frames before it in the smoothing window; each of those counts this fraction as much as the current frame, so higher values blend more and fade notes more slowly.";

export const smoothingWindowHelp = `Whole number, ${SMOOTHING_WINDOW_RANGE.min} to ${SMOOTHING_WINDOW_RANGE.max}. How many earlier frames are mixed into each frame: with 1 each frame is blended with the one before it, with ${SMOOTHING_WINDOW_RANGE.max} with the ${SMOOTHING_WINDOW_RANGE.max} before it. A note that stops is gone that many frames later. It has no effect while Smoothing is 0.`;

/** The spacing explanation, followed by the live step between windows when the value is usable (`stepHint` is empty otherwise). */
export function spacingHelp(stepHint: string): string {
  const base = "Distance between the starts of windows, as a multiple of the window size.";
  return stepHint ? `${base} ${stepHint}` : base;
}

export const resolutionHelp =
  "How fine the picture is. 1\u00d7 is the original grid of 12 \u00d7 7 values, one for each note. Higher values, up to 5\u00d7 (60 \u00d7 35), make new values between the notes by interpolating, so the picture has more and smaller tiles (or finer contour steps) in the same size. The threshold and the colors then apply to those new values.";
