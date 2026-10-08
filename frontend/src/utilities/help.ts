import { BRIGHTNESS_RANGE, ENERGY_RANGE, FRAME_RATE_RANGE, HUE_STEPS, THRESHOLD_RANGE, UNIT_STEPS } from "./validation";

/** The explanation behind each setting's info button. Problems the user must act on are not here: they stay inline. */
export const windowSizeHelp = "Larger windows separate low notes better but blur changes over time.";

export const frameRateHelp = `${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`;

// Shown as the Saturation setting (the API's brightness): a root on each tile's note level.
export const brightnessHelp = `Whole number, ${BRIGHTNESS_RANGE.min} to ${BRIGHTNESS_RANGE.max}. How strongly a tile's color shows follows how strong its note is. Higher values give quiet notes stronger colors but show less contrast.`;

// Shown as the Brightness setting (the API's energy): a root on how loud each frame is.
export const energyHelp = `Whole number, ${ENERGY_RANGE.min} to ${ENERGY_RANGE.max}. How bright the whole picture is follows how loud the sound is, compared with the loudest moment. Higher values make quiet passages brighter; 1 is a straight proportion.`;

// The three step settings round a finished value to evenly spaced levels (the multiples of the step up to the top of the scale).
const stepHelp = (what: string, steps: readonly number[], extra: string) =>
  `Rounds ${what} to a few evenly spaced levels. N/A leaves it smooth. Choose ${steps.join(", ")}: a larger step gives fewer, bolder levels. ${extra}`;

export const hueStepHelp = stepHelp(
  "each tile's hue",
  HUE_STEPS,
  "The levels are every step in degrees from 0 to 360, so 180 gives 3 levels (0°, 180°, 360°). Both ends of the wheel are red, so 180 gives only red and cyan.",
);

export const saturationStepHelp = stepHelp(
  "each tile's saturation",
  UNIT_STEPS,
  "The levels are every step from 0 to 100, so 50 gives 3 levels (0, 50, 100).",
);

export const brightnessStepHelp = stepHelp(
  "each frame's brightness",
  UNIT_STEPS,
  "The levels are every step from 0 to 100, so 50 gives 3 levels (black, half, full); the loudest frame stays at full brightness.",
);

export const thresholdHelp = `A note whose volume is below the threshold is drawn black. The threshold is a share of the loudest note in the whole file: ${THRESHOLD_RANGE.min} (the left end) is off, and ${THRESHOLD_RANGE.max} (the right end) is ${THRESHOLD_RANGE.max}% of the loudest note. Louder notes are never changed.`;

export const smoothingHelp = "0 is no smoothing; higher values fade notes more slowly.";

/** The spacing explanation, followed by the live step between windows when the value is usable (`stepHint` is empty otherwise). */
export function spacingHelp(stepHint: string): string {
  const base = "Distance between the starts of windows, as a multiple of the window size.";
  return stepHint ? `${base} ${stepHint}` : base;
}
