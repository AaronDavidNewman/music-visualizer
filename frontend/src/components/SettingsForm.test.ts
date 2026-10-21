import { createSSRApp } from "vue";
import { renderToString } from "vue/server-renderer";
import { describe, expect, it } from "vitest";
import SettingsForm from "./SettingsForm.vue";
import formSource from "./SettingsForm.vue?raw";
import { COLORMAPS, DEFAULT_COLORMAP } from "../utilities/validation";

async function render(busy = false): Promise<string> {
  const app = createSSRApp(SettingsForm, { busy, file: null, sampleRate: 44100 });
  return renderToString(app);
}

/** The text of the options of the <select> with this id, in order. */
function options(html: string, id: string): string[] {
  const select = html.match(new RegExp(`<select id="${id}"[^>]*>([\\s\\S]*?)</select>`));
  expect(select, `select #${id}`).not.toBeNull();
  return [...select![1].matchAll(/<option[^>]*>([^<]*)<\/option>/g)].map((m) => m[1]);
}

describe("the threshold slider", () => {
  const input = (html: string) => html.match(/<input id="threshold"[^>]*>/)?.[0] ?? "";

  it("is a range from 0 to 10 in steps of 1, starting at 0 with the readout Off", async () => {
    const html = await render();
    const tag = input(html);
    expect(tag).toContain('type="range"');
    expect(tag).toContain('min="0"');
    expect(tag).toContain('max="10"');
    expect(tag).toContain('step="1"');
    expect(tag).toContain('value="0"');
    expect(html).toMatch(/<output[^>]*for="threshold"[^>]*>Off<\/output>/);
  });

  it("has a label and an info button", async () => {
    const html = await render();
    expect(html).toContain(">Threshold</label>");
    expect(html).toContain('aria-label="About threshold"');
  });

  it("comes after Image type (it is in the group of the type) and is disabled only while a job is running", async () => {
    const html = await render();
    expect(html.indexOf('for="threshold"')).toBeGreaterThan(html.indexOf('for="image-type"'));
    expect(html.indexOf('for="threshold"')).toBeLessThan(html.indexOf('for="smoothing-window"'));
    expect(input(html)).not.toContain("disabled");
    expect(input(await render(true))).toContain("disabled");
  });
});

describe("the smoothing window field", () => {
  const input = (html: string) => html.match(/<input id="smoothing-window"[^>]*>/)?.[0] ?? "";

  it("is a whole-number input from 1 to 20, starting at 1", async () => {
    const tag = input(await render());
    expect(tag).toContain('type="number"');
    expect(tag).toContain('min="1"');
    expect(tag).toContain('max="20"');
    expect(tag).toContain('step="1"');
    expect(tag).toContain('value="1"');
  });

  it("has a label and an info button", async () => {
    const html = await render();
    expect(html).toContain(">Smoothing window (frames)</label>");
    expect(html).toContain('aria-label="About smoothing window"');
  });

  it("comes before the Smoothing slider and is disabled while a job is running", async () => {
    const html = await render();
    expect(html.indexOf('for="smoothing-window"')).toBeGreaterThan(0);
    expect(html.indexOf('for="smoothing-window"')).toBeLessThan(html.indexOf('for="smoothing"'));
    expect(input(html)).not.toContain("disabled");
    expect(input(await render(true))).toContain("disabled");
  });
});

