<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  BRIGHTNESS_RANGE,
  DEFAULT_BRIGHTNESS,
  DEFAULT_ENERGY,
  DEFAULT_SMOOTHING,
  DEFAULT_SMOOTHING_WINDOW,
  DEFAULT_STEP,
  DEFAULT_THRESHOLD,
  DEFAULT_WINDOW_SIZE,
  ENERGY_RANGE,
  HUE_SCALE,
  HUE_STEPS,
  NA_STEP,
  SMOOTHING_RANGE,
  SMOOTHING_WINDOW_RANGE,
  THRESHOLD_RANGE,
  UNIT_SCALE,
  UNIT_STEPS,
  WINDOW_SIZES,
  formatSmoothing,
  formatThreshold,
  levelLabel,
  stepToNumber,
  validateBrightness,
  validateEnergy,
  validateFile,
  validateFrameRate,
  validateSmoothing,
  validateSmoothingWindow,
  validateStep,
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
  brightnessHelp,
  brightnessStepHelp,
  energyHelp,
  frameRateHelp,
  hueStepHelp,
  saturationStepHelp,
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
const brightnessText = ref(String(DEFAULT_BRIGHTNESS));
const energyText = ref(String(DEFAULT_ENERGY));
// The step choices are kept as the text of the selected option: "N/A" or a number.
const hueStepText = ref(DEFAULT_STEP);
const saturationStepText = ref(DEFAULT_STEP);
const brightnessStepText = ref(DEFAULT_STEP);
const smoothing = ref<number>(DEFAULT_SMOOTHING);
const smoothingWindowText = ref(String(DEFAULT_SMOOTHING_WINDOW));
const threshold = ref<number>(DEFAULT_THRESHOLD);
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
const smoothingWindowError = computed(() => validateSmoothingWindow(smoothingWindowText.value));
const thresholdError = computed(() => validateThreshold(threshold.value));
const hueStepError = computed(() => validateStep(hueStepText.value, HUE_STEPS, "hue"));
const saturationStepError = computed(() => validateStep(saturationStepText.value, UNIT_STEPS, "saturation"));
const brightnessStepError = computed(() => validateStep(brightnessStepText.value, UNIT_STEPS, "brightness"));
const canSubmit = computed(
  () =>
    !fileError.value &&
    !windowError.value &&
    !frameRateError.value &&
    !spacingError.value &&
    !brightnessError.value &&
    !energyError.value &&
    !smoothingError.value &&
    !smoothingWindowError.value &&
    !thresholdError.value &&
    !hueStepError.value &&
    !saturationStepError.value &&
    !brightnessStepError.value,
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
    hueStep: stepToNumber(hueStepText.value),
    saturationStep: stepToNumber(saturationStepText.value),
    brightnessStep: stepToNumber(brightnessStepText.value),
    threshold: threshold.value,
    smoothingWindow: Number(smoothingWindowText.value),
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

    <!-- Steps round a finished value to evenly spaced levels; N/A leaves it smooth. The API fields are
         `hue_step`, `saturation_step` and `brightness_step`. -->
    <div class="field-row">
      <div class="field">
        <div class="field-head">
          <label for="hue-step">Hue steps</label>
          <InfoPopover label="hue steps" :text="hueStepHelp" />
        </div>
        <select id="hue-step" v-model="hueStepText" :disabled="busy">
          <option :value="NA_STEP">{{ NA_STEP }}</option>
          <option v-for="step in HUE_STEPS" :key="step" :value="String(step)">{{ step }}</option>
        </select>
        <output class="level-count" for="hue-step">{{ levelLabel(hueStepText, HUE_SCALE) }}</output>
        <small v-if="hueStepError" class="error">{{ hueStepError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="saturation-step">Saturation steps</label>
          <InfoPopover label="saturation steps" :text="saturationStepHelp" />
        </div>
        <select id="saturation-step" v-model="saturationStepText" :disabled="busy">
          <option :value="NA_STEP">{{ NA_STEP }}</option>
          <option v-for="step in UNIT_STEPS" :key="step" :value="String(step)">{{ step }}</option>
        </select>
        <output class="level-count" for="saturation-step">{{ levelLabel(saturationStepText, UNIT_SCALE) }}</output>
        <small v-if="saturationStepError" class="error">{{ saturationStepError }}</small>
      </div>

      <div class="field">
        <div class="field-head">
          <label for="brightness-step">Brightness steps</label>
          <InfoPopover label="brightness steps" :text="brightnessStepHelp" />
        </div>
        <select id="brightness-step" v-model="brightnessStepText" :disabled="busy">
          <option :value="NA_STEP">{{ NA_STEP }}</option>
          <option v-for="step in UNIT_STEPS" :key="step" :value="String(step)">{{ step }}</option>
        </select>
        <output class="level-count" for="brightness-step">{{ levelLabel(brightnessStepText, UNIT_SCALE) }}</output>
        <small v-if="brightnessStepError" class="error">{{ brightnessStepError }}</small>
      </div>
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
          :disabled="busy"
        />
        <output class="slider-value slider-value-wide" for="threshold">{{ formatThreshold(threshold) }}</output>
      </span>
      <small v-if="thresholdError" class="error">{{ thresholdError }}</small>
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
.level-count {
  color: #555;
  font-size: 0.85em;
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
