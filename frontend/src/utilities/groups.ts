import { beatColoringApplies, gridSettingsApply, isChromaticType, isEnergyType, isPolarType, isPolychordType, isRhythmType, isRingsType, isSpirographType, noteLayoutApplies, usesHeldNotes, usesObjExport } from "./validation";

/**
 * The groups of the settings form (feature 020): which groups there are, what is in each, which are shown for an image type, and
 * the open or closed state of a group. No Vue here, so that all of it can be tested without a browser.
 */

export interface GroupDefinition {
  id: string;
  title: string;
  /** The ids of the controls, in the order they are laid out (left to right, then the next row). */
  controls: readonly string[];
}

export const GROUPS: readonly GroupDefinition[] = [
  { id: "analysis", title: "Analysis", controls: ["window-size", "frame-rate"] },
  { id: "colormap", title: "Colormap", controls: ["colormap"] },
  { id: "image-type", title: "Image type", controls: ["image-type"] },
  // the wave count of the beat wave (feature 028) comes after Threshold and Notes
  { id: "contour", title: "Contour", controls: ["threshold", "notes", "wave-count"] },
  // the decay rate of the Decay picture (feature 027): the frames between two decay steps, and the four decay amounts, one for each saturation level
  { id: "decay", title: "Decay", controls: ["decay-rate", "decay-low", "decay-medium", "decay-high", "decay-saturated"] },
  // Decay Exp (feature 030): the same decay rate, and no decay amounts, because its loss is given by a formula
  { id: "decay-exp", title: "Decay", controls: ["decay-rate"] },
  // Notes shown by Polar Chords (feature 032): how many of the loudest notes get a bar
  { id: "polar-chords", title: "Polar chords", controls: ["polar-notes"] },
  // the decay rate of Chromatic Decay (feature 035): a whole number of frames from 1 to 10, its own control (the decay rate of Decay and Decay Exp is 0.25 to 4), and its
  // Threshold (feature 037), the same control and value as the one of Contour
  { id: "chromatic-decay", title: "Chromatic Decay", controls: ["threshold", "chromatic-decay-rate"] },
  // Chromatic Wireframe (feature 039) draws the points of Chromatic Decay, so it has the same two controls (and the same values) in a group of its own
  { id: "chromatic-wireframe", title: "Chromatic Wireframe", controls: ["threshold", "chromatic-decay-rate"] },
  // Polychord (feature 042): the links in a figure, the fewest and the most copies of it, and how fast the picture turns
  { id: "polychord", title: "Polychord", controls: ["polychord-notes", "polychord-min-copies", "polychord-max-copies", "polychord-rotation"] },
  // Spirograph (feature 046): the notes tracked in each frame, the history of frames in a picture and how fast it fades; the beat sets the turns and the big circle, so the Local peaks group (Minimum distance) follows
  { id: "spirograph", title: "Spirograph", controls: ["spirograph-notes", "spirograph-history", "spirograph-fade"] },
  // Rhythm Circles (feature 047): the Vote limit of the tempos voted from the starts of the loudest notes; Held notes (Extra notes) and Local peaks (Minimum distance) follow
  { id: "rhythm-circles", title: "Rhythm Circles", controls: ["vote-limit"] },
  // the Extra notes (feature 044) of the eight pictures that take the n loudest notes: one setting, in a group of its own after the group of the type
  { id: "held-notes", title: "Held notes", controls: ["extra-notes"] },
  // the export of 3D files (feature 045) of Contour and Chromatic Wireframe: one checkbox, in a group of its own after the group of the type (and after Held notes)
  { id: "obj-export", title: "3D export", controls: ["export-obj"] },
  // which note is in which cell (feature 026), for the pictures with one shape for each note
  { id: "note-layout", title: "Note layout", controls: ["note-layout"] },
  // the beat coloring of Contour, its beat wave (feature 028): its own group, after the group of the type
  { id: "local-peaks", title: "Local peaks", controls: ["beat-coloring", "peak-distance"] },
  // the same two settings for Decay (feature 027) and the pictures after it: the beat always charges them, so no checkbox (the id is from Concentric, feature 025, the first picture that had it)
  { id: "concentric-peaks", title: "Local peaks", controls: ["peak-distance"] },
  { id: "image-smoothing", title: "Image smoothing", controls: ["resolution", "interpolate", "gaussian"] },
];

/** The ids of the groups that belong to one image type: exactly one of them follows the Image type group. */
const TYPE_GROUPS = ["contour", "decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe", "polychord", "spirograph", "rhythm-circles"];

const byId = new Map(GROUPS.map((g) => [g.id, g]));

export function groupTitle(id: string): string {
  return byId.get(id)?.title ?? id;
}

export function controlsIn(id: string): readonly string[] {
  return byId.get(id)?.controls ?? [];
}

/**
 * The ids of the groups shown for an image type, top to bottom: the top group, Colormap, Image type, the group of the type
 * (none for Energy graphs, which has no controls of its own, nor for a type that is not one of the ten; Rhythm Circles has the Vote limit), Held notes for the eight pictures that take the n loudest notes
 * (Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe, Polychord, Spirograph and Rhythm Circles), Note layout for Decay, Decay Exp and Polar Chords,
 * Local peaks for Contour (with the checkbox) and for Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe, Polychord and Spirograph (without it), and Image smoothing when the type draws a grid (Contour). Energy graphs has
 * no group of its own: only the top group, Colormap and Image type. Rhythm Circles has the Rhythm Circles group (Vote limit), Held notes and Local peaks (without the checkbox).
 */
export function groupsFor(imageType: string): string[] {
  const ids = ["analysis", "colormap", "image-type"];
  if (TYPE_GROUPS.includes(imageType)) ids.push(imageType);
  if (usesHeldNotes(imageType)) ids.push("held-notes");
  if (usesObjExport(imageType)) ids.push("obj-export");
  if (noteLayoutApplies(imageType)) ids.push("note-layout");
  if (beatColoringApplies(imageType)) ids.push("local-peaks");
  if (isRingsType(imageType) || isPolarType(imageType) || isChromaticType(imageType) || isRhythmType(imageType) || isPolychordType(imageType) || isSpirographType(imageType)) ids.push("concentric-peaks");
  if (gridSettingsApply(imageType)) ids.push("image-smoothing");
  return ids;
}

/** The group a control is in for an image type, or undefined when that control is not shown for the type. */
export function groupOf(controlId: string, imageType: string): string | undefined {
  return groupsFor(imageType).find((id) => controlsIn(id).includes(controlId));
}

/** The sizes of the rows a group of ``count`` controls is laid out in: rows of two, and a single control last when odd. */
export function rowsOf(count: number): number[] {
  if (!Number.isInteger(count) || count < 0) throw new Error("The number of controls must be a whole number of at least 0.");
  const rows = new Array<number>(Math.floor(count / 2)).fill(2);
  if (count % 2 === 1) rows.push(1);
  return rows;
}

/** Which groups are open. A group that was never mentioned is open. */
export type OpenState = Readonly<Record<string, boolean>>;

export function isOpen(state: OpenState, id: string): boolean {
  return state[id] !== false;
}

export function setOpen(state: OpenState, id: string, open: boolean): OpenState {
  return { ...state, [id]: open };
}

export function toggle(state: OpenState, id: string): OpenState {
  return setOpen(state, id, !isOpen(state, id));
}
