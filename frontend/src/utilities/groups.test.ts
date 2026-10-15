import { describe, expect, it } from "vitest";
import { GROUPS, controlsIn, groupOf, groupTitle, groupsFor, isOpen, rowsOf, setOpen, toggle } from "./groups";
import { IMAGE_TYPES } from "./validation";

const TYPES = IMAGE_TYPES.map((t) => t.value);

// What each image type must show, written out here independently of the module under test (spec FR-003 to FR-009).
const COMMON_TOP = ["window-size", "frame-rate", "window-spacing", "colormap", "image-type"];
const EXPECTED: Record<string, string[]> = {
  tiles: [...COMMON_TOP, "threshold", "notes", "smoothing-window", "smoothing", "resolution", "interpolate"],
  contour: [...COMMON_TOP, "threshold", "notes", "smoothing-window", "smoothing", "resolution", "interpolate"],
  blended: [...COMMON_TOP, "threshold", "notes", "blend-width", "smoothing-window", "smoothing", "resolution", "interpolate"],
  circles: [...COMMON_TOP, "circle-unit", "circle-radius", "circle-resize", "circle-memory", "circle-notes", "smoothing-window", "smoothing"],
  circles_paint: [...COMMON_TOP, "circle-unit", "circle-radius", "circle-resize", "circle-notes", "smoothing-window", "smoothing"],
};

describe("the groups", () => {
  it("are the nine groups of the data model, with their titles and controls in order", () => {
    expect(GROUPS.map((g) => [g.id, g.title, [...g.controls]])).toEqual([
      ["analysis", "Analysis", ["window-size", "frame-rate", "window-spacing"]],
      ["colormap", "Colormap", ["colormap"]],
      ["image-type", "Image type", ["image-type"]],
      ["tiles", "Tiles", ["threshold", "notes"]],
      ["contour", "Contour", ["threshold", "notes"]],
      ["blended", "Blended Tiles", ["threshold", "notes", "blend-width"]],
      ["circles", "Circles", ["circle-unit", "circle-radius", "circle-resize", "circle-memory", "circle-notes"]],
      ["circles_paint", "Circles paint", ["circle-unit", "circle-radius", "circle-resize", "circle-notes"]],
      ["data-smoothing", "Data smoothing", ["smoothing-window", "smoothing"]],
      ["image-smoothing", "Image smoothing", ["resolution", "interpolate"]],
    ]);
  });

  it("have a title and a list of controls through groupTitle and controlsIn", () => {
    for (const g of GROUPS) {
      expect(groupTitle(g.id)).toBe(g.title);
      expect([...controlsIn(g.id)]).toEqual([...g.controls]);
    }
    expect(controlsIn("no-such-group")).toEqual([]);
  });
});

describe("the groups shown for each image type", () => {
  it.each(TYPES)("are, for %s, in this order: the top group, Colormap, Image type, the type's group, Data smoothing, Image smoothing", (type) => {
    const want = ["analysis", "colormap", "image-type", type, "data-smoothing"];
    if (type !== "circles" && type !== "circles_paint") want.push("image-smoothing");
    expect(groupsFor(type)).toEqual(want);
  });

  it.each(TYPES)("hold, for %s, exactly the controls that apply to it, each in exactly one group, in order", (type) => {
    const all = groupsFor(type).flatMap((id) => [...controlsIn(id)]);
    expect(all).toEqual(EXPECTED[type]);
    expect(new Set(all).size).toBe(all.length); // no control twice
    for (const control of all) expect(groupsFor(type)).toContain(groupOf(control, type));
  });

  it("show no control of another type: Threshold, Notes and Blend width are not in Circles; the circle controls are not in the grid types", () => {
    const circles = groupsFor("circles").flatMap((id) => [...controlsIn(id)]);
    for (const c of ["threshold", "notes", "blend-width", "resolution", "interpolate"]) expect(circles).not.toContain(c);
    for (const type of ["tiles", "contour", "blended"]) {
      const grid = groupsFor(type).flatMap((id) => [...controlsIn(id)]);
      for (const c of ["circle-unit", "circle-radius", "circle-resize", "circle-memory", "circle-notes"]) expect(grid).not.toContain(c);
    }
    expect(groupsFor("tiles").flatMap((id) => [...controlsIn(id)])).not.toContain("blend-width");
    expect(groupsFor("contour").flatMap((id) => [...controlsIn(id)])).not.toContain("blend-width");
  });

  it("give Circles paint the circle controls of Circles without Memory, which only Circles has", () => {
    expect([...controlsIn("circles_paint")]).toEqual(["circle-unit", "circle-radius", "circle-resize", "circle-notes"]);
    expect(groupTitle("circles_paint")).toBe("Circles paint");
    expect(groupOf("circle-memory", "circles")).toBe("circles");
    expect(groupOf("circle-memory", "circles_paint")).toBeUndefined();
    for (const control of ["circle-unit", "circle-radius", "circle-resize", "circle-notes"]) expect(groupOf(control, "circles_paint")).toBe("circles_paint");
    for (const control of ["threshold", "notes", "blend-width", "resolution", "interpolate"]) expect(groupOf(control, "circles_paint")).toBeUndefined();
    expect(groupsFor("circles_paint")).not.toContain("image-smoothing");
  });

  it("keep Threshold and Blend width in the type groups and not in Data smoothing (the clarification)", () => {
    expect([...controlsIn("data-smoothing")]).toEqual(["smoothing-window", "smoothing"]);
  });

  it("find the group of a control for a type, and none for a control that is not shown", () => {
    expect(groupOf("threshold", "tiles")).toBe("tiles");
    expect(groupOf("threshold", "contour")).toBe("contour");
    expect(groupOf("threshold", "blended")).toBe("blended");
    expect(groupOf("threshold", "circles")).toBeUndefined();
    expect(groupOf("circle-memory", "circles")).toBe("circles");
    expect(groupOf("resolution", "circles")).toBeUndefined();
    expect(groupOf("resolution", "blended")).toBe("image-smoothing");
  });

  it("show no type group for a type that is not one of the four", () => {
    const ids = groupsFor("nonsense");
    for (const t of TYPES) expect(ids).not.toContain(t);
    expect(ids.slice(0, 3)).toEqual(["analysis", "colormap", "image-type"]);
  });
});

