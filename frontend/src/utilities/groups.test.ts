import { describe, expect, it } from "vitest";
import { GROUPS, controlsIn, groupOf, groupTitle, groupsFor, isOpen, rowsOf, setOpen, toggle } from "./groups";
import { IMAGE_TYPES } from "./validation";

const TYPES = IMAGE_TYPES.map((t) => t.value);

// What each image type must show, written out here independently of the module under test (spec FR-003 to FR-009).
const COMMON_TOP = ["window-size", "frame-rate", "window-spacing", "colormap", "image-type"];
const BEAT = ["beat-coloring", "peak-distance", "peak-prominence"];
const EXPECTED: Record<string, string[]> = {
  contour: [...COMMON_TOP, "threshold", "notes", "wave-count", ...BEAT, "smoothing-window", "smoothing", "resolution", "interpolate", "gaussian"],
  decay: [...COMMON_TOP, "decay-rate", "decay-low", "decay-medium", "decay-high", "decay-saturated", "note-layout", "peak-distance", "peak-prominence", "smoothing-window", "smoothing"],
  "decay-exp": [...COMMON_TOP, "decay-rate", "note-layout", "peak-distance", "peak-prominence", "smoothing-window", "smoothing"],
  "polar-chords": [...COMMON_TOP, "polar-notes", "note-layout", "peak-distance", "peak-prominence", "smoothing-window", "smoothing"],
  "energy-graphs": [...COMMON_TOP], // no setting of its own, and the data is not smoothed
  "chromatic-decay": [...COMMON_TOP, "threshold", "chromatic-decay-rate", "peak-distance", "peak-prominence", "smoothing-window", "smoothing"],
  "rhythm-circles": [...COMMON_TOP, "peak-distance", "peak-prominence"], // the two Local peaks settings and nothing else: the data is not smoothed
  "chromatic-wireframe": [...COMMON_TOP, "threshold", "chromatic-decay-rate", "peak-distance", "peak-prominence", "smoothing-window", "smoothing"], // the controls of Chromatic Decay (feature 039)
};

