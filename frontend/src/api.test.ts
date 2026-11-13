import { afterEach, describe, expect, it, vi } from "vitest";
import { createVideo, submitJob, videoUrl, type JobResult, type JobSettings } from "./api";

const SETTINGS: JobSettings = {
  windowSize: 8192,
  frameRate: 24,
  windowSpacing: 0.75,
  smoothing: 0.3,
  threshold: 4,
  smoothingWindow: 3,
  imageType: "decay",
  colormap: "inferno",
  resolution: 3,
  noteCount: 36,
  interpolate: 2,
  gaussian: 2.5,
  beatColoring: true,
  peakDistance: 450,
  peakProminence: 25,
  noteLayout: "spiral",
  decayRate: 3,
  polarNotes: 6,
  waveCount: 7,
  decayLow: 1.5,
  decayMedium: 2,
  decayHigh: 2.5,
  decaySaturated: 3,
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
      image_type: "decay",
      colormap: "inferno",
      resolution: "3",
      note_count: "36",
      interpolate: "2",
      gaussian: "2.5",
      beat_coloring: "true",
      peak_distance: "450",
      peak_prominence: "25",
      note_layout: "spiral",
      decay_rate: "3",
      polar_notes: "6",
      wave_count: "7",
      decay_low: "1.5",
      decay_medium: "2",
      decay_high: "2.5",
      decay_saturated: "3",
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

describe("the decay rate field of the request (feature 027)", () => {
  it("sends the rate as a number in text, a quarter of a frame included, and the image type decay", async () => {
    expect((await posted({ ...SETTINGS, imageType: "decay", decayRate: 4 })).decay_rate).toBe("4");
    expect((await posted({ ...SETTINGS, imageType: "decay", decayRate: 0.25 })).decay_rate).toBe("0.25");
    expect((await posted({ ...SETTINGS, imageType: "decay", decayRate: 1 })).image_type).toBe("decay");
  });

  it("shows the server's message for a refused rate", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 400, json: async () => ({ detail: "The decay rate must be a whole number from 1 to 10." }) }));
    await expect(submitJob(new File(["x"], "song.wav"), SETTINGS)).rejects.toThrow("The decay rate must be a whole number from 1 to 10.");
  });
});

describe("the wave count field of the request (feature 028)", () => {
  it("sends the count as a whole number in text, with the image type contour and the beat coloring", async () => {
    const fields = await posted({ ...SETTINGS, imageType: "contour", beatColoring: true, waveCount: 10 });
    expect([fields.image_type, fields.beat_coloring, fields.wave_count]).toEqual(["contour", "true", "10"]);
    expect((await posted({ ...SETTINGS, waveCount: 2 })).wave_count).toBe("2");
  });

  it("shows the server's message for a refused count", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 400, json: async () => ({ detail: "The wave count must be a whole number from 2 to 10." }) }));
    await expect(submitJob(new File(["x"], "song.wav"), SETTINGS)).rejects.toThrow("The wave count must be a whole number from 2 to 10.");
  });
});

describe("the decay amount fields of the request (feature 027, revised)", () => {
  it("sends the four amounts as numbers in text under their field names", async () => {
    const fields = await posted({ ...SETTINGS, imageType: "decay", decayLow: 0.5, decayMedium: 1, decayHigh: 2, decaySaturated: 3 });
    expect([fields.decay_low, fields.decay_medium, fields.decay_high, fields.decay_saturated]).toEqual(["0.5", "1", "2", "3"]);
  });

  it("shows the server's message for a refused amount", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 400, json: async () => ({ detail: "The high saturation decay must be a number from 0.5 to 3." }) }));
    await expect(submitJob(new File(["x"], "song.wav"), SETTINGS)).rejects.toThrow("The high saturation decay must be a number from 0.5 to 3.");
  });
});

