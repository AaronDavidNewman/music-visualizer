<script setup lang="ts">
import { ref } from "vue";
import FramePlayer from "./components/FramePlayer.vue";
import FilePicker from "./components/FilePicker.vue";
import SettingsForm from "./components/SettingsForm.vue";
import { submitJob, type JobResult, type JobSettings } from "./api";
import { DEFAULT_SAMPLE_RATE, formatSpacing } from "./utilities/spacing";
import {
  colormapLabel,
  formatBlendWidthSummary,
  formatCircleMemory,
  formatDecayRate,
  formatCircleNotes,
  formatCircleResize,
  formatCircleRadius,
  formatCircleUnit,
  formatBeatColoring,
  formatGaussian,
  formatPeakDistance,
  formatPeakProminence,
  beatColoringApplies,
  peakSettingsShown,
  noteLayoutApplies,
  noteLayoutLabel,
  gridSettingsApply,
  isCirclesType,
  formatNoteCountSummary,
  formatResolution,
  formatThresholdSummary,
  imageTypeLabel,
} from "./utilities/validation";

type Status = "idle" | "busy" | "done" | "error";

const file = ref<File | null>(null);
const fileSampleRate = ref<number>(DEFAULT_SAMPLE_RATE); // the chosen file's rate; 44.1 kHz until a file is chosen
const status = ref<Status>("idle");
const result = ref<JobResult | null>(null);
const errorMessage = ref("");

async function onSubmit(chosen: File, settings: JobSettings) {
  status.value = "busy";
  errorMessage.value = "";
  try {
    result.value = await submitJob(chosen, settings);
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
    <div class="layout">
      <div class="column">
        <FilePicker v-model:file="file" :busy="status === 'busy'" @update:sample-rate="fileSampleRate = $event" />

        <p v-if="status === 'busy'" class="busy" role="status">
          Uploading and creating frames… this can take a little while for long files.
        </p>
        <p v-if="status === 'error'" class="error-box" role="alert">{{ errorMessage }}</p>

        <section v-if="result" class="results">
          <FramePlayer :result="result" />
          <h2>{{ result.file_name }}</h2>
          <ul class="summary">
            <li>Duration: {{ result.duration_seconds.toFixed(2) }} s</li>
            <li>Sample rate: {{ result.sample_rate }} Hz</li>
            <li>Window size: {{ result.window_size }}</li>
            <li>Frame rate: {{ result.frame_rate }} fps</li>
            <li>Frames: {{ result.frame_count }}</li>
            <li>Colormap: {{ colormapLabel(result.colormap) }}</li>
            <li>Smoothing: {{ result.smoothing.toFixed(2) }}</li>
            <li>Smoothing window: {{ result.smoothing_window }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Threshold: {{ formatThresholdSummary(result.threshold) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Notes: {{ formatNoteCountSummary(result.note_count) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Interpolate: {{ result.interpolate }}</li>
            <li>Image type: {{ imageTypeLabel(result.image_type) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Oversampling: {{ formatResolution(result.resolution) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Gaussian smoothing: {{ formatGaussian(result.gaussian) }}</li>
            <template v-if="isCirclesType(result.image_type)">
              <li>Movement: {{ formatCircleUnit(result.circle_unit) }}</li>
              <li>Radius: {{ formatCircleRadius(result.circle_radius) }}</li>
              <li>Resize by volume: {{ formatCircleResize(result.circle_resize) }}</li>
              <li v-if="result.image_type === 'circles'">Memory: {{ formatCircleMemory(result.circle_memory) }}</li>
              <li>Notes: {{ formatCircleNotes(result.circle_notes) }}</li>
            </template>
            <li v-if="result.image_type === 'decay'">Decay rate: {{ formatDecayRate(result.decay_rate) }}</li>
            <li v-if="noteLayoutApplies(result.image_type)">Note layout: {{ noteLayoutLabel(result.note_layout) }}</li>
            <li v-if="beatColoringApplies(result.image_type)">Beat coloring: {{ formatBeatColoring(result.beat_coloring) }}</li>
            <li v-if="peakSettingsShown(result.image_type, result.beat_coloring)">Minimum distance: {{ formatPeakDistance(result.peak_distance) }}</li>
            <li v-if="peakSettingsShown(result.image_type, result.beat_coloring)">Prominence: {{ formatPeakProminence(result.peak_prominence) }}</li>
            <li v-if="result.image_type === 'blended'">Blend width: {{ formatBlendWidthSummary(result.blend_width) }}</li>
            <li>Window spacing: {{ formatSpacing(result.window_spacing) }}</li>
            <li>Step: {{ Number(result.step_samples.toFixed(2)) }} samples</li>
            <li>Windows analyzed: {{ result.window_count }}</li>
          </ul>
          <p v-if="result.spacing_raised" class="notice-box" role="status">
            The window spacing was raised to {{ formatSpacing(result.window_spacing) }} so the step is one sample.
          </p>
        </section>
      </div>

      <div class="column">
        <SettingsForm :busy="status === 'busy'" :file="file" :sample-rate="fileSampleRate" @submit="onSubmit" />
      </div>
    </div>
  </main>
</template>

<style>
/* the font and size of the form labels and group titles */
:root {
  --label-font: "Roboto Slab", Georgia, serif;
  --label-size: 0.9rem;
}
body {
  font-family: system-ui, sans-serif;
  margin: 0;
}
main {
  max-width: 76rem;
  margin: 0 auto;
  padding: 1.5rem 1rem 3rem;
  display: grid;
  gap: 1.5rem;
}
.layout {
  display: grid;
  gap: 1.5rem;
}
.column {
  display: grid;
  gap: 1.5rem;
  align-content: start;
  min-width: 0;
}
@media (min-width: 60rem) {
  .layout {
    grid-template-columns: minmax(0, 1fr) 30rem;
    align-items: start;
  }
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
.results {
  display: grid;
  gap: 0.75rem;
}
.results h2,
.results .summary {
  margin: 0;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.5rem;
  padding: 0;
  list-style: none;
}
</style>
