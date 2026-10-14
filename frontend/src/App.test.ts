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
    for (const label of ["Threshold:", "Notes:", "Interpolate:", "Oversampling:"]) {
      const line = summary.split("\n").find((l) => l.includes(label)) ?? "";
      expect(line, label).toContain("gridSettingsApply(result.image_type)");
    }
  });

  it("shows the four circle settings for circles", () => {
    const circles = summary.slice(summary.indexOf("result.image_type === 'circles'"));
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

  it("uses the new names and none of the old ones", () => {
    const labels = [...summary.matchAll(/<li[^>]*>([^<{:]*):/g)].map((m) => m[1].trim());
    for (const want of ["Movement", "Radius", "Resize by volume", "Memory", "Notes", "Oversampling"]) expect(labels).toContain(want);
    for (const old of ["Circle unit", "Circle size", "Circle memory", "Circles per frame", "Resolution"]) expect(labels).not.toContain(old);
  });

  it("shows the circle lines in the order of the Circles group, and the grid lines for the grid types only", () => {
    const circles = summary.slice(summary.indexOf("result.image_type === 'circles'"));
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
