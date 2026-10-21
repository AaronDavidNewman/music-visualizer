<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  BLEND_WIDTH_RANGE,
  COLORMAPS,
  DEFAULT_COLORMAP,
  DEFAULT_BLEND_WIDTH,
  DEFAULT_CIRCLE_MEMORY,
  DEFAULT_CIRCLE_NOTES,
  DEFAULT_CIRCLE_RESIZE,
  DEFAULT_CIRCLE_RADIUS,
  DEFAULT_CIRCLE_UNIT,
  DEFAULT_IMAGE_TYPE,
  DEFAULT_GAUSSIAN,
  DEFAULT_INTERPOLATE,
  DEFAULT_NOTE_COUNT,
  DEFAULT_RESOLUTION,
  DEFAULT_SMOOTHING,
  DEFAULT_SMOOTHING_WINDOW,
  DEFAULT_THRESHOLD,
  DEFAULT_WINDOW_SIZE,
  CIRCLE_MEMORY_RANGE,
  CIRCLE_NOTES_RANGE,
  CIRCLE_RADIUS_RANGE,
  CIRCLE_UNIT_RANGE,
  IMAGE_TYPES,
  GAUSSIAN_RANGE,
  INTERPOLATE_RANGE,
  NOTE_COUNT_RANGE,
  RESOLUTION_RANGE,
  SMOOTHING_RANGE,
  SMOOTHING_WINDOW_RANGE,
  THRESHOLD_RANGE,
  WINDOW_SIZES,
  formatBlendWidth,
  formatCircleMemory,
  formatCircleNotes,
  formatCircleResize,
  formatCircleRadius,
  formatCircleUnit,
  formatGaussian,
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
  validateCircleRadius,
  validateCircleUnit,
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
  blendWidthHelp,
  colormapHelp,
  frameRateHelp,
  circleMemoryHelp,
  circleNotesHelp,
  circleResizeHelp,
  circleRadiusHelp,
  circleUnitHelp,
  imageTypeHelp,
  gaussianHelp,
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
const blendWidth = ref<number>(DEFAULT_BLEND_WIDTH);
const resolution = ref<number>(DEFAULT_RESOLUTION);
const noteCount = ref<number>(DEFAULT_NOTE_COUNT);
const interpolate = ref<number>(DEFAULT_INTERPOLATE);
const gaussian = ref<number>(DEFAULT_GAUSSIAN);
const circleUnit = ref<number>(DEFAULT_CIRCLE_UNIT);
const circleMemory = ref<number>(DEFAULT_CIRCLE_MEMORY);
const circleNotes = ref<number>(DEFAULT_CIRCLE_NOTES);
const circleRadius = ref<number>(DEFAULT_CIRCLE_RADIUS);
const circleResize = ref<boolean>(DEFAULT_CIRCLE_RESIZE);
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
const gaussianError = computed(() => validateGaussian(gaussian.value));
const circleUnitError = computed(() => validateCircleUnit(circleUnit.value));
const circleMemoryError = computed(() => validateCircleMemory(circleMemory.value));
const circleNotesError = computed(() => validateCircleNotes(circleNotes.value));
const circleRadiusError = computed(() => validateCircleRadius(circleRadius.value));
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
    !gaussianError.value &&
    !circleUnitError.value &&
    !circleMemoryError.value &&
    !circleNotesError.value &&
    !circleRadiusError.value,
);

