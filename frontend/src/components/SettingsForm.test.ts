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

describe("the step dropdowns", () => {
  it("offer N/A and the allowed steps for hue, saturation and brightness", async () => {
    const html = await render();
    expect(options(html, "hue-step")).toEqual(["N/A", "12", "36", "90", "180"]);
    expect(options(html, "saturation-step")).toEqual(["N/A", "5", "10", "20", "50"]);
    expect(options(html, "brightness-step")).toEqual(["N/A", "5", "10", "20", "50"]);
  });

  it("are labelled Hue steps, Saturation steps and Brightness steps, in that order, with info buttons", async () => {
    const html = await render();
    const labels = ["Hue steps", "Saturation steps", "Brightness steps"].map((l) => html.indexOf(`>${l}</label>`));
    expect(labels.every((i) => i > 0)).toBe(true);
    expect([...labels].sort((a, b) => a - b)).toEqual(labels);
    for (const name of ["hue steps", "saturation steps", "brightness steps"]) expect(html).toContain(name);
  });

  it("start at N/A and show that the value is smooth", async () => {
    const html = await render();
    expect(html.match(/N\/A \(smooth\)/g)).toHaveLength(3);
    for (const id of ["hue-step", "saturation-step", "brightness-step"]) {
      const select = html.match(new RegExp(`<select id="${id}"[^>]*>([^]*?)</select>`));
      expect(select![1]).toMatch(/<option value="N\/A"[^>]*selected/);  // the starting choice
      expect(html).toContain(`for="${id}"`);
    }
  });

  it("are disabled while a job is running", async () => {
    const html = await render(true);
    for (const id of ["hue-step", "saturation-step", "brightness-step"]) {
      expect(html).toMatch(new RegExp(`<select id="${id}"[^>]*disabled`));
    }
    expect(await render(false)).not.toMatch(/<select id="hue-step"[^>]*disabled/);
  });
});

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
