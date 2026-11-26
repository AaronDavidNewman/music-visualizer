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
  polychordMaxCopiesHelp,
  polychordMinCopiesHelp,
  polychordNotesHelp,
  polychordRotationHelp,
  spirographFadeHelp,
  spirographHistoryHelp,
  spirographNotesHelp,
  waveCountHelp,
  noteCountHelp,
  resolutionHelp,
  thresholdHelp,
  windowSizeHelp,
} from "./help";
import { FRAME_RATE_RANGE } from "./validation";

describe("setting explanations", () => {
  it("keeps the wording that used to be printed under the fields", () => {
    expect(windowSizeHelp).toBe("Larger windows separate low notes better but blur changes over time.");
  });

  it("states the frame rate range from the validation constants and says that the notes are measured every 60 ms", () => {
    expect(frameRateHelp).toContain(`${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`);
    expect(frameRateHelp).toContain("every 60 milliseconds");
    expect(frameRateHelp).toContain("average of the measurements");
    expect(frameRateHelp).toContain("repeats the latest measurement");
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


import { beatColoringHelp, peakDistanceHelp } from "./help";
import * as helpModule from "./help";

describe("the Local peaks explanations (feature 024)", () => {
  it("explain that the box is off by default and turns on the beat wave of the contour only", () => {
    expect(beatColoringHelp).toContain("Off by default");
    expect(beatColoringHelp).toContain("Only used by Contour");
    expect(beatColoringHelp).toContain("beat wave");
    expect(beatColoringHelp).not.toContain("Tiles");
  });

  it("give the range and the default of the minimum distance, and say that the prominence is fixed at 20 percent (feature 040)", () => {
    expect(peakDistanceHelp).toContain("100 to 2000");
    expect(peakDistanceHelp).toContain("default 350");
    expect(peakDistanceHelp).toContain("20 percent");
    expect(peakDistanceHelp).toContain("fixed");
    expect("peakProminenceHelp" in helpModule).toBe(false);
    for (const text of [beatColoringHelp, peakDistanceHelp]) expect(text.length).toBeGreaterThan(60);
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
    expect(imageTypeHelp).toContain("jumps to the arc of the new note");
    expect(imageTypeHelp).not.toContain("one arc a frame");
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

describe("the image type help for Rhythm Circles (features 038 and 047)", () => {
  const text = () => {
    const from = imageTypeHelp.indexOf("Rhythm Circles:");
    return imageTypeHelp.slice(from, imageTypeHelp.indexOf("Chromatic Wireframe:", from));
  };

  it("comes after Chromatic Decay, keeps the paragraphs before it, and is followed only by Chromatic Wireframe", () => {
    expect(imageTypeHelp.indexOf("Rhythm Circles:")).toBeGreaterThan(imageTypeHelp.indexOf("Chromatic Decay:"));
    expect(imageTypeHelp).toContain("Energy graphs:");
    expect(imageTypeHelp.indexOf("Chromatic Wireframe:")).toBeGreaterThan(imageTypeHelp.indexOf("Rhythm Circles:"));
  });

  it("names the six circles, the three layers and what turns each of them", () => {
    expect(text()).toContain("six concentric circles");
    expect(text()).toContain("three layers");
    expect(text()).toContain("beats per minute");
    expect(text()).toContain("its rate of change");
    expect(text()).toContain("the difference between the last two peak tempos divided by the time between them");
  });

  it("says how the notes vote: the starts of the loudest notes, the note values, 18 tempos, 2 votes won and 1 lost, the limit", () => {
    const t = text();
    for (const piece of [
      "every time a new one of the loudest notes starts",
      "a half, a quarter, an eighth or a sixteenth note, any of those dotted, or a triplet note",
      "18 tempos (76 to 144 beats per minute in steps of 4",
      "the metronome markings",
      "gets 2 votes (1 if it fits only as a dotted note or a triplet), and every tempo loses 1 vote",
      "never below 0, and never above the Vote limit",
      "A tempo with no votes is shown as 120",
      "Extra notes setting keeps a sustained note as one note",
    ]) expect(t, piece).toContain(piece);
  });

  it("puts the average of the best-voted tempos on the outside, then the best-voted tempo itself, and the local peak on the inside", () => {
    const t = text();
    const order = ["as the average of the best-voted tempos of the last 5 note starts and, inside it, as the best-voted tempo itself", "and on the inside the local peak", "The local peak, found from the peaks"];
    const places = order.map((phrase) => t.indexOf(phrase));
    expect(places.every((p) => p >= 0)).toBe(true);
    expect([...places].sort((a, b) => a - b)).toEqual(places); // in the order of the layers, from the outside in
  });

  it("does not describe the tempo finder or the circles of the earlier versions of the feature", () => {
    for (const gone of ["second rate of change", "averaged", "eight concentric", "four concentric", "four layers", "two layers", "standard deviation", "from 60 to 156", "starts at 120"]) {
      expect(text(), gone).not.toContain(gone);
    }
  });

  it("says which way they turn and what the notch is", () => {
    expect(text()).toContain("clockwise");
    expect(text()).toContain("either direction");
    expect(text()).toContain("notch");
    expect(text()).toContain("an eighth");
  });

  it("names the settings that apply: Extra notes, Vote limit and Minimum distance, and says the others are ignored", () => {
    expect(text()).toContain("Extra notes, Vote limit and Minimum distance (for the peaks) apply to it");
    expect(text()).not.toContain("Prominence");
    expect(text()).toContain("the other settings are ignored");
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

describe("the Polychord help (feature 042)", () => {
  it("explains the number of notes: 5 to 8, default 6, the loudest notes, a link each, 22.5 degrees per fifth", () => {
    for (const piece of ["5 to 8", "default 6", "Only used by Polychord", "loudest", "22.5 degrees"]) expect(polychordNotesHelp).toContain(piece);
  });

  it("explains the copies: 1 to 12, the defaults 3 and 12, the beat, and that the maximum cannot be less than the minimum", () => {
    for (const piece of ["1 to 12", "default 3", "lowest point of the beat", "Copies (maximum)"]) expect(polychordMinCopiesHelp).toContain(piece);
    for (const piece of ["1 to 12", "default 12", "top of a beat", "Copies (minimum)", "full turn"]) expect(polychordMaxCopiesHelp).toContain(piece);
  });

  it("explains the rotation: -360 to 360 degrees a second, default 15, either way, still at 0", () => {
    for (const piece of ["-360 to 360", "default 15", "clockwise", "counterclockwise", "0 holds it still"]) expect(polychordRotationHelp).toContain(piece);
  });

  it("is in the image type help, after Chromatic Wireframe, with the tempo coloring and the black background", () => {
    expect(imageTypeHelp).toContain("Polychord:");
    expect(imageTypeHelp.indexOf("Polychord:")).toBeGreaterThan(imageTypeHelp.indexOf("Chromatic Wireframe:"));
    const text = imageTypeHelp.slice(imageTypeHelp.indexOf("Polychord:"));
    for (const piece of ["fifth", "Copies (maximum)", "Rotation", "60", "156", "black"]) expect(text).toContain(piece);
  });

  it("names Polychord in the Local peaks help", () => {
    expect(peakDistanceHelp).toContain("Polychord");
    expect(peakDistanceHelp).toContain("Spirograph");
  });
});

import { extraNotesHelp as extraNotesHelpText, imageTypeHelp as imageTypeHelpText } from "./help";

describe("the help of the Extra notes setting (feature 044)", () => {
  it("explains held notes, k, the range, the free place and the default", () => {
    for (const piece of ["1 to the number of notes", "Default 2", "held", "n + k", "louder new note has to wait", "free"]) expect(extraNotesHelpText).toContain(piece);
    for (const picture of ["Polar Chords", "Polychord", "Chromatic Wireframe"]) expect(extraNotesHelpText).toContain(picture);
  });

  it("is said in the descriptions of the six pictures that take the n loudest notes", () => {
    expect(imageTypeHelpText.match(/Extra notes/g)?.length ?? 0).toBeGreaterThanOrEqual(6);
    expect(imageTypeHelpText).toContain("the 5 loudest notes are held notes");
    expect(imageTypeHelpText).toContain("the notes that get a bar are held notes");
    expect(imageTypeHelpText).toContain("the five loudest letters are held letters");
    expect(imageTypeHelpText).toContain("the notes of the figure are held notes");
  });
});

import { exportObjHelp as exportObjHelpText } from "./help";

describe("the help of the Export 3D files setting (feature 045)", () => {
  it("explains the files, the axes and ranges, the colors, the modifiers, the two pictures and that the pictures are still made", () => {
    for (const piece of ["Wavefront OBJ", "one ZIP", "Blender", "Subdivision Surface", "0 to 11", "0 to 12", "three numbers from 0 to 1", "84 points and 66 faces", "11 frames before it", "still made"]) {
      expect(exportObjHelpText).toContain(piece);
    }
    for (const picture of ["Contour", "Chromatic Wireframe"]) expect(exportObjHelpText).toContain(picture);
  });

  it("is said in the descriptions of Contour and Chromatic Wireframe", () => {
    expect(imageTypeHelpText.match(/Export 3D files/g)?.length ?? 0).toBeGreaterThanOrEqual(2);
    expect(imageTypeHelpText).toContain("84 points and 66 faces");
    expect(imageTypeHelpText).toContain("the 11 frames before it");
  });
});

describe("the Spirograph help (feature 046)", () => {
  it("explains the number of notes: 5 to 12, default 8, the loudest notes, a curve each, the 13 colors", () => {
    for (const piece of ["5 to 12", "default 8", "Only used by Spirograph", "loudest", "13 colors"]) expect(spirographNotesHelp).toContain(piece);
  });

  it("explains the history: 5 to 12 frames, default 8, the frame itself and the ones before, counted in frames", () => {
    for (const piece of ["5 to 12", "default 8", "Only used by Spirograph", "the frame itself", "counted in frames"]) expect(spirographHistoryHelp).toContain(piece);
  });

  it("explains the history fade: 0.4 to 0.85, default 0.7, multiplied once for every frame older, the newest keeps its size", () => {
    for (const piece of ["0.4 to 0.85", "default 0.7", "Only used by Spirograph", "once for every frame", "keeps its full size"]) expect(spirographFadeHelp).toContain(piece);
  });

  it("is in the image type help, after Polychord, with the rolling circle, the colors, the history and the black background", () => {
    expect(imageTypeHelp).toContain("Spirograph:");
    expect(imageTypeHelp.indexOf("Spirograph:")).toBeGreaterThan(imageTypeHelp.indexOf("Polychord:"));
    const text = imageTypeHelp.slice(imageTypeHelp.indexOf("Spirograph:"));
    for (const piece of ["rolling", "13 colors", "History length", "black", "6 times", "20 times", "Local peaks settings"]) expect(text).toContain(piece);
    expect(text).not.toContain("no beat");
  });

  it("names Spirograph in the Extra notes help, with the limit of 8", async () => {
    const { extraNotesHelp } = await import("./help");
    expect(extraNotesHelp).toContain("Spirograph");
    expect(extraNotesHelp).toContain("never more than 8");
  });
});
