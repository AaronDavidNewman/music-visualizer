<script setup lang="ts">
import { ref } from "vue";
import FramePlayer from "./components/FramePlayer.vue";
import UploadForm from "./components/UploadForm.vue";
import { submitJob, type JobResult } from "./api";
import { formatSpacing } from "./lib/spacing";

type Status = "idle" | "busy" | "done" | "error";

const status = ref<Status>("idle");
const result = ref<JobResult | null>(null);
const errorMessage = ref("");

async function onSubmit(file: File, windowSize: number, frameRate: number, windowSpacing: number) {
  status.value = "busy";
  errorMessage.value = "";
  try {
    result.value = await submitJob(file, windowSize, frameRate, windowSpacing);
    status.value = "done";
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : "Something went wrong.";
    status.value = "error";
  }
}
</script>

<template>
  <main>
    <h1>Music Visualizer</h1>
    <UploadForm :busy="status === 'busy'" @submit="onSubmit" />

    <p v-if="status === 'busy'" class="busy" role="status">
      Uploading and creating frames… this can take a little while for long files.
    </p>
    <p v-if="status === 'error'" class="error-box" role="alert">{{ errorMessage }}</p>

    <section v-if="result" class="results">
      <h2>{{ result.file_name }}</h2>
      <ul class="summary">
        <li>Duration: {{ result.duration_seconds.toFixed(2) }} s</li>
        <li>Sample rate: {{ result.sample_rate }} Hz</li>
        <li>Window size: {{ result.window_size }}</li>
        <li>Frame rate: {{ result.frame_rate }} fps</li>
        <li>Frames: {{ result.frame_count }}</li>
        <li>Window spacing: {{ formatSpacing(result.window_spacing) }}</li>
        <li>Step: {{ Number(result.step_samples.toFixed(2)) }} samples</li>
        <li>Windows analyzed: {{ result.window_count }}</li>
      </ul>
      <p v-if="result.spacing_raised" class="notice-box" role="status">
        The window spacing was raised to {{ formatSpacing(result.window_spacing) }} so the step is one sample.
      </p>
      <FramePlayer :result="result" />
    </section>
  </main>
</template>

<style>
body {
  font-family: system-ui, sans-serif;
  margin: 0;
}
main {
  max-width: 48rem;
  margin: 0 auto;
  padding: 1.5rem 1rem 3rem;
  display: grid;
  gap: 1.5rem;
}
.busy {
  color: #333;
}
.error-box {
  color: #b00020;
  background: #fdecee;
  padding: 0.75rem 1rem;
  border-radius: 0.25rem;
}
.notice-box {
  color: #6b4200;
  background: #fff4e0;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.5rem;
  padding: 0;
  list-style: none;
}
</style>
