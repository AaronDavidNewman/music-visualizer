<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  BRIGHTNESS_RANGE,
  DEFAULT_BRIGHTNESS,
  DEFAULT_ENERGY,
  DEFAULT_SMOOTHING,
  DEFAULT_WINDOW_SIZE,
  ENERGY_RANGE,
  SMOOTHING_RANGE,
  WINDOW_SIZES,
  formatSmoothing,
  validateBrightness,
  validateEnergy,
  validateFile,
  validateFrameRate,
  validateSmoothing,
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
  brightnessHelp,
  energyHelp,
  frameRateHelp,
  smoothingHelp,
  spacingHelp,
  windowSizeHelp,
} from "../utilities/help";
import InfoPopover from "./InfoPopover.vue";
import type { JobSettings } from "../api";

const props = defineProps<{ busy: boolean; file: File | null; sampleRate: number }>();
const emit = defineEmits<{ submit: [file: File, settings: JobSettings] }>();

const windowSize = ref<number>(DEFAULT_WINDOW_SIZE);
const frameRateText = ref("30");
const brightnessText = ref(String(DEFAULT_BRIGHTNESS));
const energyText = ref(String(DEFAULT_ENERGY));
const smoothing = ref<number>(DEFAULT_SMOOTHING);
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
const brightnessError = computed(() => validateBrightness(brightnessText.value));
const energyError = computed(() => validateEnergy(energyText.value));
const smoothingError = computed(() => validateSmoothing(smoothing.value));
const canSubmit = computed(
  () =>
    !fileError.value &&
    !windowError.value &&
    !frameRateError.value &&
    !spacingError.value &&
    !brightnessError.value &&
    !energyError.value &&
    !smoothingError.value,
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
    brightness: Number(brightnessText.value),
    energy: Number(energyText.value),
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

    <!-- What the user sees is Brightness then Saturation. The values keep the API names: Brightness is the
         `energy` setting (a root, 1 to 8, on the frame's loudness) and Saturation is the `brightness` setting
         (a root, 2 to 100, on each tile's note level). -->
    <div class="field-row">
      <div class="field">
        <div class="field-head">
          <label for="brightness">Brightness</label>
          <InfoPopover label="brightness" :text="energyHelp" />
        </div>
        <input
          id="brightness"
          v-model="energyText"
          type="number"
          step="1"
          :min="ENERGY_RANGE.min"
          :max="ENERGY_RANGE.max"
          inputmode="numeric"
          :disabled="busy"
        />
        <small v-if="energyError" class="error">{{ energyError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="saturation">Saturation</label>
          <InfoPopover label="saturation" :text="brightnessHelp" />
        </div>
        <input
          id="saturation"
          v-model="brightnessText"
          type="number"
          step="1"
          :min="BRIGHTNESS_RANGE.min"
          :max="BRIGHTNESS_RANGE.max"
          inputmode="numeric"
          :disabled="busy"
        />
        <small v-if="brightnessError" class="error">{{ brightnessError }}</small>
      </div>
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
