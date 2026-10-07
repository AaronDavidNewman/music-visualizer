import { describe, expect, it } from "vitest";
import {
  BRIGHTNESS_RANGE,
  SMOOTHING_RANGE,
  DEFAULT_BRIGHTNESS,
  DEFAULT_ENERGY,
  DEFAULT_SMOOTHING,
  DEFAULT_WINDOW_SIZE,
  ENERGY_RANGE,
  WINDOW_SIZES,
  formatSmoothing,
  validateBrightness,
  validateEnergy,
  validateFile,
  validateFrameRate,
  validateSmoothing,
  validateWindowSize,
} from "./validation";

describe("window sizes", () => {
  it("are the powers of 2 from 4096 to 32768", () => {
    expect([...WINDOW_SIZES]).toEqual([4096, 8192, 16384, 32768]);
    expect(DEFAULT_WINDOW_SIZE).toBe(4096);
  });
});

describe("validateWindowSize", () => {
  it.each(["4096", "8192", "16384", "32768", 4096])("accepts %s", (v) => {
    expect(validateWindowSize(v)).toBeNull();
  });

  it.each(["2048", "256", "4095", "5000", "65536", "0", "-4096", "4096.5", "", "abc", "  "])(
    "rejects %j",
    (v) => {
      const msg = validateWindowSize(v);
      expect(msg).not.toBeNull();
      expect(msg).toContain("4096");
      expect(msg).toContain("32768");
    },
  );
});

describe("validateFrameRate", () => {
  it.each(["1", "30", "60", "29.97", 24])("accepts %s", (v) => {
    expect(validateFrameRate(v)).toBeNull();
  });

  it.each(["0", "61", "0.5", "", "abc"])("rejects %j", (v) => {
    const msg = validateFrameRate(v);
    expect(msg).not.toBeNull();
    expect(msg).toContain("1");
    expect(msg).toContain("60");
  });
});

describe("validateFile", () => {
  it("rejects a missing file", () => {
    expect(validateFile(null)).toMatch(/choose/i);
  });

  it("rejects non-wav names", () => {
    expect(validateFile({ name: "song.mp3" })).toMatch(/\.wav/i);
    expect(validateFile({ name: "wav" })).toMatch(/\.wav/i);
  });

  it("accepts .wav in any case", () => {
    expect(validateFile({ name: "Song.WAV" })).toBeNull();
    expect(validateFile({ name: "my song.wav" })).toBeNull();
  });
});

describe("saturation (the API's brightness setting)", () => {
  it("is a whole number from 2 to 100, defaulting to 2", () => {
    expect(BRIGHTNESS_RANGE).toEqual({ min: 2, max: 100 });
    expect(DEFAULT_BRIGHTNESS).toBe(2);
  });

  it.each(["2", "3", "50", "100", 7, "5.0", " 10 "])("accepts %s", (v) => {
    expect(validateBrightness(v)).toBeNull();
  });

  it.each(["1", "101", "0", "-3", "2.5", "", "  ", "abc", "NaN", "Infinity", "1e9", "99.9"])("rejects %j", (v) => {
    expect(validateBrightness(v)).toBe("The saturation must be a whole number from 2 to 100.");
  });
});

describe("brightness (the API's energy setting)", () => {
  it("is a whole number from 1 to 8, defaulting to 1", () => {
    expect(ENERGY_RANGE).toEqual({ min: 1, max: 8 });
    expect(DEFAULT_ENERGY).toBe(1);
  });

  it.each(["1", "2", "8", "5", 4, "3.0", " 6 "])("accepts %s", (v) => {
    expect(validateEnergy(v)).toBeNull();
  });

  it.each(["0", "9", "-1", "2.5", "", "  ", "abc", "NaN", "Infinity", "-Infinity", "1e9", 0, 9, NaN, Infinity])(
    "rejects %j",
    (v) => {
      expect(validateEnergy(v)).toBe("The brightness must be a whole number from 1 to 8.");
    },
  );
});

describe("smoothing", () => {
  it("is a number from 0 to 0.8 in steps of 0.01, defaulting to 0", () => {
    expect(SMOOTHING_RANGE).toEqual({ min: 0, max: 0.8, step: 0.01 });
    expect(DEFAULT_SMOOTHING).toBe(0);
  });

  it("gives the slider 81 positions with the right end at exactly 0.8", () => {
    const { min, max, step } = SMOOTHING_RANGE;
    expect(Math.round((max - min) / step) + 1).toBe(81);
    expect(Math.round(max * 100) / 100).toBe(0.8);
    expect(Math.round(min * 100) / 100).toBe(0);
  });

  it.each([0, 0.8, "0.35", "0", "0.80", 0.01, " 0.5 "])("accepts %s", (v) => {
    expect(validateSmoothing(v)).toBeNull();
  });

  it.each([-0.01, 0.81, 1, "", "  ", "abc", "NaN", "Infinity", "-Infinity", "1e9"])("rejects %j", (v) => {
    expect(validateSmoothing(v)).toBe("The smoothing must be a number from 0.0 to 0.8.");
  });

  it("formats with two decimals and no float noise", () => {
    expect(formatSmoothing(0)).toBe("0.00");
    expect(formatSmoothing(0.3)).toBe("0.30");
    expect(formatSmoothing(0.30000000000000004)).toBe("0.30");
    expect(formatSmoothing(0.8)).toBe("0.80");
    expect(formatSmoothing(0.35)).toBe("0.35");
  });
});
