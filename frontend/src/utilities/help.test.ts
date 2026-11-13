import { describe, expect, it } from "vitest";
import {
  chromaticRateHelp,
  colormapHelp,
  frameRateHelp,
  imageTypeHelp,
  gaussianHelp,
  interpolateHelp,
  decayAmountHelp,
  decayExpRateHelp,
  decayRateHelp,
  polarNotesHelp,
  waveCountHelp,
  noteCountHelp,
  resolutionHelp,
  smoothingHelp,
  smoothingWindowHelp,
  spacingHelp,
  thresholdHelp,
  windowSizeHelp,
} from "./help";
import { FRAME_RATE_RANGE } from "./validation";

describe("setting explanations", () => {
  it("keeps the wording that used to be printed under the fields", () => {
    expect(windowSizeHelp).toBe("Larger windows separate low notes better but blur changes over time.");
  });

  it("states the frame rate range from the validation constants", () => {
    expect(frameRateHelp).toBe(`${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`);
  });

  it("explains the spacing and adds the step hint when there is one", () => {
    const base = spacingHelp("");
    expect(base).toBe("Distance between the starts of windows, as a multiple of the window size.");
    expect(spacingHelp("Step between windows: 1024 samples (23.2 ms).")).toBe(
      `${base} Step between windows: 1024 samples (23.2 ms).`,
    );
  });

  it("explains the threshold: not drawn below it (the value is 0 in the contour), a share of the loudest note in the file, left end off, right end 10%", () => {
    expect(thresholdHelp).toContain("is not drawn");
    expect(thresholdHelp).toContain("with Contour its value is 0");
    expect(thresholdHelp).not.toContain("Tiles");
    expect(thresholdHelp).not.toContain("Blended");
    expect(thresholdHelp).toContain("loudest note in the whole file");
    expect(thresholdHelp).toContain("left end");
    expect(thresholdHelp).toContain("off");
    expect(thresholdHelp).toContain("right end");
    expect(thresholdHelp).toContain("10% of the loudest note");
  });

  it("explains Smoothing as the weight of the earlier frames in the window", () => {
    expect(smoothingHelp).toContain("0 is no smoothing");
    expect(smoothingHelp).toContain("smoothing window");
    expect(smoothingHelp).toContain("counts this fraction as much as the current frame");
  });

  it("explains the smoothing window: earlier frames mixed in, a stopped note gone, the range, and no effect at 0", () => {
    expect(smoothingWindowHelp).toContain("1 to 20");
    expect(smoothingWindowHelp).toContain("earlier frames are mixed into each frame");
    expect(smoothingWindowHelp).toContain("gone that many frames later");
    expect(smoothingWindowHelp).toContain("no effect while Smoothing is 0");
  });

  it("explains the gaussian smoothing: 0 to 5, off at 0, a 3:2 radius, which image types", () => {
    expect(gaussianHelp).toContain("0 to 5");
    expect(gaussianHelp).toContain("0 is off");
    expect(gaussianHelp).toContain("3:2");
    expect(gaussianHelp).toContain("6 pixels across and 4 down"); // the example of a setting of 4
    expect(gaussianHelp).toContain("Only used by Contour");
    expect(gaussianHelp).not.toContain("Tiles");
  });

  it("does not describe the five kinds of picture that were removed", () => {
    expect(imageTypeHelp).not.toMatch(/(^|\. )(Tiles|Blended tiles|Circles|Circles paint|Concentric): /);
    expect(imageTypeHelp).not.toContain("like Concentric");
  });

  it("explains the image types that are left, starting with the contour", () => {
    expect(imageTypeHelp.startsWith("Contour:")).toBe(true);
    expect(imageTypeHelp).toContain("contour map");
    for (const kept of ["Decay:", "Decay Exp:", "Polar Chords:", "Energy graphs:", "Chromatic Decay:", "Rhythm Circles:", "Chromatic Wireframe:"]) expect(imageTypeHelp).toContain(kept);
  });


  it("explains the colormap: what the four scales look like and that the same strength always gets the same color", () => {
    expect(colormapHelp).toContain("same strength always gets the same color");
    expect(colormapHelp).toContain("Summer: green to yellow");
    expect(colormapHelp).toContain("Autumn: red to yellow");
    expect(colormapHelp).toContain("Hot: dark red");
    expect(colormapHelp).toContain("Cool: cyan to magenta");
  });
});

