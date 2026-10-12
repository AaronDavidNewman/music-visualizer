import { describe, expect, it } from "vitest";
import {
  blendWidthHelp,
  colormapHelp,
  frameRateHelp,
  imageTypeHelp,
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

  it("explains the three image types", () => {
    expect(imageTypeHelp).toContain("Tiles:");
    expect(imageTypeHelp).toContain("flat");
    expect(imageTypeHelp).toContain("hard edges");
    expect(imageTypeHelp).toContain("Blended tiles:");
    expect(imageTypeHelp).toContain("fade into each other");
    expect(imageTypeHelp).toContain("Contour:");
    expect(imageTypeHelp).toContain("contour map");
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
