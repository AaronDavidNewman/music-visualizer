import { describe, expect, it } from "vitest";
import { GROUPS, controlsIn, groupOf, groupTitle, groupsFor, isOpen, rowsOf, setOpen, toggle } from "./groups";
import { IMAGE_TYPES } from "./validation";

const TYPES = IMAGE_TYPES.map((t) => t.value);

// What each image type must show, written out here independently of the module under test (spec FR-003 to FR-009).
const COMMON_TOP = ["window-size", "frame-rate", "colormap", "image-type"];
const BEAT = ["beat-coloring", "peak-distance"];
const EIGHT = ["decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe", "polychord", "spirograph", "rhythm-circles"]; // the pictures that take the n loudest notes (feature 044, Spirograph feature 046, Rhythm Circles feature 047)
const EXPECTED: Record<string, string[]> = {
  contour: [...COMMON_TOP, "threshold", "notes", "wave-count", "export-obj", ...BEAT, "resolution", "interpolate", "gaussian"],
  decay: [...COMMON_TOP, "decay-rate", "decay-low", "decay-medium", "decay-high", "decay-saturated", "extra-notes", "note-layout", "peak-distance"],
  "decay-exp": [...COMMON_TOP, "decay-rate", "extra-notes", "note-layout", "peak-distance"],
  "polar-chords": [...COMMON_TOP, "polar-notes", "extra-notes", "note-layout", "peak-distance"],
  "energy-graphs": [...COMMON_TOP], // no setting of its own, and the data is not smoothed
  "chromatic-decay": [...COMMON_TOP, "threshold", "chromatic-decay-rate", "extra-notes", "peak-distance"],
  "rhythm-circles": [...COMMON_TOP, "vote-limit", "extra-notes", "peak-distance"], // feature 047: the Vote limit, the Extra notes of the starts and Minimum distance of the peaks; the data is not smoothed
  "chromatic-wireframe": [...COMMON_TOP, "threshold", "chromatic-decay-rate", "extra-notes", "export-obj", "peak-distance"], // the controls of Chromatic Decay (feature 039)
  polychord: [...COMMON_TOP, "polychord-notes", "polychord-min-copies", "polychord-max-copies", "polychord-rotation", "extra-notes", "peak-distance"], // feature 042
  spirograph: [...COMMON_TOP, "spirograph-notes", "spirograph-history", "spirograph-fade", "extra-notes", "peak-distance"], // feature 046: the beat sets the turns and the big circle
};

