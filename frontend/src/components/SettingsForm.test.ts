import { createSSRApp } from "vue";
import { renderToString } from "vue/server-renderer";
import { describe, expect, it } from "vitest";
import SettingsForm from "./SettingsForm.vue";

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

  it("offer Tiles and Blended tiles in a dropdown that starts at Tiles", async () => {
    const html = await render();
    expect(options(html, "image-type")).toEqual(["Tiles", "Blended tiles"]);
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
  it("offers Summer, Autumn, Hot and Cool in that order, starts at Hot, and has a label and an info button", async () => {
    const html = await render();
    expect(options(html, "colormap")).toEqual(["Summer", "Autumn", "Hot", "Cool"]);
    const select = html.match(new RegExp(`<select id="colormap"[^>]*>([^]*?)</select>`));
    expect(select![1]).toMatch(/<option value="hot"[^>]*selected/);
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
