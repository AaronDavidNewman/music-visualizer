import { describe, expect, it } from "vitest";
import playerSource from "./FramePlayer.vue?raw";

// The look of the player cannot be seen without a browser, so these guard its styles (feature 021: frames are 600 x 400 pixels).
describe("the frame player's styles", () => {
  const css = playerSource.slice(playerSource.indexOf("<style"));
  const rule = (selector: string) => css.match(new RegExp(`${selector.replace(".", "\\.")}\\s*\\{([^}]*)\\}`))?.[1] ?? "";

  it("shows the frame at up to its own width, 600 pixels, and no wider", () => {
    const frame = rule(".frame");
    expect(frame).toMatch(/width:\s*100%/);
    expect(frame).toMatch(/max-width:\s*600px/);
    expect(frame).not.toMatch(/660px/);
  });

  it("keeps the 3:2 shape at any width, so that nothing is cropped or distorted", () => {
    expect(rule(".frame")).toMatch(/aspect-ratio:\s*3\s*\/\s*2/);
  });

  it("scales smoothly: the frames are no longer enlarged, so there is no pixelated rendering", () => {
    expect(css).not.toContain("image-rendering");
  });

  it("has no border that would take pixels from the 600 of the frame", () => {
    expect(rule(".frame")).not.toMatch(/(^|[;\s])border:/);
  });

  it("gives the time slider the same maximum width as the frame", () => {
    expect(rule(".slider")).toMatch(/max-width:\s*600px|width:\s*min\(100%,\s*600px\)/);
  });

  it("describes the frames as 600 x 400 and no longer as 252 x 168", () => {
    expect(playerSource).toContain("600 x 400");
    expect(playerSource).not.toContain("252");
  });
});
