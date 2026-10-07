import { describe, expect, it } from "vitest";
import {
  DEFAULT_SAMPLE_RATE,
  defaultSpacing,
  formatSpacing,
  isBelowMinimum,
  minimumMessage,
  minSpacing,
  stepMilliseconds,
  stepSamples,
  validateSpacing,
} from "./spacing";

describe("minSpacing and step", () => {
  it("minimum spacing is one sample", () => {
    expect(minSpacing(4096)).toBe(1 / 4096);
    expect(minSpacing(32768)).toBe(1 / 32768);
  });

  it("step in samples is spacing times window size", () => {
    expect(stepSamples(0.25, 8192)).toBe(2048);
    expect(stepSamples(1, 4096)).toBe(4096);
    expect(stepSamples(2, 4096)).toBe(8192);
  });

  it("step in milliseconds uses the sample rate", () => {
    expect(stepMilliseconds(0.25, 8192, 44100)).toBeCloseTo(46.4399, 3);
    expect(stepMilliseconds(1, 4096, 48000)).toBeCloseTo(85.3333, 3);
  });
});

describe("validateSpacing", () => {
  it.each(["0.25", "1", "2", "1e-3", 0.3, "100"])("accepts %s", (v) => {
    expect(validateSpacing(v)).toBeNull();
  });

  it.each(["", "  ", "0", "-1", "-0.5", "abc", "Infinity", "NaN", "1,5"])("rejects %j", (v) => {
    expect(validateSpacing(v)).toBe("The window spacing must be a number greater than 0.");
  });
});

describe("formatSpacing", () => {
  it("shows plain decimals without trailing zeros", () => {
    expect(formatSpacing(0.25)).toBe("0.25");
    expect(formatSpacing(1)).toBe("1");
    expect(formatSpacing(0.358886)).toBe("0.358886");
    expect(formatSpacing(2)).toBe("2");
  });

  it("never uses exponent notation for values of at least 0.000001", () => {
    expect(formatSpacing(0.000001)).toBe("0.000001");
    expect(formatSpacing(1 / 32768)).toBe("0.000031");
    expect(formatSpacing(0.0000123)).not.toMatch(/e/i);
  });
});

// Shared with backend/tests/test_window_spacing.py: [sampleRate, frameRate, windowSize, expected]
const DEFAULT_TABLE: [number, number, number, number][] = [
  [44100, 30, 4096, 0.358886],
  [44100, 60, 4096, 0.179443],
  [44100, 60, 8192, 0.089721],
  [48000, 30, 4096, 0.390625],
  [44100, 30, 32768, 0.04486],
];

describe("defaultSpacing", () => {
  it.each(DEFAULT_TABLE)("(%d Hz, %d fps, window %d) is %d", (sampleRate, frameRate, windowSize, expected) => {
    expect(defaultSpacing(sampleRate, frameRate, windowSize)).toBeCloseTo(expected, 9);
  });

  it("assumes 44.1 kHz when no file is chosen", () => {
    expect(DEFAULT_SAMPLE_RATE).toBe(44100);
  });

  it("accepts the frame rate as text", () => {
    expect(defaultSpacing(44100, "30", 4096)).toBeCloseTo(0.358886, 9);
  });

  it.each(["", "  ", "0", "-5", "abc", NaN, 0, -1])("returns null for frame rate %j", (frameRate) => {
    expect(defaultSpacing(44100, frameRate, 4096)).toBeNull();
  });

  it("is rounded down: the step never exceeds one frame period", () => {
    for (const sampleRate of [44100, 48000]) {
      for (const frameRate of [1, 7, 24, 29.97, 30, 60]) {
        for (const windowSize of [4096, 8192, 16384, 32768]) {
          const spacing = defaultSpacing(sampleRate, frameRate, windowSize)!;
          expect(spacing * windowSize).toBeLessThanOrEqual(sampleRate / frameRate + 1e-9);
        }
      }
    }
  });
});

describe("minimum spacing notice", () => {
  it("is below the minimum when the step would be under one sample", () => {
    expect(isBelowMinimum(0.00001, 4096)).toBe(true);
    expect(isBelowMinimum(0.0002, 4096)).toBe(true);
    expect(isBelowMinimum(1 / 4096, 4096)).toBe(false);
    expect(isBelowMinimum(0.001, 4096)).toBe(false);
    expect(isBelowMinimum(2, 4096)).toBe(false);
  });

  it("tells the user what the value will be raised to", () => {
    expect(minimumMessage(4096)).toBe("The spacing will be raised to 0.000244 so the step is one sample.");
    expect(minimumMessage(32768)).toBe("The spacing will be raised to 0.000031 so the step is one sample.");
  });
});