describe("resolution explanation", () => {
  it("explains the interpolation, the original grid, the highest value and the finer contour", () => {
    expect(resolutionHelp).toContain("interpolat");
    expect(resolutionHelp).toContain("12 \u00d7 7");
    expect(resolutionHelp).toContain("5\u00d7");
    expect(resolutionHelp).toContain("60 \u00d7 35");
    expect(resolutionHelp).toContain("finer steps");
    expect(resolutionHelp).toContain("Oversampling");
    expect(resolutionHelp).not.toMatch(/\bResolution\b/);
    expect(resolutionHelp).toContain("Only used by Contour");
  });
});

describe("number of notes explanation", () => {
  it("explains the choice by energy over the whole file, the bigger features, the range and that it is not always steadier", () => {
    expect(noteCountHelp).toContain("most energy");
    expect(noteCountHelp).toContain("whole file");
    expect(noteCountHelp).toContain("12 to 84");
    expect(noteCountHelp).toContain("bigger");
    expect(noteCountHelp).toContain("not steadier in every case");
  });
});

describe("interpolation explanation", () => {
  it("explains that only every n-th frame is drawn, that the frames between are blends of their neighbors, and that it is faster", () => {
    expect(interpolateHelp).toContain("every n-th frame");
    expect(interpolateHelp).toContain("blending");
    expect(interpolateHelp).toContain("neighbors");
    expect(interpolateHelp).toContain("contour");
    expect(interpolateHelp).toContain("1 to 5");
  });

  it("no longer offers a choice of function", () => {
    expect(interpolateHelp).not.toContain("Soft light");
    expect(interpolateHelp).not.toContain("Subtract");
  });
});


import { beatColoringHelp, peakDistanceHelp, peakProminenceHelp } from "./help";

describe("the Local peaks explanations (feature 024)", () => {
  it("explain that the box is off by default and turns on the beat wave of the contour only", () => {
    expect(beatColoringHelp).toContain("Off by default");
    expect(beatColoringHelp).toContain("Only used by Contour");
    expect(beatColoringHelp).toContain("beat wave");
    expect(beatColoringHelp).not.toContain("Tiles");
  });

  it("give the ranges and defaults of the two settings", () => {
    expect(peakDistanceHelp).toContain("100 to 2000");
    expect(peakDistanceHelp).toContain("default 100");
    expect(peakProminenceHelp).toContain("0 to 100");
    expect(peakProminenceHelp).toContain("default 50");
    for (const text of [beatColoringHelp, peakDistanceHelp, peakProminenceHelp]) expect(text.length).toBeGreaterThan(60);
  });
});


import { noteLayoutHelp } from "./help";

describe("the Note layout help (feature 026)", () => {
  it("explains the two layouts, where middle C is, the two directions and which pictures have it", () => {
    expect(noteLayoutHelp).toContain("Rows");
    expect(noteLayoutHelp).toContain("Spiral");
    expect(noteLayoutHelp).toContain("default"); // Rows is the default
    expect(noteLayoutHelp).toContain("middle C");
    expect(noteLayoutHelp).toContain("3rd row");
    expect(noteLayoutHelp).toContain("6th column");
    expect(noteLayoutHelp).toContain("clockwise");
    expect(noteLayoutHelp).toContain("counterclockwise");
    expect(noteLayoutHelp).toContain("Only used by Decay, Decay Exp and Polar Chords");
    expect(noteLayoutHelp).not.toContain("Tiles");
    expect(noteLayoutHelp).not.toContain("Concentric");
  });
});

