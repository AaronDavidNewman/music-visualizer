import { describe, expect, it } from "vitest";
import { frameAtElapsed, frameTime, preloadRange } from "./playback";

describe("frameAtElapsed", () => {
  it("advances at the frame rate", () => {
    expect(frameAtElapsed(0, 0, 30, 100, false)).toEqual({ index: 0, finished: false });
    expect(frameAtElapsed(0, 0.5, 30, 100, false)).toEqual({ index: 15, finished: false });
    expect(frameAtElapsed(10, 1, 30, 100, false)).toEqual({ index: 40, finished: false });
  });

  it("stops on the last frame when not looping", () => {
    expect(frameAtElapsed(0, 10, 30, 100, false)).toEqual({ index: 99, finished: true });
    expect(frameAtElapsed(0, 99 / 30, 30, 100, false)).toEqual({ index: 99, finished: true });
  });

  it("wraps around when looping", () => {
    expect(frameAtElapsed(0, 100 / 30, 30, 100, true)).toEqual({ index: 0, finished: false });
    expect(frameAtElapsed(90, 15 / 30, 30, 100, true)).toEqual({ index: 5, finished: false });
  });

  it("skips ahead after a long stall instead of crawling", () => {
    expect(frameAtElapsed(0, 2, 30, 1000, false).index).toBe(60);
  });

  it("is not thrown off by floating-point noise", () => {
    // 0.1 * 30 is 3.0000000000000004 in floating point; 0.3 * 10 is 3.0000000000000004 too
    expect(frameAtElapsed(0, 0.3, 10, 100, false).index).toBe(3);
    expect(frameAtElapsed(0, 0.7, 10, 100, false).index).toBe(7);
  });

  it("handles a single-frame result", () => {
    expect(frameAtElapsed(0, 5, 30, 1, false)).toEqual({ index: 0, finished: true });
    expect(frameAtElapsed(0, 5, 30, 1, true)).toEqual({ index: 0, finished: false });
  });
});

describe("frameTime", () => {
  it("gives the start time of a frame in seconds", () => {
    expect(frameTime(45, 30)).toBe(1.5);
    expect(frameTime(0, 30)).toBe(0);
    expect(frameTime(5, 10)).toBe(0.5);
  });
});

describe("preloadRange", () => {
  it("lists the next frames, clamped to valid indexes", () => {
    expect(preloadRange(0, 100, 3)).toEqual([1, 2, 3]);
    expect(preloadRange(98, 100, 5)).toEqual([99]);
    expect(preloadRange(99, 100, 5)).toEqual([]);
    expect(preloadRange(0, 1, 5)).toEqual([]);
  });
});
