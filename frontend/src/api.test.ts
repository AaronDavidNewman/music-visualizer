import { afterEach, describe, expect, it, vi } from "vitest";
import { submitJob, type JobSettings } from "./api";

const SETTINGS: JobSettings = {
  windowSize: 8192,
  frameRate: 24,
  windowSpacing: 0.75,
  smoothing: 0.3,
  threshold: 4,
  smoothingWindow: 3,
  imageType: "circles_paint",
  blendWidth: 15,
  colormap: "inferno",
  resolution: 3,
  noteCount: 36,
  interpolate: 2,
  circleUnit: 7,
  circleRadius: 6,
  circleResize: true,
  gaussian: 2.5,
  circleMemory: 250,
  circleNotes: 9,
  beatColoring: true,
  peakDistance: 450,
  peakProminence: 25,
  noteLayout: "spiral",
};

afterEach(() => vi.unstubAllGlobals());

/** Submit with the settings and return what was posted, as a plain object of the form fields. */
async function posted(settings: JobSettings): Promise<Record<string, string>> {
  let body: FormData | undefined;
  vi.stubGlobal("fetch", async (_url: string, init: { body: FormData }) => {
    body = init.body;
    return { ok: true, json: async () => ({}) };
  });
  await submitJob(new File(["x"], "song.wav"), settings);
  const fields: Record<string, string> = {};
  for (const [key, value] of body!.entries()) if (typeof value === "string") fields[key] = value;
  return fields;
}

describe("the request that submitJob sends", () => {
  it("carries every setting under the field name that the server expects, as text", async () => {
    expect(await posted(SETTINGS)).toEqual({
      window_size: "8192",
      frame_rate: "24",
      window_spacing: "0.75",
      smoothing: "0.3",
      threshold: "4",
      smoothing_window: "3",
      image_type: "circles_paint",
      blend_width: "15",
      colormap: "inferno",
      resolution: "3",
      note_count: "36",
      interpolate: "2",
      circle_unit: "7",
      circle_radius: "6",
      circle_resize: "true",
      gaussian: "2.5",
      beat_coloring: "true",
      peak_distance: "450",
      peak_prominence: "25",
      note_layout: "spiral",
      circle_memory: "250",
      circle_notes: "9",
    });
  });

  it("sends the gaussian smoothing as 0 when it is off, and the file", async () => {
    expect((await posted({ ...SETTINGS, gaussian: 0 })).gaussian).toBe("0");
    let sent: FormData | undefined;
    vi.stubGlobal("fetch", async (_url: string, init: { body: FormData }) => {
      sent = init.body;
      return { ok: true, json: async () => ({}) };
    });
    await submitJob(new File(["x"], "song.wav"), SETTINGS);
    expect((sent!.get("file") as File).name).toBe("song.wav");
  });

  it("rejects with the server's message when it refuses the request", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 400, json: async () => ({ detail: "The gaussian smoothing must be a number from 0 to 5." }) }));
    await expect(submitJob(new File(["x"], "song.wav"), SETTINGS)).rejects.toThrow("The gaussian smoothing must be a number from 0 to 5.");
  });
});

describe("the beat coloring fields of the request (feature 024)", () => {
  it("sends the checkbox as true or false and the two settings as numbers", async () => {
    const on = await posted(SETTINGS);
    expect([on.beat_coloring, on.peak_distance, on.peak_prominence]).toEqual(["true", "450", "25"]);
    const off = await posted({ ...SETTINGS, beatColoring: false, peakDistance: 100, peakProminence: 50 });
    expect([off.beat_coloring, off.peak_distance, off.peak_prominence]).toEqual(["false", "100", "50"]);
  });

  it("shows the server's message for a refused setting", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 400, json: async () => ({ detail: "The prominence must be a number from 0 to 100 percent." }) }));
    await expect(submitJob(new File(["x"], "song.wav"), SETTINGS)).rejects.toThrow("The prominence must be a number from 0 to 100 percent.");
  });
});

describe("the note layout field of the request (feature 026)", () => {
  it("sends rows and spiral as the lowercase names", async () => {
    expect((await posted({ ...SETTINGS, noteLayout: "rows" })).note_layout).toBe("rows");
    expect((await posted({ ...SETTINGS, noteLayout: "spiral" })).note_layout).toBe("spiral");
  });

  it("shows the server's message for a refused layout", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 400, json: async () => ({ detail: "The note layout must be one of rows, spiral." }) }));
    await expect(submitJob(new File(["x"], "song.wav"), SETTINGS)).rejects.toThrow("The note layout must be one of rows, spiral.");
  });
});
