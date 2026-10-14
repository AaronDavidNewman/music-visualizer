/** Window sizes the user can choose: the powers of 2 from 4096 to 32768. */
export const WINDOW_SIZES = [4096, 8192, 16384, 32768] as const;
export const DEFAULT_WINDOW_SIZE = WINDOW_SIZES[0];
export const FRAME_RATE_RANGE = { min: 1, max: 60 } as const;
/** Smoothing is a running average of each note over the frames (0 = none). The slider moves in steps of 0.01. */
export const SMOOTHING_RANGE = { min: 0, max: 0.8, step: 0.01 } as const;
export const DEFAULT_SMOOTHING = SMOOTHING_RANGE.min;

const windowSizeMessage = `The window size must be one of ${WINDOW_SIZES.join(", ")}.`;
const smoothingMessage = `The smoothing must be a number from ${SMOOTHING_RANGE.min.toFixed(1)} to ${SMOOTHING_RANGE.max.toFixed(1)}.`;
const frameRateMessage = `The frame rate must be a number from ${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`;

function parseNumber(value: string | number): number {
  const text = String(value).trim();
  return text === "" ? NaN : Number(text);
}

/** Returns an error message, or null when the window size is one of the allowed sizes. */
export function validateWindowSize(value: string | number): string | null {
  const n = parseNumber(value);
  return (WINDOW_SIZES as readonly number[]).includes(n) ? null : windowSizeMessage;
}

/** Returns an error message, or null when the frame rate is valid. */
export function validateFrameRate(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= FRAME_RATE_RANGE.min && n <= FRAME_RATE_RANGE.max;
  return ok ? null : frameRateMessage;
}

/** Returns an error message, or null when a usable file is chosen. */
export function validateFile(file: { name: string } | null): string | null {
  if (!file) return "Choose a .wav file.";
  return file.name.toLowerCase().endsWith(".wav") && file.name.length > 4
    ? null
    : "The file must be a .wav file.";
}

/** Returns an error message, or null when the smoothing is a finite number from 0 to 0.8. */
export function validateSmoothing(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= SMOOTHING_RANGE.min && n <= SMOOTHING_RANGE.max;
  return ok ? null : smoothingMessage;
}

/** The smoothing as text with two decimals, such as "0.30" (no floating-point noise). */
export function formatSmoothing(value: number): string {
  return value.toFixed(2);
}

/** The threshold hides faint notes: a note below this percentage of the file's loudest note value is drawn black. 0 is off. The slider moves in steps of 1. */
export const THRESHOLD_RANGE = { min: 0, max: 10, step: 1 } as const;
export const DEFAULT_THRESHOLD = THRESHOLD_RANGE.min;

const thresholdMessage = `The threshold must be a number from ${THRESHOLD_RANGE.min} to ${THRESHOLD_RANGE.max}.`;

/** Returns an error message, or null when the threshold is a finite number from 0 to 10. */
export function validateThreshold(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= THRESHOLD_RANGE.min && n <= THRESHOLD_RANGE.max;
  return ok ? null : thresholdMessage;
}

/** The readout beside the slider: "Off" at 0, otherwise the percentage of the loudest note. */
export function formatThreshold(value: number): string {
  return value === 0 ? "Off" : `${Number(value.toFixed(2))}% of the loudest note`;
}

/** The result summary item: "Off" or the percentage such as "30%". */
export function formatThresholdSummary(value: number): string {
  return value === 0 ? "Off" : `${Number(value.toFixed(2))}%`;
}

/** Smoothing window: how many earlier frames are mixed into each frame (a whole number). */
export const SMOOTHING_WINDOW_RANGE = { min: 1, max: 20 } as const;
export const DEFAULT_SMOOTHING_WINDOW = SMOOTHING_WINDOW_RANGE.min;

const smoothingWindowMessage = `The smoothing window must be a whole number from ${SMOOTHING_WINDOW_RANGE.min} to ${SMOOTHING_WINDOW_RANGE.max}.`;

/** Returns an error message, or null when the smoothing window is a whole number from 1 to 20. */
export function validateSmoothingWindow(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= SMOOTHING_WINDOW_RANGE.min && n <= SMOOTHING_WINDOW_RANGE.max;
  return ok ? null : smoothingWindowMessage;
}

/**
 * The kinds of picture: Tiles (flat tiles with hard edges, the default), Blended tiles (colors fade across the tile
 * edges) and Contour (the notes drawn as a filled contour map).
 */
export const IMAGE_TYPES = [
  { value: "tiles", label: "Tiles" },
  { value: "blended", label: "Blended tiles" },
  { value: "contour", label: "Contour" },
  { value: "circles", label: "Circles" },
] as const;
export const DEFAULT_IMAGE_TYPE = "tiles";

const imageTypeMessage = `The image type must be one of ${IMAGE_TYPES.map((t) => t.value).join(", ")}.`;

