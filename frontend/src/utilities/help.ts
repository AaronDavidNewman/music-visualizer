import {
  BLEND_WIDTH_RANGE,
  FRAME_RATE_RANGE,
  SMOOTHING_WINDOW_RANGE,
  THRESHOLD_RANGE,
} from "./validation";

/** The explanation behind each setting's info button. Problems the user must act on are not here: they stay inline. */
export const windowSizeHelp = "Larger windows separate low notes better but blur changes over time.";

export const frameRateHelp = `${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.`;

export const colormapHelp =
  "How each tile is colored: its color is the color of the chosen scale at how strong its own note is, quiet notes at the start of the scale and the loudest note of the file at the end, so the same strength always gets the same color. Summer: green to yellow. Autumn: red to yellow. Hot: dark red through red and yellow to white. Cool: cyan to magenta.";

export const thresholdHelp = `A note whose volume is below the threshold is not drawn: with Tiles its tile is black; with Blended tiles there is no tile at all, so the place keeps the background, the middle color of the colormap, and the tiles that are drawn fade into it. The threshold is a share of the loudest note in the whole file: ${THRESHOLD_RANGE.min} (the left end) is off, and ${THRESHOLD_RANGE.max} (the right end) is ${THRESHOLD_RANGE.max}% of the loudest note. Louder notes are never changed.`;

export const imageTypeHelp =
  "Tiles: the picture is a grid of flat colored tiles with hard edges. Blended tiles: the same grid and colors, but the colors of neighboring tiles fade into each other across the edges between them. Circles: no grid at all: the strongest notes of every frame each put down a circle, placed relative to the circle of the same rank in the previous frame and colored by the colormap, and the last circles stay in the picture, so the music draws a wandering trail. Circles paint: the same circles with no memory: every frame is a copy of the previous picture with the new circles painted on top of it, solid, so the paint stays until a later circle covers it and never fades. Contour: the same grid of notes drawn as a filled contour map, bands of color that flow from one note to the next, from the start of the colormap for silence to its end for the loudest note of the file; with Beat coloring on, concentric rings pulse over it with the beat. Concentric: 84 circles, one for each note, on the same 12 by 7 grid as the tiles. The size of a circle comes from how loud its note is compared with the loudest note of the frame, in 12 steps: the loudest note is full size (just touching its neighbours) and every circle is made of as many flat rings as its step, so a full circle is 12 rings. The colors of the rings follow the beat (the Local peaks measurement): at the top of the beat the 12 rings run through the whole colormap and at the bottom only half way, so the rings of a circle never change order. The background is the middle color of the colormap, so at the bottom of the beat the outermost ring of a full circle looks like the background. Only the Local peaks settings and the data smoothing apply to it. Decay: the same 84 circles in the same places, but each is one flat disc that keeps points (0 to 64) from frame to frame. The 5 loudest notes of each frame add points to their circles (the loudest the most, a little more at the top of the beat), and every few frames (the decay rate) each circle gives some of its points to the circles around it, so the loud spots spread out and fade. The size of a disc follows its points up to 24, and its color runs along the colormap up to 32 points; above that the disc gets rings like Concentric, which open up from the brightest color in the middle towards the first color of the colormap at the edge, so a circle with 64 points has 12 rings and you can see it fade all the way down. The Note layout, the Local peaks settings and the data smoothing apply to it. Decay Exp: the same as Decay, with a different rate at which the circles take on and give away points: a note that would add some points adds only part of them (the more points it would add, the smaller the part; the cut eases off slowly as the picture goes on, and tightens again whenever more than 10 circles have more than 32 points), and a circle gives to the circles around it more the more points it has, so a full circle drains fast and a nearly empty one hardly at all. Only the decay rate is set; the four decay settings of Decay do not apply to it. Polar Chords: a polar bar graph, with bars that start at the center of the circle. The circle has 84 equal arcs, starting at the top. Going clockwise, each of the 84 notes has an arc and the loudest notes of the frame (Notes shown, 5 to 8) get a bar in theirs. Going counterclockwise, the circle has 84 arcs too, one for each of the 12 letters (a note without its octave: A, A#, B and so on) and each of the 7 chord types: the 7 types of the first letter, then the 7 of the next letter, and so on. The chord that the loudest notes form gets a bar in the arc of its root letter and its type (the octave and the inversion do not matter). Every bar reaches out between half and all of the radius, following the beat. When the note of a bar changes, the bar moves one arc a frame toward the new note instead of jumping there, which smooths the animation. The notes are colored from the middle of the colormap toward its start and the chord from the middle toward its end (a colormap with two different colors at its ends, such as Cool Warm, shows them best). The Note layout (rows or spiral) says in which arc each note is, as it says in which cell it is for the other pictures; the chord does not depend on it. The Local peaks settings and the data smoothing apply to it. Energy graphs: a histogram of the 84 notes that updates from frame to frame, with two data sets for each note, side by side. The first (frequency) adds points in every analysis window by rank: 84 for the loudest note, 83 for the second loudest and so on, nothing for a silent note. The second (amplitude) adds, in every window, the quasi-decibel value of the note, 20 log10 of its amplitude divided by 20 log10 of the largest amplitude of any note in the file, so the loudest note of the file adds 1 and fainter ones less. Both keep what they have collected since the start of the file. To draw them on the same scale each data set is divided by its largest total and put through a softmax; because a softmax is never zero and its values are close together, the smallest value of each data set is then given the height zero so that the clear winners stand out, and the whole picture is scaled so that the tallest bar is always the same height. It has no settings of its own: only the analysis settings and the colormap apply, and the others are ignored.";

