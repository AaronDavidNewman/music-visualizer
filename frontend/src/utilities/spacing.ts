// Window spacing: how far apart analysis windows start, as a multiple of the window size.
// The default and the one-sample minimum are mirrored in backend/app/services/window_spacing.py;
// both test suites share a table of expected values.

const spacingMessage = "The window spacing must be a number greater than 0.";

/** Smallest spacing: one sample, as a multiple of the window size. */
export function minSpacing(windowSize: number): number {
  return 1 / windowSize;
}

/** Distance in samples between window starts. */
export function stepSamples(spacing: number, windowSize: number): number {
  return spacing * windowSize;
}

/** Distance in milliseconds between window starts. */
export function stepMilliseconds(spacing: number, windowSize: number, sampleRate: number): number {
  return (stepSamples(spacing, windowSize) / sampleRate) * 1000;
}

/** Returns an error message, or null when the text is a finite number greater than 0. */
export function validateSpacing(value: string | number): string | null {
  const text = String(value).trim();
  const n = text === "" ? NaN : Number(text);
  return Number.isFinite(n) && n > 0 ? null : spacingMessage;
}

/** Plain decimal text with at most 6 decimals and no trailing zeros (never exponent notation). */
export function formatSpacing(value: number): string {
  return parseFloat(value.toFixed(6)).toString();
}

/** Sample rate assumed before a file is chosen, and when a file's rate cannot be read. */
export const DEFAULT_SAMPLE_RATE = 44100;

/**
 * Spacing that gives each frame its own window: one frame period in samples, over the window size,
 * rounded down to 6 decimals so the step is never longer than a frame period.
 * Returns null when the frame rate is not a positive number.
 */
export function defaultSpacing(sampleRate: number, frameRate: string | number, windowSize: number): number | null {
  const text = String(frameRate).trim();
  const fps = text === "" ? NaN : Number(text);
  if (!Number.isFinite(fps) || fps <= 0) return null;
  return Math.floor((1e6 * (sampleRate / fps)) / windowSize + 1e-9) / 1e6;
}

/** True when the spacing would give a step under one sample (the server raises it to the minimum). */
export function isBelowMinimum(spacing: number, windowSize: number): boolean {
  return spacing * windowSize < 1;
}

/** Notice shown while the typed spacing is below the one-sample minimum. */
export function minimumMessage(windowSize: number): string {
  return `The spacing will be raised to ${formatSpacing(minSpacing(windowSize))} so the step is one sample.`;
}
