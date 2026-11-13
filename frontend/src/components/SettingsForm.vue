<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  COLORMAPS,
  DEFAULT_COLORMAP,
  DEFAULT_BEAT_COLORING,
  DECAY_AMOUNT_RANGE,
  DECAY_LEVELS,
  DEFAULT_DECAY_AMOUNTS,
  DEFAULT_CHROMATIC_RATE,
  DEFAULT_DECAY_RATE,
  DEFAULT_WAVE_COUNT,
  WAVE_COUNT_RANGE,
  DEFAULT_POLAR_NOTES,
  POLAR_NOTES_RANGE,
  DEFAULT_NOTE_LAYOUT,
  CHROMATIC_RATE_RANGE,
  DECAY_RATE_RANGE,
  NOTE_LAYOUTS,
  DEFAULT_PEAK_DISTANCE,
  DEFAULT_PEAK_PROMINENCE,
  PEAK_DISTANCE_RANGE,
  PEAK_PROMINENCE_RANGE,
  DEFAULT_IMAGE_TYPE,
  DEFAULT_GAUSSIAN,
  DEFAULT_INTERPOLATE,
  DEFAULT_NOTE_COUNT,
  DEFAULT_RESOLUTION,
  DEFAULT_SMOOTHING,
  DEFAULT_SMOOTHING_WINDOW,
  DEFAULT_THRESHOLD,
  DEFAULT_WINDOW_SIZE,
  IMAGE_TYPES,
  GAUSSIAN_RANGE,
  INTERPOLATE_RANGE,
  NOTE_COUNT_RANGE,
  RESOLUTION_RANGE,
  SMOOTHING_RANGE,
  SMOOTHING_WINDOW_RANGE,
  THRESHOLD_RANGE,
  WINDOW_SIZES,
  formatBeatColoring,
  formatDecayAmount,
  formatChromaticRate,
  formatDecayRate,
  formatPolarNotes,
  formatWaveCount,
  formatPeakDistance,
  formatPeakProminence,
  formatGaussian,
  formatInterpolate,
  formatNoteCount,
  formatResolution,
  formatSmoothing,
  formatThreshold,
  validatePeakDistance,
  validateDecayAmount,
  validateChromaticRate,
  validateDecayRate,
  validatePolarNotes,
  validateWaveCount,
  validateNoteLayout,
  isChromaticType,
  noteLayoutApplies,
  validatePeakProminence,
  validateColormap,
  validateFile,
  validateFrameRate,
  validateImageType,
  validateGaussian,
  validateInterpolate,
  validateNoteCount,
  validateResolution,
  validateSmoothing,
  validateSmoothingWindow,
  validateThreshold,
  validateWindowSize,
} from "../utilities/validation";
import {
  defaultSpacing,
  formatSpacing,
  isBelowMinimum,
  minimumMessage,
  stepMilliseconds,
  stepSamples,
  validateSpacing,
} from "../utilities/spacing";
import {
  colormapHelp,
  frameRateHelp,
  imageTypeHelp,
  gaussianHelp,
  beatColoringHelp,
  decayAmountHelp,
  decayExpRateHelp,
  chromaticRateHelp,
  decayRateHelp,
  polarNotesHelp,
  waveCountHelp,
  noteLayoutHelp,
  peakDistanceHelp,
  peakProminenceHelp,
  interpolateHelp,
  noteCountHelp,
  resolutionHelp,
  smoothingHelp,
  smoothingWindowHelp,
  spacingHelp,
  thresholdHelp,
  windowSizeHelp,
} from "../utilities/help";
import InfoPopover from "./InfoPopover.vue";
import SettingsGroup from "./SettingsGroup.vue";
import { controlsIn, groupTitle, groupsFor, isOpen, setOpen, type OpenState } from "../utilities/groups";
import type { JobSettings } from "../api";

const props = defineProps<{ busy: boolean; file: File | null; sampleRate: number; initialImageType?: string }>();
const emit = defineEmits<{ submit: [file: File, settings: JobSettings] }>();

