import { beatColoringApplies, gridSettingsApply, isChromaticType, isEnergyType, isPolarType, isRingsType, noteLayoutApplies } from "./validation";

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
  { id: "analysis", title: "Analysis", controls: ["window-size", "frame-rate", "window-spacing"] },
  { id: "colormap", title: "Colormap", controls: ["colormap"] },
  { id: "image-type", title: "Image type", controls: ["image-type"] },
  { id: "tiles", title: "Tiles", controls: ["threshold", "notes"] },
  // the wave count of the beat wave (feature 028) comes after Threshold and Notes
  { id: "contour", title: "Contour", controls: ["threshold", "notes", "wave-count"] },
  { id: "blended", title: "Blended Tiles", controls: ["threshold", "notes", "blend-width"] },
  {
    id: "circles",
    title: "Circles",
    controls: ["circle-unit", "circle-radius", "circle-resize", "circle-memory", "circle-notes"],
  },
  // the same circles with no memory (feature 022): so no Memory control
  { id: "circles_paint", title: "Circles paint", controls: ["circle-unit", "circle-radius", "circle-resize", "circle-notes"] },
  // the decay rate of the Decay picture (feature 027): the frames between two decay steps, and the four decay amounts, one for each saturation level
  { id: "decay", title: "Decay", controls: ["decay-rate", "decay-low", "decay-medium", "decay-high", "decay-saturated"] },
  // Decay Exp (feature 030): the same decay rate, and no decay amounts, because its loss is given by a formula
  { id: "decay-exp", title: "Decay", controls: ["decay-rate"] },
  // Notes shown by Polar Chords (feature 032): how many of the loudest notes get a bar
  { id: "polar-chords", title: "Polar chords", controls: ["polar-notes"] },
  // the decay rate of Chromatic Decay (feature 035): a whole number of frames from 1 to 10, its own control (the decay rate of Decay and Decay Exp is 0.25 to 4), and its
  // Threshold (feature 037), the same control and value as the one of Tiles, Contour and Blended tiles
  { id: "chromatic-decay", title: "Chromatic Decay", controls: ["threshold", "chromatic-decay-rate"] },
  // which note is in which cell (feature 026), for the pictures with one shape for each note
  { id: "note-layout", title: "Note layout", controls: ["note-layout"] },
  // the beat coloring of Tiles and Blended tiles (feature 024) and the beat wave of Contour (feature 028): its own group, after the group of the type
  { id: "local-peaks", title: "Local peaks", controls: ["beat-coloring", "peak-distance", "peak-prominence"] },
  // the same two settings for Concentric (feature 025) and Decay (feature 027): the beat always colors or charges them, so no checkbox
  { id: "concentric-peaks", title: "Local peaks", controls: ["peak-distance", "peak-prominence"] },
  { id: "data-smoothing", title: "Data smoothing", controls: ["smoothing-window", "smoothing"] },
  { id: "image-smoothing", title: "Image smoothing", controls: ["resolution", "interpolate", "gaussian"] },
];

/** The ids of the groups that belong to one image type: exactly one of them follows the Image type group. */
const TYPE_GROUPS = ["tiles", "contour", "blended", "circles", "circles_paint", "decay", "decay-exp", "polar-chords", "chromatic-decay"];

const byId = new Map(GROUPS.map((g) => [g.id, g]));

export function groupTitle(id: string): string {
  return byId.get(id)?.title ?? id;
}

export function controlsIn(id: string): readonly string[] {
  return byId.get(id)?.controls ?? [];
}

/**
 * The ids of the groups shown for an image type, top to bottom: the top group, Colormap, Image type, the group of the type
 * (none for Concentric, which has no controls of its own, nor for a type that is not one of the eight), Note layout for Tiles, Blended
 * tiles, Concentric, Decay and Decay Exp, Local peaks for Tiles, Blended tiles and Contour (with the checkbox) and for Concentric, Decay and Decay Exp
 * (without it), Data smoothing (not for Energy graphs, which does not smooth the data), and Image smoothing when the type draws a grid. Energy graphs has
 * no group of its own: only the top group, Colormap and Image type.
 */
export function groupsFor(imageType: string): string[] {
  const ids = ["analysis", "colormap", "image-type"];
  if (TYPE_GROUPS.includes(imageType)) ids.push(imageType);
  if (noteLayoutApplies(imageType)) ids.push("note-layout");
  if (beatColoringApplies(imageType)) ids.push("local-peaks");
  if (isRingsType(imageType) || isPolarType(imageType) || isChromaticType(imageType)) ids.push("concentric-peaks");
  if (!isEnergyType(imageType)) ids.push("data-smoothing");
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
