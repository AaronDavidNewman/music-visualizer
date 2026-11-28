/** Window sizes the user can choose: the powers of 2 from 4096 to 32768. */
export const WINDOW_SIZES = [4096, 8192, 16384, 32768] as const;
export const DEFAULT_WINDOW_SIZE = WINDOW_SIZES[0];
export const FRAME_RATE_RANGE = { min: 1, max: 60 } as const;

const windowSizeMessage = `The window size must be one of ${WINDOW_SIZES.join(", ")}.`;
const frameRateMessage = `The frame rate must be a number from ${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`;

function parseNumber(value: string | number): number {
  const text = String(value).trim();
  return text === "" ? NaN : Number(text);
}

/** Returns an error message, or null when the window size is one of the allowed sizes. */
export function validateWindowSize(value: string | number): string | null {
  const n = parseNumber(value);
  return (WINDOW_SIZES as readonly number[]).includes(n) ? null : windowSizeMessage;
}

/** Returns an error message, or null when the frame rate is valid. */
export function validateFrameRate(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= FRAME_RATE_RANGE.min && n <= FRAME_RATE_RANGE.max;
  return ok ? null : frameRateMessage;
}

/** Returns an error message, or null when a usable file is chosen. */
export function validateFile(file: { name: string } | null): string | null {
  if (!file) return "Choose a .wav file.";
  return file.name.toLowerCase().endsWith(".wav") && file.name.length > 4
    ? null
    : "The file must be a .wav file.";
}

/** The threshold hides faint notes: a note below this percentage of the file's loudest note value is drawn black. 0 is off. The slider moves in steps of 1. */
export const THRESHOLD_RANGE = { min: 0, max: 10, step: 1 } as const;
export const DEFAULT_THRESHOLD = THRESHOLD_RANGE.min;

const thresholdMessage = `The threshold must be a number from ${THRESHOLD_RANGE.min} to ${THRESHOLD_RANGE.max}.`;

/** Returns an error message, or null when the threshold is a finite number from 0 to 10. */
export function validateThreshold(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= THRESHOLD_RANGE.min && n <= THRESHOLD_RANGE.max;
  return ok ? null : thresholdMessage;
}

/** The readout beside the slider: "Off" at 0, otherwise the percentage of the loudest note. */
export function formatThreshold(value: number): string {
  return value === 0 ? "Off" : `${Number(value.toFixed(2))}%`;
}

/** The result summary item: "Off" or the percentage such as "30%". */
export function formatThresholdSummary(value: number): string {
  return value === 0 ? "Off" : `${Number(value.toFixed(2))}%`;
}

/**
 * The kinds of picture: Contour (the notes drawn as a filled contour map, the default), Decay (a circle for each of the 84 notes, each a disc that keeps points and fades into its
 * neighbours), Decay Exp (Decay with the points gained and lost along an exponential curve), Polar Chords (the loudest notes clockwise and the chord of the frame
 * counterclockwise as bars of a polar bar graph), Energy graphs, Chromatic Decay, Rhythm Circles, Chromatic Wireframe and Polychord (feature 042: the loudest notes as a rosette
 * of links that bend by the circle of fifths) and Spirograph (feature 046: the loudest notes of the last frames as spirograph curves, a circle rolling inside a circle).
 * (Tiles, Blended tiles, Circles, Circles paint and Concentric were removed in feature 040.)
 */
export const IMAGE_TYPES = [
  { value: "contour", label: "Contour" },
  { value: "decay", label: "Decay" },
  { value: "decay-exp", label: "Decay Exp" },
  { value: "polar-chords", label: "Polar Chords" },
  { value: "energy-graphs", label: "Energy graphs" },
  { value: "chromatic-decay", label: "Chromatic Decay" },
  { value: "rhythm-circles", label: "Rhythm Circles" },
  { value: "chromatic-wireframe", label: "Chromatic Wireframe" },
  { value: "polychord", label: "Polychord" },
  { value: "spirograph", label: "Spirograph" },
] as const;
export const DEFAULT_IMAGE_TYPE = "contour";

const imageTypeMessage = `The image type must be one of ${IMAGE_TYPES.map((t) => t.value).join(", ")}.`;