const windowSize = ref<number>(DEFAULT_WINDOW_SIZE);
const frameRateText = ref("30");
const colormap = ref<string>(DEFAULT_COLORMAP);
const smoothing = ref<number>(DEFAULT_SMOOTHING);
const smoothingWindowText = ref(String(DEFAULT_SMOOTHING_WINDOW));
const threshold = ref<number>(DEFAULT_THRESHOLD);
const imageType = ref<string>(props.initialImageType ?? DEFAULT_IMAGE_TYPE);
const resolution = ref<number>(DEFAULT_RESOLUTION);
const noteCount = ref<number>(DEFAULT_NOTE_COUNT);
const interpolate = ref<number>(DEFAULT_INTERPOLATE);
const gaussian = ref<number>(DEFAULT_GAUSSIAN);
const noteLayout = ref<string>(DEFAULT_NOTE_LAYOUT);
const decayRate = ref<number>(DEFAULT_DECAY_RATE);
const chromaticRate = ref<number>(DEFAULT_CHROMATIC_RATE); // the decay rate of Chromatic Decay (1 to 10): its own value, so each type keeps its own
const decayAmounts = ref<number[]>([...DEFAULT_DECAY_AMOUNTS]); // low, medium, high, saturated
const waveCount = ref<number>(DEFAULT_WAVE_COUNT);
const polarNotes = ref<number>(DEFAULT_POLAR_NOTES);
const beatColoring = ref<boolean>(DEFAULT_BEAT_COLORING);
const peakDistance = ref<number>(DEFAULT_PEAK_DISTANCE);
const peakProminence = ref<number>(DEFAULT_PEAK_PROMINENCE);
const spacingText = ref(defaultSpacingText(props.sampleRate, frameRateText.value, windowSize.value) ?? "");

function defaultSpacingText(sampleRate: number, frameRate: string, size: number): string | null {
  const spacing = defaultSpacing(sampleRate, frameRate, size);
  return spacing === null ? null : formatSpacing(spacing);
}

// The default spacing follows the window size, frame rate and file: any change replaces what is in the field.
// If the frame rate is not usable yet (empty, partly typed), the field is left alone.
watch([windowSize, frameRateText, () => props.sampleRate, () => props.file], () => {
  const text = defaultSpacingText(props.sampleRate, frameRateText.value, windowSize.value);
  if (text !== null) spacingText.value = text;
});

const fileError = computed(() => validateFile(props.file));
const windowError = computed(() => validateWindowSize(windowSize.value));
const frameRateError = computed(() => validateFrameRate(frameRateText.value));
const spacingError = computed(() => validateSpacing(spacingText.value));
const smoothingError = computed(() => validateSmoothing(smoothing.value));
const smoothingWindowError = computed(() => validateSmoothingWindow(smoothingWindowText.value));
const thresholdError = computed(() => validateThreshold(threshold.value));
const imageTypeError = computed(() => validateImageType(imageType.value));
const colormapError = computed(() => validateColormap(colormap.value));
const resolutionError = computed(() => validateResolution(resolution.value));
const noteCountError = computed(() => validateNoteCount(noteCount.value));
const interpolateError = computed(() => validateInterpolate(interpolate.value));
const gaussianError = computed(() => validateGaussian(gaussian.value));
const noteLayoutError = computed(() => validateNoteLayout(noteLayout.value));
const decayRateError = computed(() => validateDecayRate(decayRate.value));
const chromaticRateError = computed(() => validateChromaticRate(chromaticRate.value));
const decayAmountErrors = computed(() => DECAY_LEVELS.map((level, index) => validateDecayAmount(decayAmounts.value[index], level.name)));
const waveCountError = computed(() => validateWaveCount(waveCount.value));
const polarNotesError = computed(() => validatePolarNotes(polarNotes.value));
const peakDistanceError = computed(() => validatePeakDistance(peakDistance.value));
const peakProminenceError = computed(() => validatePeakProminence(peakProminence.value));
const canSubmit = computed(
  () =>
    !fileError.value &&
    !windowError.value &&
    !frameRateError.value &&
    !spacingError.value &&
    !smoothingError.value &&
    !smoothingWindowError.value &&
    !thresholdError.value &&
    !imageTypeError.value &&
    !colormapError.value &&
    !resolutionError.value &&
    !noteCountError.value &&
    !interpolateError.value &&
    !gaussianError.value &&
    !noteLayoutError.value &&
    !decayRateError.value &&
    !chromaticRateError.value &&
    decayAmountErrors.value.every((e) => !e) &&
    !waveCountError.value &&
    !polarNotesError.value &&
    !peakDistanceError.value &&
    !peakProminenceError.value,
);

