export interface JobResult {
  job_id: string;
  file_name: string;
  sample_rate: number;
  duration_seconds: number;
  window_size: number;
  frame_rate: number;
  frame_count: number;
  window_spacing: number;
  step_samples: number;
  window_count: number;
  spacing_raised: boolean;
  frame_url_template: string;
}

/** Uploads the file and waits for the frames to be created. Rejects with a message fit to show the user. */
export async function submitJob(
  file: File,
  windowSize: number,
  frameRate: number,
  windowSpacing: number,
): Promise<JobResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("window_size", String(windowSize));
  body.append("frame_rate", String(frameRate));
  body.append("window_spacing", String(windowSpacing));

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
