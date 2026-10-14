export interface JobResult {
  job_id: string;
  file_name: string;
  sample_rate: number;
  duration_seconds: number;
  window_size: number;
  frame_rate: number;
  frame_count: number;
  smoothing: number;
  /** Percent of the loudest note value below which a note is drawn black (0 is off). */
  threshold: number;
  /** How many earlier frames are mixed into each frame (1 to 20). */
  smoothing_window: number;
  /** "tiles", "blended" or "contour". */
  image_type: string;
  /** The fade width used for blended tiles, as a percentage of the tile width (10 to 25). */
  blend_width: number;
  /** The colormap used: one of the names in COLORMAPS (utilities/validation.ts). */
  colormap: string;
  /** How many times finer than the original 12 \u00d7 7 grid the picture is drawn (1 to 5). */
  resolution: number;
  /** How many of the 84 drawn notes make up the picture: the ones with the most energy (12 to 84). */
  note_count: number;
  /** Only every n-th frame is drawn (1 to 5); the frames between are made from their neighbors. */
  interpolate: number;
  /** The Circles image type: the unit in pixels, the memory in circles and the notes per frame. */
  circle_unit: number;
  circle_size: number;
  circle_memory: number;
  circle_notes: number;
  window_spacing: number;
  step_samples: number;
  window_count: number;
  spacing_raised: boolean;
  frame_url_template: string;
}

/** What the user chooses besides the file. */
export interface JobSettings {
  windowSize: number;
  frameRate: number;
  windowSpacing: number;
  smoothing: number;
  /** 0 (off) to 10, percent of the loudest note value. */
  threshold: number;
  /** 1 to 20. */
  smoothingWindow: number;
  /** "tiles", "blended" or "contour". */
  imageType: string;
  /** 10 to 25. Only used by blended tiles (not by tiles or contour). */
  blendWidth: number;
  /** One of the names in COLORMAPS (utilities/validation.ts). */
  colormap: string;
  /** 1 to 5: a whole number. */
  resolution: number;
  /** 12 to 84: a whole number. */
  noteCount: number;
  /** 1 to 5: a whole number. */
  interpolate: number;
  /** Only used by Circles: 1 to 10 pixels, 100 to 500 circles, 5 to 12 notes per frame. */
  circleUnit: number;
  circleSize: number;
  circleMemory: number;
  circleNotes: number;
}

/** Uploads the file and waits for the frames to be created. Rejects with a message fit to show the user. */
export async function submitJob(file: File, settings: JobSettings): Promise<JobResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("window_size", String(settings.windowSize));
  body.append("frame_rate", String(settings.frameRate));
  body.append("window_spacing", String(settings.windowSpacing));
  body.append("smoothing", String(settings.smoothing));
  body.append("threshold", String(settings.threshold));
  body.append("smoothing_window", String(settings.smoothingWindow));
  body.append("image_type", settings.imageType);
  body.append("blend_width", String(settings.blendWidth));
  body.append("colormap", settings.colormap);
  body.append("resolution", String(settings.resolution));
  body.append("note_count", String(settings.noteCount));
  body.append("interpolate", String(settings.interpolate));
  body.append("circle_unit", String(settings.circleUnit));
  body.append("circle_size", String(settings.circleSize));
  body.append("circle_memory", String(settings.circleMemory));
  body.append("circle_notes", String(settings.circleNotes));

  let res: Response;
  try {
    res = await fetch("/api/jobs", { method: "POST", body });
  } catch {
    throw new Error("Could not reach the server. Check that it is running and try again.");
  }

  if (!res.ok) {
    let detail = `The server returned an error (${res.status}).`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // keep the generic message
    }
    throw new Error(detail);
  }
  return (await res.json()) as JobResult;
}

export function frameUrl(job: JobResult, index: number): string {
  return job.frame_url_template.replace("{index}", String(index));
}
