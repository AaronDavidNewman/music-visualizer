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
  isCirclesType,
  GAUSSIAN_RANGE,
  DEFAULT_GAUSSIAN,
  formatGaussian,
  validateGaussian,
  formatThreshold,
  formatThresholdSummary,
  validateFile,
  validateFrameRate,
  blendWidthApplies,
  DEFAULT_NOTE_COUNT,
  DEFAULT_RESOLUTION,
  NOTE_COUNT_RANGE,
  formatNoteCount,
  formatNoteCountSummary,
  validateNoteCount,
  CIRCLE_MEMORY_RANGE,
  CIRCLE_RADIUS_RANGE,
  CIRCLE_NOTES_RANGE,
  CIRCLE_UNIT_RANGE,
  DEFAULT_CIRCLE_MEMORY,
  DEFAULT_CIRCLE_RESIZE,
  DEFAULT_CIRCLE_RADIUS,
  DEFAULT_CIRCLE_NOTES,
  DEFAULT_CIRCLE_UNIT,
  formatCircleMemory,
  formatCircleResize,
  formatCircleRadius,
  formatCircleNotes,
  formatCircleUnit,
  gridSettingsApply,
  validateCircleMemory,
  validateCircleRadius,
  validateCircleNotes,
  validateCircleUnit,
  DEFAULT_INTERPOLATE,
  INTERPOLATE_RANGE,
  formatInterpolate,
  validateInterpolate,
  RESOLUTION_RANGE,
  formatResolution,
  validateResolution,
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

  it("shows Off at the left end and just the percentage otherwise (the info text says of what)", () => {
    expect(formatThreshold(0)).toBe("Off");
    expect(formatThreshold(1)).toBe("1%");
    expect(formatThreshold(10)).toBe("10%");
    expect(formatThreshold(2.5)).toBe("2.5%");
    expect(formatThreshold(0.1 + 0.2)).toBe("0.3%");
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
  const values = IMAGE_TYPES.map((t) => t.value as string);

  it("offers Tiles, Blended tiles, Contour, Circles, Circles paint, Concentric, Decay, Decay Exp, Polar Chords, Energy graphs and Chromatic Decay in that order and starts at tiles", () => {
    expect(IMAGE_TYPES.map((t) => [t.value, t.label])).toEqual([
      ["tiles", "Tiles"],
      ["blended", "Blended tiles"],
      ["contour", "Contour"],
      ["circles", "Circles"],
      ["circles_paint", "Circles paint"],
      ["concentric", "Concentric"],
      ["decay", "Decay"],
      ["decay-exp", "Decay Exp"],
      ["polar-chords", "Polar Chords"],
      ["energy-graphs", "Energy graphs"],
      ["chromatic-decay", "Chromatic Decay"],
    ]);
    expect(DEFAULT_IMAGE_TYPE).toBe("tiles");
    expect(imageTypeLabel("tiles")).toBe("Tiles");
    expect(imageTypeLabel("blended")).toBe("Blended tiles");
    expect(imageTypeLabel("contour")).toBe("Contour");
    expect(imageTypeLabel("circles")).toBe("Circles");
    expect(imageTypeLabel("circles_paint")).toBe("Circles paint");
    expect(imageTypeLabel("concentric")).toBe("Concentric");
    expect(imageTypeLabel("decay")).toBe("Decay");
    expect(imageTypeLabel("decay-exp")).toBe("Decay Exp");
    expect(imageTypeLabel("polar-chords")).toBe("Polar Chords");
    expect(imageTypeLabel("energy-graphs")).toBe("Energy graphs");
    expect(imageTypeLabel("chromatic-decay")).toBe("Chromatic Decay");
  });

  it.each(values)("accepts %j", (v) => {
    expect(validateImageType(v)).toBeNull();
  });

  it.each(["", "Tiles", " blended", "Contour", "contour ", "contours", "Circles", "circle", "gradient", "tiles,blended", "circle_paint", "Circles_paint", "circles paint", "circles-paint", " circles_paint", "Concentric", "concentrics", "concentric ", "Decay", "decay ", "decays", "decay_exp", "decayexp", "Decay-Exp", "decay-exp ", "decay-", "polar_chords", "polarchords", "Polar-Chords", "polar-chords ", "polar-", "energy_graphs", "energygraphs", "Energy-Graphs", "energy-graphs ", "energy-", "chromatic_decay", "chromaticdecay", "Chromatic-Decay", "chromatic-decay ", "chromatic"])("rejects %j", (v) => {
    expect(validateImageType(v)).toBe("The image type must be one of tiles, blended, contour, circles, circles_paint, concentric, decay, decay-exp, polar-chords, energy-graphs, chromatic-decay.");
  });

  it("knows the two circle types, and the grid settings apply to neither", () => {
    expect(isCirclesType("circles")).toBe(true);
    expect(isCirclesType("circles_paint")).toBe(true);
    for (const type of ["tiles", "blended", "contour", "", "circle", "paint"]) expect(isCirclesType(type), type).toBe(false);
    expect(gridSettingsApply("circles")).toBe(false);
    expect(gridSettingsApply("circles_paint")).toBe(false);
    for (const type of ["tiles", "blended", "contour"]) expect(gridSettingsApply(type), type).toBe(true);
  });

  it("applies the blend width to Blended tiles only", () => {
    expect(blendWidthApplies("blended")).toBe(true);
    expect(blendWidthApplies("tiles")).toBe(false);
    expect(blendWidthApplies("contour")).toBe(false);
    expect(blendWidthApplies("circles")).toBe(false);
    expect(blendWidthApplies("")).toBe(false);
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

// Nothing here names a colormap: the list can be changed by hand. (That each name is a valid matplotlib colormap, and
// that this list matches the backend's, is checked by backend/tests/test_colormaps.py.)
describe("colormap", () => {
  const values = COLORMAPS.map((c) => c.value as string);
  const message = `The colormap must be one of ${values.join(", ")}.`;
  const rejected = ["", " ", "no_such_colormap", "1"]
    .concat(values.flatMap((v) => [v.toUpperCase(), v.toLowerCase(), ` ${v}`, `${v} `, `${v}_r`, `${v},`]))
    .filter((v) => !values.includes(v));

  it("offers at least one colormap, each with a distinct value and a label, and starts at one of them", () => {
    expect(values.length).toBeGreaterThan(0);
    expect(new Set(values).size).toBe(values.length);
    expect(COLORMAPS.every((c) => (c.value as string) !== "" && (c.label as string) !== "")).toBe(true);
    expect(values).toContain(DEFAULT_COLORMAP);
  });

  it.each(COLORMAPS.map((c) => [c.value, c.label]))("shows %j as %j", (value, label) => {
    expect(colormapLabel(value)).toBe(label);
  });

  it("shows an unknown value as it is", () => {
    expect(colormapLabel("no_such_colormap")).toBe("no_such_colormap");
  });

  it.each(values)("accepts %j", (v) => {
    expect(validateColormap(v)).toBeNull();
  });

  it.each(rejected)("rejects %j with the offered choices", (v) => {
    expect(validateColormap(v)).toBe(message);
  });
});

describe("resolution", () => {
  it("ranges from 1 to 5 in whole steps and starts at 1", () => {
    expect(RESOLUTION_RANGE).toEqual({ min: 1, max: 5, step: 1 });
    expect(DEFAULT_RESOLUTION).toBe(1);
  });

  it.each([1, 2, 3, 4, 5, "1", "5", " 3 ", 3.0])("accepts %j", (v) => {
    expect(validateResolution(v)).toBeNull();
  });

  it.each([0, 6, -1, 2.5, "", "  ", "abc", "NaN", "Infinity", "1e9", "3x", NaN, Infinity])("rejects %j", (v) => {
    expect(validateResolution(v)).toBe("The oversampling must be a whole number from 1 to 5.");
  });

  it("shows the multiple, and the grid it gives above 1", () => {
    expect(formatResolution(1)).toBe("1\u00d7");
    expect(formatResolution(2)).toBe("2\u00d7 (24 \u00d7 14)");
    expect(formatResolution(3)).toBe("3\u00d7 (36 \u00d7 21)");
    expect(formatResolution(5)).toBe("5\u00d7 (60 \u00d7 35)");
  });

  it("gives a grid of 12 times and 7 times the resolution for every offered value", () => {
    for (let r = RESOLUTION_RANGE.min; r <= RESOLUTION_RANGE.max; r += RESOLUTION_RANGE.step) {
      if (r > 1) expect(formatResolution(r)).toContain(`(${12 * r} \u00d7 ${7 * r})`);
    }
  });
});

describe("number of notes", () => {
  it("ranges from 12 to 84 in whole steps and starts at 84", () => {
    expect(NOTE_COUNT_RANGE).toEqual({ min: 12, max: 84, step: 1 });
    expect(DEFAULT_NOTE_COUNT).toBe(84);
  });

  it.each([12, 13, 48, 83, 84, "12", "84", " 36 ", 36.0])("accepts %j", (v) => {
    expect(validateNoteCount(v)).toBeNull();
  });

  it.each([0, 11, 85, -1, 36.5, "", "  ", "abc", "NaN", "Infinity", "1e9", "36x", NaN, Infinity])("rejects %j", (v) => {
    expect(validateNoteCount(v)).toBe("The number of notes must be a whole number from 12 to 84.");
  });

  it("says how many of the 84 notes are used", () => {
    expect(formatNoteCount(84)).toBe("All 84 notes");
    expect(formatNoteCount(36)).toBe("36 of 84 notes");
    expect(formatNoteCount(12)).toBe("12 of 84 notes");
    expect(formatNoteCountSummary(84)).toBe("All 84");
    expect(formatNoteCountSummary(24)).toBe("24 of 84");
  });
});

describe("interpolate", () => {
  it("ranges from 1 to 5 in whole steps and starts at 1", () => {
    expect(INTERPOLATE_RANGE).toEqual({ min: 1, max: 5, step: 1 });
    expect(DEFAULT_INTERPOLATE).toBe(1);
  });

  it.each([1, 2, 3, 4, 5, "1", "5", " 3 ", 3.0])("accepts %j", (v) => {
    expect(validateInterpolate(v)).toBeNull();
  });

  it.each([0, 6, -1, 2.5, "", "  ", "abc", "NaN", "Infinity", "1e9", "3x", NaN, Infinity])("rejects %j", (v) => {
    expect(validateInterpolate(v)).toBe("The interpolate value must be a whole number from 1 to 5.");
  });

  it("says how many frames are drawn", () => {
    expect(formatInterpolate(1).trim()).toBe("1");
    expect(formatInterpolate(3)).toBe("(1/3 frames)");
    expect(formatInterpolate(5)).toBe("(1/5 frames)");
  });
});

describe("gaussian smoothing", () => {
  it("ranges from 0 to 5 in steps of one half and starts at 0, which is off", () => {
    expect(GAUSSIAN_RANGE).toEqual({ min: 0, max: 5, step: 0.5 });
    expect(DEFAULT_GAUSSIAN).toBe(0);
  });

  it.each([0, 0.5, 1, 2.5, 4, 5, "3", " 4 ", 4.0, "0.5", "1e0"])("accepts %j", (v) => {
    expect(validateGaussian(v)).toBeNull();
  });

  it.each([-0.5, -1, 5.5, 6, "", "  ", "abc", "NaN", "Infinity", "-Infinity", "1e9", NaN, Infinity, "2,5"])("refuses %j with the server's message", (v) => {
    expect(validateGaussian(v)).toBe("The gaussian smoothing must be a number from 0 to 5.");
  });

  it("shows Off at zero and the number otherwise, in the readout and in the summary", () => {
    expect(formatGaussian(0)).toBe("Off");
    expect(formatGaussian(0.5)).toBe("0.5");
    expect(formatGaussian(4)).toBe("4");
    expect(formatGaussian(5)).toBe("5");
  });
});

describe("circles settings", () => {
  it("has no circumference setting any more (the size became the radius)", async () => {
    const all = (await import("./validation")) as Record<string, unknown>;
    for (const old of ["CIRCLE_SIZE_RANGE", "DEFAULT_CIRCLE_SIZE", "validateCircleSize", "formatCircleSize"]) expect(old in all, old).toBe(false);
  });

  it("has the ranges and defaults of the spec", () => {
    expect(CIRCLE_UNIT_RANGE).toMatchObject({ min: 1, max: 10, step: 1 });
    expect(CIRCLE_MEMORY_RANGE).toMatchObject({ min: 100, max: 500 });
    expect(CIRCLE_NOTES_RANGE).toMatchObject({ min: 5, max: 12, step: 1 });
    expect(CIRCLE_RADIUS_RANGE).toMatchObject({ min: 4, max: 8, step: 1 });
    expect([DEFAULT_CIRCLE_UNIT, DEFAULT_CIRCLE_MEMORY, DEFAULT_CIRCLE_NOTES, DEFAULT_CIRCLE_RADIUS]).toEqual([4, 300, 8, 4]);
    expect(DEFAULT_CIRCLE_RESIZE).toBe(false);
  });

  it.each([
    ["movement", validateCircleUnit, [1, 4, 10, "7", " 5 ", 3.0], [0, 11, -1, 2.5, "", "  ", "abc", "NaN", "Infinity", "1e9", NaN, Infinity], "The circle movement must be a whole number from 1 to 10."],
    ["radius", validateCircleRadius, [4, 6, 8, "5", " 7 ", 6.0], [0, 3, 9, 4.5, "", "  ", "abc", "NaN", "Infinity", "1e9", NaN, Infinity], "The circle radius must be a whole number from 4 to 8."],
    ["memory", validateCircleMemory, [100, 300, 500, "250", " 400 ", 200.0], [0, 99, 501, 250.5, "", "abc", "NaN", "Infinity", "1e9", NaN, Infinity], "The circle memory must be a whole number from 100 to 500."],
    ["notes", validateCircleNotes, [5, 8, 12, "6", " 9 ", 7.0], [0, 4, 13, 7.5, "", "abc", "NaN", "Infinity", "1e9", NaN, Infinity], "The number of circle notes must be a whole number from 5 to 12."],
  ] as const)("the %s validator accepts the whole numbers of its range and refuses the rest with the server's message", (_name, check, good, bad, message) => {
    for (const v of good) expect(check(v), String(v)).toBeNull();
    for (const v of bad) expect(check(v), String(v)).toBe(message);
  });

  it("shows the unit in pixels, the memory in circles and the notes per frame", () => {
    expect(formatCircleUnit(4)).toBe("4 px");
    expect(formatCircleRadius(4)).toBe("4 px");
    expect(formatCircleResize(false)).toBe("Off");
    expect(formatCircleResize(true)).toBe("On");
    expect(formatCircleMemory(300)).toBe("300 circles");
    expect(formatCircleNotes(8)).toBe("8 notes");
  });

  it("applies the grid settings to every image type except circles", () => {
    for (const type of ["tiles", "blended", "contour"]) expect(gridSettingsApply(type)).toBe(true);
    expect(gridSettingsApply("circles")).toBe(false);
  });
});

import { DECAY_AMOUNT_RANGE, DECAY_LEVELS, DEFAULT_DECAY_AMOUNTS, formatDecayAmount, validateDecayAmount } from "./validation";
import { DEFAULT_WAVE_COUNT, WAVE_COUNT_RANGE, formatWaveCount, validateWaveCount, waveCountApplies } from "./validation";
import { DECAY_RATE_RANGE, DEFAULT_DECAY_RATE, decayRateApplies, formatDecayRate, isRingsType, validateDecayRate } from "./validation";
import {
  DEFAULT_BEAT_COLORING,
  DEFAULT_PEAK_DISTANCE,
  DEFAULT_PEAK_PROMINENCE,
  PEAK_DISTANCE_RANGE,
  PEAK_PROMINENCE_RANGE,
  beatColoringApplies,
  formatBeatColoring,
  formatPeakDistance,
  formatPeakProminence,
  validatePeakDistance,
  validatePeakProminence,
} from "./validation";

describe("beat coloring (feature 024)", () => {
  const DISTANCE_MESSAGE = "The minimum distance must be a number from 100 to 2000 milliseconds.";
  const PROMINENCE_MESSAGE = "The prominence must be a number from 0 to 100 percent.";

  it("is off by default, with a minimum distance of 100 ms and a prominence of 50 percent", () => {
    expect(DEFAULT_BEAT_COLORING).toBe(false);
    expect(DEFAULT_PEAK_DISTANCE).toBe(100);
    expect(DEFAULT_PEAK_PROMINENCE).toBe(50);
    expect(PEAK_DISTANCE_RANGE).toEqual({ min: 100, max: 2000, step: 50 });
    expect(PEAK_PROMINENCE_RANGE).toEqual({ min: 0, max: 100, step: 5 });
  });

  it("accepts a minimum distance from 100 to 2000 milliseconds, as a number or as text", () => {
    for (const v of [100, 2000, 100.5, 750, 1999.9, "100", "2000", "750.5"]) expect(validatePeakDistance(v), String(v)).toBeNull();
  });

  it("refuses a minimum distance outside that range or not a number, with the server's message", () => {
    for (const v of [99.9, 0, -100, 2000.1, 5000, NaN, Infinity, -Infinity, "", "abc", "100 ms"]) {
      expect(validatePeakDistance(v), String(v)).toBe(DISTANCE_MESSAGE);
    }
  });

  it("accepts a prominence from 0 to 100 percent and refuses the rest, with the server's message", () => {
    for (const v of [0, 100, 50, 50.5, "0", "100", "25"]) expect(validatePeakProminence(v), String(v)).toBeNull();
    for (const v of [-0.1, 100.1, 101, NaN, Infinity, "", "abc", "50%"]) expect(validatePeakProminence(v), String(v)).toBe(PROMINENCE_MESSAGE);
  });

  it("applies to Tiles, Blended tiles and Contour only", () => {
    expect(beatColoringApplies("tiles")).toBe(true);
    expect(beatColoringApplies("blended")).toBe(true);
    expect(beatColoringApplies("contour")).toBe(true);
    for (const t of ["circles", "circles_paint", "concentric", "decay", "nonsense", ""]) expect(beatColoringApplies(t), t).toBe(false);
  });

  it("is shown as Off or On, a number of milliseconds and a percentage", () => {
    expect(formatBeatColoring(false)).toBe("Off");
    expect(formatBeatColoring(true)).toBe("On");
    expect(formatPeakDistance(100)).toBe("100 ms");
    expect(formatPeakDistance(1250)).toBe("1250 ms");
    expect(formatPeakProminence(50)).toBe("50%");
    expect(formatPeakProminence(0)).toBe("0%");
  });
});

import { peakSettingsShown } from "./validation";

describe("Concentric (feature 025)", () => {
  it("is not a grid type and not a circles type, and the beat coloring checkbox does not apply to it", () => {
    expect(gridSettingsApply("concentric")).toBe(false);
    expect(isCirclesType("concentric")).toBe(false);
    expect(beatColoringApplies("concentric")).toBe(false);
  });

  it("shows the Local peaks settings always for Concentric, for Tiles and Blended tiles only with the box on, and for no other type", () => {
    for (const box of [true, false]) expect(peakSettingsShown("concentric", box), String(box)).toBe(true);
    for (const type of ["tiles", "blended", "contour"]) {
      expect(peakSettingsShown(type, true), type).toBe(true);
      expect(peakSettingsShown(type, false), type).toBe(false);
    }
    for (const type of ["circles", "circles_paint", "nonsense"]) {
      for (const box of [true, false]) expect(peakSettingsShown(type, box), type).toBe(false);
    }
  });
});

import { DEFAULT_NOTE_LAYOUT, NOTE_LAYOUTS, noteLayoutApplies, noteLayoutLabel, validateNoteLayout } from "./validation";

describe("note layout (feature 026)", () => {
  const MESSAGE = "The note layout must be one of rows, spiral.";

  it("offers Rows and Spiral in that order and starts at rows", () => {
    expect(NOTE_LAYOUTS.map((l) => [l.value, l.label])).toEqual([
      ["rows", "Rows"],
      ["spiral", "Spiral"],
    ]);
    expect(DEFAULT_NOTE_LAYOUT).toBe("rows");
    expect(noteLayoutLabel("rows")).toBe("Rows");
    expect(noteLayoutLabel("spiral")).toBe("Spiral");
    expect(noteLayoutLabel("other")).toBe("other");
  });

  it.each(["rows", "spiral"])("accepts %j", (v) => {
    expect(validateNoteLayout(v)).toBeNull();
  });

  it.each(["", "Rows", "SPIRAL", " rows", "spiral ", "row", "spirals", "circle", "1"])("rejects %j with the server's message", (v) => {
    expect(validateNoteLayout(v)).toBe(MESSAGE);
  });

  it("applies to Tiles, Blended tiles, Concentric, Decay, Decay Exp and Polar Chords only", () => {
    for (const type of ["tiles", "blended", "concentric", "decay", "decay-exp", "polar-chords"]) expect(noteLayoutApplies(type), type).toBe(true);
    for (const type of ["contour", "circles", "circles_paint", "nonsense", ""]) expect(noteLayoutApplies(type), type).toBe(false);
  });
});

describe("Decay (feature 027)", () => {
  it("is not a grid type, has no checkbox, uses the Local peaks settings always and has the note layout", () => {
    expect(gridSettingsApply("decay")).toBe(false);
    expect(isCirclesType("decay")).toBe(false);
    expect(beatColoringApplies("decay")).toBe(false);
    for (const box of [true, false]) expect(peakSettingsShown("decay", box), String(box)).toBe(true);
    expect(noteLayoutApplies("decay")).toBe(true);
    expect(isRingsType("decay") && isRingsType("concentric")).toBe(true);
    for (const type of ["tiles", "blended", "contour", "circles", "circles_paint"]) expect(isRingsType(type), type).toBe(false);
  });

  it("has a decay rate from 1 to 10 in steps of 1, 5 at the start, applying to Decay only", () => {
    expect(DECAY_RATE_RANGE).toEqual({ min: 0.25, max: 4, step: 0.25 });
    expect(DEFAULT_DECAY_RATE).toBe(1);
    expect(decayRateApplies("decay")).toBe(true);
    for (const type of ["tiles", "blended", "contour", "circles", "circles_paint", "concentric", ""]) expect(decayRateApplies(type), type).toBe(false);
  });

  it.each([0.25, 0.5, 0.75, 1, 1.25, 2.5, 3.75, 4, "0.25", " 1.5 ", 3.0])("accepts the decay rate %j", (v) => {
    expect(validateDecayRate(v)).toBeNull();
  });

  it.each([0, 0.2, 0.24, 0.3, 1.1, 3.9, 4.25, 5, 10, -1, -0.25, "", "abc", "1e3", NaN, Infinity])("refuses the decay rate %j with the message", (v) => {
    expect(validateDecayRate(v)).toBe("The decay rate must be a number from 0.25 to 4 in steps of 0.25.");
  });

  it("writes the rate in frames, one frame in the singular", () => {
    expect(formatDecayRate(1)).toBe("1 frame");
    expect(formatDecayRate(0.25)).toBe("0.25 frames");
    expect(formatDecayRate(2.5)).toBe("2.5 frames");
    expect(formatDecayRate(4)).toBe("4 frames");
  });
});

describe("the wave count (feature 028)", () => {
  it("is 2 to 10 in steps of 1, 4 at the start, applying to Contour only", () => {
    expect(WAVE_COUNT_RANGE).toEqual({ min: 2, max: 10, step: 1 });
    expect(DEFAULT_WAVE_COUNT).toBe(4);
    expect(waveCountApplies("contour")).toBe(true);
    for (const type of ["tiles", "blended", "circles", "circles_paint", "concentric", "decay", ""]) expect(waveCountApplies(type), type).toBe(false);
  });

  it.each([2, 3, 4, 9, 10, "3", " 4 ", 7.0])("accepts the wave count %j", (v) => {
    expect(validateWaveCount(v)).toBeNull();
  });

  it.each([0, 1, 11, 2.5, -1, "", "abc", "1e3", NaN, Infinity, "0.5"])("refuses the wave count %j with the message", (v) => {
    expect(validateWaveCount(v)).toBe("The wave count must be a whole number from 2 to 10.");
  });

  it("writes the count in waves", () => {
    expect(formatWaveCount(2)).toBe("2 waves");
    expect(formatWaveCount(10)).toBe("10 waves");
  });

  it("keeps Contour a grid picture without a note layout, with the beat coloring and the Local peaks settings available", () => {
    expect(gridSettingsApply("contour")).toBe(true);
    expect(noteLayoutApplies("contour")).toBe(false);
    expect(beatColoringApplies("contour")).toBe(true);
  });
});

describe("the decay amounts, one for each saturation level (feature 027, revised)", () => {
  it("are 0.5 to 3 in steps of 0.5 with the defaults 0.5, 1, 2 and 3 and four named levels", () => {
    expect(DECAY_AMOUNT_RANGE).toEqual({ min: 0.5, max: 3, step: 0.5 });
    expect([...DEFAULT_DECAY_AMOUNTS]).toEqual([0.5, 1, 2, 3]);
    expect(DECAY_LEVELS.map((l) => [l.name, l.control, l.label])).toEqual([
      ["low", "decay-low", "Low saturation"],
      ["medium", "decay-medium", "Medium saturation"],
      ["high", "decay-high", "High saturation"],
      ["saturated", "decay-saturated", "Saturated"],
    ]);
  });

  it.each([0.5, 1, 1.25, 2, 2.999, 3, "0.5", " 2.5 "])("accepts the amount %j", (v) => {
    expect(validateDecayAmount(v, "high")).toBeNull();
  });

  it.each([0, 0.49, 3.01, 4, -1, "", "abc", NaN, Infinity, "1e3"])("refuses the amount %j with the message of its level", (v) => {
    for (const level of ["low", "medium", "high", "saturated"]) {
      expect(validateDecayAmount(v, level)).toBe(`The ${level} saturation decay must be a number from 0.5 to 3.`);
    }
  });

  it("writes the amount per frame", () => {
    expect(formatDecayAmount(0.5)).toBe("0.5 per frame");
    expect(formatDecayAmount(3)).toBe("3 per frame");
  });
});

describe("Decay Exp (feature 030)", () => {
  it("is a rings type like Decay: not a grid type, no checkbox, the Local peaks settings always, the note layout", () => {
    expect(gridSettingsApply("decay-exp")).toBe(false);
    expect(isCirclesType("decay-exp")).toBe(false);
    expect(isRingsType("decay-exp")).toBe(true);
    expect(beatColoringApplies("decay-exp")).toBe(false);
    for (const box of [true, false]) expect(peakSettingsShown("decay-exp", box), String(box)).toBe(true);
    expect(noteLayoutApplies("decay-exp")).toBe(true);
  });

  it("has the decay rate, which applies to Decay and Decay Exp only", () => {
    expect(decayRateApplies("decay-exp")).toBe(true);
    expect(decayRateApplies("decay")).toBe(true);
    for (const type of ["tiles", "blended", "contour", "circles", "circles_paint", "concentric", "decay_exp", "Decay-Exp", ""]) expect(decayRateApplies(type), type).toBe(false);
  });

  it("does not apply the wave count, and is an image type the validation accepts", () => {
    expect(waveCountApplies("decay-exp")).toBe(false);
    expect(validateImageType("decay-exp")).toBeNull();
  });
});

import { DEFAULT_POLAR_NOTES, POLAR_NOTES_RANGE, formatPolarNotes, isEnergyType, isPolarType, validatePolarNotes } from "./validation";

describe("Polar Chords (feature 032)", () => {
  it("has Notes shown from 5 to 8 in steps of 1, 5 at the start", () => {
    expect(POLAR_NOTES_RANGE).toEqual({ min: 5, max: 8, step: 1 });
    expect(DEFAULT_POLAR_NOTES).toBe(5);
  });

  it.each([5, 6, 7, 8, "5", " 7 ", 8.0])("accepts Notes shown %j", (v) => {
    expect(validatePolarNotes(v)).toBeNull();
  });

  it.each([4, 9, 0, -5, 6.5, "", "abc", "1e1", NaN, Infinity])("refuses Notes shown %j with the message", (v) => {
    expect(validatePolarNotes(v)).toBe("The number of notes shown must be a whole number from 5 to 8.");
  });

  it("formats the readout beside the slider and the summary item as a number of notes", () => {
    expect(formatPolarNotes(5)).toBe("5 notes");
    expect(formatPolarNotes(8)).toBe("8 notes");
  });

  it("is the polar type only for polar-chords", () => {
    expect(isPolarType("polar-chords")).toBe(true);
    for (const type of ["tiles", "blended", "contour", "circles", "circles_paint", "concentric", "decay", "decay-exp", "polar_chords", "Polar-Chords", ""]) {
      expect(isPolarType(type), type).toBe(false);
    }
  });

  it("is not a grid type, has no checkbox, uses the Local peaks settings always and has the note layout (rows or spiral)", () => {
    expect(gridSettingsApply("polar-chords")).toBe(false);
    expect(isCirclesType("polar-chords")).toBe(false);
    expect(isRingsType("polar-chords")).toBe(false);
    expect(beatColoringApplies("polar-chords")).toBe(false);
    for (const box of [true, false]) expect(peakSettingsShown("polar-chords", box), String(box)).toBe(true);
    expect(noteLayoutApplies("polar-chords")).toBe(true);
    expect(decayRateApplies("polar-chords")).toBe(false);
    expect(waveCountApplies("polar-chords")).toBe(false);
  });

  it("leaves the other types as they were", () => {
    for (const type of ["tiles", "blended", "contour", "circles", "circles_paint", "concentric", "decay", "decay-exp"]) {
      expect(peakSettingsShown(type, false) === (isRingsType(type)), type).toBe(true);
    }
  });
});

describe("Energy graphs (feature 034)", () => {
  it("is the energy type only for energy-graphs", () => {
    expect(isEnergyType("energy-graphs")).toBe(true);
    for (const type of IMAGE_TYPES.map((t) => t.value).filter((t) => t !== "energy-graphs")) expect(isEnergyType(type), type).toBe(false);
  });

  it("uses none of the settings of the other types", () => {
    expect(gridSettingsApply("energy-graphs")).toBe(false);
    expect(isCirclesType("energy-graphs")).toBe(false);
    expect(isRingsType("energy-graphs")).toBe(false);
    expect(isPolarType("energy-graphs")).toBe(false);
    expect(beatColoringApplies("energy-graphs")).toBe(false);
    for (const box of [true, false]) expect(peakSettingsShown("energy-graphs", box), String(box)).toBe(false);
    expect(noteLayoutApplies("energy-graphs")).toBe(false);
    expect(decayRateApplies("energy-graphs")).toBe(false);
    expect(waveCountApplies("energy-graphs")).toBe(false);
    expect(blendWidthApplies("energy-graphs")).toBe(false);
  });
});

import { CHROMATIC_RATE_RANGE, DEFAULT_CHROMATIC_RATE, formatChromaticRate, isChromaticType, validateChromaticRate } from "./validation";

describe("Chromatic Decay (feature 035)", () => {
  it("is the chromatic type only for chromatic-decay", () => {
    expect(isChromaticType("chromatic-decay")).toBe(true);
    for (const type of IMAGE_TYPES.map((t) => t.value).filter((t) => t !== "chromatic-decay")) expect(isChromaticType(type), type).toBe(false);
  });

  it("has a decay rate of a whole number of frames from 1 to 10, starting at 1", () => {
    expect(CHROMATIC_RATE_RANGE).toEqual({ min: 1, max: 10, step: 1 });
    expect(DEFAULT_CHROMATIC_RATE).toBe(1);
  });

  it.each([1, 2, 5, 9, 10, "1", "10", "3", 3.0])("accepts the decay rate %j", (v) => {
    expect(validateChromaticRate(v)).toBeNull();
  });

  it.each([0, 11, -1, 0.5, 0.25, 2.5, 10.5, "", " ", "x", "nan", "1,5", NaN, Infinity, -Infinity])("refuses the decay rate %j with the message", (v) => {
    expect(validateChromaticRate(v)).toBe("The decay rate must be a whole number from 1 to 10.");
  });

  it("shows the readout as 1 frame, 2 frames, 10 frames", () => {
    expect(formatChromaticRate(1)).toBe("1 frame");
    expect(formatChromaticRate(2)).toBe("2 frames");
    expect(formatChromaticRate(10)).toBe("10 frames");
  });

  it("uses the Local peaks settings (the beat always charges it) but no grid, layout, beat coloring, decay-amount or wave setting", () => {
    expect(peakSettingsShown("chromatic-decay", true)).toBe(true);
    expect(peakSettingsShown("chromatic-decay", false)).toBe(true);
    expect(gridSettingsApply("chromatic-decay")).toBe(false);
    expect(isCirclesType("chromatic-decay")).toBe(false);
    expect(isRingsType("chromatic-decay")).toBe(false);
    expect(isPolarType("chromatic-decay")).toBe(false);
    expect(isEnergyType("chromatic-decay")).toBe(false);
    expect(beatColoringApplies("chromatic-decay")).toBe(false);
    expect(noteLayoutApplies("chromatic-decay")).toBe(false);
    expect(decayRateApplies("chromatic-decay")).toBe(false); // the old decay rate control (0.25 to 4) is not for it
    expect(waveCountApplies("chromatic-decay")).toBe(false);
    expect(blendWidthApplies("chromatic-decay")).toBe(false);
  });

  it("leaves the decay rate of Decay and Decay Exp as it was", () => {
    expect(decayRateApplies("decay")).toBe(true);
    expect(decayRateApplies("decay-exp")).toBe(true);
    expect(validateDecayRate(0.25)).toBeNull();
    expect(validateDecayRate(5)).not.toBeNull();
  });
});