describe("rowsOf", () => {
  it.each([
    [0, []],
    [1, [1]],
    [2, [2]],
    [3, [2, 1]],
    [4, [2, 2]],
    [5, [2, 2, 1]],
    [6, [2, 2, 2]],
  ])("lays %i controls out as %j", (n, rows) => {
    expect(rowsOf(n)).toEqual(rows);
  });

  it("refuses a count that is not a whole number of at least 0", () => {
    for (const bad of [-1, 1.5, NaN, Infinity]) expect(() => rowsOf(bad)).toThrow();
  });

  it.each(TYPES)("gives, for every shown group of %s, rows of at most two and a single control only as the last row", (type) => {
    for (const id of groupsFor(type)) {
      const rows = rowsOf(controlsIn(id).length);
      expect(rows.reduce((a, b) => a + b, 0)).toBe(controlsIn(id).length);
      expect(Math.max(...rows)).toBeLessThanOrEqual(2);
      rows.slice(0, -1).forEach((n) => expect(n).toBe(2));
      if (controlsIn(id).length % 2 === 1) expect(rows[rows.length - 1]).toBe(1);
    }
  });

  it("puts Window size and Frame rate on one row and Window spacing alone, and Notes alone last in Circles", () => {
    expect(rowsOf(controlsIn("analysis").length)).toEqual([2, 1]);
    expect(rowsOf(controlsIn("circles").length)).toEqual([2, 2, 1]);
    expect(rowsOf(controlsIn("circles_paint").length)).toEqual([2, 2]);
    expect(rowsOf(controlsIn("blended").length)).toEqual([2, 1]);
    expect(rowsOf(controlsIn("colormap").length)).toEqual([1]);
  });
});

describe("the open state of a group", () => {
  it("is open for a group that was never touched", () => {
    expect(isOpen({}, "analysis")).toBe(true);
    for (const g of GROUPS) expect(isOpen({}, g.id)).toBe(true);
  });

  it("toggles one group and leaves the others alone, without changing the old state", () => {
    const start = {};
    const once = toggle(start, "colormap");
    expect(isOpen(once, "colormap")).toBe(false);
    for (const g of GROUPS.filter((x) => x.id !== "colormap")) expect(isOpen(once, g.id)).toBe(true);
    expect(start).toEqual({});
    const twice = toggle(once, "colormap");
    expect(isOpen(twice, "colormap")).toBe(true);
  });

  it("is set to the value that the browser reports, whatever the old value was", () => {
    expect(isOpen(setOpen({}, "tiles", false), "tiles")).toBe(false);
    expect(isOpen(setOpen(setOpen({}, "tiles", false), "tiles", true), "tiles")).toBe(true);
    expect(isOpen(setOpen(setOpen({}, "tiles", false), "tiles", false), "tiles")).toBe(false); // the same report twice changes nothing
    expect(isOpen(setOpen({}, "tiles", false), "circles")).toBe(true);
  });

  it("is kept for each type's own group while the form lives, so a type that is chosen again is as it was left", () => {
    let state = setOpen({}, "blended", false);
    state = setOpen(state, "circles", true);
    expect(isOpen(state, "blended")).toBe(false);
    expect(isOpen(state, "tiles")).toBe(true); // a group shown for the first time starts open
  });
});
