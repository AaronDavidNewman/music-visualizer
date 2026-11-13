import { describe, expect, it } from "vitest";
import appSource from "./App.vue?raw";
import pickerSource from "./components/FilePicker.vue?raw";
import indexHtml from "../index.html?raw";

describe("the label font (Roboto Slab, 0.9 rem)", () => {
  it("is defined once as the variables --label-font and --label-size on the page", () => {
    expect(appSource).toMatch(/:root\s*\{[^}]*--label-font:\s*"Roboto Slab"[^}]*serif[^}]*\}/);
    expect(appSource).toMatch(/:root\s*\{[^}]*--label-size:\s*0\.9rem/);
  });

  it("is loaded from Google Fonts in the page head, with the weights the labels use", () => {
    expect(indexHtml).toMatch(/<link[^>]*href="https:\/\/fonts\.googleapis\.com\/css2\?family=Roboto\+Slab:wght@[^"]*600[^"]*"/);
    expect(indexHtml).toContain('rel="preconnect"');
  });

  it("is used by the file picker's label as well", () => {
    const rule = pickerSource.match(/\.field span\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(rule).toContain("font-family: var(--label-font)");
    expect(rule).toContain("font-size: var(--label-size)");
  });
});

// The result summary is part of App.vue and is only rendered after a job, so these guards read its template.
describe("the result summary", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));

  it("shows the settings that describe the grid of notes only for the image type that uses a grid", () => {
    for (const label of ["Threshold:", "Notes:", "Interpolate:", "Oversampling:", "Gaussian smoothing:"]) {
      const line = summary.split("\n").find((l) => l.includes(label)) ?? "";
      expect(line, label).toContain("gridSettingsApply(result.image_type)");
    }
  });


  it("shows the Gaussian smoothing with the readout Off or its number", () => {
    const line = summary.split("\n").find((l) => l.includes("Gaussian smoothing:")) ?? "";
    expect(line).toContain("formatGaussian(result.gaussian)");
  });

  it("uses the new names and none of the old ones, and none of the settings of the removed pictures", () => {
    const labels = [...summary.matchAll(/<li[^>]*>([^<{:]*):/g)].map((m) => m[1].trim());
    for (const want of ["Notes", "Oversampling"]) expect(labels).toContain(want);
    for (const old of ["Circle unit", "Circle size", "Circle memory", "Circles per frame", "Resolution", "Movement", "Radius", "Resize by volume", "Memory", "Blend width"]) expect(labels).not.toContain(old);
    expect(summary).not.toContain("isCirclesType");
  });

  it("shows the grid lines for the grid types only", () => {
    expect(summary.split("\n").find((l) => l.includes("Oversampling:")) ?? "").toContain("gridSettingsApply(result.image_type)");
  });

  it("always shows the image type", () => {
    expect(summary.split("\n").find((l) => l.includes("Image type:")) ?? "").not.toContain("v-if");
  });
});

describe("the result summary: beat coloring (feature 024)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows the checkbox for Contour only", () => {
    expect(line("Beat coloring:")).toContain("beatColoringApplies(result.image_type)");
    expect(line("Beat coloring:")).toContain("formatBeatColoring(result.beat_coloring)");
  });

  it("shows the two settings only for those types and only when the box is on", () => {
    for (const label of ["Minimum distance:", "Prominence:"]) {
      expect(line(label), label).toContain("peakSettingsShown(result.image_type, result.beat_coloring)");
    }
    expect(line("Minimum distance:")).toContain("formatPeakDistance(result.peak_distance)");
    expect(line("Prominence:")).toContain("formatPeakProminence(result.peak_prominence)");
  });
});

describe("the result summary for Concentric (feature 025)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows Minimum distance and Prominence through the one rule that includes Concentric and the box", () => {
    for (const label of ["Minimum distance:", "Prominence:"]) expect(line(label), label).toContain("peakSettingsShown(result.image_type, result.beat_coloring)");
  });

  it("shows Beat coloring only where the checkbox applies, which is not for Concentric", () => {
    expect(line("Beat coloring:")).toContain("beatColoringApplies(result.image_type)");
  });
});

describe("the result summary: note layout (feature 026)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows the layout, by its label, for the pictures that have the choice only", () => {
    expect(line("Note layout:")).toContain("noteLayoutApplies(result.image_type)");
    expect(line("Note layout:")).toContain("noteLayoutLabel(result.note_layout)");
  });
});

describe("the result summary for Decay (feature 027)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows the decay rate in frames for Decay and Decay Exp only", () => {
    expect(line("Decay rate:")).toContain("decayRateApplies(result.image_type)");
    expect(line("Decay rate:")).toContain("formatDecayRate(result.decay_rate)");
  });

  it("shows the note layout and the Local peaks settings, and not Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing or Beat coloring", () => {
    expect(line("Note layout:")).toContain("noteLayoutApplies(result.image_type)");
    for (const label of ["Minimum distance:", "Prominence:"]) expect(line(label), label).toContain("peakSettingsShown(result.image_type, result.beat_coloring)");
    expect(line("Beat coloring:")).toContain("beatColoringApplies(result.image_type)");
    for (const label of ["Oversampling:", "Gaussian smoothing:"]) expect(line(label), label).toContain("gridSettingsApply(result.image_type)");
  });
});

