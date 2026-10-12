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

/** The colormaps that can be chosen: four of matplotlib's named scales. A tile's color is the color of the chosen scale at its note's strength. */
export const COLORMAPS = [
  { value: "summer", label: "Summer" },
  { value: "autumn", label: "Autumn" },
  { value: "hot", label: "Hot" },
  { value: "cool", label: "Cool" },
  { value: "viridis", label: "Viridis"},
  { value: "Greys", label: "Grayscale"},
  { value: "hsv", label: "HSV"}
] as const;
export const DEFAULT_COLORMAP = "hot";

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
