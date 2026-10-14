import { describe, expect, it } from "vitest";
import appSource from "./App.vue?raw";

// The result summary is part of App.vue and is only rendered after a job, so these guards read its template.
describe("the result summary", () => {
  const summary = appSource.slice(appSource.indexOf('<ul class="summary">'), appSource.indexOf("</ul>", appSource.indexOf('<ul class="summary">')));

  it("shows the settings that describe a grid of tiles only for the image types that use a grid", () => {
    for (const label of ["Threshold:", "Notes:", "Interpolate:", "Resolution:"]) {
      const line = summary.split("\n").find((l) => l.includes(label)) ?? "";
      expect(line, label).toContain("gridSettingsApply(result.image_type)");
    }
  });

  it("shows the four circle settings for circles", () => {
    const circles = summary.slice(summary.indexOf("result.image_type === 'circles'"));
    expect(circles).toContain("Circle unit:");
    expect(circles).toContain("formatCircleUnit(result.circle_unit)");
    expect(circles).toContain("Circle size:");
    expect(circles).toContain("formatCircleSize(result.circle_size)");
    expect(circles).toContain("Resize by volume:");
    expect(circles).toContain("formatCircleResize(result.circle_resize)");
    expect(circles).toContain("Circle memory:");
    expect(circles).toContain("formatCircleMemory(result.circle_memory)");
    expect(circles).toContain("Circles per frame:");
    expect(circles).toContain("formatCircleNotes(result.circle_notes)");
  });

  it("always shows the image type and shows the blend width for blended tiles only", () => {
    expect(summary.split("\n").find((l) => l.includes("Image type:")) ?? "").not.toContain("v-if");
    expect(summary.split("\n").find((l) => l.includes("Blend width:")) ?? "").toContain("result.image_type === 'blended'");
  });
});
