export interface JobResult {
  job_id: string;
  file_name: string;
  sample_rate: number;
  duration_seconds: number;
  window_size: number;
  frame_rate: number;
  frame_count: number;
  brightness: number;
  smoothing: number;
  energy: number;
  /** The steps used for hue, saturation and brightness: null is N/A (smooth). */
  hue_step: number | null;
  saturation_step: number | null;
  brightness_step: number | null;
  /** Percent of the loudest note value below which a note is drawn black (0 is off). */
  threshold: number;
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
  brightness: number;
  smoothing: number;
  energy: number;
  /** null is N/A (smooth); otherwise one of the allowed steps. */
  hueStep: number | null;
  saturationStep: number | null;
  brightnessStep: number | null;
  /** 0 (off) to 50, percent of the loudest note value. */
  threshold: number;
}

/** Uploads the file and waits for the frames to be created. Rejects with a message fit to show the user. */
export async function submitJob(file: File, settings: JobSettings): Promise<JobResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("window_size", String(settings.windowSize));
  body.append("frame_rate", String(settings.frameRate));
  body.append("window_spacing", String(settings.windowSpacing));
  body.append("brightness", String(settings.brightness));
  body.append("smoothing", String(settings.smoothing));
  body.append("energy", String(settings.energy));
  body.append("hue_step", settings.hueStep === null ? "N/A" : String(settings.hueStep));
  body.append("saturation_step", settings.saturationStep === null ? "N/A" : String(settings.saturationStep));
  body.append("brightness_step", settings.brightnessStep === null ? "N/A" : String(settings.brightnessStep));
  body.append("threshold", String(settings.threshold));

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