export const blendWidthHelp = `Number from ${BLEND_WIDTH_RANGE.min} to ${BLEND_WIDTH_RANGE.max}. How far the fade reaches on each side of an edge between two tiles, as a percentage of a tile's width: larger values give wider, softer fades and smaller ones sharper edges. Only used by Blended tiles.`;

export const smoothingHelp =
  "0 is no smoothing. Otherwise each frame is averaged with the frames before it in the smoothing window; each of those counts this fraction as much as the current frame, so higher values blend more and fade notes more slowly.";

export const smoothingWindowHelp = `Whole number, ${SMOOTHING_WINDOW_RANGE.min} to ${SMOOTHING_WINDOW_RANGE.max}. How many earlier frames are mixed into each frame: with 1 each frame is blended with the one before it, with ${SMOOTHING_WINDOW_RANGE.max} with the ${SMOOTHING_WINDOW_RANGE.max} before it. A note that stops is gone that many frames later. It has no effect while Smoothing is 0.`;

/** The spacing explanation, followed by the live step between windows when the value is usable (`stepHint` is empty otherwise). */
export function spacingHelp(stepHint: string): string {
  const base = "Distance between the starts of windows, as a multiple of the window size.";
  return stepHint ? `${base} ${stepHint}` : base;
}

export const resolutionHelp =
  "Oversampling: how fine the picture is. 1\u00d7 is the original grid of 12 \u00d7 7 values, one for each note. Higher values, up to 5\u00d7 (60 \u00d7 35), make new values between the notes by interpolating, so the picture has more and smaller tiles (or finer contour steps) in the same size. The threshold and the colors then apply to those new values.";

export const noteCountHelp =
  "Only the notes with the most energy in the whole file are used: 12 to 84 of the 84 drawn notes. Their values are spread over the whole picture, so each one covers a larger area. Fewer notes remove the flicker of faint notes and make bigger features; the picture is not steadier in every case. The colors keep their scale.";

