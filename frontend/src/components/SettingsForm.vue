<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  BLEND_WIDTH_RANGE,
  COLORMAPS,
  DEFAULT_COLORMAP,
  DEFAULT_BLEND_WIDTH,
  DEFAULT_CIRCLE_MEMORY,
  DEFAULT_CIRCLE_NOTES,
  DEFAULT_CIRCLE_SIZE,
  DEFAULT_CIRCLE_UNIT,
  DEFAULT_IMAGE_TYPE,
  DEFAULT_INTERPOLATE,
  DEFAULT_NOTE_COUNT,
  DEFAULT_RESOLUTION,
  DEFAULT_SMOOTHING,
  DEFAULT_SMOOTHING_WINDOW,
  DEFAULT_THRESHOLD,
  DEFAULT_WINDOW_SIZE,
  CIRCLE_MEMORY_RANGE,
  CIRCLE_NOTES_RANGE,
  CIRCLE_SIZE_RANGE,
  CIRCLE_UNIT_RANGE,
  IMAGE_TYPES,
  INTERPOLATE_RANGE,
  NOTE_COUNT_RANGE,
  RESOLUTION_RANGE,
  SMOOTHING_RANGE,
  SMOOTHING_WINDOW_RANGE,
  THRESHOLD_RANGE,
  WINDOW_SIZES,
  blendWidthApplies,
  gridSettingsApply,
  formatBlendWidth,
  formatCircleMemory,
  formatCircleNotes,
  formatCircleSize,
  formatCircleUnit,
  formatInterpolate,
  formatNoteCount,
  formatResolution,
  formatSmoothing,
  formatThreshold,
  validateBlendWidth,
  validateColormap,
  validateFile,
  validateFrameRate,
  validateCircleMemory,
  validateCircleNotes,
  validateCircleSize,
  validateCircleUnit,
  validateImageType,
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
  blendWidthHelp,
  colormapHelp,
  frameRateHelp,
  circleMemoryHelp,
  circleNotesHelp,
  circleSizeHelp,
  circleUnitHelp,
  imageTypeHelp,
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
import type { JobSettings } from "../api";

const props = defineProps<{ busy: boolean; file: File | null; sampleRate: number }>();
const emit = defineEmits<{ submit: [file: File, settings: JobSettings] }>();

const windowSize = ref<number>(DEFAULT_WINDOW_SIZE);
const frameRateText = ref("30");
const colormap = ref<string>(DEFAULT_COLORMAP);
const smoothing = ref<number>(DEFAULT_SMOOTHING);
const smoothingWindowText = ref(String(DEFAULT_SMOOTHING_WINDOW));
const threshold = ref<number>(DEFAULT_THRESHOLD);
const imageType = ref<string>(DEFAULT_IMAGE_TYPE);
const blendWidth = ref<number>(DEFAULT_BLEND_WIDTH);
const resolution = ref<number>(DEFAULT_RESOLUTION);
const noteCount = ref<number>(DEFAULT_NOTE_COUNT);
const interpolate = ref<number>(DEFAULT_INTERPOLATE);
const circleUnit = ref<number>(DEFAULT_CIRCLE_UNIT);
const circleMemory = ref<number>(DEFAULT_CIRCLE_MEMORY);
const circleNotes = ref<number>(DEFAULT_CIRCLE_NOTES);
const circleSize = ref<number>(DEFAULT_CIRCLE_SIZE);
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
const blendWidthError = computed(() => validateBlendWidth(blendWidth.value));
const colormapError = computed(() => validateColormap(colormap.value));
const resolutionError = computed(() => validateResolution(resolution.value));
const noteCountError = computed(() => validateNoteCount(noteCount.value));
const interpolateError = computed(() => validateInterpolate(interpolate.value));
const circleUnitError = computed(() => validateCircleUnit(circleUnit.value));
const circleMemoryError = computed(() => validateCircleMemory(circleMemory.value));
const circleNotesError = computed(() => validateCircleNotes(circleNotes.value));
const circleSizeError = computed(() => validateCircleSize(circleSize.value));
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
    !blendWidthError.value &&
    !colormapError.value &&
    !resolutionError.value &&
    !noteCountError.value &&
    !interpolateError.value &&
    !circleUnitError.value &&
    !circleMemoryError.value &&
    !circleNotesError.value &&
    !circleSizeError.value,
);

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
    blendWidth: blendWidth.value,
    colormap: colormap.value,
    resolution: resolution.value,
    noteCount: noteCount.value,
    interpolate: interpolate.value,
    circleUnit: circleUnit.value,
    circleMemory: circleMemory.value,
    circleNotes: circleNotes.value,
    circleSize: circleSize.value,
    smoothing: Math.round(smoothing.value * 100) / 100,
  });
}
</script>