describe("the groups", () => {
  it("are the fourteen groups of the data model, with their titles and controls in order", () => {
    expect(GROUPS.map((g) => [g.id, g.title, [...g.controls]])).toEqual([
      ["analysis", "Analysis", ["window-size", "frame-rate", "window-spacing"]],
      ["colormap", "Colormap", ["colormap"]],
      ["image-type", "Image type", ["image-type"]],
      ["contour", "Contour", ["threshold", "notes", "wave-count"]],
      ["decay", "Decay", ["decay-rate", "decay-low", "decay-medium", "decay-high", "decay-saturated"]],
      ["decay-exp", "Decay", ["decay-rate"]],
      ["polar-chords", "Polar chords", ["polar-notes"]],
      ["chromatic-decay", "Chromatic Decay", ["threshold", "chromatic-decay-rate"]],
      ["chromatic-wireframe", "Chromatic Wireframe", ["threshold", "chromatic-decay-rate"]],
      ["note-layout", "Note layout", ["note-layout"]],
      ["local-peaks", "Local peaks", ["beat-coloring", "peak-distance", "peak-prominence"]],
      ["concentric-peaks", "Local peaks", ["peak-distance", "peak-prominence"]],
      ["data-smoothing", "Data smoothing", ["smoothing-window", "smoothing"]],
      ["image-smoothing", "Image smoothing", ["resolution", "interpolate", "gaussian"]],
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
    const want = ["analysis", "colormap", "image-type"];
    if (type !== "energy-graphs" && type !== "rhythm-circles") want.push(type); // Energy graphs and Rhythm Circles have no group of their own
    if (type === "decay" || type === "decay-exp" || type === "polar-chords") want.push("note-layout");
    if (type === "contour") want.push("local-peaks");
    if (type === "decay" || type === "decay-exp" || type === "polar-chords" || type === "chromatic-decay" || type === "chromatic-wireframe" || type === "rhythm-circles") want.push("concentric-peaks");
    if (type !== "energy-graphs" && type !== "rhythm-circles") want.push("data-smoothing"); // Energy graphs and Rhythm Circles do not smooth the data
    if (type === "contour") want.push("image-smoothing");
    expect(groupsFor(type)).toEqual(want);
  });

  it.each(TYPES)("hold, for %s, exactly the controls that apply to it, each in exactly one group, in order", (type) => {
    const all = groupsFor(type).flatMap((id) => [...controlsIn(id)]);
    expect(all).toEqual(EXPECTED[type]);
    expect(new Set(all).size).toBe(all.length); // no control twice
    for (const control of all) expect(groupsFor(type)).toContain(groupOf(control, type));
  });



  it("keep Threshold and Blend width in the type groups and not in Data smoothing (the clarification)", () => {
    expect([...controlsIn("data-smoothing")]).toEqual(["smoothing-window", "smoothing"]);
  });

  it("put the Gaussian smoothing in Image smoothing, last, for the contour only", () => {
    expect([...controlsIn("image-smoothing")]).toEqual(["resolution", "interpolate", "gaussian"]);
    expect(groupOf("gaussian", "contour")).toBe("image-smoothing");
    for (const type of TYPES.filter((t) => t !== "contour")) expect(groupOf("gaussian", type), type).toBeUndefined();
  });

  it("find the group of a control for a type, and none for a control that is not shown", () => {
    expect(groupOf("threshold", "contour")).toBe("contour");
    expect(groupOf("threshold", "decay")).toBeUndefined();
    expect(groupOf("resolution", "decay")).toBeUndefined();
    expect(groupOf("resolution", "contour")).toBe("image-smoothing");
    expect(groupOf("decay-rate", "decay")).toBe("decay");
    expect(groupOf("blend-width", "contour")).toBeUndefined();
    expect(groupOf("circle-memory", "decay")).toBeUndefined();
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

  it("puts Window size and Frame rate on one row and Window spacing alone", () => {
    expect(rowsOf(controlsIn("analysis").length)).toEqual([2, 1]);
    expect(rowsOf(controlsIn("image-smoothing").length)).toEqual([2, 1]); // Gaussian smoothing alone on the second row
    expect(rowsOf(controlsIn("contour").length)).toEqual([2, 1]);
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

describe("the Local peaks group (feature 024)", () => {
  it("has the checkbox and the two settings of the measurement, in this order, and a title", () => {
    expect([...controlsIn("local-peaks")]).toEqual(["beat-coloring", "peak-distance", "peak-prominence"]);
    expect(groupTitle("local-peaks")).toBe("Local peaks");
  });

  it("follows the group of Contour, before Data smoothing, and is shown for no other type", () => {
    const contour = groupsFor("contour");
    expect(contour.indexOf("local-peaks")).toBe(contour.indexOf("contour") + 1); // Contour has no Note layout group
    expect(contour.indexOf("local-peaks")).toBeLessThan(contour.indexOf("data-smoothing"));
    for (const type of [...TYPES.filter((t) => t !== "contour"), "nonsense"]) expect(groupsFor(type), type).not.toContain("local-peaks");
  });

  it("puts each control in the group, for Contour only", () => {
    for (const control of ["beat-coloring", "peak-distance", "peak-prominence"]) {
      expect(groupOf(control, "contour"), control).toBe("local-peaks");
      expect(groupOf(control, "decay"), control).not.toBe("local-peaks");
    }
    expect(groupOf("beat-coloring", "decay")).toBeUndefined();
  });

  it("is laid out as one row of two and a single control last", () => {
    expect(rowsOf(controlsIn("local-peaks").length)).toEqual([2, 1]);
  });
});

describe("the Local peaks group without the checkbox (feature 025)", () => {
  it("has the two settings of the measurement and no checkbox, under the same title as the group of Contour", () => {
    expect([...controlsIn("concentric-peaks")]).toEqual(["peak-distance", "peak-prominence"]);
    expect(groupTitle("concentric-peaks")).toBe("Local peaks");
    expect(rowsOf(controlsIn("concentric-peaks").length)).toEqual([2]);
  });

  it("is shown for Decay, Decay Exp and Polar Chords after the Note layout group and before Data smoothing, with no group of its own", () => {
    expect(groupsFor("decay-exp")).toEqual(["analysis", "colormap", "image-type", "decay-exp", "note-layout", "concentric-peaks", "data-smoothing"]);
    for (const type of ["contour", "nonsense"]) expect(groupsFor(type), type).not.toContain("concentric-peaks");
    expect(groupsFor("decay")).not.toContain("local-peaks");
  });

  it("puts Minimum distance and Prominence in it for Decay, and none of the grid or checkbox controls in any group", () => {
    expect(groupOf("peak-distance", "decay")).toBe("concentric-peaks");
    expect(groupOf("peak-prominence", "decay")).toBe("concentric-peaks");
    for (const control of ["beat-coloring", "threshold", "notes", "resolution", "interpolate", "gaussian"]) {
      expect(groupOf(control, "decay"), control).toBeUndefined();
    }
    expect(groupOf("peak-distance", "contour")).toBe("local-peaks");
  });
});

describe("the Note layout group (feature 026)", () => {
  it("has the one dropdown and a title", () => {
    expect([...controlsIn("note-layout")]).toEqual(["note-layout"]);
    expect(groupTitle("note-layout")).toBe("Note layout");
    expect(rowsOf(controlsIn("note-layout").length)).toEqual([1]);
  });

  it("is shown for Decay, Decay Exp and Polar Chords, after the group of the type and before Local peaks, and for no other type", () => {
    for (const type of ["decay", "decay-exp", "polar-chords"]) {
      const ids = groupsFor(type);
      expect(ids.indexOf("note-layout"), type).toBe(ids.indexOf(type) + 1);
      expect(ids.indexOf("concentric-peaks"), type).toBe(ids.indexOf("note-layout") + 1);
    }
    for (const type of ["contour", "chromatic-decay", "chromatic-wireframe", "energy-graphs", "rhythm-circles", "nonsense"]) expect(groupsFor(type), type).not.toContain("note-layout");
  });

  it("puts the control in the group for those three types only", () => {
    for (const type of ["decay", "decay-exp", "polar-chords"]) expect(groupOf("note-layout", type), type).toBe("note-layout");
    for (const type of TYPES.filter((t) => !["decay", "decay-exp", "polar-chords"].includes(t))) expect(groupOf("note-layout", type), type).toBeUndefined();
  });
});

describe("the Decay group (feature 027)", () => {
  it("is titled Decay and has the decay rate and the four decay amounts, one for each saturation level", () => {
    expect(groupTitle("decay")).toBe("Decay");
    expect([...controlsIn("decay")]).toEqual(["decay-rate", "decay-low", "decay-medium", "decay-high", "decay-saturated"]);
    expect(rowsOf(controlsIn("decay").length)).toEqual([2, 2, 1]);
  });

  it("puts each decay amount in the Decay group for Decay and in no group of any other type", () => {
    for (const control of ["decay-low", "decay-medium", "decay-high", "decay-saturated"]) {
      expect(groupOf(control, "decay"), control).toBe("decay");
      for (const type of TYPES.filter((t) => t !== "decay")) expect(groupOf(control, type), control + type).toBeUndefined();
    }
  });

  it("is shown for Decay only, between Image type and Note layout, with Local peaks without the checkbox", () => {
    expect(groupsFor("decay")).toEqual(["analysis", "colormap", "image-type", "decay", "note-layout", "concentric-peaks", "data-smoothing"]);
    for (const type of ["contour", "decay-exp", "nonsense"]) expect(groupsFor(type), type).not.toContain("decay");
  });

  it("puts the controls in their groups for Decay and none of the grid controls anywhere", () => {
    expect(groupOf("decay-rate", "decay")).toBe("decay");
    expect(groupOf("note-layout", "decay")).toBe("note-layout");
    expect(groupOf("peak-distance", "decay")).toBe("concentric-peaks");
    expect(groupOf("peak-prominence", "decay")).toBe("concentric-peaks");
    for (const control of ["threshold", "notes", "blend-width", "beat-coloring", "resolution", "interpolate", "gaussian", "circle-unit"]) {
      expect(groupOf(control, "decay"), control).toBeUndefined();
    }
    for (const type of TYPES.filter((t) => t !== "decay" && t !== "decay-exp")) expect(groupOf("decay-rate", type), type).toBeUndefined();
  });
});

describe("the Contour group and the wave count (feature 028)", () => {
  it("has Threshold, Notes and the wave count, three controls, the wave count alone on the last row", () => {
    expect([...controlsIn("contour")]).toEqual(["threshold", "notes", "wave-count"]);
    expect(rowsOf(controlsIn("contour").length)).toEqual([2, 1]);
  });

  it("puts the wave count in the Contour group and in no group of any other type", () => {
    expect(groupOf("wave-count", "contour")).toBe("contour");
    for (const type of TYPES.filter((t) => t !== "contour")) expect(groupOf("wave-count", type), type).toBeUndefined();
  });

  it("shows, for Contour, the groups in the order of the contract", () => {
    expect(groupsFor("contour")).toEqual(["analysis", "colormap", "image-type", "contour", "local-peaks", "data-smoothing", "image-smoothing"]);
  });
});

describe("the Decay Exp group (feature 030)", () => {
  it("is titled Decay and has the decay rate only, alone on its row", () => {
    expect(groupTitle("decay-exp")).toBe("Decay");
    expect([...controlsIn("decay-exp")]).toEqual(["decay-rate"]);
    expect(rowsOf(controlsIn("decay-exp").length)).toEqual([1]);
  });

  it("is shown for Decay Exp only, between Image type and Note layout, with Local peaks without the checkbox", () => {
    expect(groupsFor("decay-exp")).toEqual(["analysis", "colormap", "image-type", "decay-exp", "note-layout", "concentric-peaks", "data-smoothing"]);
    for (const type of TYPES.filter((t) => t !== "decay-exp")) expect(groupsFor(type), type).not.toContain("decay-exp");
  });

  it("puts the decay rate in its group and none of the four decay amounts anywhere for Decay Exp", () => {
    expect(groupOf("decay-rate", "decay-exp")).toBe("decay-exp");
    expect(groupOf("decay-rate", "decay")).toBe("decay");
    expect(groupOf("note-layout", "decay-exp")).toBe("note-layout");
    expect(groupOf("peak-distance", "decay-exp")).toBe("concentric-peaks");
    for (const control of ["decay-low", "decay-medium", "decay-high", "decay-saturated", "threshold", "notes", "blend-width", "beat-coloring", "resolution", "interpolate", "gaussian", "circle-unit"]) {
      expect(groupOf(control, "decay-exp"), control).toBeUndefined();
    }
    for (const control of ["decay-low", "decay-medium", "decay-high", "decay-saturated"]) expect(groupOf(control, "decay"), control).toBe("decay");
  });
});

describe("the Polar chords group (feature 032)", () => {
  it("is titled Polar chords and has Notes shown alone on its row", () => {
    expect(groupTitle("polar-chords")).toBe("Polar chords");
    expect([...controlsIn("polar-chords")]).toEqual(["polar-notes"]);
    expect(rowsOf(controlsIn("polar-chords").length)).toEqual([1]);
  });

  it("is shown for Polar Chords only, between Image type and Note layout, without the image smoothing", () => {
    expect(groupsFor("polar-chords")).toEqual(["analysis", "colormap", "image-type", "polar-chords", "note-layout", "concentric-peaks", "data-smoothing"]);
    for (const type of TYPES.filter((t) => t !== "polar-chords")) expect(groupsFor(type), type).not.toContain("polar-chords");
  });

  it("puts Notes shown in its group for Polar Chords and in no group of any other type", () => {
    expect(groupOf("polar-notes", "polar-chords")).toBe("polar-chords");
    for (const type of TYPES.filter((t) => t !== "polar-chords")) expect(groupOf("polar-notes", type), type).toBeUndefined();
  });

  it("puts the note layout and the Local peaks settings in their groups (without the checkbox) and shows none of the controls that do not apply", () => {
    expect(groupOf("note-layout", "polar-chords")).toBe("note-layout");
    expect(groupOf("peak-distance", "polar-chords")).toBe("concentric-peaks");
    expect(groupOf("peak-prominence", "polar-chords")).toBe("concentric-peaks");
    for (const control of ["beat-coloring", "threshold", "notes", "blend-width", "resolution", "interpolate", "gaussian", "circle-unit", "decay-rate", "decay-low", "wave-count"]) {
      expect(groupOf(control, "polar-chords"), control).toBeUndefined();
    }
  });

  it("leaves the groups of the other eight types as they were", () => {
    expect(groupsFor("decay-exp")).toEqual(["analysis", "colormap", "image-type", "decay-exp", "note-layout", "concentric-peaks", "data-smoothing"]);
  });
});

describe("the groups of Energy graphs (feature 034)", () => {
  it("are only the top group, Colormap and Image type: no group of its own, no layout, peaks or smoothing", () => {
    expect(groupsFor("energy-graphs")).toEqual(["analysis", "colormap", "image-type"]);
  });

  it("add no group to any other type and take no control of any other type", () => {
    for (const type of TYPES.filter((t) => t !== "energy-graphs")) expect(groupsFor(type), type).not.toContain("energy-graphs");
    for (const control of ["smoothing", "smoothing-window", "note-layout", "peak-distance", "polar-notes", "threshold", "resolution"]) {
      expect(groupOf(control, "energy-graphs"), control).toBeUndefined();
    }
  });

  it("leave Data smoothing in the other types as it was (all but Rhythm Circles, which does not smooth the data either)", () => {
    for (const type of TYPES.filter((t) => t !== "energy-graphs" && t !== "rhythm-circles")) expect(groupsFor(type), type).toContain("data-smoothing");
  });
});

describe("the groups of Chromatic Decay (feature 035)", () => {
  it("are Analysis, Colormap, Image type, Chromatic Decay (its decay rate), Local peaks (no checkbox) and Data smoothing, in this order", () => {
    expect(groupsFor("chromatic-decay")).toEqual(["analysis", "colormap", "image-type", "chromatic-decay", "concentric-peaks", "data-smoothing"]);
  });

  it("has a group of its own with two controls, the threshold and the decay rate (feature 037), in a row of two", () => {
    expect(groupTitle("chromatic-decay")).toBe("Chromatic Decay");
    expect([...controlsIn("chromatic-decay")]).toEqual(["threshold", "chromatic-decay-rate"]);
    expect(rowsOf(controlsIn("chromatic-decay").length)).toEqual([2]);
  });

  it("has the Threshold control in its group, and the other types keep theirs (Contour only)", () => {
    expect(groupOf("threshold", "chromatic-decay")).toBe("chromatic-decay");
    expect(groupOf("threshold", "contour")).toBe("contour");
    for (const type of TYPES.filter((t) => !["contour", "chromatic-decay", "chromatic-wireframe"].includes(t))) expect(groupOf("threshold", type), type).toBeUndefined();
  });

  it("shows neither the Note layout nor Image smoothing nor the old decay controls for it", () => {
    for (const control of ["note-layout", "decay-rate", "decay-low", "polar-notes", "notes", "resolution", "beat-coloring"]) {
      expect(groupOf(control, "chromatic-decay"), control).toBeUndefined();
    }
    expect(groupOf("chromatic-decay-rate", "chromatic-decay")).toBe("chromatic-decay");
    expect(groupOf("peak-distance", "chromatic-decay")).toBe("concentric-peaks");
    expect(groupOf("smoothing", "chromatic-decay")).toBe("data-smoothing");
  });

  it("adds no group and no control to any other type", () => {
    for (const type of TYPES.filter((t) => t !== "chromatic-decay" && t !== "chromatic-wireframe")) {
      expect(groupsFor(type), type).not.toContain("chromatic-decay");
      expect(groupOf("chromatic-decay-rate", type), type).toBeUndefined();
    }
  });
});

describe("the groups of Rhythm Circles (feature 038)", () => {
  it("are Analysis, Colormap, Image type and Local peaks (no checkbox): no group of its own, no layout, no smoothing", () => {
    expect(groupsFor("rhythm-circles")).toEqual(["analysis", "colormap", "image-type", "concentric-peaks"]);
  });

  it("shows the two Local peaks controls and none of the settings of the other types", () => {
    expect(groupOf("peak-distance", "rhythm-circles")).toBe("concentric-peaks");
    expect(groupOf("peak-prominence", "rhythm-circles")).toBe("concentric-peaks");
    for (const control of ["smoothing", "smoothing-window", "threshold", "notes", "resolution", "interpolate", "gaussian", "note-layout", "decay-rate", "chromatic-decay-rate", "polar-notes", "beat-coloring"]) {
      expect(groupOf(control, "rhythm-circles"), control).toBeUndefined();
    }
  });

  it("adds no group to any other type and takes no Local peaks control from them", () => {
    for (const type of TYPES.filter((t) => t !== "rhythm-circles")) expect(groupsFor(type), type).not.toContain("rhythm-circles");
    expect(groupsFor("energy-graphs")).toEqual(["analysis", "colormap", "image-type"]);
    expect(groupsFor("chromatic-decay")).toEqual(["analysis", "colormap", "image-type", "chromatic-decay", "concentric-peaks", "data-smoothing"]);
  });
});

describe("the groups of Chromatic Wireframe (feature 039)", () => {
  it("are those of Chromatic Decay, with a group of its own: Analysis, Colormap, Image type, Chromatic Wireframe, Local peaks (no checkbox) and Data smoothing", () => {
    expect(groupsFor("chromatic-wireframe")).toEqual(["analysis", "colormap", "image-type", "chromatic-wireframe", "concentric-peaks", "data-smoothing"]);
    expect(groupsFor("chromatic-wireframe").map((id) => (id === "chromatic-wireframe" ? "chromatic-decay" : id))).toEqual(groupsFor("chromatic-decay"));
  });

  it("has the title Chromatic Wireframe and the Threshold and the decay rate of Chromatic Decay (a whole number of frames), on one row", () => {
    expect(groupTitle("chromatic-wireframe")).toBe("Chromatic Wireframe");
    expect([...controlsIn("chromatic-wireframe")]).toEqual(["threshold", "chromatic-decay-rate"]);
    expect(rowsOf(controlsIn("chromatic-wireframe").length)).toEqual([2]);
  });

  it("puts the controls in the groups of the type and none of the controls the type does not use", () => {
    expect(groupOf("threshold", "chromatic-wireframe")).toBe("chromatic-wireframe");
    expect(groupOf("chromatic-decay-rate", "chromatic-wireframe")).toBe("chromatic-wireframe");
    expect(groupOf("peak-distance", "chromatic-wireframe")).toBe("concentric-peaks");
    expect(groupOf("peak-prominence", "chromatic-wireframe")).toBe("concentric-peaks");
    expect(groupOf("smoothing", "chromatic-wireframe")).toBe("data-smoothing");
    for (const control of ["note-layout", "decay-rate", "decay-low", "polar-notes", "notes", "resolution", "interpolate", "gaussian", "beat-coloring", "wave-count", "blend-width"]) {
      expect(groupOf(control, "chromatic-wireframe"), control).toBeUndefined();
    }
  });

  it("adds no group and no control to any other type", () => {
    for (const type of TYPES.filter((t) => t !== "chromatic-wireframe")) expect(groupsFor(type), type).not.toContain("chromatic-wireframe");
    expect(groupsFor("chromatic-decay")).toEqual(["analysis", "colormap", "image-type", "chromatic-decay", "concentric-peaks", "data-smoothing"]);
    expect(groupsFor("rhythm-circles")).toEqual(["analysis", "colormap", "image-type", "concentric-peaks"]);
  });
});
