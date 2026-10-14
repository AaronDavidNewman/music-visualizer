import { describe, expect, it } from "vitest";
import {
  blendWidthHelp,
  colormapHelp,
  frameRateHelp,
  imageTypeHelp,
  interpolateHelp,
  circleMemoryHelp,
  circleResizeHelp,
  circleSizeHelp,
  circleNotesHelp,
  circleUnitHelp,
  noteCountHelp,
  resolutionHelp,
  smoothingHelp,
  smoothingWindowHelp,
  spacingHelp,
  thresholdHelp,
  windowSizeHelp,
} from "./help";
import { FRAME_RATE_RANGE } from "./validation";

describe("setting explanations", () => {
  it("keeps the wording that used to be printed under the fields", () => {
    expect(windowSizeHelp).toBe("Larger windows separate low notes better but blur changes over time.");
  });

  it("states the frame rate range from the validation constants", () => {
    expect(frameRateHelp).toBe(`${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`);
  });

  it("explains the spacing and adds the step hint when there is one", () => {
    const base = spacingHelp("");
    expect(base).toBe("Distance between the starts of windows, as a multiple of the window size.");
    expect(spacingHelp("Step between windows: 1024 samples (23.2 ms).")).toBe(
      `${base} Step between windows: 1024 samples (23.2 ms).`,
    );
  });

  it("explains the threshold: black below it, a share of the loudest note in the file, left end off, right end 10%", () => {
    expect(thresholdHelp).toContain("drawn black");
    expect(thresholdHelp).toContain("loudest note in the whole file");
    expect(thresholdHelp).toContain("left end");
    expect(thresholdHelp).toContain("off");
    expect(thresholdHelp).toContain("right end");
    expect(thresholdHelp).toContain("10% of the loudest note");
  });

  it("explains Smoothing as the weight of the earlier frames in the window", () => {
    expect(smoothingHelp).toContain("0 is no smoothing");
    expect(smoothingHelp).toContain("smoothing window");
    expect(smoothingHelp).toContain("counts this fraction as much as the current frame");
  });

  it("explains the smoothing window: earlier frames mixed in, a stopped note gone, the range, and no effect at 0", () => {
    expect(smoothingWindowHelp).toContain("1 to 20");
    expect(smoothingWindowHelp).toContain("earlier frames are mixed into each frame");
    expect(smoothingWindowHelp).toContain("gone that many frames later");
    expect(smoothingWindowHelp).toContain("no effect while Smoothing is 0");
  });

  it("explains the four image types", () => {
    expect(imageTypeHelp).toContain("Tiles:");
    expect(imageTypeHelp).toContain("flat");
    expect(imageTypeHelp).toContain("hard edges");
    expect(imageTypeHelp).toContain("Blended tiles:");
    expect(imageTypeHelp).toContain("fade into each other");
    expect(imageTypeHelp).toContain("Contour:");
    expect(imageTypeHelp).toContain("contour map");
    expect(imageTypeHelp).toContain("Circles:");
    expect(imageTypeHelp).toContain("circles");
  });

  it("explains the blend width: the reach on each side of an edge, as a share of a tile, the range, and where it applies", () => {
    expect(blendWidthHelp).toContain("10 to 25");
    expect(blendWidthHelp).toContain("each side of an edge");
    expect(blendWidthHelp).toContain("percentage of a tile");
    expect(blendWidthHelp).toContain("Only used by Blended tiles");
  });

  it("explains the colormap: what the four scales look like and that the same strength always gets the same color", () => {
    expect(colormapHelp).toContain("same strength always gets the same color");
    expect(colormapHelp).toContain("Summer: green to yellow");
    expect(colormapHelp).toContain("Autumn: red to yellow");
    expect(colormapHelp).toContain("Hot: dark red");
    expect(colormapHelp).toContain("Cool: cyan to magenta");
  });
});

describe("resolution explanation", () => {
  it("explains the interpolation, the original grid, the highest value and the smaller tiles", () => {
    expect(resolutionHelp).toContain("interpolat");
    expect(resolutionHelp).toContain("12 \u00d7 7");
    expect(resolutionHelp).toContain("5\u00d7");
    expect(resolutionHelp).toContain("60 \u00d7 35");
    expect(resolutionHelp).toContain("smaller tiles");
    expect(resolutionHelp).toContain("contour");
  });
});

describe("number of notes explanation", () => {
  it("explains the choice by energy over the whole file, the bigger features, the range and that it is not always steadier", () => {
    expect(noteCountHelp).toContain("most energy");
    expect(noteCountHelp).toContain("whole file");
    expect(noteCountHelp).toContain("12 to 84");
    expect(noteCountHelp).toContain("bigger");
    expect(noteCountHelp).toContain("not steadier in every case");
  });
});

describe("interpolation explanation", () => {
  it("explains that only every n-th frame is drawn, that the frames between are blends of their neighbors, and that it is faster", () => {
    expect(interpolateHelp).toContain("every n-th frame");
    expect(interpolateHelp).toContain("blending");
    expect(interpolateHelp).toContain("neighbors");
    expect(interpolateHelp).toContain("contour");
    expect(interpolateHelp).toContain("1 to 5");
  });

  it("no longer offers a choice of function", () => {
    expect(interpolateHelp).not.toContain("Soft light");
    expect(interpolateHelp).not.toContain("Subtract");
  });
});

describe("circles explanations", () => {
  it("explains the unit in pixels, the memory of the last circles, and how many of the strongest notes put a circle down", () => {
    expect(circleUnitHelp).toContain("1 to 10");
    expect(circleUnitHelp).toContain("pixels");
    expect(circleMemoryHelp).toContain("100 to 500");
    expect(circleMemoryHelp).toContain("oldest");
    expect(circleNotesHelp).toContain("5 to 12");
    expect(circleNotesHelp).toContain("strongest");
  });

  it("explains the size as the circumference, apart from the step, and the fading of old circles", () => {
    expect(circleSizeHelp).toContain("25 to 50");
    expect(circleSizeHelp).toContain("circumference");
    expect(circleUnitHelp).not.toContain("radius");
    expect(circleUnitHelp).toContain("stays in place");
    expect(circleResizeHelp).toContain("three times");
    expect(circleResizeHelp).toContain("no circle is smaller");
    expect(circleResizeHelp).not.toContain("half");
    expect(circleResizeHelp).toContain("Off by default");
    expect(circleMemoryHelp).toContain("fade");
    expect(circleMemoryHelp).toContain("middle color");
  });
});
