<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  DEFAULT_WINDOW_SIZE,
  FRAME_RATE_RANGE,
  WINDOW_SIZES,
  validateFile,
  validateFrameRate,
  validateWindowSize,
} from "../lib/validation";
import {
  DEFAULT_SAMPLE_RATE,
  defaultSpacing,
  formatSpacing,
  isBelowMinimum,
  minimumMessage,
  stepMilliseconds,
  stepSamples,
  validateSpacing,
} from "../lib/spacing";
import { readSampleRate } from "../lib/wavHeader";

defineProps<{ busy: boolean }>();
const emit = defineEmits<{ submit: [file: File, windowSize: number, frameRate: number, windowSpacing: number] }>();

const file = ref<File | null>(null);
const windowSize = ref<number>(DEFAULT_WINDOW_SIZE);
const frameRateText = ref("30");
const fileSampleRate = ref(DEFAULT_SAMPLE_RATE); // the chosen file's rate; 44.1 kHz until a file is chosen
const spacingText = ref(defaultSpacingText(DEFAULT_SAMPLE_RATE, frameRateText.value, windowSize.value) ?? "");

function defaultSpacingText(sampleRate: number, frameRate: string, size: number): string | null {
  const spacing = defaultSpacing(sampleRate, frameRate, size);
  return spacing === null ? null : formatSpacing(spacing);
}

// The default spacing follows the window size, frame rate and file: any change replaces what is in the field.
// If the frame rate is not usable yet (empty, partly typed), the field is left alone.
watch([windowSize, frameRateText, fileSampleRate, file], () => {
  const text = defaultSpacingText(fileSampleRate.value, frameRateText.value, windowSize.value);
  if (text !== null) spacingText.value = text;
});

const fileError = computed(() => validateFile(file.value));
const windowError = computed(() => validateWindowSize(windowSize.value));
const frameRateError = computed(() => validateFrameRate(frameRateText.value));
const spacingError = computed(() => validateSpacing(spacingText.value));
const canSubmit = computed(
  () => !fileError.value && !windowError.value && !frameRateError.value && !spacingError.value,
);

const belowMinimum = computed(
  () => !spacingError.value && isBelowMinimum(Number(spacingText.value), windowSize.value),
);

const stepHint = computed(() => {
  if (spacingError.value) return "";
  const spacing = Number(spacingText.value);
  const samples = stepSamples(spacing, windowSize.value);
  const ms = stepMilliseconds(spacing, windowSize.value, fileSampleRate.value);
  return `Step between windows: ${Number(samples.toFixed(2))} samples (${ms.toFixed(1)} ms).`;
});

function formatSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

let latestFile = 0;

async function onFile(event: Event) {
  const chosen = (event.target as HTMLInputElement).files?.[0] ?? null;
  file.value = chosen;
  const ticket = ++latestFile;
  const rate = chosen ? await readSampleRate(chosen) : null;
  if (ticket === latestFile) fileSampleRate.value = rate ?? DEFAULT_SAMPLE_RATE; // ignore a stale answer
}

function onSubmit() {
  if (!canSubmit.value || !file.value) return;
  emit("submit", file.value, windowSize.value, Number(frameRateText.value), Number(spacingText.value));
}
</script>

<template>
  <form class="upload" @submit.prevent="onSubmit">
    <label class="field">
      <span>Audio file</span>
      <input type="file" accept=".wav,audio/wav,audio/x-wav" :disabled="busy" @change="onFile" />
      <small v-if="file">{{ file.name }} ({{ formatSize(file.size) }})</small>
      <small v-else>Choose a .wav file.</small>
      <small v-if="file && fileError" class="error">{{ fileError }}</small>
    </label>

    <label class="field">
      <span>Window size (samples)</span>
      <select v-model.number="windowSize" :disabled="busy">
        <option v-for="size in WINDOW_SIZES" :key="size" :value="size">{{ size }}</option>
      </select>
      <small :class="{ error: windowError }">
        {{ windowError ?? "Larger windows separate low notes better but blur changes over time." }}
      </small>
    </label>

    <label class="field">
      <span>Frame rate (frames per second)</span>
      <input v-model="frameRateText" type="number" step="any" inputmode="decimal" :disabled="busy" />
      <small :class="{ error: frameRateError }">
        {{ frameRateError ?? `${FRAME_RATE_RANGE.min} to ${FRAME_RATE_RANGE.max}.` }}
      </small>
    </label>

    <label class="field">
      <span>Window spacing (× window size)</span>
      <input v-model="spacingText" type="number" step="any" inputmode="decimal" :disabled="busy" />
      <small v-if="spacingError" class="error">{{ spacingError }}</small>
      <small v-else-if="belowMinimum" class="notice">{{ minimumMessage(windowSize) }}</small>
      <small v-else>{{ stepHint }}</small>
    </label>

    <button type="submit" :disabled="!canSubmit || busy">{{ busy ? "Working…" : "Create frames" }}</button>
  </form>
</template>

<style scoped>
.upload {
  display: grid;
  gap: 1rem;
  max-width: 28rem;
}
.field {
  display: grid;
  gap: 0.25rem;
}
.field span {
  font-weight: 600;
}
small {
  color: #555;
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
