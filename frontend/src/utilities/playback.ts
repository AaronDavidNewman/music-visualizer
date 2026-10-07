// Guards floor() against floating-point noise such as 0.3 * 10 = 3.0000000000000004 or 0.7 * 10 = 7.000000000000001
const EPSILON = 1e-9;

export interface PlaybackPosition {
  index: number;
  finished: boolean;
}

/**
 * Frame to show `elapsedSeconds` after playback started at `startFrame`.
 * Based on elapsed time, so a late tick skips ahead rather than slowing the animation down.
 */
export function frameAtElapsed(
  startFrame: number,
  elapsedSeconds: number,
  frameRate: number,
  frameCount: number,
  loop: boolean,
): PlaybackPosition {
  const raw = startFrame + Math.floor(elapsedSeconds * frameRate + EPSILON);
  if (loop) {
    return { index: ((raw % frameCount) + frameCount) % frameCount, finished: false };
  }
  const last = frameCount - 1;
  return raw >= last ? { index: last, finished: true } : { index: raw, finished: false };
}

/** Start time in seconds of a frame. */
export function frameTime(index: number, frameRate: number): number {
  return index / frameRate;
}

/** Indexes of the `ahead` frames after `index`, clamped to the last frame. */
export function preloadRange(index: number, frameCount: number, ahead: number): number[] {
  const out: number[] = [];
  for (let i = index + 1; i <= Math.min(index + ahead, frameCount - 1); i++) out.push(i);
  return out;
}