describe("the video request (feature 029)", () => {
  const JOB = { job_id: "0123456789abcdef0123456789abcdef" } as JobResult;
  const VIDEO = {
    job_id: JOB.job_id,
    file_name: "video.mp4",
    path: "C:\app\backend\output\video.mp4",
    size_bytes: 1000,
    frame_count: 240,
    frame_rate: 24,
    duration_seconds: 10,
    url: `/api/jobs/${JOB.job_id}/video`,
  };

  it("posts to the video address of the job and returns what the server says", async () => {
    let seen: { url: string; method: string | undefined } | undefined;
    vi.stubGlobal("fetch", async (url: string, init: { method?: string }) => {
      seen = { url, method: init.method };
      return { ok: true, status: 200, json: async () => VIDEO };
    });
    expect(await createVideo(JOB)).toEqual(VIDEO);
    expect(seen).toEqual({ url: `/api/jobs/${JOB.job_id}/video`, method: "POST" });
  });

  it("shows the server's message when the video cannot be made", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 503, json: async () => ({ detail: "ffmpeg was not found." }) }));
    await expect(createVideo(JOB)).rejects.toThrow("ffmpeg was not found.");
  });

  it("has a generic message when the error has no detail", async () => {
    vi.stubGlobal("fetch", async () => ({ ok: false, status: 500, json: async () => ({}) }));
    await expect(createVideo(JOB)).rejects.toThrow("The server returned an error (500).");
  });

  it("says the server could not be reached when the request fails", async () => {
    vi.stubGlobal("fetch", async () => {
      throw new TypeError("failed");
    });
    await expect(createVideo(JOB)).rejects.toThrow("Could not reach the server.");
  });

  it("builds the download address of the job's video", () => {
    expect(videoUrl(JOB)).toBe(`/api/jobs/${JOB.job_id}/video`);
  });
});

describe("the request for Decay Exp (feature 030)", () => {
  it("sends the image type with its hyphen, the decay rate, and the four decay amounts as for any type", async () => {
    const fields = await posted({ ...SETTINGS, imageType: "decay-exp", decayRate: 0.25 });
    expect(fields.image_type).toBe("decay-exp");
    expect(fields.decay_rate).toBe("0.25");
    expect([fields.decay_low, fields.decay_medium, fields.decay_high, fields.decay_saturated]).toEqual(["1.5", "2", "2.5", "3"]);
  });
});

describe("the request for Polar Chords (feature 032)", () => {
  it("sends the image type with its hyphen and Notes shown as text", async () => {
    const fields = await posted({ ...SETTINGS, imageType: "polar-chords", polarNotes: 8 });
    expect(fields.image_type).toBe("polar-chords");
    expect(fields.polar_notes).toBe("8");
  });
});

describe("the request for Energy graphs (feature 034)", () => {
  it("sends the image type with its hyphen and the same fields as for any other type: no field of its own", async () => {
    const energy = await posted({ ...SETTINGS, imageType: "energy-graphs" });
    const polar = await posted({ ...SETTINGS, imageType: "polar-chords" });
    expect(energy.image_type).toBe("energy-graphs");
    expect(Object.keys(energy).sort()).toEqual(Object.keys(polar).sort());
  });
});

describe("the request for Chromatic Decay (feature 035)", () => {
  it("sends the image type with its hyphen and the decay rate as text, with the same fields as any other type", async () => {
    const chromatic = await posted({ ...SETTINGS, imageType: "chromatic-decay", decayRate: 7 });
    const decay = await posted({ ...SETTINGS, imageType: "decay-exp" });
    expect(chromatic.image_type).toBe("chromatic-decay");
    expect(chromatic.decay_rate).toBe("7");
    expect(Object.keys(chromatic).sort()).toEqual(Object.keys(decay).sort());
  });
});

describe("the request for Rhythm Circles (feature 038)", () => {
  it("sends the image type with its hyphen and the same fields as for any other type, the two Local peaks settings among them", async () => {
    const rhythm = await posted({ ...SETTINGS, imageType: "rhythm-circles", peakDistance: 700, peakProminence: 30 });
    const polar = await posted({ ...SETTINGS, imageType: "polar-chords" });
    expect(rhythm.image_type).toBe("rhythm-circles");
    expect(rhythm.peak_distance).toBe("700");
    expect(rhythm.peak_prominence).toBe("30");
    expect(Object.keys(rhythm).sort()).toEqual(Object.keys(polar).sort());
  });
});

describe("the request for Chromatic Wireframe (feature 039)", () => {
  it("sends the image type with its hyphen and the decay rate as text, with the same fields as any other type", async () => {
    const wireframe = await posted({ ...SETTINGS, imageType: "chromatic-wireframe", decayRate: 6, threshold: 3 });
    const decay = await posted({ ...SETTINGS, imageType: "decay-exp" });
    expect(wireframe.image_type).toBe("chromatic-wireframe");
    expect(wireframe.decay_rate).toBe("6");
    expect(Object.keys(wireframe).sort()).toEqual(Object.keys(decay).sort());
  });
});