describe("the image type controls", () => {
  const slider = (html: string) => html.match(/<input id="blend-width"[^>]*>/)?.[0] ?? "";
  const blended = (busy = false) => renderType("blended", busy);

  it("offer Tiles, Blended tiles, Contour, Circles and Circles paint in a dropdown that starts at Tiles", async () => {
    const html = await render();
    expect(options(html, "image-type")).toEqual(["Tiles", "Blended tiles", "Contour", "Circles", "Circles paint"]);
    const select = html.match(new RegExp(`<select id="image-type"[^>]*>([^]*?)</select>`));
    expect(select![1]).toMatch(/<option value="tiles"[^>]*selected/);
    expect(html).toContain(">Image type</label>");
    expect(html).toContain('aria-label="About image type"');
  });

  it("have a blend width slider from 10 to 25 in steps of 1, starting at 25 with its readout, for Blended tiles", async () => {
    const html = await blended();
    const tag = slider(html);
    expect(tag).toContain('type="range"');
    expect(tag).toContain('min="10"');
    expect(tag).toContain('max="25"');
    expect(tag).toContain('step="1"');
    expect(tag).toContain('value="25"');
    expect(html).toMatch(/<output[^>]*for="blend-width"[^>]*>25% of a tile<\/output>/);
    expect(html).toContain(">Blend width</label>");
    expect(html).toContain('aria-label="About blend width"');
  });

  it("show the slider for Blended tiles only, and disable it and the dropdown only while a job runs", async () => {
    for (const type of ["tiles", "contour", "circles"]) expect(await renderType(type)).not.toContain('id="blend-width"');
    expect(slider(await blended())).not.toContain("disabled");
    expect(slider(await blended(true))).toContain("disabled");
    expect(await render(true)).toMatch(/<select id="image-type"[^>]*disabled/);
    expect(await render(false)).not.toMatch(/<select id="image-type"[^>]*disabled/);
  });

  it("come before the group of the type: Image type first, then Threshold, Notes and Blend width", async () => {
    const html = await blended();
    expect(html.indexOf('for="threshold"')).toBeGreaterThan(html.indexOf('for="image-type"'));
    expect(html.indexOf('for="blend-width"')).toBeGreaterThan(html.indexOf('for="notes"'));
  });
});

describe("the colormap dropdown", () => {
  it("offers every colormap of the list in order, starts at the default, and has a label and an info button", async () => {
    const html = await render();
    expect(options(html, "colormap")).toEqual(COLORMAPS.map((c) => c.label));
    const select = html.match(new RegExp(`<select id="colormap"[^>]*>([^]*?)</select>`));
    expect(select![1]).toMatch(new RegExp(`<option value="${DEFAULT_COLORMAP}"[^>]*selected`));
    for (const c of COLORMAPS) expect(select![1]).toContain(`<option value="${c.value}"`);
    expect(html).toContain(">Colormap</label>");
    expect(html).toContain('aria-label="About colormap"');
  });

  it("is disabled while a job is running and not otherwise", async () => {
    expect(await render(true)).toMatch(/<select id="colormap"[^>]*disabled/);
    expect(await render(false)).not.toMatch(/<select id="colormap"[^>]*disabled/);
  });

  it("comes after the window size row and before the smoothing window", async () => {
    const html = await render();
    expect(html.indexOf('for="colormap"')).toBeGreaterThan(html.indexOf('for="window-spacing"'));
    expect(html.indexOf('for="colormap"')).toBeLessThan(html.indexOf('for="smoothing-window"'));
  });

  it("replaces the controls that were removed: no brightness, saturation or level steps", async () => {
    const html = await render();
    for (const id of ["brightness", "saturation", "hue-step", "saturation-step", "brightness-step"]) {
      expect(html).not.toContain(`id="${id}"`);
    }
    for (const label of ["Brightness", "Saturation", "Hue steps", "Saturation steps", "Brightness steps"]) {
      expect(html).not.toContain(`>${label}</label>`);
    }
  });
});

describe("the blend width slider's rule", () => {
  // The slider is in the group of the type and is shown by the group model for Blended tiles only (groups.test.ts); this guards that
  // the template really asks the model, not a comparison with one image type.
  it("is shown by the group model, not by a comparison with one image type", () => {
    const cell = formSource.match(/<div v-if="inTypeGroup\('blend-width'\)" class="field">/)?.[0] ?? "";
    expect(cell).not.toBe("");
    expect(formSource).not.toMatch(/imageType\s*===\s*'blended'/);
  });
});

describe("the resolution slider", () => {
  const slider = (html: string) => html.match(/<input id="resolution"[^>]*>/)?.[0] ?? "";

  it("is a slider from 1 to 5 in steps of 1 starting at 1, with its readout, label and info button", async () => {
    const html = await render();
    const tag = slider(html);
    expect(tag).toContain('type="range"');
    expect(tag).toContain('min="1"');
    expect(tag).toContain('max="5"');
    expect(tag).toContain('step="1"');
    expect(tag).toContain('value="1"');
    expect(html).toMatch(/<output[^>]*for="resolution"[^>]*>1\u00d7<\/output>/);
    expect(html).toMatch(/<label for="resolution"[^>]*>Oversampling<\/label>/);
    expect(html).toContain('aria-label="About oversampling"');
  });

  it("is enabled when no job runs and disabled while one runs", async () => {
    expect(slider(await render(false))).not.toContain("disabled");
    expect(slider(await render(true))).toContain("disabled");
  });

  it("is in the Image smoothing group, which is shown for the grid types and not for circles", async () => {
    expect(formSource).toMatch(/<SettingsGroup\s+v-if="showImageSmoothing"/);
    expect(await renderType("circles")).not.toContain('id="resolution"');
    for (const type of ["tiles", "contour", "blended"]) expect(await renderType(type)).toContain('id="resolution"');
  });

  it("comes after the group of the type and the Data smoothing group", async () => {
    const html = await renderType("blended");
    expect(html.indexOf('for="resolution"')).toBeGreaterThan(html.indexOf('for="blend-width"'));
    expect(html.indexOf('for="resolution"')).toBeGreaterThan(html.indexOf('for="smoothing"'));
  });
});