// The groups (feature 020). The group of the chosen image type follows the Image type group; a control the type does not use is not
// shown. Every value stays in its ref, so it is kept when a group is folded or the type is changed, and is still sent.
const TYPE_GROUP_IDS = ["contour", "decay", "decay-exp", "polar-chords", "chromatic-decay", "chromatic-wireframe"];
const shownGroups = computed(() => groupsFor(imageType.value));
const typeGroup = computed(() => shownGroups.value.find((id) => TYPE_GROUP_IDS.includes(id)));
const showDataSmoothing = computed(() => shownGroups.value.includes("data-smoothing")); // not for Energy graphs (feature 034)
const showImageSmoothing = computed(() => shownGroups.value.includes("image-smoothing"));
// the Local peaks group has one of two ids: local-peaks (Contour: with the checkbox) or concentric-peaks (Decay, Decay Exp, Polar Chords, Chromatic Decay and Chromatic Wireframe: without; the id is from the first picture that had it)
const showNoteLayout = computed(() => noteLayoutApplies(imageType.value));
const peaksGroup = computed(() => shownGroups.value.find((id) => id === "local-peaks" || id === "concentric-peaks") ?? "");
function inTypeGroup(control: string): boolean {
  return typeGroup.value !== undefined && controlsIn(typeGroup.value).includes(control);
}

// Which groups are open: every group starts open; the state is only kept in memory.
const openState = reactive<Record<string, boolean>>({});
function onToggle(id: string, open: boolean) {
  Object.assign(openState, setOpen(openState as OpenState, id, open));
}

// A group is flagged "needs attention" when one of its controls has a value that is not allowed (the same errors that disable Create frames).
const analysisProblem = computed(() => !!(windowError.value || frameRateError.value || spacingError.value));
const colormapProblem = computed(() => !!colormapError.value);
const imageTypeProblem = computed(() => !!imageTypeError.value);
const typeGroupProblem = computed(
  () =>
    (inTypeGroup("threshold") && !!thresholdError.value) ||
    (inTypeGroup("notes") && !!noteCountError.value) ||
    (inTypeGroup("decay-rate") && !!decayRateError.value) ||
    (inTypeGroup("chromatic-decay-rate") && !!chromaticRateError.value) ||
    (inTypeGroup("decay-low") && decayAmountErrors.value.some((e) => !!e)) ||
    (inTypeGroup("polar-notes") && !!polarNotesError.value) ||
    (inTypeGroup("wave-count") && !!waveCountError.value),
);
const noteLayoutProblem = computed(() => !!noteLayoutError.value);
const localPeaksProblem = computed(() => !!(peakDistanceError.value || peakProminenceError.value));
const dataSmoothingProblem = computed(() => !!(smoothingWindowError.value || smoothingError.value));
const imageSmoothingProblem = computed(() => !!(resolutionError.value || interpolateError.value || gaussianError.value));

const belowMinimum = computed(
  () => !spacingError.value && isBelowMinimum(Number(spacingText.value), windowSize.value),
);

const stepHint = computed(() => {
  if (spacingError.value) return "";
  const spacing = Number(spacingText.value);
  const samples = stepSamples(spacing, windowSize.value);
  const ms = stepMilliseconds(spacing, windowSize.value, props.sampleRate);
  return `Step between windows: ${Number(samples.toFixed(2))} samples (${ms.toFixed(1)} ms).`;
});