// The groups (feature 020). The group of the chosen image type follows the Image type group; a control the type does not use is not
// shown. Every value stays in its ref, so it is kept when a group is folded or the type is changed, and is still sent.
const TYPE_GROUP_IDS = ["tiles", "contour", "blended", "circles", "circles_paint"];
const shownGroups = computed(() => groupsFor(imageType.value));
const typeGroup = computed(() => shownGroups.value.find((id) => TYPE_GROUP_IDS.includes(id)));
const showImageSmoothing = computed(() => shownGroups.value.includes("image-smoothing"));
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
    (inTypeGroup("blend-width") && !!blendWidthError.value) ||
    (inTypeGroup("circle-unit") && !!circleUnitError.value) ||
    (inTypeGroup("circle-radius") && !!circleRadiusError.value) ||
    (inTypeGroup("circle-memory") && !!circleMemoryError.value) ||
    (inTypeGroup("circle-notes") && !!circleNotesError.value),
);
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
    blendWidth: blendWidth.value,
    colormap: colormap.value,
    resolution: resolution.value,
    noteCount: noteCount.value,
    interpolate: interpolate.value,
    gaussian: gaussian.value,
    circleUnit: circleUnit.value,
    circleMemory: circleMemory.value,
    circleNotes: circleNotes.value,
    circleRadius: circleRadius.value,
    circleResize: circleResize.value,
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

    <!-- the group of the chosen image type: Tiles, Contour, Blended Tiles or Circles; a control that the type does not use is not shown -->
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

      <div v-if="inTypeGroup('blend-width')" class="field">
        <div class="field-head">
          <label for="blend-width">Blend width</label>
          <InfoPopover label="blend width" :text="blendWidthHelp" />
          <output class="slider-value" for="blend-width">{{ formatBlendWidth(blendWidth) }}</output>
        </div>
        <input
          id="blend-width"
          v-model.number="blendWidth"
          type="range"
          :min="BLEND_WIDTH_RANGE.min"
          :max="BLEND_WIDTH_RANGE.max"
          :step="BLEND_WIDTH_RANGE.step"
          :disabled="busy"
        />
        <small v-if="blendWidthError" class="error">{{ blendWidthError }}</small>
      </div>

      <div v-if="inTypeGroup('circle-unit')" class="field">
        <div class="field-head">
          <label for="circle-unit">Movement</label>
          <InfoPopover label="circle movement" :text="circleUnitHelp" />
          <output class="slider-value" for="circle-unit">{{ formatCircleUnit(circleUnit) }}</output>
        </div>
        <input
          id="circle-unit"
          v-model.number="circleUnit"
          type="range"
          :min="CIRCLE_UNIT_RANGE.min"
          :max="CIRCLE_UNIT_RANGE.max"
          :step="CIRCLE_UNIT_RANGE.step"
          :disabled="busy"
        />
        <small v-if="circleUnitError" class="error">{{ circleUnitError }}</small>
      </div>

      <div v-if="inTypeGroup('circle-radius')" class="field">
        <div class="field-head">
          <label for="circle-radius">Radius</label>
          <InfoPopover label="circle radius" :text="circleRadiusHelp" />
          <output class="slider-value" for="circle-radius">{{ formatCircleRadius(circleRadius) }}</output>
        </div>
        <input
          id="circle-radius"
          v-model.number="circleRadius"
          type="range"
          :min="CIRCLE_RADIUS_RANGE.min"
          :max="CIRCLE_RADIUS_RANGE.max"
          :step="CIRCLE_RADIUS_RANGE.step"
          :disabled="busy"
        />
        <small v-if="circleRadiusError" class="error">{{ circleRadiusError }}</small>
      </div>

      <div v-if="inTypeGroup('circle-resize')" class="field">
        <div class="field-head">
          <label for="circle-resize">Resize by volume</label>
          <InfoPopover label="resize by volume" :text="circleResizeHelp" />
          <output class="slider-value" for="circle-resize">{{ formatCircleResize(circleResize) }}</output>
        </div>
        <input id="circle-resize" v-model="circleResize" type="checkbox" :disabled="busy" />
      </div>

      <div v-if="inTypeGroup('circle-memory')" class="field">
        <div class="field-head">
          <label for="circle-memory">Memory</label>
          <InfoPopover label="circle memory" :text="circleMemoryHelp" />
          <output class="slider-value" for="circle-memory">{{ formatCircleMemory(circleMemory) }}</output>
        </div>
        <input
          id="circle-memory"
          v-model.number="circleMemory"
          type="range"
          :min="CIRCLE_MEMORY_RANGE.min"
          :max="CIRCLE_MEMORY_RANGE.max"
          :step="CIRCLE_MEMORY_RANGE.step"
          :disabled="busy"
        />
        <small v-if="circleMemoryError" class="error">{{ circleMemoryError }}</small>
      </div>

      <div v-if="inTypeGroup('circle-notes')" class="field">
        <div class="field-head">
          <label for="circle-notes">Notes</label>
          <InfoPopover label="circle notes" :text="circleNotesHelp" />
          <output class="slider-value" for="circle-notes">{{ formatCircleNotes(circleNotes) }}</output>
        </div>
        <input
          id="circle-notes"
          v-model.number="circleNotes"
          type="range"
          :min="CIRCLE_NOTES_RANGE.min"
          :max="CIRCLE_NOTES_RANGE.max"
          :step="CIRCLE_NOTES_RANGE.step"
          :disabled="busy"
        />
        <small v-if="circleNotesError" class="error">{{ circleNotesError }}</small>
      </div>
    </SettingsGroup>

    <SettingsGroup
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