/** The name shown for an image type value such as "blended". */
export function imageTypeLabel(value: string): string {
  return IMAGE_TYPES.find((t) => t.value === value)?.label ?? value;
}

/** Returns an error message, or null when the image type is exactly one of the offered values. */
export function validateImageType(value: string): string | null {
  return IMAGE_TYPES.some((t) => t.value === value) ? null : imageTypeMessage;
}

/** Whether the blend width does anything for this image type: only Blended tiles fade across the tile edges. */
export function blendWidthApplies(imageType: string): boolean {
  return imageType === "blended";
}

/** The blend width: how far the fade between tiles reaches on each side of an edge, as a percentage of the tile width. */
export const BLEND_WIDTH_RANGE = { min: 10, max: 25, step: 1 } as const;
export const DEFAULT_BLEND_WIDTH = BLEND_WIDTH_RANGE.max;

const blendWidthMessage = `The blend width must be a number from ${BLEND_WIDTH_RANGE.min} to ${BLEND_WIDTH_RANGE.max}.`;

/** Returns an error message, or null when the blend width is a finite number from 10 to 25. */
export function validateBlendWidth(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= BLEND_WIDTH_RANGE.min && n <= BLEND_WIDTH_RANGE.max;
  return ok ? null : blendWidthMessage;
}

/** The readout beside the slider, such as "25% of a tile". */
export function formatBlendWidth(value: number): string {
  return `${Number(value.toFixed(2))}% of a tile`;
}

/** The result summary item, such as "25%". */
export function formatBlendWidthSummary(value: number): string {
  return `${Number(value.toFixed(2))}%`;
}
// "coolwarm", "YlOrRd", "inferno", "Blues", "YlGn", "Greys", "hsv"
/** The colormaps that can be chosen: four of matplotlib's named scales. A tile's color is the color of the chosen scale at its note's strength. */
export const COLORMAPS = [
  { value: "coolwarm", label: "Cool Warm" },
  { value: "YlOrRd", label: "Autumn" },
  { value: "inferno", label: "Hot" },
  { value: "Blues", label: "Blues" },
  { value: "viridis", label: "Viridis"},
  { value: "Greys", label: "Grayscale"},
  { value: "hsv", label: "HSV"}
] as const;
export const DEFAULT_COLORMAP = "coolwarm";

const colormapMessage = `The colormap must be one of ${COLORMAPS.map((c) => c.value).join(", ")}.`;

/** The name shown for a colormap value such as "hot". */
export function colormapLabel(value: string): string {
  return COLORMAPS.find((c) => c.value === value)?.label ?? value;
}

/** Returns an error message, or null when the colormap is exactly one of the offered values. */
export function validateColormap(value: string): string | null {
  return COLORMAPS.some((c) => c.value === value) ? null : colormapMessage;
}

/** The original grid of a frame: 12 columns (the notes of an octave) by 7 rows (the octaves). */
export const GRID_COLUMNS = 12;
export const GRID_ROWS = 7;

/** The resolution: how many times finer than the original grid the picture is drawn (a whole number). */
export const RESOLUTION_RANGE = { min: 1, max: 5, step: 1 } as const;
export const DEFAULT_RESOLUTION = RESOLUTION_RANGE.min;

const resolutionMessage = `The resolution must be a whole number from ${RESOLUTION_RANGE.min} to ${RESOLUTION_RANGE.max}.`;

/** Returns an error message, or null when the resolution is a whole number from 1 to 5. */
export function validateResolution(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= RESOLUTION_RANGE.min && n <= RESOLUTION_RANGE.max;
  return ok ? null : resolutionMessage;
}

/** The readout beside the slider and the result summary item: "1\u00d7", or the multiple and its grid, "3\u00d7 (36 \u00d7 21)". */
export function formatResolution(value: number): string {
  return value === 1 ? "1\u00d7" : `${value}\u00d7 (${GRID_COLUMNS * value} \u00d7 ${GRID_ROWS * value})`;
}

/** The number of notes: how many of the 84 drawn notes make up the picture (the ones with the most energy). */
export const NOTE_COUNT_RANGE = { min: 12, max: GRID_COLUMNS * GRID_ROWS, step: 1 } as const;
export const DEFAULT_NOTE_COUNT = NOTE_COUNT_RANGE.max;

const noteCountMessage = `The number of notes must be a whole number from ${NOTE_COUNT_RANGE.min} to ${NOTE_COUNT_RANGE.max}.`;

/** Returns an error message, or null when the number of notes is a whole number from 12 to 84. */
export function validateNoteCount(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= NOTE_COUNT_RANGE.min && n <= NOTE_COUNT_RANGE.max;
  return ok ? null : noteCountMessage;
}

/** The readout beside the slider: "All 84 notes", or how many of the 84 are used, "36 of 84 notes". */
export function formatNoteCount(value: number): string {
  return value === NOTE_COUNT_RANGE.max ? `All ${NOTE_COUNT_RANGE.max} notes` : `${value} of ${NOTE_COUNT_RANGE.max} notes`;
}

