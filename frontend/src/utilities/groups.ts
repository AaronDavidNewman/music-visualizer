import { beatColoringApplies, gridSettingsApply, noteLayoutApplies } from "./validation";

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
  { id: "contour", title: "Contour", controls: ["threshold", "notes"] },
  { id: "blended", title: "Blended Tiles", controls: ["threshold", "notes", "blend-width"] },
  {
    id: "circles",
    title: "Circles",
    controls: ["circle-unit", "circle-radius", "circle-resize", "circle-memory", "circle-notes"],
  },
  // the same circles with no memory (feature 022): so no Memory control
  { id: "circles_paint", title: "Circles paint", controls: ["circle-unit", "circle-radius", "circle-resize", "circle-notes"] },
  // which note is in which cell (feature 026), for the three pictures with one shape for each note
  { id: "note-layout", title: "Note layout", controls: ["note-layout"] },
  // the beat coloring of Tiles and Blended tiles (feature 024): its own group, after the group of the type
  { id: "local-peaks", title: "Local peaks", controls: ["beat-coloring", "peak-distance", "peak-prominence"] },
  // the same two settings for Concentric (feature 025): the beat always colors it, so no checkbox, and no group of its own
  { id: "concentric-peaks", title: "Local peaks", controls: ["peak-distance", "peak-prominence"] },
  { id: "data-smoothing", title: "Data smoothing", controls: ["smoothing-window", "smoothing"] },
  { id: "image-smoothing", title: "Image smoothing", controls: ["resolution", "interpolate", "gaussian"] },
];

/** The ids of the groups that belong to one image type: exactly one of them follows the Image type group. */
const TYPE_GROUPS = ["tiles", "contour", "blended", "circles", "circles_paint"];

const byId = new Map(GROUPS.map((g) => [g.id, g]));

export function groupTitle(id: string): string {
  return byId.get(id)?.title ?? id;
}

export function controlsIn(id: string): readonly string[] {
  return byId.get(id)?.controls ?? [];
}

/**
 * The ids of the groups shown for an image type, top to bottom: the top group, Colormap, Image type, the group of the type
 * (none for Concentric, which has no controls of its own, nor for a type that is not one of the six), Note layout for Tiles, Blended
 * tiles and Concentric, Local peaks for Tiles and
 * Blended tiles (with the checkbox) and for Concentric (without it), Data smoothing, and Image smoothing when the type draws a grid.
 */
export function groupsFor(imageType: string): string[] {
  const ids = ["analysis", "colormap", "image-type"];
  if (TYPE_GROUPS.includes(imageType)) ids.push(imageType);
  if (noteLayoutApplies(imageType)) ids.push("note-layout");
  if (beatColoringApplies(imageType)) ids.push("local-peaks");
  if (imageType === "concentric") ids.push("concentric-peaks");
  ids.push("data-smoothing");
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