function onSubmit() {
  if (!canSubmit.value || !props.file) return;
  emit("submit", props.file, {
    windowSize: windowSize.value,
    frameRate: Number(frameRateText.value),
    windowSpacing: Number(spacingText.value),
    threshold: threshold.value,
    smoothingWindow: Number(smoothingWindowText.value),
    imageType: imageType.value,
    colormap: colormap.value,
    resolution: resolution.value,
    noteCount: noteCount.value,
    interpolate: interpolate.value,
    gaussian: gaussian.value,
    noteLayout: noteLayout.value,
    decayRate: isChromaticType(imageType.value) ? chromaticRate.value : decayRate.value,
    decayLow: decayAmounts.value[0],
    decayMedium: decayAmounts.value[1],
    decayHigh: decayAmounts.value[2],
    decaySaturated: decayAmounts.value[3],
    waveCount: waveCount.value,
    polarNotes: polarNotes.value,
    beatColoring: beatColoring.value,
    peakDistance: peakDistance.value,
    peakProminence: peakProminence.value,
    smoothing: Math.round(smoothing.value * 100) / 100,
  });
}
</script>

<template>
  <form class="settings" @submit.prevent="onSubmit">
    <SettingsGroup
      id="analysis"
      :title="groupTitle('analysis')"
      :open="isOpen(openState, 'analysis')"
      :problem="analysisProblem"
      @toggle="onToggle('analysis', $event)"
    >
      <div class="field">
        <div class="field-head">
          <label for="window-size">FFT Window size</label>
          <InfoPopover label="window size" :text="windowSizeHelp" />
        </div>
        <select id="window-size" v-model.number="windowSize" :disabled="busy">
          <option v-for="size in WINDOW_SIZES" :key="size" :value="size">{{ size }}</option>
        </select>
        <small v-if="windowError" class="error">{{ windowError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="frame-rate">Frame rate (FPS)</label>
          <InfoPopover label="frame rate" :text="frameRateHelp" />
        </div>
        <input id="frame-rate" v-model="frameRateText" type="number" step="any" inputmode="decimal" :disabled="busy" />
        <small v-if="frameRateError" class="error">{{ frameRateError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="window-spacing">Window spacing</label>
          <InfoPopover label="window spacing" :text="spacingHelp(stepHint)" />
        </div>
        <input
          id="window-spacing"
          v-model="spacingText"
          type="number"
          step="any"
          inputmode="decimal"
          :disabled="busy"
        />
        <small v-if="spacingError" class="error">{{ spacingError }}</small>
        <small v-else-if="belowMinimum" class="notice">{{ minimumMessage(windowSize) }}</small>
      </div>
    </SettingsGroup>

    <SettingsGroup
      id="colormap"
      :title="groupTitle('colormap')"
      :open="isOpen(openState, 'colormap')"
      :problem="colormapProblem"
      @toggle="onToggle('colormap', $event)"
    >
      <div class="field">
        <div class="field-head">
          <label for="colormap">Colormap</label>
          <InfoPopover label="colormap" :text="colormapHelp" />
        </div>
        <select id="colormap" v-model="colormap" :disabled="busy">
          <option v-for="map in COLORMAPS" :key="map.value" :value="map.value">{{ map.label }}</option>
        </select>
        <small v-if="colormapError" class="error">{{ colormapError }}</small>
      </div>
    </SettingsGroup>

    <SettingsGroup
      id="image-type"
      :title="groupTitle('image-type')"
      :open="isOpen(openState, 'image-type')"
      :problem="imageTypeProblem"
      @toggle="onToggle('image-type', $event)"
    >
      <div class="field">
        <div class="field-head">
          <label for="image-type">Image type</label>
          <InfoPopover label="image type" :text="imageTypeHelp" />
        </div>
        <select id="image-type" v-model="imageType" :disabled="busy">
          <option v-for="type in IMAGE_TYPES" :key="type.value" :value="type.value">{{ type.label }}</option>
        </select>
        <small v-if="imageTypeError" class="error">{{ imageTypeError }}</small>
      </div>
    </SettingsGroup>

    <!-- the group of the chosen image type (Contour, Decay, ...); a control that the type does not use is not shown -->
    <SettingsGroup
      v-if="typeGroup"
      :id="typeGroup"
      :title="groupTitle(typeGroup)"
      :open="isOpen(openState, typeGroup)"
      :problem="typeGroupProblem"
      @toggle="onToggle(typeGroup, $event)"
    >
      <div v-if="inTypeGroup('threshold')" class="field">
        <div class="field-head">
          <label for="threshold">Threshold</label>
          <InfoPopover label="threshold" :text="thresholdHelp" />
          <output class="slider-value" for="threshold">{{ formatThreshold(threshold) }}</output>
        </div>
        <input
          id="threshold"
          v-model.number="threshold"
          type="range"
          :min="THRESHOLD_RANGE.min"
          :max="THRESHOLD_RANGE.max"
          :step="THRESHOLD_RANGE.step"
          :disabled="busy"
        />
        <small v-if="thresholdError" class="error">{{ thresholdError }}</small>
      </div>

      <div v-if="inTypeGroup('notes')" class="field">
        <div class="field-head">
          <label for="notes">Notes</label>
          <InfoPopover label="notes" :text="noteCountHelp" />
          <output class="slider-value" for="notes">{{ formatNoteCount(noteCount) }}</output>
        </div>
        <input
          id="notes"
          v-model.number="noteCount"
          type="range"
          :min="NOTE_COUNT_RANGE.min"
          :max="NOTE_COUNT_RANGE.max"
          :step="NOTE_COUNT_RANGE.step"
          :disabled="busy"
        />
        <small v-if="noteCountError" class="error">{{ noteCountError }}</small>
      </div>

      <div v-if="inTypeGroup('polar-notes')" class="field">
        <div class="field-head">
          <label for="polar-notes">Notes shown</label>
          <InfoPopover label="notes shown" :text="polarNotesHelp" />
          <output class="slider-value" for="polar-notes">{{ formatPolarNotes(polarNotes) }}</output>
        </div>
        <input
          id="polar-notes"
          v-model.number="polarNotes"
          type="range"
          :min="POLAR_NOTES_RANGE.min"
          :max="POLAR_NOTES_RANGE.max"
          :step="POLAR_NOTES_RANGE.step"
          :disabled="busy"
        />
        <small v-if="polarNotesError" class="error">{{ polarNotesError }}</small>
      </div>

      <div v-if="inTypeGroup('decay-rate')" class="field">
        <div class="field-head">
          <label for="decay-rate">Decay rate</label>
          <InfoPopover label="decay rate" :text="imageType === 'decay-exp' ? decayExpRateHelp : decayRateHelp" />
          <output class="slider-value" for="decay-rate">{{ formatDecayRate(decayRate) }}</output>
        </div>
        <input
          id="decay-rate"
          v-model.number="decayRate"
          type="range"
          :min="DECAY_RATE_RANGE.min"
          :max="DECAY_RATE_RANGE.max"
          :step="DECAY_RATE_RANGE.step"
          :disabled="busy"
        />
        <small v-if="decayRateError" class="error">{{ decayRateError }}</small>
      </div>

      <div v-if="inTypeGroup('chromatic-decay-rate')" class="field">
        <div class="field-head">
          <label for="chromatic-decay-rate">Decay rate</label>
          <InfoPopover label="decay rate" :text="chromaticRateHelp" />
          <output class="slider-value" for="chromatic-decay-rate">{{ formatChromaticRate(chromaticRate) }}</output>
        </div>
        <input
          id="chromatic-decay-rate"
          v-model.number="chromaticRate"
          type="range"
          :min="CHROMATIC_RATE_RANGE.min"
          :max="CHROMATIC_RATE_RANGE.max"
          :step="CHROMATIC_RATE_RANGE.step"
          :disabled="busy"
        />
        <small v-if="chromaticRateError" class="error">{{ chromaticRateError }}</small>
      </div>

      <template v-for="(level, index) in DECAY_LEVELS" :key="level.control">
        <div v-if="inTypeGroup(level.control)" class="field">
          <div class="field-head">
            <label :for="level.control">{{ level.label }}</label>
            <InfoPopover :label="level.label.toLowerCase() + ' decay'" :text="decayAmountHelp[level.name]" />
            <output class="slider-value" :for="level.control">{{ formatDecayAmount(decayAmounts[index]) }}</output>
          </div>
          <input
            :id="level.control"
            v-model.number="decayAmounts[index]"
            type="range"
            :min="DECAY_AMOUNT_RANGE.min"
            :max="DECAY_AMOUNT_RANGE.max"
            :step="DECAY_AMOUNT_RANGE.step"
            :disabled="busy"
          />
          <small v-if="decayAmountErrors[index]" class="error">{{ decayAmountErrors[index] }}</small>
        </div>
      </template>

      <div v-if="inTypeGroup('wave-count')" class="field">
        <div class="field-head">
          <label for="wave-count">Wave count</label>
          <InfoPopover label="wave count" :text="waveCountHelp" />
          <output class="slider-value" for="wave-count">{{ formatWaveCount(waveCount) }}</output>
        </div>
        <input
          id="wave-count"
          v-model.number="waveCount"
          type="range"
          :min="WAVE_COUNT_RANGE.min"
          :max="WAVE_COUNT_RANGE.max"
          :step="WAVE_COUNT_RANGE.step"
          :disabled="busy"
        />
        <small v-if="waveCountError" class="error">{{ waveCountError }}</small>
      </div>
    </SettingsGroup>

    <SettingsGroup
      v-if="showNoteLayout"
      id="note-layout"
      :title="groupTitle('note-layout')"
      :open="isOpen(openState, 'note-layout')"
      :problem="noteLayoutProblem"
      @toggle="onToggle('note-layout', $event)"
    >
      <div class="field">
        <div class="field-head">
          <label for="note-layout">Note layout</label>
          <InfoPopover label="note layout" :text="noteLayoutHelp" />
        </div>
        <select id="note-layout" v-model="noteLayout" :disabled="busy">
          <option v-for="layout in NOTE_LAYOUTS" :key="layout.value" :value="layout.value">{{ layout.label }}</option>
        </select>
        <small v-if="noteLayoutError" class="error">{{ noteLayoutError }}</small>
      </div>
    </SettingsGroup>

    <SettingsGroup
      v-if="peaksGroup"
      :id="peaksGroup"
      :title="groupTitle(peaksGroup)"
      :open="isOpen(openState, peaksGroup)"
      :problem="localPeaksProblem"
      @toggle="onToggle(peaksGroup, $event)"
    >
      <div v-if="peaksGroup === 'local-peaks'" class="field">
        <div class="field-head">
          <label for="beat-coloring">Beat coloring</label>
          <InfoPopover label="beat coloring" :text="beatColoringHelp" />
          <output class="slider-value" for="beat-coloring">{{ formatBeatColoring(beatColoring) }}</output>
        </div>
        <input id="beat-coloring" v-model="beatColoring" type="checkbox" :disabled="busy" />
      </div>

      <div class="field">
        <div class="field-head">
          <label for="peak-distance">Minimum distance</label>
          <InfoPopover label="minimum distance" :text="peakDistanceHelp" />
          <output class="slider-value" for="peak-distance">{{ formatPeakDistance(peakDistance) }}</output>
        </div>
        <input
          id="peak-distance"
          v-model.number="peakDistance"
          type="range"
          :min="PEAK_DISTANCE_RANGE.min"
          :max="PEAK_DISTANCE_RANGE.max"
          :step="PEAK_DISTANCE_RANGE.step"
          :disabled="busy"
        />
        <small v-if="peakDistanceError" class="error">{{ peakDistanceError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="peak-prominence">Prominence</label>
          <InfoPopover label="prominence" :text="peakProminenceHelp" />
          <output class="slider-value" for="peak-prominence">{{ formatPeakProminence(peakProminence) }}</output>
        </div>
        <input
          id="peak-prominence"
          v-model.number="peakProminence"
          type="range"
          :min="PEAK_PROMINENCE_RANGE.min"
          :max="PEAK_PROMINENCE_RANGE.max"
          :step="PEAK_PROMINENCE_RANGE.step"
          :disabled="busy"
        />
        <small v-if="peakProminenceError" class="error">{{ peakProminenceError }}</small>
      </div>
    </SettingsGroup>

    <SettingsGroup
      v-if="showDataSmoothing"
      id="data-smoothing"
      :title="groupTitle('data-smoothing')"
      :open="isOpen(openState, 'data-smoothing')"
      :problem="dataSmoothingProblem"
      @toggle="onToggle('data-smoothing', $event)"
    >
      <div class="field">
        <div class="field-head">
          <label for="smoothing-window">Smoothing window (frames)</label>
          <InfoPopover label="smoothing window" :text="smoothingWindowHelp" />
        </div>
        <input
          id="smoothing-window"
          v-model="smoothingWindowText"
          type="number"
          step="1"
          :min="SMOOTHING_WINDOW_RANGE.min"
          :max="SMOOTHING_WINDOW_RANGE.max"
          inputmode="numeric"
          :disabled="busy"
        />
        <small v-if="smoothingWindowError" class="error">{{ smoothingWindowError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="smoothing">Smoothing</label>
          <InfoPopover label="smoothing" :text="smoothingHelp" />
          <output class="slider-value" for="smoothing">{{ formatSmoothing(smoothing) }}</output>
        </div>
        <input
          id="smoothing"
          v-model.number="smoothing"
          type="range"
          :min="SMOOTHING_RANGE.min"
          :max="SMOOTHING_RANGE.max"
          :step="SMOOTHING_RANGE.step"
          :disabled="busy"
        />
        <small v-if="smoothingError" class="error">{{ smoothingError }}</small>
      </div>
    </SettingsGroup>

    <SettingsGroup
      v-if="showImageSmoothing"
      id="image-smoothing"
      :title="groupTitle('image-smoothing')"
      :open="isOpen(openState, 'image-smoothing')"
      :problem="imageSmoothingProblem"
      @toggle="onToggle('image-smoothing', $event)"
    >
      <div class="field">
        <div class="field-head">
          <label for="resolution">Oversampling</label>
          <InfoPopover label="oversampling" :text="resolutionHelp" />
          <output class="slider-value" for="resolution">{{ formatResolution(resolution) }}</output>
        </div>
        <input
          id="resolution"
          v-model.number="resolution"
          type="range"
          :min="RESOLUTION_RANGE.min"
          :max="RESOLUTION_RANGE.max"
          :step="RESOLUTION_RANGE.step"
          :disabled="busy"
        />
        <small v-if="resolutionError" class="error">{{ resolutionError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="interpolate">Interpolate</label>
          <InfoPopover label="interpolate" :text="interpolateHelp" />
          <output class="slider-value" for="interpolate">{{ formatInterpolate(interpolate) }}</output>
        </div>
        <input
          id="interpolate"
          v-model.number="interpolate"
          type="range"
          :min="INTERPOLATE_RANGE.min"
          :max="INTERPOLATE_RANGE.max"
          :step="INTERPOLATE_RANGE.step"
          :disabled="busy"
        />
        <small v-if="interpolateError" class="error">{{ interpolateError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="gaussian">Gaussian smoothing</label>
          <InfoPopover label="gaussian smoothing" :text="gaussianHelp" />
          <output class="slider-value" for="gaussian">{{ formatGaussian(gaussian) }}</output>
        </div>
        <input
          id="gaussian"
          v-model.number="gaussian"
          type="range"
          :min="GAUSSIAN_RANGE.min"
          :max="GAUSSIAN_RANGE.max"
          :step="GAUSSIAN_RANGE.step"
          :disabled="busy"
        />
        <small v-if="gaussianError" class="error">{{ gaussianError }}</small>
      </div>
    </SettingsGroup>

    <button type="submit" :disabled="!canSubmit || busy">{{ busy ? "Working…" : "Create frames" }}</button>
  </form>
</template>

<style scoped>
.settings {
  display: grid;
  gap: 0.75rem;
}
.field {
  display: grid;
  gap: 0.25rem;
  align-content: start;
  min-width: 0;
}
.field-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.2rem 0.35rem;
}
.field-head label {
  font-family: var(--label-font);
  font-size: var(--label-size);
}
.field input:not([type="range"]):not([type="checkbox"]),
.field select {
  width: 100%;
  box-sizing: border-box;
}
.field input[type="range"] {
  width: 100%;
  box-sizing: border-box;
  margin: 0;
}
.field input[type="checkbox"] {
  justify-self: start;
}
small {
  color: #555;
}
/* the readout of a slider sits in the label row, at the right, so that a half-width cell has all its width for the slider */
.slider-value {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  text-align: right;
}
small.error {
  color: #b00020;
}
small.notice {
  color: #8a5300;
}
button {
  padding: 0.5rem 1rem;
  font-size: 1rem;
}
</style>