/** The name shown for an image type value such as "decay-exp". */
export function imageTypeLabel(value: string): string {
  return IMAGE_TYPES.find((t) => t.value === value)?.label ?? value;
}

/** Returns an error message, or null when the image type is exactly one of the offered values. */
export function validateImageType(value: string): string | null {
  return IMAGE_TYPES.some((t) => t.value === value) ? null : imageTypeMessage;
}

/** The colormaps that can be chosen: four of matplotlib's named scales. A picture's colors come from the chosen scale. */
export const COLORMAPS = [
  { value: "coolwarm", label: "Cool Warm" },
  { value: "YlOrRd", label: "Autumn" },
  { value: "inferno", label: "Hot" },
  { value: "Blues", label: "Blues" },
  { value: "viridis", label: "Viridis"},
  { value: "Greys", label: "Grayscale"},
  { value: "hsv", label: "HSV"},
  { value: "hot", label: "Hot (classic)" },
  { value: "Wistia", label: "Wistia" },
  { value: "Paired", label: "Paired" },
  { value: "gist_rainbow", label: "Rainbow" }
] as const;
export const DEFAULT_COLORMAP = "coolwarm";

const colormapMessage = `The colormap must be one of ${COLORMAPS.map((c) => c.value).join(", ")}.`;

/** The name shown for a colormap value such as "hot". */
export function colormapLabel(value: string): string {
  return COLORMAPS.find((c) => c.value === value)?.label ?? value;
}

/** Returns an error message, or null when the colormap is exactly one of the offered values. */
export function validateColormap(value: string): string | null {
  return COLORMAPS.some((c) => c.value === value) ? null : colormapMessage;
}

/** The original grid of a frame: 12 columns (the notes of an octave) by 7 rows (the octaves). */
export const GRID_COLUMNS = 12;
export const GRID_ROWS = 7;

/** The oversampling (the `resolution` field of the request): how many times finer than the original grid the picture is drawn (a whole number). */
export const RESOLUTION_RANGE = { min: 1, max: 5, step: 1 } as const;
export const DEFAULT_RESOLUTION = RESOLUTION_RANGE.min;

const resolutionMessage = `The oversampling must be a whole number from ${RESOLUTION_RANGE.min} to ${RESOLUTION_RANGE.max}.`;

/** Returns an error message, or null when the resolution is a whole number from 1 to 5. */
export function validateResolution(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= RESOLUTION_RANGE.min && n <= RESOLUTION_RANGE.max;
  return ok ? null : resolutionMessage;
}

/** The readout beside the slider and the result summary item: "1\u00d7", or the multiple and its grid, "3\u00d7 (36 \u00d7 21)". */
export function formatResolution(value: number): string {
  return value === 1 ? "1\u00d7" : `${value}\u00d7 (${GRID_COLUMNS * value} \u00d7 ${GRID_ROWS * value})`;
}

/** The number of notes: how many of the 84 drawn notes make up the picture (the ones with the most energy). */
export const NOTE_COUNT_RANGE = { min: 12, max: GRID_COLUMNS * GRID_ROWS, step: 1 } as const;
export const DEFAULT_NOTE_COUNT = NOTE_COUNT_RANGE.max;

const noteCountMessage = `The number of notes must be a whole number from ${NOTE_COUNT_RANGE.min} to ${NOTE_COUNT_RANGE.max}.`;

/** Returns an error message, or null when the number of notes is a whole number from 12 to 84. */
export function validateNoteCount(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= NOTE_COUNT_RANGE.min && n <= NOTE_COUNT_RANGE.max;
  return ok ? null : noteCountMessage;
}

/** The readout beside the slider: "All 84 notes", or how many of the 84 are used, "36 of 84 notes". */
export function formatNoteCount(value: number): string {
  return value === NOTE_COUNT_RANGE.max ? `All ${NOTE_COUNT_RANGE.max} notes` : `${value} of ${NOTE_COUNT_RANGE.max} notes`;
}