<template>
  <form class="settings" @submit.prevent="onSubmit">
    <div class="field-row">
      <div class="field">
        <div class="field-head">
          <label for="window-size">Window size (samples)</label>
          <InfoPopover label="window size" :text="windowSizeHelp" />
        </div>
        <select id="window-size" v-model.number="windowSize" :disabled="busy">
          <option v-for="size in WINDOW_SIZES" :key="size" :value="size">{{ size }}</option>
        </select>
        <small v-if="windowError" class="error">{{ windowError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="frame-rate">Frame rate (frames per second)</label>
          <InfoPopover label="frame rate" :text="frameRateHelp" />
        </div>
        <input id="frame-rate" v-model="frameRateText" type="number" step="any" inputmode="decimal" :disabled="busy" />
        <small v-if="frameRateError" class="error">{{ frameRateError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="window-spacing">Window spacing (× window size)</label>
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
    </div>

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
      </div>
      <span class="slider-row">
        <input
          id="smoothing"
          v-model.number="smoothing"
          type="range"
          :min="SMOOTHING_RANGE.min"
          :max="SMOOTHING_RANGE.max"
          :step="SMOOTHING_RANGE.step"
          :disabled="busy"
        />
        <output class="slider-value" for="smoothing">{{ formatSmoothing(smoothing) }}</output>
      </span>
      <small v-if="smoothingError" class="error">{{ smoothingError }}</small>
    </div>

    <div class="field">
      <div class="field-head">
        <label for="threshold">Threshold</label>
        <InfoPopover label="threshold" :text="thresholdHelp" />
      </div>
      <span class="slider-row">
        <input
          id="threshold"
          v-model.number="threshold"
          type="range"
          :min="THRESHOLD_RANGE.min"
          :max="THRESHOLD_RANGE.max"
          :step="THRESHOLD_RANGE.step"
          :disabled="busy || !gridSettingsApply(imageType)"
        />
        <output class="slider-value slider-value-wide" for="threshold">{{ formatThreshold(threshold) }}</output>
      </span>
      <small v-if="thresholdError" class="error">{{ thresholdError }}</small>
    </div>

    <div class="field">
      <div class="field-head">
        <label for="notes">Notes</label>
        <InfoPopover label="notes" :text="noteCountHelp" />
      </div>
      <span class="slider-row">
        <input
          id="notes"
          v-model.number="noteCount"
          type="range"
          :min="NOTE_COUNT_RANGE.min"
          :max="NOTE_COUNT_RANGE.max"
          :step="NOTE_COUNT_RANGE.step"
          :disabled="busy || !gridSettingsApply(imageType)"
        />
        <output class="slider-value slider-value-wide" for="notes">{{ formatNoteCount(noteCount) }}</output>
      </span>
      <small v-if="noteCountError" class="error">{{ noteCountError }}</small>
    </div>

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

    <div class="field">
      <div class="field-head">
        <label for="blend-width">Blend width</label>
        <InfoPopover label="blend width" :text="blendWidthHelp" />
      </div>
      <span class="slider-row">
        <input
          id="blend-width"
          v-model.number="blendWidth"
          type="range"
          :min="BLEND_WIDTH_RANGE.min"
          :max="BLEND_WIDTH_RANGE.max"
          :step="BLEND_WIDTH_RANGE.step"
          :disabled="busy || !blendWidthApplies(imageType)"
        />
        <output class="slider-value slider-value-wide" for="blend-width">{{ formatBlendWidth(blendWidth) }}</output>
      </span>
      <small v-if="blendWidthError" class="error">{{ blendWidthError }}</small>
    </div>

    <template v-if="imageType === 'circles'">
      <div class="field">
        <div class="field-head">
          <label for="circle-unit">Unit</label>
          <InfoPopover label="circle unit" :text="circleUnitHelp" />
        </div>
        <span class="slider-row">
          <input
            id="circle-unit"
            v-model.number="circleUnit"
            type="range"
            :min="CIRCLE_UNIT_RANGE.min"
            :max="CIRCLE_UNIT_RANGE.max"
            :step="CIRCLE_UNIT_RANGE.step"
            :disabled="busy"
          />
          <output class="slider-value slider-value-wide" for="circle-unit">{{ formatCircleUnit(circleUnit) }}</output>
        </span>
        <small v-if="circleUnitError" class="error">{{ circleUnitError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="circle-size">Size</label>
          <InfoPopover label="circle size" :text="circleSizeHelp" />
        </div>
        <span class="slider-row">
          <input
            id="circle-size"
            v-model.number="circleSize"
            type="range"
            :min="CIRCLE_SIZE_RANGE.min"
            :max="CIRCLE_SIZE_RANGE.max"
            :step="CIRCLE_SIZE_RANGE.step"
            :disabled="busy"
          />
          <output class="slider-value slider-value-wide" for="circle-size">{{ formatCircleSize(circleSize) }}</output>
        </span>
        <small v-if="circleSizeError" class="error">{{ circleSizeError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="circle-memory">Memory</label>
          <InfoPopover label="circle memory" :text="circleMemoryHelp" />
        </div>
        <span class="slider-row">
          <input
            id="circle-memory"
            v-model.number="circleMemory"
            type="range"
            :min="CIRCLE_MEMORY_RANGE.min"
            :max="CIRCLE_MEMORY_RANGE.max"
            :step="CIRCLE_MEMORY_RANGE.step"
            :disabled="busy"
          />
          <output class="slider-value slider-value-wide" for="circle-memory">{{ formatCircleMemory(circleMemory) }}</output>
        </span>
        <small v-if="circleMemoryError" class="error">{{ circleMemoryError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="circle-notes">Circles per frame</label>
          <InfoPopover label="circles per frame" :text="circleNotesHelp" />
        </div>
        <span class="slider-row">
          <input
            id="circle-notes"
            v-model.number="circleNotes"
            type="range"
            :min="CIRCLE_NOTES_RANGE.min"
            :max="CIRCLE_NOTES_RANGE.max"
            :step="CIRCLE_NOTES_RANGE.step"
            :disabled="busy"
          />
          <output class="slider-value slider-value-wide" for="circle-notes">{{ formatCircleNotes(circleNotes) }}</output>
        </span>
        <small v-if="circleNotesError" class="error">{{ circleNotesError }}</small>
      </div>
    </template>

    <div class="field">
      <div class="field-head">
        <label for="resolution">Resolution</label>
        <InfoPopover label="resolution" :text="resolutionHelp" />
      </div>
      <span class="slider-row">
        <input
          id="resolution"
          v-model.number="resolution"
          type="range"
          :min="RESOLUTION_RANGE.min"
          :max="RESOLUTION_RANGE.max"
          :step="RESOLUTION_RANGE.step"
          :disabled="busy || !gridSettingsApply(imageType)"
        />
        <output class="slider-value slider-value-wide" for="resolution">{{ formatResolution(resolution) }}</output>
      </span>
      <small v-if="resolutionError" class="error">{{ resolutionError }}</small>
    </div>

    <div class="field">
      <div class="field-head">
        <label for="interpolate">Interpolate</label>
        <InfoPopover label="interpolate" :text="interpolateHelp" />
      </div>
      <span class="slider-row">
        <input
          id="interpolate"
          v-model.number="interpolate"
          type="range"
          :min="INTERPOLATE_RANGE.min"
          :max="INTERPOLATE_RANGE.max"
          :step="INTERPOLATE_RANGE.step"
          :disabled="busy || !gridSettingsApply(imageType)"
        />
        <output class="slider-value slider-value-wide" for="interpolate">{{ formatInterpolate(interpolate) }}</output>
      </span>
      <small v-if="interpolateError" class="error">{{ interpolateError }}</small>
    </div>

    <button type="submit" :disabled="!canSubmit || busy">{{ busy ? "Working…" : "Create frames" }}</button>
  </form>
</template>

<style scoped>
.settings {
  display: grid;
  gap: 1rem;
}
.field-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr));
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
  align-items: flex-start;
  gap: 0.35rem;
}
.field-head label {
  font-weight: 600;
}
.field input:not([type="range"]),
.field select {
  width: 100%;
  box-sizing: border-box;
}
small {
  color: #555;
}
.slider-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.slider-row input {
  flex: 1;
}
.slider-value {
  min-width: 3rem;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.slider-value-wide {
  min-width: 9rem;
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
