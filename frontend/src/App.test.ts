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

  it("shows the settings that describe a grid of tiles only for the image types that use a grid", () => {
    for (const label of ["Threshold:", "Notes:", "Interpolate:", "Oversampling:", "Gaussian smoothing:"]) {
      const line = summary.split("\n").find((l) => l.includes(label)) ?? "";
      expect(line, label).toContain("gridSettingsApply(result.image_type)");
    }
  });

  it("shows the circle settings for both circle types, and Memory for Circles only", () => {
    const circles = summary.slice(summary.indexOf("isCirclesType(result.image_type)"));
    expect(summary).toContain("isCirclesType(result.image_type)");
    const memory = summary.split("\n").find((l) => l.includes("Memory:")) ?? "";
    expect(memory).toContain("result.image_type === 'circles'");
    expect(memory).not.toContain("circles_paint");
    expect(circles).toContain("Movement:");
    expect(circles).toContain("formatCircleUnit(result.circle_unit)");
    expect(circles).toContain("Radius:");
    expect(circles).toContain("formatCircleRadius(result.circle_radius)");
    expect(circles).toContain("Resize by volume:");
    expect(circles).toContain("formatCircleResize(result.circle_resize)");
    expect(circles).toContain("Memory:");
    expect(circles).toContain("formatCircleMemory(result.circle_memory)");
    expect(circles).toContain("Notes:");
    expect(circles).toContain("formatCircleNotes(result.circle_notes)");
  });

  it("shows the Gaussian smoothing with the readout Off or its number", () => {
    const line = summary.split("\n").find((l) => l.includes("Gaussian smoothing:")) ?? "";
    expect(line).toContain("formatGaussian(result.gaussian)");
  });

  it("uses the new names and none of the old ones", () => {
    const labels = [...summary.matchAll(/<li[^>]*>([^<{:]*):/g)].map((m) => m[1].trim());
    for (const want of ["Movement", "Radius", "Resize by volume", "Memory", "Notes", "Oversampling"]) expect(labels).toContain(want);
    for (const old of ["Circle unit", "Circle size", "Circle memory", "Circles per frame", "Resolution"]) expect(labels).not.toContain(old);
  });

  it("shows the circle lines in the order of the Circles group, and the grid lines for the grid types only", () => {
    const circles = summary.slice(summary.indexOf("isCirclesType(result.image_type)"));
    const order = ["Movement:", "Radius:", "Resize by volume:", "Memory:", "Notes:"].map((l) => circles.indexOf(l));
    expect(order.every((i) => i > 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    expect(summary.split("\n").find((l) => l.includes("Oversampling:")) ?? "").toContain("gridSettingsApply(result.image_type)");
  });

  it("always shows the image type and shows the blend width for blended tiles only", () => {
    expect(summary.split("\n").find((l) => l.includes("Image type:")) ?? "").not.toContain("v-if");
    expect(summary.split("\n").find((l) => l.includes("Blend width:")) ?? "").toContain("result.image_type === 'blended'");
  });
});

describe("the result summary: beat coloring (feature 024)", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));
  const line = (label: string) => summary.split("\n").find((l) => l.includes(label)) ?? "";

  it("shows the checkbox for Tiles and Blended tiles only", () => {
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