/** The result summary item: "All 84" or "36 of 84". */
export function formatNoteCountSummary(value: number): string {
  return value === NOTE_COUNT_RANGE.max ? `All ${NOTE_COUNT_RANGE.max}` : `${value} of ${NOTE_COUNT_RANGE.max}`;
}

/** Interpolate: only every n-th frame is drawn, the frames between are made from their neighbors (a whole number). */
export const INTERPOLATE_RANGE = { min: 1, max: 5, step: 1 } as const;
export const DEFAULT_INTERPOLATE = INTERPOLATE_RANGE.min;

const interpolateMessage = `The interpolate value must be a whole number from ${INTERPOLATE_RANGE.min} to ${INTERPOLATE_RANGE.max}.`;

/** Returns an error message, or null when the interpolate value is a whole number from 1 to 5. */
export function validateInterpolate(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isInteger(n) && n >= INTERPOLATE_RANGE.min && n <= INTERPOLATE_RANGE.max;
  return ok ? null : interpolateMessage;
}

/** The readout beside the slider: "1 (every frame drawn)", or "3 (one frame in 3 drawn)". */
export function formatInterpolate(value: number): string {
  return value === INTERPOLATE_RANGE.min ? `${value} ` : `(1/${value} frames)`;
}

/** The Gaussian smoothing of the finished picture: a number from 0 (off) to 5, in steps of one half. */
export const GAUSSIAN_RANGE = { min: 0, max: 5, step: 0.5 } as const;
export const DEFAULT_GAUSSIAN = 0;

const gaussianMessage = `The gaussian smoothing must be a number from ${GAUSSIAN_RANGE.min} to ${GAUSSIAN_RANGE.max}.`;

/** Returns an error message, or null when the Gaussian smoothing is a finite number from 0 to 5. */
export function validateGaussian(value: string | number): string | null {
  const n = parseNumber(value);
  return Number.isFinite(n) && n >= GAUSSIAN_RANGE.min && n <= GAUSSIAN_RANGE.max ? null : gaussianMessage;
}

/** The readout beside the slider and the result summary item: "Off" at 0, otherwise the number, such as "2.5". */
export function formatGaussian(value: number): string {
  return value === 0 ? "Off" : String(value);
}

function validateWhole(value: string | number, min: number, max: number, message: string): string | null {
  const n = parseNumber(value);
  return Number.isInteger(n) && n >= min && n <= max ? null : message;
}

/** Whether the settings that describe the grid of notes (Notes, Oversampling, Interpolate, Gaussian) mean anything: only for Contour, the one picture that is drawn from the grid. */
export function gridSettingsApply(imageType: string): boolean {
  return imageType === "contour";
}

/** Whether the picture is one with a circle for each of the 84 notes that the beat always charges: Decay (feature 027) and Decay Exp (feature 030). */
export function isRingsType(imageType: string): boolean {
  return imageType === "decay" || imageType === "decay-exp";
}

/** Whether the picture is Polar Chords (feature 032): bars of the loudest notes and of the chord, whose length the beat always sets. */
export function isPolarType(imageType: string): boolean {
  return imageType === "polar-chords";
}

/** Whether the picture is Energy graphs (feature 034): a running histogram of the notes with two data sets. It has no setting of its own and uses neither the grid settings, the layout nor the beat. */
export function isEnergyType(imageType: string): boolean {
  return imageType === "energy-graphs";
}

/**
 * Whether the picture runs the points of Chromatic Decay (feature 035: Decay Exp for the 12 chromatic tones, with its own decay rate, a whole number of frames from 1 to 10)
 * and so has its settings: Chromatic Decay itself, and Chromatic Wireframe (feature 039), which draws the same points as a plot in three dimensions.
 */
export function isChromaticType(imageType: string): boolean {
  return imageType === "chromatic-decay" || imageType === "chromatic-wireframe";
}

/** Whether the picture is Rhythm Circles (feature 038): six notched rings turned by the two best-voted tempos (76 to 144 beats per minute) of the starts of the sustained loudest notes and by the local peak, each with its rate of change (feature 047). Its settings are Vote limit, Extra notes and Minimum distance. */
export function isRhythmType(imageType: string): boolean {
  return imageType === "rhythm-circles";
}

