import { describe, expect, it } from "vitest";
import {
  brightnessHelp,
  brightnessStepHelp,
  energyHelp,
  frameRateHelp,
  hueStepHelp,
  saturationStepHelp,
  smoothingHelp,
  spacingHelp,
  thresholdHelp,
  windowSizeHelp,
} from "./help";
import { BRIGHTNESS_RANGE, ENERGY_RANGE, FRAME_RATE_RANGE, HUE_STEPS, UNIT_STEPS } from "./validation";

describe("setting explanations", () => {
  it("explains the Brightness setting (energy): its range, what it does, and what 1 means", () => {
    expect(energyHelp).toContain(`${ENERGY_RANGE.min} to ${ENERGY_RANGE.max}`);
    expect(energyHelp).toContain("whole picture");
    expect(energyHelp).toContain("quiet passages");
    expect(energyHelp).toContain("1 is");
  });

  it("keeps the wording that used to be printed under the fields", () => {
    expect(windowSizeHelp).toBe("Larger windows separate low notes better but blur changes over time.");
    expect(smoothingHelp).toBe("0 is no smoothing; higher values fade notes more slowly.");
  });

  it("states the frame rate range from the validation constants", () => {
    expect(frameRateHelp).toBe(`${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`);
  });

  it("explains the Saturation setting (brightness): its range and what it does", () => {
    expect(brightnessHelp).toContain(`${BRIGHTNESS_RANGE.min} to ${BRIGHTNESS_RANGE.max}`);
    expect(brightnessHelp).toContain("how strong its note is");
    expect(brightnessHelp).toContain("Higher values give quiet notes stronger colors but show less contrast.");
  });

  it("explains the spacing and adds the step hint when there is one", () => {
    const base = spacingHelp("");
    expect(base).toBe("Distance between the starts of windows, as a multiple of the window size.");
    expect(spacingHelp("Step between windows: 1024 samples (23.2 ms).")).toBe(
      `${base} Step between windows: 1024 samples (23.2 ms).`,
    );
  });

  it("explains the step settings: what N/A means, that a larger step gives fewer levels, and the choices", () => {
    expect(hueStepHelp).toContain(HUE_STEPS.join(", "));
    expect(saturationStepHelp).toContain(UNIT_STEPS.join(", "));
    expect(brightnessStepHelp).toContain(UNIT_STEPS.join(", "));
    for (const text of [hueStepHelp, saturationStepHelp, brightnessStepHelp]) {
      expect(text).toContain("N/A leaves it smooth");
      expect(text).toContain("larger step gives fewer, bolder levels");
    }
    expect(hueStepHelp).toContain("Both ends of the wheel are red");
    expect(brightnessStepHelp).toContain("loudest frame stays at full brightness");
  });

  it("explains the threshold: black below it, a share of the loudest note in the file, left end off, right end 10%", () => {
    expect(thresholdHelp).toContain("drawn black");
    expect(thresholdHelp).toContain("loudest note in the whole file");
    expect(thresholdHelp).toContain("left end");
    expect(thresholdHelp).toContain("off");
    expect(thresholdHelp).toContain("right end");
    expect(thresholdHelp).toContain("10% of the loudest note");
  });
});
