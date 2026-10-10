import { describe, expect, it } from "vitest";
import {
  BRIGHTNESS_RANGE,
  SMOOTHING_RANGE,
  SMOOTHING_WINDOW_RANGE,
  DEFAULT_BRIGHTNESS,
  DEFAULT_ENERGY,
  DEFAULT_SMOOTHING,
  DEFAULT_SMOOTHING_WINDOW,
  DEFAULT_STEP,
  DEFAULT_THRESHOLD,
  DEFAULT_WINDOW_SIZE,
  ENERGY_RANGE,
  HUE_SCALE,
  HUE_STEPS,
  THRESHOLD_RANGE,
  UNIT_SCALE,
  UNIT_STEPS,
  WINDOW_SIZES,
  formatSmoothing,
  formatThreshold,
  formatThresholdSummary,
  levelCount,
  levelLabel,
  stepToNumber,
  validateBrightness,
  validateEnergy,
  validateFile,
  validateFrameRate,
  validateSmoothing,
  validateSmoothingWindow,
  validateStep,
  validateThreshold,
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

describe("color level steps", () => {
  it("are the allowed choices, on scales of 360 and 100, starting at N/A", () => {
    expect([...HUE_STEPS]).toEqual([12, 36, 90, 180]);
    expect([...UNIT_STEPS]).toEqual([5, 10, 20, 50]);
    expect([HUE_SCALE, UNIT_SCALE]).toEqual([360, 100]);
    expect(DEFAULT_STEP).toBe("N/A");
  });

  it("give round((scale + step) / step) levels, never fewer than 3", () => {
    expect(HUE_STEPS.map((s) => levelCount(s, HUE_SCALE))).toEqual([31, 11, 5, 3]);
    expect(UNIT_STEPS.map((s) => levelCount(s, UNIT_SCALE))).toEqual([21, 11, 6, 3]);
  });

  it("label the choice with its level count", () => {
    expect(levelLabel("N/A", UNIT_SCALE)).toBe("N/A (smooth)");
    expect(levelLabel("n/a", UNIT_SCALE)).toBe("N/A (smooth)");
    expect(levelLabel("20", UNIT_SCALE)).toBe("20 (6 levels)");
    expect(levelLabel(10, UNIT_SCALE)).toBe("10 (11 levels)");
    expect(levelLabel("90", HUE_SCALE)).toBe("90 (5 levels)");
    expect(levelLabel("12", HUE_SCALE)).toBe("12 (31 levels)");
    expect(levelLabel("", HUE_SCALE)).toBe("");
  });

  it.each(["N/A", "n/a", " N/A ", "12", "36", "90", "180", 90])("accepts %j for hue", (v) => {
    expect(validateStep(v, HUE_STEPS, "hue")).toBeNull();
  });

  it.each(["N/A", "5", "10", "20", "50", 50])("accepts %j for saturation", (v) => {
    expect(validateStep(v, UNIT_STEPS, "saturation")).toBeNull();
  });

  it.each(["", "0", "7", "51", "abc", "2.5", "-5", "5", "NaN", "Infinity"])("rejects %j for hue", (v) => {
    expect(validateStep(v, HUE_STEPS, "hue")).toBe("The hue step must be N/A or one of 12, 36, 90, 180.");
  });

  it.each(["", "0", "7", "51", "abc", "2.5", "90", "180"])("rejects %j for brightness", (v) => {
    expect(validateStep(v, UNIT_STEPS, "brightness")).toBe("The brightness step must be N/A or one of 5, 10, 20, 50.");
  });

  it("turns the choice into the value that is sent", () => {
    expect(stepToNumber("N/A")).toBeNull();
    expect(stepToNumber("n/a")).toBeNull();
    expect(stepToNumber("20")).toBe(20);
    expect(stepToNumber("180")).toBe(180);
  });
});

describe("threshold", () => {
  it("ranges from 0 (off) to 10 in steps of 1 and starts at 0", () => {
    expect(THRESHOLD_RANGE).toEqual({ min: 0, max: 10, step: 1 });
    expect(DEFAULT_THRESHOLD).toBe(0);
  });

  it.each([0, 1, 5, 10, "7", "2.5", "0", 2.5])("accepts %j", (v) => {
    expect(validateThreshold(v)).toBeNull();
  });

  it.each([-1, -0.01, 10.01, 11, 100, "", "  ", "abc", "NaN", "Infinity", "-Infinity", "1e9", "20%"])("rejects %j", (v) => {
    expect(validateThreshold(v)).toBe("The threshold must be a number from 0 to 10.");
  });

  it("shows Off at the left end and the percentage of the loudest note otherwise", () => {
    expect(formatThreshold(0)).toBe("Off");
    expect(formatThreshold(1)).toBe("1% of the loudest note");
    expect(formatThreshold(10)).toBe("10% of the loudest note");
    expect(formatThreshold(2.5)).toBe("2.5% of the loudest note");
    expect(formatThreshold(0.1 + 0.2)).toBe("0.3% of the loudest note");
  });

  it("shows Off or the percentage in the result summary", () => {
    expect(formatThresholdSummary(0)).toBe("Off");
    expect(formatThresholdSummary(7)).toBe("7%");
    expect(formatThresholdSummary(2.5)).toBe("2.5%");
  });
});

describe("smoothing window", () => {
  it("is a whole number from 1 to 20 and starts at 1", () => {
    expect(SMOOTHING_WINDOW_RANGE).toEqual({ min: 1, max: 20 });
    expect(DEFAULT_SMOOTHING_WINDOW).toBe(1);
  });

  it.each([1, 5, 20, "1", "20", "7", " 7 "])("accepts %j", (v) => {
    expect(validateSmoothingWindow(v)).toBeNull();
  });

  it.each([0, 21, -1, 2.5, "", "  ", "abc", "NaN", "Infinity", "1e9", "5%"])("rejects %j", (v) => {
    expect(validateSmoothingWindow(v)).toBe("The smoothing window must be a whole number from 1 to 20.");
  });
});