/** Whether the picture is Polychord (feature 042): the loudest notes of a frame as a rosette of links that bend by the circle of fifths; the beat sets the number of copies and the tempo the color. */
export function isPolychordType(imageType: string): boolean {
  return imageType === "polychord";
}

/** Whether the picture is Spirograph (feature 046): the loudest notes of the last frames as spirograph curves, a circle rolling inside a circle. The beat sets the turns of the small circle and the radius of the big one. */
export function isSpirographType(imageType: string): boolean {
  return imageType === "spirograph";
}

/** Whether Minimum distance is used: always by Decay, Decay Exp, Polar Chords, Chromatic Decay (the beat colors, charges or lengthens them), Rhythm Circles (the peaks turn its rings), Polychord (the beat sets the copies, the tempo the color) and Spirograph (the place in the peak sets the turns and the big circle), by Contour with the Beat coloring box on, never by the others. */
export function peakSettingsShown(imageType: string, beatColoring: boolean): boolean {
  return (
    isRingsType(imageType) ||
    isPolarType(imageType) ||
    isChromaticType(imageType) ||
    isRhythmType(imageType) ||
    isPolychordType(imageType) ||
    isSpirographType(imageType) ||
    (beatColoringApplies(imageType) && beatColoring)
  );
}

/** Notes shown by Polar Chords (feature 032): how many of the loudest notes of a frame get a bar, from 5 to 8. */
export const POLAR_NOTES_RANGE = { min: 5, max: 8, step: 1 } as const;
export const DEFAULT_POLAR_NOTES = 5;

const polarNotesMessage = `The number of notes shown must be a whole number from ${POLAR_NOTES_RANGE.min} to ${POLAR_NOTES_RANGE.max}.`;

/** Returns an error message, or null when Notes shown is a whole number from 5 to 8. */
export function validatePolarNotes(value: string | number): string | null {
  return validateWhole(value, POLAR_NOTES_RANGE.min, POLAR_NOTES_RANGE.max, polarNotesMessage);
}

/** The readout beside the slider and the summary item: "5 notes". */
export function formatPolarNotes(value: number): string {
  return `${value} notes`;
}

/**
 * Extra notes (feature 044, the user's k): how far down the ranking a note that is still sounding keeps its place among the n loudest notes of a frame: it is held while it is among the
 * loudest n + k. A whole number from 1 to n, the number of notes of the picture (at most 8). Used by the seven pictures that take the n loudest notes.
 */
export const EXTRA_NOTES_RANGE = { min: 1, max: 8, step: 1 } as const;
export const DEFAULT_EXTRA_NOTES = 2;

/** Whether the picture takes the n loudest notes of each frame and so has the Extra notes setting (feature 044): Decay, Decay Exp, Polar Chords, Chromatic Decay, Chromatic Wireframe, Polychord and Spirograph (Rhythm Circles had it for the starts of its voted tempos until the fourth round of feature 047; they now come from the rise of the notes). */
export function usesHeldNotes(imageType: string): boolean {
  return ["decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe", "polychord", "spirograph"].includes(imageType);
}

/**
 * The number of notes n of a picture, the most k can be: 5, the Notes shown of Polar Chords, the Number of notes of Polychord, the smaller of the Number of notes of Spirograph and 8;
 * 8 (the most k can be) for a picture that does not use the setting.
 */
export function heldNotesCount(imageType: string, polarNotes: number, polychordNotes: number, spirographNotes: number = EXTRA_NOTES_RANGE.max): number {
  if (imageType === "polar-chords") return polarNotes;
  if (imageType === "polychord") return polychordNotes;
  if (imageType === "spirograph") return Math.min(spirographNotes, EXTRA_NOTES_RANGE.max);
  return usesHeldNotes(imageType) ? 5 : EXTRA_NOTES_RANGE.max;
}

/** Returns an error message, or null when Extra notes is a whole number from 1 to ``notes`` (the number of notes of the picture). */
export function validateExtraNotes(value: string | number, notes: number): string | null {
  return validateWhole(value, EXTRA_NOTES_RANGE.min, notes, `The extra notes must be a whole number from ${EXTRA_NOTES_RANGE.min} to ${notes}.`);
}