describe("the notes slider", () => {
  const slider = (html: string) => html.match(/<input id="notes"[^>]*>/)?.[0] ?? "";

  it("is a slider from 12 to 84 in steps of 1 starting at 84, with its readout, label and info button", async () => {
    const html = await render();
    const tag = slider(html);
    expect(tag).toContain('type="range"');
    expect(tag).toContain('min="12"');
    expect(tag).toContain('max="84"');
    expect(tag).toContain('step="1"');
    expect(tag).toContain('value="84"');
    expect(html).toMatch(/<output[^>]*for="notes"[^>]*>All 84 notes<\/output>/);
    expect(html).toContain(">Notes</label>");
    expect(html).toContain('aria-label="About notes"');
  });

  it("is enabled when no job runs and disabled while one runs", async () => {
    expect(slider(await render(false))).not.toContain("disabled");
    expect(slider(await render(true))).toContain("disabled");
  });

  it("is in the group of the grid types (shown by the group model) and not in Circles, where Notes is another control", async () => {
    expect(formSource).toContain("v-if=\"inTypeGroup('notes')\"");
    expect(await renderType("circles")).not.toContain('id="notes"');
    for (const type of ["tiles", "contour", "blended"]) expect(await renderType(type)).toContain('id="notes"');
  });

  it("comes after the Threshold field and after the Image type field", async () => {
    const html = await render();
    expect(html.indexOf('for="notes"')).toBeGreaterThan(html.indexOf('for="threshold"'));
    expect(html.indexOf('for="notes"')).toBeGreaterThan(html.indexOf('for="image-type"'));
  });
});

describe("the interpolate slider", () => {
  const slider = (html: string) => html.match(/<input id="interpolate"[^>]*>/)?.[0] ?? "";

  it("is a slider from 1 to 5 in steps of 1 starting at 1 with its readout, label and info button", async () => {
    const html = await render();
    const tag = slider(html);
    expect(tag).toContain('type="range"');
    expect(tag).toContain('min="1"');
    expect(tag).toContain('max="5"');
    expect(tag).toContain('step="1"');
    expect(tag).toContain('value="1"');
    expect(html).toMatch(/<output[^>]*for="interpolate"[^>]*>1\s*<\/output>/);
    expect(html).toContain(">Interpolate</label>");
    expect(html).toContain('aria-label="About interpolate"');
  });

  it("is enabled when no job runs and disabled while one runs", async () => {
    expect(slider(await render(false))).not.toContain("disabled");
    expect(slider(await render(true))).toContain("disabled");
  });

  it("has no function dropdown any more (only blend is made)", async () => {
    const html = await render();
    expect(html).not.toContain("interpolate-function");
    expect(html).not.toContain("Interpolation function");
    expect(formSource).not.toContain("interpolate-function");
  });

  it("comes after the Oversampling field", async () => {
    const html = await render();
    expect(html.indexOf('for="interpolate"')).toBeGreaterThan(html.indexOf('for="resolution"'));
  });
});

