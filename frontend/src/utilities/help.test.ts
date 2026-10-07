import { describe, expect, it } from "vitest";
import { brightnessHelp, frameRateHelp, smoothingHelp, spacingHelp, windowSizeHelp } from "./help";
import { BRIGHTNESS_RANGE, FRAME_RATE_RANGE } from "./validation";

describe("setting explanations", () => {
  it("keeps the wording that used to be printed under the fields", () => {
    expect(windowSizeHelp).toBe("Larger windows separate low notes better but blur changes over time.");
    expect(smoothingHelp).toBe("0 is no smoothing; higher values fade notes more slowly.");
  });

  it("states the frame rate range from the validation constants", () => {
    expect(frameRateHelp).toBe(`${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`);
  });

  it("states the brightness range from the validation constants", () => {
    expect(brightnessHelp).toContain(`${BRIGHTNESS_RANGE.min} to ${BRIGHTNESS_RANGE.max}`);
    expect(brightnessHelp).toContain("Higher values lift quiet notes more but show less contrast.");
  });

  it("explains the spacing and adds the step hint when there is one", () => {
    const base = spacingHelp("");
    expect(base).toBe("Distance between the starts of windows, as a multiple of the window size.");
    expect(spacingHelp("Step between windows: 1024 samples (23.2 ms).")).toBe(
      `${base} Step between windows: 1024 samples (23.2 ms).`,
    );
  });
});
