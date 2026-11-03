import { createSSRApp, h } from "vue";
import { renderToString } from "vue/server-renderer";
import { describe, expect, it } from "vitest";
import VideoExport from "./VideoExport.vue";
import videoSource from "./VideoExport.vue?raw";
import appSource from "../App.vue?raw";
import type { JobResult } from "../api";

const RESULT = { job_id: "0123456789abcdef0123456789abcdef", frame_count: 10, frame_rate: 24 } as JobResult;

async function render(): Promise<string> {
  return renderToString(createSSRApp({ render: () => h(VideoExport, { result: RESULT }) }));
}

describe("the video export (feature 029)", () => {
  it("offers a Create video button that can be pressed, and shows nothing else before it is pressed", async () => {
    const html = await render();
    expect(html).toContain("Create video");
    expect(html).not.toMatch(/<button[^>]*\sdisabled/);
    expect(html).not.toContain("Making the video");
    expect(html).not.toContain("Video saved to");
    expect(html).not.toContain('role="alert"');
  });

  it("is shown under the player in the results", () => {
    expect(appSource).toMatch(/<VideoExport :result="result" \/>/);
    expect(appSource.indexOf("<FramePlayer")).toBeLessThan(appSource.indexOf("<VideoExport"));
  });

  it("makes the video with the api and has the four states", () => {
    expect(videoSource).toContain("createVideo(");
    for (const state of ["idle", "working", "done", "error"]) expect(videoSource).toContain(`"${state}"`);
  });

  it("disables the button and ignores a second press while it works, and says it is working", () => {
    expect(videoSource).toMatch(/:disabled="status === 'working'"/);
    expect(videoSource).toMatch(/if \(status\.value === "working"\) return;/);
    expect(videoSource).toMatch(/role="status"[\s\S]*Making the video/);
  });

  it("shows an error in an alert and the saved place with a download link when done", () => {
    expect(videoSource).toMatch(/class="error-box" role="alert"/);
    expect(videoSource).toContain("Video saved to");
    expect(videoSource).toMatch(/<a :href="videoUrl\(result\)" download>/);
  });

  it("goes back to idle when a new render replaces the result, and ignores an answer for an old render", () => {
    expect(videoSource).toMatch(/watch\(\s*\(\) => props\.result/);
    expect(videoSource).toContain("current !== job.job_id");
  });
});