describe("the circles controls", () => {
  it("are not shown at the starting image type (Tiles)", async () => {
    const html = await render();
    for (const id of ["circle-unit", "circle-radius", "circle-resize", "circle-memory", "circle-notes"]) expect(html).not.toContain(`id="${id}"`);
  });

  it("are four sliders shown only while Circles is chosen, with readouts and info buttons", async () => {
    const circles = await renderType("circles");
    for (const [id, label] of [["circle-unit", "Movement"], ["circle-radius", "Radius"], ["circle-memory", "Memory"], ["circle-notes", "Notes"]] as const) {
      const input = circles.match(new RegExp(`<input id="${id}"[^>]*>`))?.[0] ?? "";
      expect(input, id).toContain('type="range"');
      expect(input).not.toContain("disabled");
      expect(circles).toMatch(new RegExp(`<label for="${id}"[^>]*>${label}</label>`));
      expect(circles).toMatch(new RegExp(`<output[^>]*for="${id}"`));
      expect(formSource).toContain(`v-if="inTypeGroup('${id}')"`);
    }
    for (const aria of ["About circle movement", "About circle radius", "About circle memory", "About circle notes"]) expect(circles).toContain(`aria-label="${aria}"`);
  });

  it("have the radius slider from 4 to 8 pixels starting at 4 and the readout 4 px", async () => {
    const circles = await renderType("circles");
    const tag = circles.match(/<input id="circle-radius"[^>]*>/)?.[0] ?? "";
    expect(tag).toContain('min="4"');
    expect(tag).toContain('max="8"');
    expect(tag).toContain('step="1"');
    expect(tag).toContain('value="4"');
    expect(circles).toMatch(/<output[^>]*for="circle-radius"[^>]*>4 px<\/output>/);
  });

  it("have a checkbox for the resize by volume, off at the start, inside the circles block and disabled while a job runs", () => {
    const input = formSource.match(/<input\s+id="circle-resize"[^>]*\/>/)?.[0] ?? "";
    expect(input).toContain('type="checkbox"');
    expect(input).toContain('v-model="circleResize"');
    expect(input).toContain(':disabled="busy"');
    expect(formSource).toContain('<label for="circle-resize">Resize by volume</label>');
    expect(formSource).toContain('label="resize by volume"');
    expect(formSource).toContain("ref<boolean>(DEFAULT_CIRCLE_RESIZE)");
    expect(formSource).toContain("circleResize: circleResize.value");
    expect(formSource).toContain("v-if=\"inTypeGroup('circle-resize')\"");
  });

  it("hide the grid controls while Circles is chosen (they are not greyed out any more)", async () => {
    const circles = await renderType("circles");
    for (const id of ["interpolate", "resolution", "notes", "threshold", "blend-width"]) expect(circles, id).not.toContain(`id="${id}"`);
    for (const id of ["window-size", "frame-rate", "window-spacing", "colormap", "image-type", "smoothing-window", "smoothing"]) {
      expect(circles, id).toContain(`id="${id}"`);
    }
  });

  it("leave the five controls enabled at the starting image type and while no job runs", async () => {
    const html = await render(false);
    for (const id of ["interpolate", "resolution", "notes", "threshold"]) {
      const tag = html.match(new RegExp(`<input id="${id}"[^>]*>`))?.[0] ?? "";
      expect(tag, id).not.toContain("disabled");
    }
  });
});

// --- the groups (feature 020) ---------------------------------------------------------------------------------------------------

async function renderType(type: string, busy = false): Promise<string> {
  const app = createSSRApp(SettingsForm, { busy, file: null, sampleRate: 44100, initialImageType: type });
  return renderToString(app);
}

interface RenderedGroup {
  id: string;
  title: string;
  open: boolean;
  controls: string[];
}

/** The groups of the rendered form: the id, the title, whether it is open, and the controls (their label targets) in order. */
function groupsOf(html: string): RenderedGroup[] {
  return html
    .split("<details")
    .slice(1)
    .map((part) => {
      const tag = part.slice(0, part.indexOf(">"));
      const summary = part.match(/<summary[^>]*>([\s\S]*?)<\/summary>/)?.[1] ?? "";
      const body = part.slice(part.indexOf("</summary>"), part.indexOf("</details>"));
      return {
        id: tag.match(/data-group="([^"]+)"/)?.[1] ?? "",
        title: summary.replace(/<[^>]*>/g, "").replace("needs attention", "").trim(),
        open: /\sopen(\s|=|$)/.test(tag),
        controls: [...body.matchAll(/<label for="([^"]+)"/g)].map((m) => m[1]),
      };
    });
}