export const interpolateHelp =
  "1 to 5. Only every n-th frame is drawn from the music (1 draws every frame); the frames between are made by blending their two drawn neighbors (a mix of the two, with more of the nearer one), so the animation has the same number of frames and speed. A contour job is faster the higher the value (drawing is the slow part); tile pictures are cheap to draw, so there is little to save. Quickly changing music can lose events that happen between two drawn frames.";

export const gaussianHelp =
  "0 to 5. 0 is off: nothing is done. Otherwise every picture is blurred with a Gaussian blur, a soft smoothing of the colors that rounds off the edges of tiles, contour bands and the soft edges of blended tiles. The number is the radius in pixels, made 3:2 like the picture so that the blur looks the same in both directions: a setting of 4 blurs by 6 pixels across and 4 down. The blurred picture has many more colors, so its file is bigger and takes longer to make. Only used by Tiles, Blended tiles and Contour.";

export const circleUnitHelp =
  "1 to 10 pixels. Movement: the length of one step of a circle (the radius of a circle is a separate setting). The number is measured against a frame 252 pixels wide and is drawn 2.4 times larger on the 600-pixel frame. A note moves its circle by an angle from its name (30 degrees for each of C, C#, D ... B) and a number of units from its octave: 1 unit for octave 4 and one more for every octave above or below it. A note that repeats at the same volume stays in place. Only used by Circles.";

export const circleRadiusHelp =
  "4 to 8 pixels. The radius of each circle, the distance from its center to its edge: 4 is a small dot, 8 is twice as wide. The number is measured against a frame 252 pixels wide and is drawn 2.4 times larger on the 600-pixel frame. It does not change how far circles move. With Resize by volume on, this is the smallest radius a circle gets. Only used by Circles.";

export const circleResizeHelp =
  "Off by default. When on, the size of each circle also follows the energy of its note: the radius goes from the chosen radius for the faintest note to three times it for the loudest note of the whole file, in a straight line along the same scale as the colors, so no circle is smaller than the radius. A circle keeps the size it was given when it was put down. Only used by Circles.";

export const circleMemoryHelp =
  "100 to 500 circles. How many of the most recent circles stay in the picture; when it is full the oldest is dropped. A larger memory leaves a longer trail. The newest circle is drawn solid and older ones fade with their age, so the oldest, just before it is dropped, is barely visible. The background is the middle color of the color map. Only used by Circles.";

export const circleNotesHelp =
  "5 to 12. Notes: how many of the strongest notes of each frame put a circle down; the circle of the strongest continues from the strongest circle of the previous frame, and so on down the ranks. More notes make a busier picture. Only used by Circles.";

export const decayRateHelp =
  "0.25 to 4 frames in steps of 0.25 (default 1). How often the circles of the Decay picture spread out: every this many frames each circle gives points to each of the circles around it, at the rate of its saturation level (the four decay settings below: how full the circle is). A step moves this many frames' worth, so the average rate is the same at any setting: A number below 1 takes several smaller steps in every frame (0.25 takes four), which is smoother, above all at higher frame rates; with a large number a circle with plenty of points can give most of what it has away in one step, so the loud spots disappear in jumps, which is why 4 is the most. A circle on an edge or in a corner loses the same total as one in the middle, but some of it goes to the circles that are not there, so it fades faster. It counts frames, so at a higher frame rate the picture fades faster in time.";

const decayAmountText = (level: string, fullness: string, standard: string) =>
  `0.5 to 3 (default ${standard}). How many points a circle at the ${level} saturation level (${fullness}) gives to each of the circles around it, every frame: 0.5 is one point every 2 frames, 3 is the fastest. A circle gives to 8 neighbours, so it loses 8 times this a frame (an edge or corner circle too, as if it had all 8; the share of the missing neighbours is lost), and never more than it has. Larger numbers make a circle at this level empty and spread to its neighbours faster; smaller ones keep it longer. Only used by Decay.`;

