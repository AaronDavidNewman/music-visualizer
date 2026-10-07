import { describe, expect, it } from "vitest";
import { popoverPosition } from "./popover";

const viewport = { width: 1000, height: 800 };
const box = { width: 200, height: 100 };

describe("popoverPosition", () => {
  it("goes below the anchor, aligned to its left edge", () => {
    const pos = popoverPosition({ left: 300, top: 200, bottom: 220 }, box, viewport);
    expect(pos).toEqual({ left: 300, top: 228 });
  });

  it("flips above when there is no room below and more room above", () => {
    const pos = popoverPosition({ left: 300, top: 700, bottom: 720 }, box, viewport);
    expect(pos).toEqual({ left: 300, top: 592 }); // 700 - 8 - 100
  });

  it("is pulled up to the bottom edge when it fits on neither side but there is more room below", () => {
    const tall = { width: 200, height: 500 };
    const pos = popoverPosition({ left: 300, top: 300, bottom: 320 }, tall, viewport);
    expect(pos.top).toBe(800 - 500 - 8);
  });

  it("is pulled in from the right edge", () => {
    const pos = popoverPosition({ left: 950, top: 200, bottom: 220 }, box, viewport);
    expect(pos.left).toBe(1000 - 200 - 8);
  });

  it("is pulled in from the left edge", () => {
    const pos = popoverPosition({ left: -20, top: 200, bottom: 220 }, box, viewport);
    expect(pos.left).toBe(8);
  });

  it("is pulled down from the top edge when flipped above with too little room", () => {
    const pos = popoverPosition({ left: 300, top: 40, bottom: 60 }, { width: 200, height: 900 }, { width: 1000, height: 100 });
    expect(pos.top).toBe(8);
  });

  it("goes above, not past the bottom edge, when the anchor is near the bottom", () => {
    const pos = popoverPosition({ left: 300, top: 760, bottom: 780 }, { width: 200, height: 300 }, viewport);
    expect(pos.top).toBe(760 - 8 - 300);
  });

  it("uses the margin when the popover is larger than the viewport", () => {
    const pos = popoverPosition({ left: 100, top: 100, bottom: 120 }, { width: 400, height: 300 }, { width: 300, height: 200 });
    expect(pos).toEqual({ left: 8, top: 8 });
  });

  it("honors a custom margin", () => {
    const pos = popoverPosition({ left: 0, top: 200, bottom: 220 }, box, viewport, 20);
    expect(pos).toEqual({ left: 20, top: 240 });
  });
});