/** The result summary item: "All 84" or "36 of 84". */
export function formatNoteCountSummary(value: number): string {
  return value === NOTE_COUNT_RANGE.max ? `All ${NOTE_COUNT_RANGE.max}` : `${value} of ${NOTE_COUNT_RANGE.max}`;
}

/** Interpolate: only every n-th frame is drawn, the frames between are made from their neighbors (a whole number). */
export const INTERPOLATE_RANGE = { min: 1, max: 5, step: 1 } as const;
export const DEFAULT_INTERPOLATE = INTERPOLATE_RANGE.min;

const interpolateMessage = `The interpolate value must be a whole number from ${INTERPOLATE_RANGE.min} to ${INTERPOLATE_RANGE.max}.`;

/** Returns an error message, or null when the interpolate value is a whole number from 1 to 5. */
export function validateInterpolate(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= INTERPOLATE_RANGE.min && n <= INTERPOLATE_RANGE.max;
  return ok ? null : interpolateMessage;
}

/** The readout beside the slider: "1 (every frame drawn)", or "3 (one frame in 3 drawn)". */
export function formatInterpolate(value: number): string {
  return value === INTERPOLATE_RANGE.min ? `${value} (every frame drawn)` : `${value} (one frame in ${value} drawn)`;
}

/** The settings of the Circles image type: the unit in pixels, the size (circumference) in pixels, the memory in circles, the strongest notes per frame. */
export const CIRCLE_UNIT_RANGE = { min: 1, max: 10, step: 1 } as const;
export const DEFAULT_CIRCLE_UNIT = 4;
export const CIRCLE_SIZE_RANGE = { min: 25, max: 50, step: 1 } as const;
export const DEFAULT_CIRCLE_SIZE = 25;
export const DEFAULT_CIRCLE_RESIZE = false;
export const CIRCLE_MEMORY_RANGE = { min: 100, max: 500, step: 10 } as const;
export const DEFAULT_CIRCLE_MEMORY = 300;
export const CIRCLE_NOTES_RANGE = { min: 5, max: 12, step: 1 } as const;
export const DEFAULT_CIRCLE_NOTES = 8;

const circleUnitMessage = `The circle unit must be a whole number from ${CIRCLE_UNIT_RANGE.min} to ${CIRCLE_UNIT_RANGE.max}.`;
const circleSizeMessage = `The circle size must be a whole number from ${CIRCLE_SIZE_RANGE.min} to ${CIRCLE_SIZE_RANGE.max}.`;
const circleMemoryMessage = `The circle memory must be a whole number from ${CIRCLE_MEMORY_RANGE.min} to ${CIRCLE_MEMORY_RANGE.max}.`;
const circleNotesMessage = `The number of circle notes must be a whole number from ${CIRCLE_NOTES_RANGE.min} to ${CIRCLE_NOTES_RANGE.max}.`;

function validateWhole(value: string | number, min: number, max: number, message: string): string | null {
  const n = parseNumber(value);
  return Number.isInteger(n) && n >= min && n <= max ? null : message;
}

/** Returns an error message, or null when the unit is a whole number of pixels from 1 to 10. */
export function validateCircleUnit(value: string | number): string | null {
  return validateWhole(value, CIRCLE_UNIT_RANGE.min, CIRCLE_UNIT_RANGE.max, circleUnitMessage);
}

/** Returns an error message, or null when the size (the circumference) is a whole number of pixels from 25 to 50. */
export function validateCircleSize(value: string | number): string | null {
  return validateWhole(value, CIRCLE_SIZE_RANGE.min, CIRCLE_SIZE_RANGE.max, circleSizeMessage);
}

/** Returns an error message, or null when the memory is a whole number of circles from 100 to 500. */
export function validateCircleMemory(value: string | number): string | null {
  return validateWhole(value, CIRCLE_MEMORY_RANGE.min, CIRCLE_MEMORY_RANGE.max, circleMemoryMessage);
}

/** Returns an error message, or null when the circles per frame are a whole number from 5 to 12. */
export function validateCircleNotes(value: string | number): string | null {
  return validateWhole(value, CIRCLE_NOTES_RANGE.min, CIRCLE_NOTES_RANGE.max, circleNotesMessage);
}

/** The readouts beside the sliders, and the result summary items: "4 px", "25 px around", "300 circles", "8 notes". */
export function formatCircleUnit(value: number): string {
  return `${value} px`;
}
export function formatCircleSize(value: number): string {
  return `${value} px around`;
}
export function formatCircleResize(value: boolean): string {
  return value ? "On" : "Off";
}
export function formatCircleMemory(value: number): string {
  return `${value} circles`;
}
export function formatCircleNotes(value: number): string {
  return `${value} notes`;
}

/** Whether the settings that describe a grid of tiles (Threshold, Notes, Resolution, Interpolate) mean anything: not for circles. */
export function gridSettingsApply(imageType: string): boolean {
  return imageType !== "circles";
}