describe("the groups", () => {
  it("are the eighteen groups of the data model, with their titles and controls in order", () => {
    expect(GROUPS.map((g) => [g.id, g.title, [...g.controls]])).toEqual([
      ["analysis", "Analysis", ["window-size", "frame-rate"]],
      ["colormap", "Colormap", ["colormap"]],
      ["image-type", "Image type", ["image-type"]],
      ["contour", "Contour", ["threshold", "notes", "wave-count"]],
      ["decay", "Decay", ["decay-rate", "decay-low", "decay-medium", "decay-high", "decay-saturated"]],
      ["decay-exp", "Decay", ["decay-rate"]],
      ["polar-chords", "Polar chords", ["polar-notes"]],
      ["chromatic-decay", "Chromatic Decay", ["threshold", "chromatic-decay-rate"]],
      ["chromatic-wireframe", "Chromatic Wireframe", ["threshold", "chromatic-decay-rate"]],
      ["polychord", "Polychord", ["polychord-notes", "polychord-min-copies", "polychord-max-copies", "polychord-rotation"]],
      ["spirograph", "Spirograph", ["spirograph-notes", "spirograph-history", "spirograph-fade"]],
      ["rhythm-circles", "Rhythm Circles", ["vote-limit"]],
      ["held-notes", "Held notes", ["extra-notes"]],
      ["obj-export", "3D export", ["export-obj"]],
      ["note-layout", "Note layout", ["note-layout"]],
      ["local-peaks", "Local peaks", ["beat-coloring", "peak-distance"]],
      ["concentric-peaks", "Local peaks", ["peak-distance"]],
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
  it.each(TYPES)("are, for %s, in this order: the top group, Colormap, Image type, the type's group, Image smoothing", (type) => {
    const want = ["analysis", "colormap", "image-type"];
    if (type !== "energy-graphs") want.push(type); // Energy graphs has no group of its own
    if (EIGHT.includes(type)) want.push("held-notes"); // feature 044: the eight pictures that take the n loudest notes
    if (type === "contour" || type === "chromatic-wireframe") want.push("obj-export"); // feature 045: the two pictures with the 3D export
    if (type === "decay" || type === "decay-exp" || type === "polar-chords") want.push("note-layout");
    if (type === "contour") want.push("local-peaks");
    if (type === "decay" || type === "decay-exp" || type === "polar-chords" || type === "chromatic-decay" || type === "chromatic-wireframe" || type === "rhythm-circles" || type === "polychord" || type === "spirograph") want.push("concentric-peaks");
    if (type === "contour") want.push("image-smoothing");
    expect(groupsFor(type)).toEqual(want);
  });

  it.each(TYPES)("hold, for %s, exactly the controls that apply to it, each in exactly one group, in order", (type) => {
    const all = groupsFor(type).flatMap((id) => [...controlsIn(id)]);
    expect(all).toEqual(EXPECTED[type]);
    expect(new Set(all).size).toBe(all.length); // no control twice
    for (const control of all) expect(groupsFor(type)).toContain(groupOf(control, type));
  });



  it("have no Data smoothing group any more, and no Window spacing, Smoothing or Smoothing window control in any group (feature 043)", () => {
    expect(GROUPS.map((g) => g.id)).not.toContain("data-smoothing");
    expect([...controlsIn("data-smoothing")]).toEqual([]);
    for (const type of TYPES) {
      expect(groupsFor(type), type).not.toContain("data-smoothing");
      for (const control of ["window-spacing", "smoothing", "smoothing-window"]) expect(groupOf(control, type), `${type} ${control}`).toBeUndefined();
    }
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

  it("puts Window size and Frame rate on one row", () => {
    expect(rowsOf(controlsIn("analysis").length)).toEqual([2]);
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
    expect([...controlsIn("local-peaks")]).toEqual(["beat-coloring", "peak-distance"]);
    expect(groupTitle("local-peaks")).toBe("Local peaks");
  });

  it("follows the group of Contour, before Image smoothing, and is shown for no other type", () => {
    const contour = groupsFor("contour");
    expect(contour.indexOf("local-peaks")).toBe(contour.indexOf("obj-export") + 1); // Contour has no Note layout group (3D export, feature 045, is between)
    expect(contour.indexOf("local-peaks")).toBeLessThan(contour.indexOf("image-smoothing"));
    for (const type of [...TYPES.filter((t) => t !== "contour"), "nonsense"]) expect(groupsFor(type), type).not.toContain("local-peaks");
  });

  it("puts each control in the group, for Contour only", () => {
    for (const control of ["beat-coloring", "peak-distance"]) {
      expect(groupOf(control, "contour"), control).toBe("local-peaks");
      expect(groupOf(control, "decay"), control).not.toBe("local-peaks");
    }
    expect(groupOf("beat-coloring", "decay")).toBeUndefined();
  });

  it("is laid out as one row of two (the checkbox and Minimum distance; the Prominence of feature 024 was removed in feature 040)", () => {
    expect(rowsOf(controlsIn("local-peaks").length)).toEqual([2]);
  });
});

describe("the Local peaks group without the checkbox (feature 025)", () => {
  it("has the Minimum distance of the measurement and no checkbox, under the same title as the group of Contour", () => {
    expect([...controlsIn("concentric-peaks")]).toEqual(["peak-distance"]);
    expect(groupTitle("concentric-peaks")).toBe("Local peaks");
    expect(rowsOf(controlsIn("concentric-peaks").length)).toEqual([1]);
  });

  it("is shown for Decay, Decay Exp and Polar Chords after the Note layout group and before Data smoothing, with no group of its own", () => {
    expect(groupsFor("decay-exp")).toEqual(["analysis", "colormap", "image-type", "decay-exp", "held-notes", "note-layout", "concentric-peaks"]);
    for (const type of ["contour", "nonsense"]) expect(groupsFor(type), type).not.toContain("concentric-peaks");
    expect(groupsFor("decay")).not.toContain("local-peaks");
  });

  it("puts Minimum distance in it for Decay, and none of the grid or checkbox controls in any group", () => {
    expect(groupOf("peak-distance", "decay")).toBe("concentric-peaks");
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

  it("is shown for Decay, Decay Exp and Polar Chords, after the group of the type and Held notes and before Local peaks, and for no other type", () => {
    for (const type of ["decay", "decay-exp", "polar-chords"]) {
      const ids = groupsFor(type);
      expect(ids.indexOf("note-layout"), type).toBe(ids.indexOf("held-notes") + 1);
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
    expect(groupsFor("decay")).toEqual(["analysis", "colormap", "image-type", "decay", "held-notes", "note-layout", "concentric-peaks"]);
    for (const type of ["contour", "decay-exp", "nonsense"]) expect(groupsFor(type), type).not.toContain("decay");
  });

  it("puts the controls in their groups for Decay and none of the grid controls anywhere", () => {
    expect(groupOf("decay-rate", "decay")).toBe("decay");
    expect(groupOf("note-layout", "decay")).toBe("note-layout");
    expect(groupOf("peak-distance", "decay")).toBe("concentric-peaks");
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
    expect(groupsFor("contour")).toEqual(["analysis", "colormap", "image-type", "contour", "obj-export", "local-peaks", "image-smoothing"]);
  });
});

describe("the Decay Exp group (feature 030)", () => {
  it("is titled Decay and has the decay rate only, alone on its row", () => {
    expect(groupTitle("decay-exp")).toBe("Decay");
    expect([...controlsIn("decay-exp")]).toEqual(["decay-rate"]);
    expect(rowsOf(controlsIn("decay-exp").length)).toEqual([1]);
  });

  it("is shown for Decay Exp only, between Image type and Note layout, with Local peaks without the checkbox", () => {
    expect(groupsFor("decay-exp")).toEqual(["analysis", "colormap", "image-type", "decay-exp", "held-notes", "note-layout", "concentric-peaks"]);
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
    expect(groupsFor("polar-chords")).toEqual(["analysis", "colormap", "image-type", "polar-chords", "held-notes", "note-layout", "concentric-peaks"]);
    for (const type of TYPES.filter((t) => t !== "polar-chords")) expect(groupsFor(type), type).not.toContain("polar-chords");
  });

  it("puts Notes shown in its group for Polar Chords and in no group of any other type", () => {
    expect(groupOf("polar-notes", "polar-chords")).toBe("polar-chords");
    for (const type of TYPES.filter((t) => t !== "polar-chords")) expect(groupOf("polar-notes", type), type).toBeUndefined();
  });

  it("puts the note layout and the Local peaks settings in their groups (without the checkbox) and shows none of the controls that do not apply", () => {
    expect(groupOf("note-layout", "polar-chords")).toBe("note-layout");
    expect(groupOf("peak-distance", "polar-chords")).toBe("concentric-peaks");
    for (const control of ["beat-coloring", "threshold", "notes", "blend-width", "resolution", "interpolate", "gaussian", "circle-unit", "decay-rate", "decay-low", "wave-count"]) {
      expect(groupOf(control, "polar-chords"), control).toBeUndefined();
    }
  });

  it("leaves the groups of the other eight types as they were", () => {
    expect(groupsFor("decay-exp")).toEqual(["analysis", "colormap", "image-type", "decay-exp", "held-notes", "note-layout", "concentric-peaks"]);
  });
});

describe("the groups of Energy graphs (feature 034)", () => {
  it("are only the top group, Colormap and Image type: no group of its own, no layout, peaks or smoothing", () => {
    expect(groupsFor("energy-graphs")).toEqual(["analysis", "colormap", "image-type"]);
  });

  it("add no group to any other type and take no control of any other type", () => {
    for (const type of TYPES.filter((t) => t !== "energy-graphs")) expect(groupsFor(type), type).not.toContain("energy-graphs");
    for (const control of ["note-layout", "peak-distance", "polar-notes", "threshold", "resolution"]) {
      expect(groupOf(control, "energy-graphs"), control).toBeUndefined();
    }
  });

});

describe("the groups of Chromatic Decay (feature 035)", () => {
  it("are Analysis, Colormap, Image type, Chromatic Decay (its decay rate), and Local peaks (no checkbox), in this order", () => {
    expect(groupsFor("chromatic-decay")).toEqual(["analysis", "colormap", "image-type", "chromatic-decay", "held-notes", "concentric-peaks"]);
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
  });

  it("adds no group and no control to any other type", () => {
    for (const type of TYPES.filter((t) => t !== "chromatic-decay" && t !== "chromatic-wireframe")) {
      expect(groupsFor(type), type).not.toContain("chromatic-decay");
      expect(groupOf("chromatic-decay-rate", type), type).toBeUndefined();
    }
  });
});

describe("the groups of Rhythm Circles (features 038 and 047)", () => {
  it("are Analysis, Colormap, Image type, Rhythm Circles (the Vote limit), Held notes and Local peaks (no checkbox), in this order: no layout, no smoothing", () => {
    expect(groupsFor("rhythm-circles")).toEqual(["analysis", "colormap", "image-type", "rhythm-circles", "held-notes", "concentric-peaks"]);
  });

  it("has the title Rhythm Circles and the one control Vote limit", () => {
    expect(groupTitle("rhythm-circles")).toBe("Rhythm Circles");
    expect([...controlsIn("rhythm-circles")]).toEqual(["vote-limit"]);
    expect(rowsOf(controlsIn("rhythm-circles").length)).toEqual([1]);
  });

  it("shows the Vote limit, the Extra notes and Minimum distance and none of the settings of the other types", () => {
    expect(groupOf("vote-limit", "rhythm-circles")).toBe("rhythm-circles");
    expect(groupOf("extra-notes", "rhythm-circles")).toBe("held-notes");
    expect(groupOf("peak-distance", "rhythm-circles")).toBe("concentric-peaks");
    for (const control of ["smoothing", "smoothing-window", "threshold", "notes", "resolution", "interpolate", "gaussian", "note-layout", "decay-rate", "chromatic-decay-rate", "polar-notes", "beat-coloring"]) {
      expect(groupOf(control, "rhythm-circles"), control).toBeUndefined();
    }
  });

  it("adds no group and no Vote limit to any other type and takes no Local peaks control from them", () => {
    for (const type of TYPES.filter((t) => t !== "rhythm-circles")) {
      expect(groupsFor(type), type).not.toContain("rhythm-circles");
      expect(groupOf("vote-limit", type), type).toBeUndefined();
    }
    expect(groupsFor("energy-graphs")).toEqual(["analysis", "colormap", "image-type"]);
    expect(groupsFor("chromatic-decay")).toEqual(["analysis", "colormap", "image-type", "chromatic-decay", "held-notes", "concentric-peaks"]);
  });
});

describe("the groups of Chromatic Wireframe (feature 039)", () => {
  it("are those of Chromatic Decay, with a group of its own: Analysis, Colormap, Image type, Chromatic Wireframe, Local peaks (no checkbox)", () => {
    expect(groupsFor("chromatic-wireframe")).toEqual(["analysis", "colormap", "image-type", "chromatic-wireframe", "held-notes", "obj-export", "concentric-peaks"]);
    expect(groupsFor("chromatic-wireframe").filter((id) => id !== "obj-export").map((id) => (id === "chromatic-wireframe" ? "chromatic-decay" : id))).toEqual(groupsFor("chromatic-decay"));
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
    for (const control of ["note-layout", "decay-rate", "decay-low", "polar-notes", "notes", "resolution", "interpolate", "gaussian", "beat-coloring", "wave-count", "blend-width"]) {
      expect(groupOf(control, "chromatic-wireframe"), control).toBeUndefined();
    }
  });

  it("adds no group and no control to any other type", () => {
    for (const type of TYPES.filter((t) => t !== "chromatic-wireframe")) expect(groupsFor(type), type).not.toContain("chromatic-wireframe");
    expect(groupsFor("chromatic-decay")).toEqual(["analysis", "colormap", "image-type", "chromatic-decay", "held-notes", "concentric-peaks"]);
    expect(groupsFor("rhythm-circles")).toEqual(["analysis", "colormap", "image-type", "rhythm-circles", "held-notes", "concentric-peaks"]);
  });
});

describe("the groups of Polychord (feature 042)", () => {
  it("are Analysis, Colormap, Image type, Polychord, and Local peaks (no checkbox), in this order", () => {
    expect(groupsFor("polychord")).toEqual(["analysis", "colormap", "image-type", "polychord", "held-notes", "concentric-peaks"]);
  });

  it("has the title Polychord and the four controls, in two rows of two", () => {
    expect(groupTitle("polychord")).toBe("Polychord");
    expect([...controlsIn("polychord")]).toEqual(["polychord-notes", "polychord-min-copies", "polychord-max-copies", "polychord-rotation"]);
    expect(rowsOf(controlsIn("polychord").length)).toEqual([2, 2]);
  });

  it("puts each control in a group, and none of the controls of other types", () => {
    for (const control of ["polychord-notes", "polychord-min-copies", "polychord-max-copies", "polychord-rotation"]) expect(groupOf(control, "polychord"), control).toBe("polychord");
    expect(groupOf("peak-distance", "polychord")).toBe("concentric-peaks");
    for (const control of ["threshold", "chromatic-decay-rate", "decay-rate", "note-layout", "polar-notes", "beat-coloring", "notes", "resolution", "wave-count"]) {
      expect(groupOf(control, "polychord"), control).toBeUndefined();
    }
  });

  it("is in the groups of no other type", () => {
    for (const type of TYPES.filter((t) => t !== "polychord")) expect(groupsFor(type), type).not.toContain("polychord");
  });
});


describe("the Held notes group (feature 044)", () => {
  it("has the title Held notes and the one control Extra notes", () => {
    expect(groupTitle("held-notes")).toBe("Held notes");
    expect([...controlsIn("held-notes")]).toEqual(["extra-notes"]);
    expect(rowsOf(controlsIn("held-notes").length)).toEqual([1]);
  });

  it("is shown for exactly the eight pictures that take the n loudest notes, right after the group of the type", () => {
    for (const type of TYPES) {
      const ids = groupsFor(type);
      if (EIGHT.includes(type)) {
        expect(ids.indexOf("held-notes"), type).toBe(ids.indexOf(type) + 1);
        expect(groupOf("extra-notes", type), type).toBe("held-notes");
      } else {
        expect(ids, type).not.toContain("held-notes");
        expect(groupOf("extra-notes", type), type).toBeUndefined();
      }
    }
  });

  it("comes before Note layout and before Local peaks", () => {
    for (const type of ["decay", "decay-exp", "polar-chords"]) {
      const ids = groupsFor(type);
      expect(ids.indexOf("held-notes"), type).toBeLessThan(ids.indexOf("note-layout"));
      expect(ids.indexOf("held-notes"), type).toBeLessThan(ids.indexOf("concentric-peaks"));
    }
  });
});

describe("the 3D export group (feature 045)", () => {
  const TWO = ["contour", "chromatic-wireframe"];

  it("has the title 3D export and the one control Export 3D files", () => {
    expect(groupTitle("obj-export")).toBe("3D export");
    expect([...controlsIn("obj-export")]).toEqual(["export-obj"]);
    expect(rowsOf(controlsIn("obj-export").length)).toEqual([1]);
  });

  it("is shown for exactly Contour and Chromatic Wireframe, right after the group of the type (and Held notes)", () => {
    for (const type of TYPES) {
      const ids = groupsFor(type);
      if (TWO.includes(type)) {
        const before = type === "contour" ? type : "held-notes"; // Chromatic Wireframe also has Held notes after its group
        expect(ids.indexOf("obj-export"), type).toBe(ids.indexOf(before) + 1);
        expect(groupOf("export-obj", type), type).toBe("obj-export");
      } else {
        expect(ids, type).not.toContain("obj-export");
        expect(groupOf("export-obj", type), type).toBeUndefined();
      }
    }
    expect(groupsFor("nonsense")).not.toContain("obj-export");
  });

  it("comes before Local peaks and before Image smoothing", () => {
    for (const type of TWO) {
      const ids = groupsFor(type);
      expect(ids.indexOf("obj-export"), type).toBeLessThan(ids.indexOf(type === "contour" ? "local-peaks" : "concentric-peaks"));
    }
    expect(groupsFor("contour").indexOf("obj-export")).toBeLessThan(groupsFor("contour").indexOf("image-smoothing"));
  });
});

describe("the groups of Spirograph (feature 046)", () => {
  it("are Analysis, Colormap, Image type, Spirograph, Held notes and Local peaks (Minimum distance only), in this order", () => {
    expect(groupsFor("spirograph")).toEqual(["analysis", "colormap", "image-type", "spirograph", "held-notes", "concentric-peaks"]);
  });

  it("has the title Spirograph and the three controls, in a row of two and a row of one", () => {
    expect(groupTitle("spirograph")).toBe("Spirograph");
    expect([...controlsIn("spirograph")]).toEqual(["spirograph-notes", "spirograph-history", "spirograph-fade"]);
    expect(rowsOf(controlsIn("spirograph").length)).toEqual([2, 1]);
  });

  it("puts each control in its group (Minimum distance in Local peaks) and shows none of the other types' controls", () => {
    for (const control of ["spirograph-notes", "spirograph-history", "spirograph-fade"]) expect(groupOf(control, "spirograph"), control).toBe("spirograph");
    expect(groupOf("extra-notes", "spirograph")).toBe("held-notes");
    expect(groupOf("peak-distance", "spirograph")).toBe("concentric-peaks");
    for (const control of ["beat-coloring", "threshold", "note-layout", "export-obj", "resolution", "polychord-notes"]) {
      expect(groupOf(control, "spirograph"), control).toBeUndefined();
    }
  });

  it("is shown for no other type", () => {
    for (const type of TYPES.filter((t) => t !== "spirograph")) expect(groupsFor(type), type).not.toContain("spirograph");
  });
});