/** The readout beside the slider and the summary item: the number. */
export function formatExtraNotes(value: number): string {
  return String(value);
}

/** The export of 3D files (feature 045): off by default, offered for Contour and Chromatic Wireframe only. */
export const DEFAULT_EXPORT_OBJ = false;
export const OBJ_EXPORT_TYPES = ["contour", "chromatic-wireframe"] as const;

/** Whether the picture has the 3D export: Contour and Chromatic Wireframe. */
export function usesObjExport(imageType: string): boolean {
  return (OBJ_EXPORT_TYPES as readonly string[]).includes(imageType);
}

/** The readout beside the checkbox and the summary item: yes or no. */
export function formatExportObj(value: boolean): string {
  return value ? "yes" : "no";
}

/** Number of notes of Polychord (feature 042): the links in one figure, a whole number from 5 to 8. */
export const POLYCHORD_NOTES_RANGE = { min: 5, max: 8, step: 1 } as const;
export const DEFAULT_POLYCHORD_NOTES = 6;

/** The copies of the figure of Polychord: a whole number from 1 to 12 (12 copies of 30 degrees make a full turn); the minimum at the bottom of the beat, the maximum at the top of a peak. */
export const POLYCHORD_COPIES_RANGE = { min: 1, max: 12, step: 1 } as const;
export const DEFAULT_POLYCHORD_MIN_COPIES = 3;
export const DEFAULT_POLYCHORD_MAX_COPIES = 12;

/** The rotation of Polychord: degrees a second, from -360 to 360 (negative turns the other way, 0 holds still). */
export const POLYCHORD_ROTATION_RANGE = { min: -360, max: 360, step: 1 } as const;
export const DEFAULT_POLYCHORD_ROTATION = 15;

const polychordNotesMessage = `The number of notes must be a whole number from ${POLYCHORD_NOTES_RANGE.min} to ${POLYCHORD_NOTES_RANGE.max}.`;
const polychordMinCopiesMessage = `The minimum number of copies must be a whole number from ${POLYCHORD_COPIES_RANGE.min} to ${POLYCHORD_COPIES_RANGE.max}.`;
const polychordMaxCopiesMessage = `The maximum number of copies must be a whole number from ${POLYCHORD_COPIES_RANGE.min} to ${POLYCHORD_COPIES_RANGE.max}.`;
const polychordCopiesOrderMessage = "The maximum number of copies must not be less than the minimum.";
const polychordRotationMessage = `The rotation must be a number from ${POLYCHORD_ROTATION_RANGE.min} to ${POLYCHORD_ROTATION_RANGE.max} degrees a second.`;

/** Returns an error message, or null when Number of notes is a whole number from 5 to 8. */
export function validatePolychordNotes(value: string | number): string | null {
  return validateWhole(value, POLYCHORD_NOTES_RANGE.min, POLYCHORD_NOTES_RANGE.max, polychordNotesMessage);
}

/** Returns an error message, or null when Copies (minimum) is a whole number from 1 to 12. */
export function validatePolychordMinCopies(value: string | number): string | null {
  return validateWhole(value, POLYCHORD_COPIES_RANGE.min, POLYCHORD_COPIES_RANGE.max, polychordMinCopiesMessage);
}

/** Returns an error message, or null when Copies (maximum) is a whole number from 1 to 12 and not less than Copies (minimum), ``minimum`` (a minimum that is not valid is not compared: its own control says so). */
export function validatePolychordMaxCopies(value: string | number, minimum: string | number): string | null {
  const own = validateWhole(value, POLYCHORD_COPIES_RANGE.min, POLYCHORD_COPIES_RANGE.max, polychordMaxCopiesMessage);
  if (own) return own;
  if (validatePolychordMinCopies(minimum)) return null;
  return parseNumber(value) < parseNumber(minimum) ? polychordCopiesOrderMessage : null;
}

/** Returns an error message, or null when Rotation is a number from -360 to 360. */
export function validatePolychordRotation(value: string | number): string | null {
  const n = parseNumber(value);
  return Number.isFinite(n) && n >= POLYCHORD_ROTATION_RANGE.min && n <= POLYCHORD_ROTATION_RANGE.max ? null : polychordRotationMessage;
}