export const decayExpRateHelp =
  "0.25 to 4 frames in steps of 0.25 (default 1). How often the circles of the Decay Exp picture spread out: every this many frames each circle gives points to each of the circles around it. How much it gives does not depend on this setting or on any other: a circle with p points gives each neighbour sin²(π/2 × p/64) per frame, so the fuller a circle is the faster it drains (a full one gives 1 to each of the 8 circles around it every frame) and a nearly empty one hardly drains at all. A step moves this many frames' worth, so the average rate is the same at any setting. A number below 1 takes several smaller steps in every frame (0.25 takes four), which is smoother, above all at higher frame rates. A circle on an edge or in a corner loses the same total as one in the middle, but some of it goes to the circles that are not there. It counts frames, so at a higher frame rate the picture fades faster in time.";

export const decayAmountHelp = {
  low: decayAmountText("low", "a circle with only a few points", "0.5"),
  medium: decayAmountText("medium", "somewhat more than low", "1"),
  high: decayAmountText("high", "a well charged circle", "2"),
  saturated: decayAmountText("saturated", "a circle that is completely full", "3"),
} as const;

export const polarNotesHelp =
  "5 to 8 (default 5). Only used by Polar Chords. How many of the loudest notes of every frame get a bar in the clockwise circle of the 84 notes: a note with no strength never gets one. The chord bar of the counterclockwise circle is drawn whenever the loudest notes form one of the 7 chords, whatever this number is.";

export const waveCountHelp =
  "2 to 10 (default 4). Only used by Contour, and only when Beat coloring is on. How many waves the rings across the picture have, counted from the center to the edge of the larger side: a larger number makes more and thinner rings, close together near the middle and wider towards the edge. The rings dim the picture by a share that swells and fades smoothly over a beat: nothing at the bottom of the beat, so the picture is the plain contour, the dark rings cut away completely half way up the beat, and nothing again at the top. The colors still run from 0 to the loudest note of the frame, so the dimmed rings look darker.";

export const beatColoringHelp =
  "Off by default. When off, the color of a tile comes 100% from the energy of its note, as it always has. When on, half of its place on the colormap comes from the energy of its note and the other half from where the music is in its beat: the frame's place between the minimum (0) and the maximum (1) of the local energy peak around it, found by the Local peaks measurement of the whole file. The strongest tile then has the middle color of the colormap at the minimum of the peak and the last color at its maximum. The place follows how strong the beats are, rising and falling from beat to beat; before the first beat it is 0. A tile hidden by the threshold is drawn as before. For Tiles and Blended tiles. For Contour, the box turns on the beat wave (see Wave count): rings that cut into the picture as the music rises in its beat, deepest half way up it and fading out again towards its top, and leave it exactly as it is at the bottom of the beat and when the box is off.";

export const peakDistanceHelp =
  "100 to 2000 milliseconds (default 100). The shortest time between two beats: of two peaks closer than this only the stronger counts. A short time follows fast music; a long one keeps only the main beats of slow music. Only used when Beat coloring is on, by Tiles and Blended tiles.";

export const peakProminenceHelp =
  "0 to 100 percent (default 50). How much a bump in the overall energy must stand out from its surroundings to count as a beat, as a share of the loudest energy in the stretch of about three seconds around it. A low value finds soft beats and also small bumps; a high value keeps only the clearest beats. Only used when Beat coloring is on, by Tiles and Blended tiles.";

export const noteLayoutHelp =
  "Rows (the default): the notes are listed in order like text, twelve to a row, the lowest at the top left. Spiral: the notes are arranged in a spiral around middle C, which is in the 3rd row and the 6th column. The next note up is one cell to the right of it and the next note down one cell to the left; the notes above middle C wind clockwise outward from it and the notes below it counterclockwise, the two taking turns. Notes close in pitch are then close on the screen in more than one direction. Only the place of a note changes: its size, color and hiding are the same, and Oversampling blends the tiles that are next to each other on the screen. Only used by Tiles, Blended tiles and Concentric.";