const TOP = ["window-size", "frame-rate", "window-spacing"];
const EXPECTED_GROUPS: Record<string, [string, string, string[]][]> = {
  tiles: [
    ["analysis", "Analysis", TOP],
    ["colormap", "Colormap", ["colormap"]],
    ["image-type", "Image type", ["image-type"]],
    ["tiles", "Tiles", ["threshold", "notes"]],
    ["data-smoothing", "Data smoothing", ["smoothing-window", "smoothing"]],
    ["image-smoothing", "Image smoothing", ["resolution", "interpolate", "gaussian"]],
  ],
  contour: [
    ["analysis", "Analysis", TOP],
    ["colormap", "Colormap", ["colormap"]],
    ["image-type", "Image type", ["image-type"]],
    ["contour", "Contour", ["threshold", "notes"]],
    ["data-smoothing", "Data smoothing", ["smoothing-window", "smoothing"]],
    ["image-smoothing", "Image smoothing", ["resolution", "interpolate", "gaussian"]],
  ],
  blended: [
    ["analysis", "Analysis", TOP],
    ["colormap", "Colormap", ["colormap"]],
    ["image-type", "Image type", ["image-type"]],
    ["blended", "Blended Tiles", ["threshold", "notes", "blend-width"]],
    ["data-smoothing", "Data smoothing", ["smoothing-window", "smoothing"]],
    ["image-smoothing", "Image smoothing", ["resolution", "interpolate", "gaussian"]],
  ],
  circles: [
    ["analysis", "Analysis", TOP],
    ["colormap", "Colormap", ["colormap"]],
    ["image-type", "Image type", ["image-type"]],
    ["circles", "Circles", ["circle-unit", "circle-radius", "circle-resize", "circle-memory", "circle-notes"]],
    ["data-smoothing", "Data smoothing", ["smoothing-window", "smoothing"]],
  ],
  circles_paint: [
    ["analysis", "Analysis", TOP],
    ["colormap", "Colormap", ["colormap"]],
    ["image-type", "Image type", ["image-type"]],
    ["circles_paint", "Circles paint", ["circle-unit", "circle-radius", "circle-resize", "circle-notes"]],
    ["data-smoothing", "Data smoothing", ["smoothing-window", "smoothing"]],
  ],
};
const TYPE_IDS = ["tiles", "contour", "blended", "circles", "circles_paint"];