/** The readout beside the slider and the summary item: "6 notes". */
export function formatPolychordNotes(value: number): string {
  return `${value} notes`;
}

/** The readout of a number of copies: "1 copy", "12 copies". */
export function formatPolychordCopies(value: number): string {
  return value === 1 ? "1 copy" : `${value} copies`;
}

/** The readout of the rotation: "15 degrees/s", "-30 degrees/s", "Still" at 0. */
export function formatPolychordRotation(value: number): string {
  return value === 0 ? "Still" : `${Number(value.toFixed(2))} degrees/s`;
}

/** Number of notes of Spirograph (feature 046): the loudest notes tracked in each frame, one curve each, a whole number from 5 to 12. */
export const SPIROGRAPH_NOTES_RANGE = { min: 5, max: 12, step: 1 } as const;
export const DEFAULT_SPIROGRAPH_NOTES = 8;

/** History length of Spirograph: how many frames' notes make up a picture (the frame itself and the ones before it), a whole number from 5 to 12. */
export const SPIROGRAPH_HISTORY_RANGE = { min: 5, max: 12, step: 1 } as const;
export const DEFAULT_SPIROGRAPH_HISTORY = 8;

/** History fade of Spirograph: each frame a history entry is older, its values are multiplied by this, a number from 0.4 (fades fast) to 0.85 (fades slowly), so the newest entry is the most prominent. */
export const SPIROGRAPH_FADE_RANGE = { min: 0.4, max: 0.85, step: 0.05 } as const;
export const DEFAULT_SPIROGRAPH_FADE = 0.7;

const spirographNotesMessage = `The number of spirograph notes must be a whole number from ${SPIROGRAPH_NOTES_RANGE.min} to ${SPIROGRAPH_NOTES_RANGE.max}.`;
const spirographFadeMessage = `The history fade must be a number from ${SPIROGRAPH_FADE_RANGE.min} to ${SPIROGRAPH_FADE_RANGE.max}.`;
const spirographHistoryMessage = `The history length must be a whole number from ${SPIROGRAPH_HISTORY_RANGE.min} to ${SPIROGRAPH_HISTORY_RANGE.max}.`;

/** Returns an error message, or null when Number of notes (Spirograph) is a whole number from 5 to 12. */
export function validateSpirographNotes(value: string | number): string | null {
  return validateWhole(value, SPIROGRAPH_NOTES_RANGE.min, SPIROGRAPH_NOTES_RANGE.max, spirographNotesMessage);
}

/** Returns an error message, or null when History length is a whole number from 5 to 12. */
export function validateSpirographHistory(value: string | number): string | null {
  return validateWhole(value, SPIROGRAPH_HISTORY_RANGE.min, SPIROGRAPH_HISTORY_RANGE.max, spirographHistoryMessage);
}

/** Returns an error message, or null when History fade is a number from 0.4 to 0.85. */
export function validateSpirographFade(value: string | number): string | null {
  const n = parseNumber(value);
  return Number.isFinite(n) && n >= SPIROGRAPH_FADE_RANGE.min && n <= SPIROGRAPH_FADE_RANGE.max ? null : spirographFadeMessage;
}

/** Vote limit of Rhythm Circles (feature 047): the most votes a tempo can have, a whole number from 1 to 100; a low limit lets the tempos change quickly. */
export const VOTE_LIMIT_RANGE = { min: 1, max: 100, step: 1 } as const;
export const DEFAULT_VOTE_LIMIT = 40; // 20 until the fifth round of feature 047

const voteLimitMessage = `The vote limit must be a whole number from ${VOTE_LIMIT_RANGE.min} to ${VOTE_LIMIT_RANGE.max}.`;

/** Returns an error message, or null when Vote limit is a whole number from 1 to 100. */
export function validateVoteLimit(value: string | number): string | null {
  return validateWhole(value, VOTE_LIMIT_RANGE.min, VOTE_LIMIT_RANGE.max, voteLimitMessage);
}

