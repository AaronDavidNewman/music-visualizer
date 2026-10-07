<script setup lang="ts">
import { computed } from "vue";
import { validateFile } from "../utilities/validation";
import { DEFAULT_SAMPLE_RATE } from "../utilities/spacing";
import { readSampleRate } from "../utilities/wavHeader";

const props = defineProps<{ busy: boolean; file: File | null }>();
const emit = defineEmits<{
  "update:file": [file: File | null];
  "update:sampleRate": [hz: number];
}>();

function formatSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

let latestFile = 0;

async function onFile(event: Event) {
  const chosen = (event.target as HTMLInputElement).files?.[0] ?? null;
  emit("update:file", chosen);
  const ticket = ++latestFile;
  const rate = chosen ? await readSampleRate(chosen) : null;
  if (ticket === latestFile) emit("update:sampleRate", rate ?? DEFAULT_SAMPLE_RATE); // ignore a stale answer
}

const fileError = computed(() => validateFile(props.file));
</script>

<template>
  <label class="field">
    <span>Audio file</span>
    <input type="file" accept=".wav,audio/wav,audio/x-wav" :disabled="busy" @change="onFile" />
    <small v-if="file" class="name">{{ file.name }} ({{ formatSize(file.size) }})</small>
    <small v-else>Choose a .wav file.</small>
    <small v-if="file && fileError" class="error">{{ fileError }}</small>
  </label>
</template>

<style scoped>
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
small.name {
  overflow-wrap: anywhere;
}
small.error {
  color: #b00020;
}
</style>
