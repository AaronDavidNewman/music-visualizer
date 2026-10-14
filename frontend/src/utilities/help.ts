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
  "Tiles: the picture is a grid of flat colored tiles with hard edges. Blended tiles: the same grid and colors, but the colors of neighboring tiles fade into each other across the edges between them. Circles: no grid at all: the strongest notes of every frame each put down a circle, placed relative to the circle of the same rank in the previous frame and colored by the colormap, and the last circles stay in the picture, so the music draws a wandering trail. Contour: the same grid of notes drawn as a filled contour map, bands of color that flow from one note to the next, from the start of the colormap for silence to its end for the loudest note of the file.";

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

export const noteCountHelp =
  "Only the notes with the most energy in the whole file are used: 12 to 84 of the 84 drawn notes. Their values are spread over the whole picture, so each one covers a larger area. Fewer notes remove the flicker of faint notes and make bigger features; the picture is not steadier in every case. The colors keep their scale.";

export const interpolateHelp =
  "1 to 5. Only every n-th frame is drawn from the music (1 draws every frame); the frames between are made by blending their two drawn neighbors (a mix of the two, with more of the nearer one), so the animation has the same number of frames and speed. A contour job is faster the higher the value (drawing is the slow part); tile pictures are cheap to draw, so there is little to save. Quickly changing music can lose events that happen between two drawn frames.";

export const circleUnitHelp =
  "1 to 10 pixels. The length of one step of a circle (the size of a circle is a separate setting). A note moves its circle by an angle from its name (30 degrees for each of C, C#, D ... B) and a number of units from its octave: 1 unit for octave 4 and one more for every octave above or below it. A note that repeats at the same volume stays in place. Only used by Circles.";

export const circleSizeHelp =
  "25 to 50 pixels. How large a circle is drawn, as the length of its circumference (the distance around it): 25 is a small dot about 8 pixels across, 50 is about 16 pixels across. It does not change how far circles move. Only used by Circles.";

export const circleResizeHelp =
  "Off by default. When on, the size of each circle also follows the energy of its note: the radius goes from the chosen size for the faintest note to three times it for the loudest note of the whole file, in a straight line along the same scale as the colors, so no circle is smaller than the size. A circle keeps the size it was given when it was put down. Only used by Circles.";

export const circleMemoryHelp =
  "100 to 500 circles. How many of the most recent circles stay in the picture; when it is full the oldest is dropped. A larger memory leaves a longer trail. The newest circle is drawn solid and older ones fade with their age, so the oldest, just before it is dropped, is barely visible. The background is the middle color of the color map. Only used by Circles.";

export const circleNotesHelp =
  "5 to 12. How many of the strongest notes of each frame put a circle down; the circle of the strongest continues from the strongest circle of the previous frame, and so on down the ranks. More notes make a busier picture. Only used by Circles.";