describe("the Decay help (feature 027)", () => {
  it("describes the Decay picture in the Image type help", () => {
    expect(imageTypeHelp).toContain("Decay:");
    expect(imageTypeHelp).toContain("84 circles");
    expect(imageTypeHelp).toContain("0 to 64");
    expect(imageTypeHelp).toContain("5 loudest notes");
    expect(imageTypeHelp).toContain("decay rate");
    expect(imageTypeHelp).toContain("24");
    expect(imageTypeHelp).toContain("32");
    expect(imageTypeHelp).toContain("12 rings");
    expect(imageTypeHelp).toContain("12 flat rings");
    expect(imageTypeHelp).toContain("Contour:");
  });

  it("explains the decay rate: the range, the default, what happens every so many frames and that it counts frames", () => {
    expect(decayRateHelp).toContain("0.25 to 4 frames");
    expect(decayRateHelp).toContain("steps of 0.25");
    expect(decayRateHelp).toContain("default 1");
    expect(decayRateHelp).toContain("0.25 takes four");
    expect(decayRateHelp).toContain("saturation level");
    expect(decayRateHelp).toContain("this many frames' worth");
    expect(decayRateHelp).toContain("frames");
    expect(decayRateHelp.length).toBeGreaterThan(60);
  });
});

describe("the beat wave help (feature 028)", () => {
  it("explains the wave count: the range, the default, that it needs Beat coloring, the rings and the beat", () => {
    expect(waveCountHelp).toContain("2 to 10");
    expect(waveCountHelp).toContain("default 4");
    expect(waveCountHelp).toContain("Contour");
    expect(waveCountHelp).toContain("Beat coloring");
    expect(waveCountHelp).toContain("rings");
    expect(waveCountHelp).toContain("beat");
    expect(waveCountHelp.length).toBeGreaterThan(60);
  });

  it("says in the Beat coloring help and the Image type help that Contour has the beat wave", () => {
    expect(beatColoringHelp).toContain("Contour");
    expect(beatColoringHelp).toContain("beat wave");
    expect(imageTypeHelp).toContain("rings pulse over it with the beat");
  });
});

describe("the decay amount help (feature 027, revised)", () => {
  it("has a text for each saturation level with the range, its default and what it does, and without listing points", () => {
    expect(Object.keys(decayAmountHelp)).toEqual(["low", "medium", "high", "saturated"]);
    const defaults: Record<string, string> = { low: "0.5", medium: "1", high: "2", saturated: "3" };
    for (const [level, text] of Object.entries(decayAmountHelp)) {
      expect(text, level).toContain("0.5 to 3");
      expect(text, level).toContain(`default ${defaults[level]}`);
      expect(text, level).toContain(`${level} saturation level`);
      expect(text, level).toContain("8 neighbours");
      expect(text.length, level).toBeGreaterThan(100);
    }
  });
});

describe("the Decay Exp help (feature 030)", () => {
  it("describes the Decay Exp picture in the Image type help, next to Decay", () => {
    expect(imageTypeHelp).toContain("Decay Exp:");
    expect(imageTypeHelp).toContain("Decay:");
    expect(imageTypeHelp).toContain("decay rate");
    expect(imageTypeHelp).toContain("four decay settings of Decay do not apply");
    expect(imageTypeHelp).toContain("more than 10 circles have more than 32 points");
  });

  it("explains its decay rate: the range, the default, the formula's effect and that it counts frames, without the saturation levels", () => {
    expect(decayExpRateHelp).toContain("0.25 to 4 frames");
    expect(decayExpRateHelp).toContain("steps of 0.25");
    expect(decayExpRateHelp).toContain("default 1");
    expect(decayExpRateHelp).toContain("sin²(π/2 × p/64)");
    expect(decayExpRateHelp).toContain("0.25 takes four");
    expect(decayExpRateHelp).toContain("counts frames");
    expect(decayExpRateHelp).not.toMatch(/saturation|decay settings below/);
  });
});