/** The readout beside the slider and the summary item: the number. */
export function formatVoteLimit(value: number): string {
  return String(value);
}

/** The readout beside the slider and the summary item: "8 notes". */
export function formatSpirographNotes(value: number): string {
  return `${value} notes`;
}

/** The readout beside the slider and the summary item: "8 frames". */
export function formatSpirographHistory(value: number): string {
  return `${value} frames`;
}

/** The readout beside the slider and the summary item: "0.7 per frame". */
export function formatSpirographFade(value: number): string {
  return `${Number(value.toFixed(2))} per frame`;
}

/**
 * The decay rate (feature 027): the number of frames between two decay steps of the Decay picture, from 0.25 to 4 in steps of 0.25 (revised 2026-11-01).
 * Below 1 there are several steps in a frame, which is smoother, above all at higher frame rates; anything above 4 blinks.
 */
export const DECAY_RATE_RANGE = { min: 0.25, max: 4, step: 0.25 } as const;
export const DEFAULT_DECAY_RATE = 1;

const decayRateMessage = `The decay rate must be a number from ${DECAY_RATE_RANGE.min} to ${DECAY_RATE_RANGE.max} in steps of ${DECAY_RATE_RANGE.step}.`;

/** Returns an error message, or null when the decay rate is a number from 0.25 to 4 that is a whole number of quarters. */
export function validateDecayRate(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= DECAY_RATE_RANGE.min && n <= DECAY_RATE_RANGE.max && Number.isInteger(n / DECAY_RATE_RANGE.step);
  return ok ? null : decayRateMessage;
}

/** The readout beside the slider and the summary item: "0.25 frames", "1 frame", "2.5 frames". */
export function formatDecayRate(value: number): string {
  return value === 1 ? "1 frame" : `${value} frames`;
}

/**
 * The decay rate of Chromatic Decay (feature 035): the number of frames between two decay steps, a **whole number from 1 to 10** (the other types keep 0.25 to
 * 4 in steps of 0.25). It is its own value on the page (the request sends it as ``decay_rate`` for this type only).
 */
export const CHROMATIC_RATE_RANGE = { min: 1, max: 10, step: 1 } as const;
export const DEFAULT_CHROMATIC_RATE = 1;

const chromaticRateMessage = `The decay rate must be a whole number from ${CHROMATIC_RATE_RANGE.min} to ${CHROMATIC_RATE_RANGE.max}.`;

/** Returns an error message, or null when the decay rate is a whole number from 1 to 10. */
export function validateChromaticRate(value: string | number): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && Number.isInteger(n) && n >= CHROMATIC_RATE_RANGE.min && n <= CHROMATIC_RATE_RANGE.max;
  return ok ? null : chromaticRateMessage;
}

/** The readout beside the slider and the summary item: "1 frame", "2 frames", "10 frames". */
export function formatChromaticRate(value: number): string {
  return formatDecayRate(value);
}

/**
 * The decay amounts (feature 027, revised): how many points a circle of the Decay picture gives to each circle around it per frame, one amount for each
 * of four saturation levels (how full the circle is). Each is a number from 0.5 to 3; the defaults are 0.5, 1, 2 and 3.
 */
export const DECAY_AMOUNT_RANGE = { min: 0.5, max: 3, step: 0.5 } as const;
export const DEFAULT_DECAY_AMOUNTS = [0.5, 1, 2, 3] as const;
export const DECAY_LEVELS = [
  { name: "low", control: "decay-low", label: "Low saturation" },
  { name: "medium", control: "decay-medium", label: "Medium saturation" },
  { name: "high", control: "decay-high", label: "High saturation" },
  { name: "saturated", control: "decay-saturated", label: "Saturated" },
] as const;

/** Returns an error message, or null when the amount is a finite number from 0.5 to 3; ``level`` is the name of the saturation level. */
export function validateDecayAmount(value: string | number, level: string): string | null {
  const n = parseNumber(value);
  const ok = Number.isFinite(n) && n >= DECAY_AMOUNT_RANGE.min && n <= DECAY_AMOUNT_RANGE.max;
  return ok ? null : `The ${level} saturation decay must be a number from ${DECAY_AMOUNT_RANGE.min} to ${DECAY_AMOUNT_RANGE.max}.`;
}