describe("the result summary for Contour (feature 028)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows the wave count in waves for Contour with the beat coloring on only", () => {
    expect(line("Wave count:")).toContain("result.image_type === 'contour'");
    expect(line("Wave count:")).toContain("result.beat_coloring");
    expect(line("Wave count:")).toContain("formatWaveCount(result.wave_count)");
  });

  it("shows Beat coloring, Minimum distance and Prominence for Contour through the same rules as for the tiles", () => {
    expect(line("Beat coloring:")).toContain("beatColoringApplies(result.image_type)");
    for (const label of ["Minimum distance:", "Prominence:"]) expect(line(label), label).toContain("peakSettingsShown(result.image_type, result.beat_coloring)");
  });
});

describe("the result summary: the decay amounts (feature 027, revised)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it.each([
    ["Low saturation decay:", "decay_low"],
    ["Medium saturation decay:", "decay_medium"],
    ["High saturation decay:", "decay_high"],
    ["Saturated decay:", "decay_saturated"],
  ])("shows %s for Decay only, per frame", (label, field) => {
    expect(line(label)).toContain("result.image_type === 'decay'");
    expect(line(label)).toContain(`formatDecayAmount(result.${field})`);
  });
});

describe("the result summary for Decay Exp (feature 030)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows the decay rate, and the note layout and Local peaks settings through the rules that include Decay Exp", () => {
    expect(line("Decay rate:")).toContain("decayRateApplies(result.image_type)");
    expect(line("Note layout:")).toContain("noteLayoutApplies(result.image_type)");
    for (const label of ["Minimum distance:", "Prominence:"]) expect(line(label), label).toContain("peakSettingsShown(result.image_type, result.beat_coloring)");
  });

  it("does not show the four decay amounts for it: they stay Decay's", () => {
    for (const label of ["Low saturation decay:", "Medium saturation decay:", "High saturation decay:", "Saturated decay:"]) {
      expect(line(label), label).toContain("result.image_type === 'decay'");
      expect(line(label), label).not.toContain("decay-exp");
      expect(line(label), label).not.toContain("decayRateApplies");
    }
  });

  it("does not show Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing or Beat coloring", () => {
    expect(line("Beat coloring:")).toContain("beatColoringApplies(result.image_type)");
    for (const label of ["Oversampling:", "Gaussian smoothing:"]) expect(line(label), label).toContain("gridSettingsApply(result.image_type)");
  });
});

describe("the result summary for Polar Chords (feature 032)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows Notes shown, as a number of notes, for Polar Chords only", () => {
    expect(line("Notes shown:")).toContain("isPolarType(result.image_type)");
    expect(line("Chromatic decay rate:")).toContain("isChromaticType(result.image_type)");
    expect(line("Notes shown:")).toContain("formatPolarNotes(result.polar_notes)");
  });

  it("shows the Note layout and the Local peaks settings, and not Threshold, Notes, Interpolate, Oversampling, Gaussian smoothing or Beat coloring", () => {
    for (const label of ["Minimum distance:", "Prominence:"]) expect(line(label), label).toContain("peakSettingsShown(result.image_type, result.beat_coloring)");
    expect(line("Note layout:")).toContain("noteLayoutApplies(result.image_type)");
    expect(line("Beat coloring:")).toContain("beatColoringApplies(result.image_type)");
    for (const label of ["Oversampling:", "Gaussian smoothing:"]) expect(line(label), label).toContain("gridSettingsApply(result.image_type)");
  });

  it("does not show the decay lines for it", () => {
    expect(line("Decay rate:")).toContain("decayRateApplies(result.image_type)");
    expect(line("Low saturation decay:")).toContain("result.image_type === 'decay'");
  });
});

describe("the result summary: the threshold of Chromatic Decay (feature 037)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows Threshold for the types of the grid and for Chromatic Decay, and still not Notes, Interpolate, Oversampling or Gaussian smoothing for Chromatic Decay", () => {
    expect(line("Threshold:")).toContain("gridSettingsApply(result.image_type)");
    expect(line("Threshold:")).toContain("isChromaticType(result.image_type)");
    expect(line("Threshold:")).toContain("formatThresholdSummary(result.threshold)");
    for (const label of ["Notes:", "Interpolate:", "Oversampling:", "Gaussian smoothing:"]) {
      expect(line(label), label).toContain("gridSettingsApply(result.image_type)");
      expect(line(label), label).not.toContain("isChromaticType");
    }
  });
});

describe("the result summary for Rhythm Circles (feature 038)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split(String.fromCharCode(10)).find((l) => l.includes(label)) ?? "";

  it("shows the Local peaks settings for it through the rule that includes it, with or without Beat coloring", () => {
    for (const label of ["Minimum distance:", "Prominence:"]) expect(line(label), label).toContain("peakSettingsShown(result.image_type, result.beat_coloring)");
  });

  it("shows none of the settings of the grid, the decay, the layout or the beat coloring for it", () => {
    for (const label of ["Notes:", "Interpolate:", "Oversampling:", "Gaussian smoothing:"]) {
      expect(line(label), label).toContain("gridSettingsApply(result.image_type)");
      expect(line(label), label).not.toContain("isRhythmType");
    }
    expect(line("Threshold:")).not.toContain("isRhythmType");
    expect(line("Decay rate:")).toContain("decayRateApplies(result.image_type)");
    expect(line("Note layout:")).toContain("noteLayoutApplies(result.image_type)");
    expect(line("Beat coloring:")).toContain("beatColoringApplies(result.image_type)");
  });
});
