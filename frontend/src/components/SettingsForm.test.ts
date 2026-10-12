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

  it("comes after Smoothing and is disabled while a job is running", async () => {
    const html = await render();
    expect(html.indexOf('for="threshold"')).toBeGreaterThan(html.indexOf('for="smoothing"'));
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

  it("offer Tiles, Blended tiles and Contour in a dropdown that starts at Tiles", async () => {
    const html = await render();
    expect(options(html, "image-type")).toEqual(["Tiles", "Blended tiles", "Contour"]);
    const select = html.match(new RegExp(`<select id="image-type"[^>]*>([^]*?)</select>`));
    expect(select![1]).toMatch(/<option value="tiles"[^>]*selected/);
    expect(html).toContain(">Image type</label>");
    expect(html).toContain('aria-label="About image type"');
  });

  it("have a blend width slider from 10 to 25 in steps of 1, starting at 25 with its readout", async () => {
    const html = await render();
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

  it("disable the slider while Tiles is selected and both controls while a job runs", async () => {
    expect(slider(await render())).toContain("disabled");
    expect(slider(await render(true))).toContain("disabled");
    expect(await render(true)).toMatch(/<select id="image-type"[^>]*disabled/);
    expect(await render(false)).not.toMatch(/<select id="image-type"[^>]*disabled/);
  });

  it("come after the Threshold field", async () => {
    const html = await render();
    expect(html.indexOf('for="image-type"')).toBeGreaterThan(html.indexOf('for="threshold"'));
    expect(html.indexOf('for="blend-width"')).toBeGreaterThan(html.indexOf('for="image-type"'));
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
  // The server-side render can only show the form at its starting image type (Tiles), so the rule for the other types is
  // tested as the helper `blendWidthApplies` (validation.test.ts); this guards that the slider really uses it, so that it
  // is enabled for Blended tiles only and disabled for Contour as well as Tiles.
  it("is bound to blendWidthApplies, not to a comparison with one image type", () => {
    const input = formSource.match(/<input\s+id="blend-width"[\s\S]*?\/>/)?.[0] ?? "";
    expect(input).toContain("!blendWidthApplies(imageType)");
    expect(input).not.toMatch(/imageType\s*===\s*'tiles'/);
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
    expect(html).toContain(">Resolution</label>");
    expect(html).toContain('aria-label="About resolution"');
  });

  it("is enabled when no job runs and disabled while one runs", async () => {
    expect(slider(await render(false))).not.toContain("disabled");
    expect(slider(await render(true))).toContain("disabled");
  });

  it("does not depend on the image type: its rule is not bound to the image type", () => {
    const input = formSource.match(/<input\s+id="resolution"[\s\S]*?\/>/)?.[0] ?? "";
    expect(input).toContain(':disabled="busy"');
    expect(input).not.toContain("imageType");
  });

  it("comes after the Blend width field", async () => {
    const html = await render();
    expect(html.indexOf('for="resolution"')).toBeGreaterThan(html.indexOf('for="blend-width"'));
  });
});