/** The readout beside a slider and the summary item: "0.5 per frame", "3 per frame". */
export function formatDecayAmount(value: number): string {
  return `${value} per frame`;
}

/** Whether the decay rate does anything: for Decay and Decay Exp. The four decay amounts are Decay's only (Decay Exp takes its loss from a formula). */
export function decayRateApplies(imageType: string): boolean {
  return imageType === "decay" || imageType === "decay-exp";
}

/** Beat coloring (feature 028): the beat wave of the contour, rings that cut into the picture as the music rises in its beat. */
export const DEFAULT_BEAT_COLORING = false;
export const PEAK_DISTANCE_RANGE = { min: 100, max: 2000, step: 50 } as const;
export const DEFAULT_PEAK_DISTANCE = 350; // feature 040: it was 100; the prominence is no longer a setting (the measurement always uses 20 percent)

const peakDistanceMessage = `The minimum distance must be a number from ${PEAK_DISTANCE_RANGE.min} to ${PEAK_DISTANCE_RANGE.max} milliseconds.`;

/** Returns an error message, or null when the minimum distance is a finite number of milliseconds from 100 to 2000. */
export function validatePeakDistance(value: string | number): string | null {
  const n = parseNumber(value);
  return Number.isFinite(n) && n >= PEAK_DISTANCE_RANGE.min && n <= PEAK_DISTANCE_RANGE.max ? null : peakDistanceMessage;
}

/** The readouts and the result summary items: "Off" or "On", "350 ms". */
export function formatBeatColoring(value: boolean): string {
  return value ? "On" : "Off";
}
export function formatPeakDistance(value: number): string {
  return `${value} ms`;
}

/** Whether the beat coloring means anything: only for Contour (it switches the beat wave on, feature 028). */
export function beatColoringApplies(imageType: string): boolean {
  return imageType === "contour";
}

/** The wave count (feature 028): the waves of the beat wave of the Contour picture across the largest dimension of its grid. */
export const WAVE_COUNT_RANGE = { min: 2, max: 10, step: 1 } as const;
export const DEFAULT_WAVE_COUNT = 4;

const waveCountMessage = `The wave count must be a whole number from ${WAVE_COUNT_RANGE.min} to ${WAVE_COUNT_RANGE.max}.`;

/** Returns an error message, or null when the wave count is a whole number from 2 to 10. */
export function validateWaveCount(value: string | number): string | null {
  return validateWhole(value, WAVE_COUNT_RANGE.min, WAVE_COUNT_RANGE.max, waveCountMessage);
}

/** The readout beside the slider: "2 waves", "4 waves". */
export function formatWaveCount(value: number): string {
  return `${value} waves`;
}

/** Whether the wave count does anything: only for Contour (and only with the Beat coloring box on). */
export function waveCountApplies(imageType: string): boolean {
  return imageType === "contour";
}

/** The note layout (feature 026): which note is drawn in which cell of the 12 x 7 grid. Rows lists the notes in order, like text. */
export const NOTE_LAYOUTS = [
  { value: "rows", label: "Rows" },
  { value: "spiral", label: "Spiral" },
] as const;
export const DEFAULT_NOTE_LAYOUT = "rows";

const noteLayoutMessage = `The note layout must be one of ${NOTE_LAYOUTS.map((l) => l.value).join(", ")}.`;

/** Returns an error message, or null when the layout is exactly one of the offered values. */
export function validateNoteLayout(value: string): string | null {
  return NOTE_LAYOUTS.some((l) => l.value === value) ? null : noteLayoutMessage;
}

/** The name shown for a layout value such as "spiral". */
export function noteLayoutLabel(value: string): string {
  return NOTE_LAYOUTS.find((l) => l.value === value)?.label ?? value;
}

/** Whether the note layout does anything: for the pictures with one shape for each note, Decay and Decay Exp, and for Polar Chords (it says in which arc each note is). */
export function noteLayoutApplies(imageType: string): boolean {
  return isRingsType(imageType) || isPolarType(imageType);
}
