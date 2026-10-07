import { BRIGHTNESS_RANGE, FRAME_RATE_RANGE } from "./validation";

/** The explanation behind each setting's info button. Problems the user must act on are not here: they stay inline. */
export const windowSizeHelp = "Larger windows separate low notes better but blur changes over time.";

export const frameRateHelp = `${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`;

export const brightnessHelp = `Whole number, ${BRIGHTNESS_RANGE.min} to ${BRIGHTNESS_RANGE.max}. Higher values lift quiet notes more but show less contrast.`;

export const smoothingHelp = "0 is no smoothing; higher values fade notes more slowly.";

/** The spacing explanation, followed by the live step between windows when the value is usable (`stepHint` is empty otherwise). */
export function spacingHelp(stepHint: string): string {
  const base = "Distance between the starts of windows, as a multiple of the window size.";
  return stepHint ? `${base} ${stepHint}` : base;
}
