import { describe, expect, it } from "vitest";
import {
  BLEND_WIDTH_RANGE,
  COLORMAPS,
  DEFAULT_COLORMAP,
  colormapLabel,
  validateColormap,
  DEFAULT_BLEND_WIDTH,
  DEFAULT_IMAGE_TYPE,
  IMAGE_TYPES,
  SMOOTHING_RANGE,
  SMOOTHING_WINDOW_RANGE,
  DEFAULT_SMOOTHING,
  DEFAULT_SMOOTHING_WINDOW,
  DEFAULT_THRESHOLD,
  DEFAULT_WINDOW_SIZE,
  THRESHOLD_RANGE,
  WINDOW_SIZES,
  formatBlendWidth,
  formatBlendWidthSummary,
  formatSmoothing,
  imageTypeLabel,
  formatThreshold,
  formatThresholdSummary,
  validateFile,
  validateFrameRate,
  validateBlendWidth,
  validateImageType,
  validateSmoothing,
  validateSmoothingWindow,
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

describe("image type", () => {
  it("offers Tiles then Blended tiles and starts at tiles", () => {
    expect(IMAGE_TYPES.map((t) => [t.value, t.label])).toEqual([
      ["tiles", "Tiles"],
      ["blended", "Blended tiles"],
    ]);
    expect(DEFAULT_IMAGE_TYPE).toBe("tiles");
    expect(imageTypeLabel("tiles")).toBe("Tiles");
    expect(imageTypeLabel("blended")).toBe("Blended tiles");
  });

  it.each(["tiles", "blended"])("accepts %j", (v) => {
    expect(validateImageType(v)).toBeNull();
  });

  it.each(["", "Tiles", " blended", "gradient", "tiles,blended"])("rejects %j", (v) => {
    expect(validateImageType(v)).toBe("The image type must be one of tiles, blended.");
  });
});

describe("blend width", () => {
  it("ranges from 10 to 25 in steps of 1 and starts at 25", () => {
    expect(BLEND_WIDTH_RANGE).toEqual({ min: 10, max: 25, step: 1 });
    expect(DEFAULT_BLEND_WIDTH).toBe(25);
  });

  it.each([10, 25, 17, "12.5", "20", 12.5])("accepts %j", (v) => {
    expect(validateBlendWidth(v)).toBeNull();
  });

  it.each([9.99, 26, 0, -10, 100, "", "  ", "abc", "NaN", "Infinity", "15%"])("rejects %j", (v) => {
    expect(validateBlendWidth(v)).toBe("The blend width must be a number from 10 to 25.");
  });

  it("shows the readout and the summary as percentages", () => {
    expect(formatBlendWidth(25)).toBe("25% of a tile");
    expect(formatBlendWidth(12.5)).toBe("12.5% of a tile");
    expect(formatBlendWidth(0.1 + 0.2 + 14.7)).toBe("15% of a tile");
    expect(formatBlendWidthSummary(15)).toBe("15%");
    expect(formatBlendWidthSummary(12.5)).toBe("12.5%");
  });
});

describe("colormap", () => {
  it("offers Summer, Autumn, Hot and Cool in that order and starts at hot", () => {
    expect(COLORMAPS.map((c) => [c.value, c.label])).toEqual([
      ["summer", "Summer"],
      ["autumn", "Autumn"],
      ["hot", "Hot"],
      ["cool", "Cool"],
    ]);
    expect(DEFAULT_COLORMAP).toBe("hot");
    expect(colormapLabel("hot")).toBe("Hot");
    expect(colormapLabel("cool")).toBe("Cool");
  });

  it.each(["summer", "autumn", "hot", "cool"])("accepts %j", (v) => {
    expect(validateColormap(v)).toBeNull();
  });

  it.each(["", "Hot", "HOT", " hot", "viridis", "hot_r", "gray"])("rejects %j", (v) => {
    expect(validateColormap(v)).toBe("The colormap must be one of summer, autumn, hot, cool.");
  });
});