describe("the form is a list of titled groups (Story 1)", () => {
  it("starts with the top group, Colormap and Image type, all open, and ends with the Create frames button", async () => {
    const html = await render();
    const groups = groupsOf(html);
    expect(groups.slice(0, 3).map((g) => [g.id, g.title])).toEqual([
      ["analysis", "Analysis"],
      ["colormap", "Colormap"],
      ["image-type", "Image type"],
    ]);
    expect(groups.every((g) => g.open)).toBe(true);
    expect(html.lastIndexOf("</details>")).toBeLessThan(html.indexOf('type="submit"'));
  });

  it("puts Window size, Frame rate and Window spacing in the top group, in that order", async () => {
    expect(groupsOf(await render())[0].controls).toEqual(TOP);
  });

  it("gives Colormap and Image type a group each with their one control", async () => {
    const groups = groupsOf(await render());
    expect(groups[1].controls).toEqual(["colormap"]);
    expect(groups[2].controls).toEqual(["image-type"]);
  });

  it("has every control exactly once, in the group of its image type", async () => {
    for (const type of TYPE_IDS) {
      const html = await renderType(type);
      expect(groupsOf(html).map((g) => [g.id, g.title, g.controls]), type).toEqual(EXPECTED_GROUPS[type]);
      const labels = [...html.matchAll(/<label for="([^"]+)"/g)].map((m) => m[1]);
      expect(new Set(labels).size, type).toBe(labels.length); // no control twice
      expect(labels.length, type).toBe(EXPECTED_GROUPS[type].reduce((n, g) => n + g[2].length, 0)); // none outside a group
    }
  });

  it("ties the open state and the problem flag of each of the six groups to the form", () => {
    expect((formSource.match(/<SettingsGroup\b/g) ?? []).length).toBe(6); // top, Colormap, Image type, the type's group, Data smoothing, Image smoothing
    expect((formSource.match(/:open="isOpen\(/g) ?? []).length).toBe(6);
    expect((formSource.match(/:problem="/g) ?? []).length).toBe(6);
    expect((formSource.match(/@toggle="/g) ?? []).length).toBe(6);
  });

  it("collapses with the open state that the group reports, so that no value is touched by it", () => {
    expect(formSource).toContain("setOpen(");
    const at = formSource.indexOf("function onToggle");
    expect(at).toBeGreaterThan(0);
    const handler = formSource.slice(at, formSource.indexOf("}", at));
    expect(handler).not.toMatch(/\.value\s*=\s*[^=]/); // no setting is assigned there; only the open map changes
  });

  it("flags a group when one of its controls has a value that is not allowed", () => {
    for (const name of ["analysisProblem", "colormapProblem", "imageTypeProblem", "typeGroupProblem", "dataSmoothingProblem", "imageSmoothingProblem"]) {
      expect(formSource, name).toContain(name);
    }
    expect(formSource).toMatch(/windowError\.value\s*\|\|\s*frameRateError\.value\s*\|\|\s*spacingError\.value/);
  });
});

describe("the groups of the chosen image type (Story 2)", () => {
  it.each(TYPE_IDS)("follow Image type with the controls of %s and no control of another type", async (type) => {
    const groups = groupsOf(await renderType(type));
    const typeGroup = groups[3];
    expect(typeGroup.id).toBe(type);
    expect(typeGroup.controls).toEqual(EXPECTED_GROUPS[type][3][2]);
    expect(groups.filter((g) => TYPE_IDS.includes(g.id))).toHaveLength(1);
  });

  it("has, for Tiles and Contour, the same two controls under the title of the chosen type", async () => {
    const tiles = groupsOf(await renderType("tiles"))[3];
    const contour = groupsOf(await renderType("contour"))[3];
    expect(tiles.controls).toEqual(contour.controls);
    expect([tiles.title, contour.title]).toEqual(["Tiles", "Contour"]);
  });

  it("has Blend width last in Blended Tiles, where it is alone on its row", async () => {
    expect(groupsOf(await renderType("blended"))[3].controls.slice(-1)).toEqual(["blend-width"]);
  });

  it("has, for Circles paint, the circle controls two to a row, Notes last, and no Memory", async () => {
    const html = await renderType("circles_paint");
    const group = groupsOf(html)[3];
    expect(group.id).toBe("circles_paint");
    expect(group.title).toBe("Circles paint");
    expect(group.controls).toEqual(["circle-unit", "circle-radius", "circle-resize", "circle-notes"]);
    expect(html).not.toContain('id="circle-memory"');
    expect(html).not.toContain('id="resolution"');
    expect(html).not.toContain('id="threshold"');
    expect(await renderType("circles")).toContain('id="circle-memory"');
  });

  it("shares the values of Movement, Radius, Resize by volume and Notes between Circles and Circles paint", () => {
    // one ref each in the form, shown by either circle group, so that switching the type keeps what was entered
    for (const control of ["circle-unit", "circle-radius", "circle-resize", "circle-notes"]) expect(formSource).toContain(`inTypeGroup('${control}')`);
    expect(formSource).toContain('TYPE_GROUP_IDS = ["tiles", "contour", "blended", "circles", "circles_paint"]');
    expect((formSource.match(/const circleUnit = ref/g) ?? []).length).toBe(1);
    expect((formSource.match(/const circleNotes = ref/g) ?? []).length).toBe(1);
  });

  it("has Notes last in Circles, alone on its row", async () => {
    expect(groupsOf(await renderType("circles"))[3].controls.slice(-1)).toEqual(["circle-notes"]);
  });

  it.each(TYPE_IDS)("disables nothing because of the image type for %s, only while a job runs", async (type) => {
    const idle = await renderType(type, false);
    for (const tag of idle.match(/<(input|select)[^>]*>/g) ?? []) expect(tag).not.toContain("disabled");
    const busy = await renderType(type, true);
    for (const tag of busy.match(/<(input|select)[^>]*>/g) ?? []) expect(tag).toContain("disabled");
  });

  it("does not grey controls out by image type any more (it hides them)", () => {
    expect(formSource).not.toContain("gridSettingsApply(imageType)");
    expect(formSource).not.toContain("blendWidthApplies(imageType)");
  });

  it("keeps the values of the other types' controls in the form, so that choosing the type again restores them", () => {
    for (const ref of ["threshold", "noteCount", "blendWidth", "circleUnit", "circleRadius", "circleResize", "circleMemory", "circleNotes"]) {
      expect(formSource, ref).toMatch(new RegExp(`const ${ref} = ref`));
    }
    expect(formSource).toContain("threshold: threshold.value");
    expect(formSource).toContain("circleMemory: circleMemory.value");
  });

  it("starts at Tiles unless it is given another starting image type", async () => {
    expect(groupsOf(await render())[3].id).toBe("tiles");
    expect(formSource).toContain("initialImageType");
  });
});

describe("the gaussian smoothing slider", () => {
  const slider = (html: string) => html.match(/<input id="gaussian"[^>]*>/)?.[0] ?? "";

  it("is a slider from 0 to 5 in steps of one half, starting at 0 with the readout Off, in the Image smoothing group", async () => {
    const html = await render();
    const tag = slider(html);
    expect(tag).toContain('type="range"');
    expect(tag).toContain('min="0"');
    expect(tag).toContain('max="5"');
    expect(tag).toContain('step="0.5"');
    expect(tag).toContain('value="0"');
    expect(html).toMatch(/<output[^>]*for="gaussian"[^>]*>Off<\/output>/);
    expect(html).toMatch(/<label for="gaussian"[^>]*>Gaussian smoothing<\/label>/);
    expect(html).toContain('aria-label="About gaussian smoothing"');
    const group = groupsOf(html).find((g) => g.id === "image-smoothing");
    expect(group?.controls).toEqual(["resolution", "interpolate", "gaussian"]);
  });

  it("is shown for the grid types and not for the two circle types", async () => {
    for (const type of ["tiles", "contour", "blended"]) expect(await renderType(type), type).toContain('id="gaussian"');
    for (const type of ["circles", "circles_paint"]) expect(await renderType(type), type).not.toContain('id="gaussian"');
  });

  it("is disabled only while a job runs, and its value is sent", async () => {
    expect(slider(await render(false))).not.toContain("disabled");
    expect(slider(await render(true))).toContain("disabled");
    expect(formSource).toMatch(/const gaussian = ref<number>\(DEFAULT_GAUSSIAN\)/);
    expect(formSource).toContain("gaussian: gaussian.value");
    expect(formSource).toContain("gaussianError");
    expect(formSource).toMatch(/const imageSmoothingProblem = computed\([^;]*resolutionError\.value[^;]*interpolateError\.value[^;]*gaussianError\.value/);
    expect(formSource).toMatch(/!gaussianError\.value/); // and Create frames waits for it too
  });
});

describe("the label font", () => {
  it("is the shared label font and size for every label of the form", () => {
    const rule = formSource.match(/\.field-head label\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(rule).toContain("font-family: var(--label-font)");
    expect(rule).toContain("font-size: var(--label-size)");
  });
});

describe("the smoothing groups and the new names (Story 3)", () => {
  it("shows Data smoothing for every image type and Image smoothing for the grid types only", async () => {
    for (const type of TYPE_IDS) {
      const ids = groupsOf(await renderType(type)).map((g) => g.id);
      expect(ids, type).toContain("data-smoothing");
      expect(ids.includes("image-smoothing"), type).toBe(type !== "circles" && type !== "circles_paint");
    }
  });

  it("labels the controls Movement, Radius, Resize by volume, Memory, Notes and Oversampling", async () => {
    const circles = await renderType("circles");
    for (const [id, label] of [
      ["circle-unit", "Movement"],
      ["circle-radius", "Radius"],
      ["circle-resize", "Resize by volume"],
      ["circle-memory", "Memory"],
      ["circle-notes", "Notes"],
    ]) {
      expect(circles, id).toMatch(new RegExp(`<label for="${id}"[^>]*>${label}</label>`));
    }
    const tiles = await render();
    expect(tiles).toMatch(/<label for="resolution"[^>]*>Oversampling<\/label>/);
    for (const aria of ["About circle movement", "About circle radius", "About oversampling"]) {
      expect(circles + tiles).toContain(`aria-label="${aria}"`);
    }
  });

  it("shows none of the old names in any rendered label or in the source's labels", async () => {
    const oldLabel = /^(Unit|Size|Circles per frame|Resolution)$/;
    for (const type of TYPE_IDS) {
      const labels = [...(await renderType(type)).matchAll(/<label[^>]*>([^<]*)<\/label>/g)].map((m) => m[1].trim());
      for (const l of labels) expect(l, type).not.toMatch(oldLabel);
    }
    const sourceLabels = [...formSource.matchAll(/<label[^>]*>([^<{]*)<\/label>/g)].map((m) => m[1].trim());
    for (const l of sourceLabels) expect(l).not.toMatch(oldLabel);
    expect(formSource).not.toMatch(/label="(circle unit|circle size|circles per frame|resolution)"/);
  });
});