describe("the Polar Chords help (feature 032)", () => {
  it("describes the Polar Chords picture in the Image type help: two rings, both directions, the 7 chords, the length from the beat", () => {
    expect(imageTypeHelp).toContain("Polar Chords:");
    expect(imageTypeHelp).toContain("counterclockwise");
    expect(imageTypeHelp).toContain("clockwise");
    expect(imageTypeHelp).toContain("84");
    expect(imageTypeHelp).toContain("7 chord types");
    expect(imageTypeHelp).toContain("12 letters");
    expect(imageTypeHelp).toContain("root letter");
    expect(imageTypeHelp).toContain("beat");
    expect(imageTypeHelp).toContain("Note layout");
    expect(imageTypeHelp).toContain("one arc a frame");
  });

  it("explains Notes shown: the range, the default and that the loudest notes get a bar", () => {
    expect(polarNotesHelp).toContain("5 to 8");
    expect(polarNotesHelp).toContain("default 5");
    expect(polarNotesHelp).toContain("loudest");
  });
});


describe("the image type help for the rings of Chromatic Decay (feature 036)", () => {
  it("says what the rings in the middle show, how big they are and how they are colored", () => {
    const text = imageTypeHelp.slice(imageTypeHelp.indexOf("Chromatic Decay:"));
    expect(text).toContain("twelve concentric rings");
    expect(text).toContain("140 pixels");
    expect(text).toContain("the center is how far the current frame is from the top of the latest beat");
    expect(text).toContain("average of the two moments before the ring inside it");
    expect(text).toContain("whole colormap, from its first color at the top of a beat to its last color at the lowest point of the beat in the file");
    expect(text).toContain("no setting of its own");
  });

  it("has nothing the page would have to escape", () => {
    const text = imageTypeHelp.slice(imageTypeHelp.indexOf("Chromatic Decay:"));
    expect(text).not.toMatch(/['"<>&]/);
  });
});

describe("the Threshold help for Chromatic Decay (feature 037)", () => {
  it("keeps the sentence about the contour and says what the threshold does for Chromatic Decay", () => {
    expect(thresholdHelp).toContain("with Contour its value is 0");
    expect(thresholdHelp).toContain("Chromatic Decay");
    expect(thresholdHelp).toContain("treated as silent");
    expect(thresholdHelp).toContain("does not charge its letter");
  });

  it("is named in the Chromatic Decay part of the image type help", () => {
    const text = imageTypeHelp.slice(imageTypeHelp.indexOf("Chromatic Decay:"));
    expect(text).toContain("The Threshold");
    expect(text).toContain("quieter than");
  });

  it("has nothing the page would have to escape in the Threshold help", () => {
    expect(thresholdHelp).not.toMatch(/['"<>&]/);
  });
});

describe("the image type help for Rhythm Circles (feature 038)", () => {
  const text = () => imageTypeHelp.slice(imageTypeHelp.indexOf("Rhythm Circles:"));

  it("comes after Chromatic Decay, keeps the paragraphs before it, and is followed only by Chromatic Wireframe", () => {
    expect(imageTypeHelp.indexOf("Rhythm Circles:")).toBeGreaterThan(imageTypeHelp.indexOf("Chromatic Decay:"));
    expect(imageTypeHelp).toContain("Energy graphs:");
  });

  it("names the eight circles, the four layers and what turns each of them", () => {
    expect(text()).toContain("eight concentric circles");
    expect(text()).toContain("four layers");
    expect(text()).toContain("beats per minute");
    expect(text()).toContain("rate of change of the tempo");
    expect(text()).toContain("rate of change of that tempo");
  });

  it("says that an aggregated tempo is the average or the fastest, whichever is closer to the current tempo", () => {
    expect(text()).toContain("either their average or the fastest of them");
    expect(text()).toContain("whichever is closer to the current tempo");
    expect(text()).not.toContain("not an average"); // the version in which it was always the fastest
  });

  it("puts the longest aggregation on the outside and the plain tempo in the middle", () => {
    const t = text();
    const order = ["The outer circle turns at the tempo of the last 8 peaks", "the same for the last 4 peaks", "the fifth and sixth for the last 2 peaks", "The seventh turns at the current tempo", "the eighth, the innermost"];
    const places = order.map((phrase) => t.indexOf(phrase));
    expect(places.every((p) => p >= 0)).toBe(true);
    expect([...places].sort((a, b) => a - b)).toEqual(places); // in the order of the rings, from the outside in
  });

  it("does not describe the circles of the earlier versions of the feature", () => {
    expect(imageTypeHelp.slice(imageTypeHelp.indexOf("Rhythm Circles:"))).not.toContain("second rate of change");
    expect(text()).not.toContain("averaged"); // the first version of the circles averaged the tempos
    expect(text()).not.toContain("six concentric");
  });

  it("says which way they turn and what the notch is", () => {
    expect(text()).toContain("clockwise");
    expect(text()).toContain("either direction");
    expect(text()).toContain("notch");
    expect(text()).toContain("an eighth");
  });

  it("names the Local peaks settings as the only ones", () => {
    expect(text()).toContain("Minimum distance");
    expect(text()).toContain("Prominence");
    expect(text()).toContain("the others are ignored");
  });

  it("has nothing the page would have to escape", () => {
    expect(text()).not.toMatch(/['"<>&]/);
  });
});

describe("the image type help for Chromatic Wireframe (feature 039)", () => {
  const text = () => imageTypeHelp.slice(imageTypeHelp.indexOf("Chromatic Wireframe:"));

  it("is the last paragraph and keeps the paragraphs before it", () => {
    expect(imageTypeHelp.indexOf("Chromatic Wireframe:")).toBeGreaterThan(imageTypeHelp.indexOf("Rhythm Circles:"));
    expect(imageTypeHelp).toContain("Chromatic Decay:");
  });

  it("says what the picture shows: the 12 letters across the width, a line for each frame with the newest in front, the sine and the radius of the circle", () => {
    expect(text()).toContain("12 letters");
    expect(text()).toContain("one line for each frame");
    expect(text()).toContain("newest in front");
    expect(text()).toContain("radius of its circle");
    expect(text()).toContain("sine");
    expect(text()).toContain("the sum of 12 sine waves");
    expect(text()).toContain("how many waves it makes, from none at 0 points to 4 at 64 points");
    expect(text()).toContain("a letter that starts a quarter of the way along the axis begins a quarter turn later");
    expect(text()).toContain("is a flat line");
    expect(text()).toContain("The waves are sines squared, so they only add up and never cancel");
    expect(text()).toContain("stretched to use the height of the picture");
  });

  it("says how a line is colored: by its place in the beat, the last color at the top of a peak", () => {
    expect(text()).toContain("place in the beat");
    expect(text()).toContain("last color of the colormap at the top of a beat");
    expect(text()).toContain("one color");
  });

  it("says that nearer lines hide the ones behind and that the settings of Chromatic Decay apply", () => {
    expect(text()).toContain("hide");
    expect(text()).toContain("settings of Chromatic Decay");
    expect(text()).toContain("The background is black");
  });

  it("has nothing the page would have to escape", () => {
    expect(text()).not.toMatch(/['"<>&]/);
  });
});

describe("the Threshold help and the decay rate help name Chromatic Wireframe (feature 039)", () => {
  it("says that the threshold treats a quiet note as silent for Chromatic Wireframe too", () => {
    expect(thresholdHelp).toContain("For Chromatic Decay and Chromatic Wireframe a note below the threshold is treated as silent");
  });

  it("says that the decay rate is also the one of the points that Chromatic Wireframe draws", () => {
    expect(chromaticRateHelp).toContain("Chromatic Wireframe");
    expect(chromaticRateHelp).not.toMatch(/['"<>&]/);
  });
});
