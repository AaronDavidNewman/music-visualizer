import { BRIGHTNESS_RANGE, ENERGY_RANGE, FRAME_RATE_RANGE } from "./validation";

/** The explanation behind each setting's info button. Problems the user must act on are not here: they stay inline. */
export const windowSizeHelp = "Larger windows separate low notes better but blur changes over time.";

export const frameRateHelp = `${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`;

// Shown as the Saturation setting (the API's brightness): a root on each tile's note level.
export const brightnessHelp = `Whole number, ${BRIGHTNESS_RANGE.min} to ${BRIGHTNESS_RANGE.max}. How strongly a tile's color shows follows how strong its note is. Higher values give quiet notes stronger colors but show less contrast.`;

// Shown as the Brightness setting (the API's energy): a root on how loud each frame is.
export const energyHelp = `Whole number, ${ENERGY_RANGE.min} to ${ENERGY_RANGE.max}. How bright the whole picture is follows how loud the sound is, compared with the loudest moment. Higher values make quiet passages brighter; 1 is a straight proportion.`;

export const smoothingHelp = "0 is no smoothing; higher values fade notes more slowly.";

/** The spacing explanation, followed by the live step between windows when the value is usable (`stepHint` is empty otherwise). */
export function spacingHelp(stepHint: string): string {
  const base = "Distance between the starts of windows, as a multiple of the window size.";
  return stepHint ? `${base} ${stepHint}` : base;
}
