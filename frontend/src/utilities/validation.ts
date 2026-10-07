/** Window sizes the user can choose: the powers of 2 from 4096 to 32768. */
export const WINDOW_SIZES = [4096, 8192, 16384, 32768] as const;
export const DEFAULT_WINDOW_SIZE = WINDOW_SIZES[0];
export const FRAME_RATE_RANGE = { min: 1, max: 60 } as const;
/** The API's brightness setting, shown on the page as Saturation: the root applied to each gray level (2 is the square root). Whole numbers only. */
export const BRIGHTNESS_RANGE = { min: 2, max: 100 } as const;
export const DEFAULT_BRIGHTNESS = BRIGHTNESS_RANGE.min;
/** The API's energy setting, shown on the page as Brightness: the root applied to each frame's energy, relative to the loudest frame, to get the frame's brightness. Whole numbers only. */
export const ENERGY_RANGE = { min: 1, max: 8 } as const;
export const DEFAULT_ENERGY = ENERGY_RANGE.min;
/** Smoothing is a running average of each note over the frames (0 = none). The slider moves in steps of 0.01. */
export const SMOOTHING_RANGE = { min: 0, max: 0.8, step: 0.01 } as const;
export const DEFAULT_SMOOTHING = SMOOTHING_RANGE.min;

const windowSizeMessage = `The window size must be one of ${WINDOW_SIZES.join(", ")}.`;
const brightnessMessage = `The saturation must be a whole number from ${BRIGHTNESS_RANGE.min} to ${BRIGHTNESS_RANGE.max}.`;
const energyMessage = `The brightness must be a whole number from ${ENERGY_RANGE.min} to ${ENERGY_RANGE.max}.`;
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

/** Returns an error message, or null when the saturation (the API's brightness setting) is a whole number from 2 to 100. */
export function validateBrightness(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= BRIGHTNESS_RANGE.min && n <= BRIGHTNESS_RANGE.max;
  return ok ? null : brightnessMessage;
}

/** Returns an error message, or null when the brightness (the API's energy setting) is a whole number from 1 to 8. */
export function validateEnergy(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= ENERGY_RANGE.min && n <= ENERGY_RANGE.max;
  return ok ? null : energyMessage;
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
