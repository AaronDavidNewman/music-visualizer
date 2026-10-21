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
