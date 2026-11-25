<script setup lang="ts">
import { ref } from "vue";
import FramePlayer from "./components/FramePlayer.vue";
import VideoExport from "./components/VideoExport.vue";
import FilePicker from "./components/FilePicker.vue";
import SettingsForm from "./components/SettingsForm.vue";
import { submitJob, type JobResult, type JobSettings } from "./api";
import {
  colormapLabel,
  formatDecayAmount,
  formatChromaticRate,
  formatDecayRate,
  decayRateApplies,
  isChromaticType,
  formatPolarNotes,
  formatPolychordCopies,
  formatPolychordNotes,
  formatPolychordRotation,
  formatSpirographFade,
  formatSpirographHistory,
  formatSpirographNotes,
  isPolarType,
  isPolychordType,
  isSpirographType,
  formatWaveCount,
  formatBeatColoring,
  formatExtraNotes,
  usesHeldNotes,
  formatExportObj,
  usesObjExport,
  formatGaussian,
  formatPeakDistance,
  beatColoringApplies,
  peakSettingsShown,
  noteLayoutApplies,
  noteLayoutLabel,
  gridSettingsApply,
  formatNoteCountSummary,
  formatResolution,
  formatThresholdSummary,
  imageTypeLabel,
} from "./utilities/validation";

type Status = "idle" | "busy" | "done" | "error";

const file = ref<File | null>(null);
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
        <FilePicker v-model:file="file" :busy="status === 'busy'" />

        <p v-if="status === 'busy'" class="busy" role="status">
          Uploading and creating frames… this can take a little while for long files.
        </p>
        <p v-if="status === 'error'" class="error-box" role="alert">{{ errorMessage }}</p>

        <section v-if="result" class="results">
          <FramePlayer :result="result" />
          <VideoExport :result="result" />
          <p v-if="result.obj_url" class="obj-download"><a :href="result.obj_url" download>Download 3D files (.zip)</a></p>
          <h2>{{ result.file_name }}</h2>
          <ul class="summary">
            <li>Duration: {{ result.duration_seconds.toFixed(2) }} s</li>
            <li>Sample rate: {{ result.sample_rate }} Hz</li>
            <li>Window size: {{ result.window_size }}</li>
            <li>Frame rate: {{ result.frame_rate }} fps</li>
            <li>Frames: {{ result.frame_count }}</li>
            <li>Colormap: {{ colormapLabel(result.colormap) }}</li>
            <li v-if="gridSettingsApply(result.image_type) || isChromaticType(result.image_type)">Threshold: {{ formatThresholdSummary(result.threshold) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Notes: {{ formatNoteCountSummary(result.note_count) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Interpolate: {{ result.interpolate }}</li>
            <li>Image type: {{ imageTypeLabel(result.image_type) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Oversampling: {{ formatResolution(result.resolution) }}</li>
            <li v-if="gridSettingsApply(result.image_type)">Gaussian smoothing: {{ formatGaussian(result.gaussian) }}</li>
            <li v-if="decayRateApplies(result.image_type)">Decay rate: {{ formatDecayRate(result.decay_rate) }}</li>
            <li v-if="isChromaticType(result.image_type)">Chromatic decay rate: {{ formatChromaticRate(result.decay_rate) }}</li>
            <li v-if="result.image_type === 'decay'">Low saturation decay: {{ formatDecayAmount(result.decay_low) }}</li>
            <li v-if="result.image_type === 'decay'">Medium saturation decay: {{ formatDecayAmount(result.decay_medium) }}</li>
            <li v-if="result.image_type === 'decay'">High saturation decay: {{ formatDecayAmount(result.decay_high) }}</li>
            <li v-if="result.image_type === 'decay'">Saturated decay: {{ formatDecayAmount(result.decay_saturated) }}</li>
            <li v-if="isPolarType(result.image_type)">Notes shown: {{ formatPolarNotes(result.polar_notes) }}</li>
            <li v-if="isPolychordType(result.image_type)">Number of notes: {{ formatPolychordNotes(result.polychord_notes) }}</li>
            <li v-if="isPolychordType(result.image_type)">Copies: {{ formatPolychordCopies(result.polychord_min_copies) }} to {{ formatPolychordCopies(result.polychord_max_copies) }}</li>
            <li v-if="isPolychordType(result.image_type)">Rotation: {{ formatPolychordRotation(result.polychord_rotation) }}</li>
            <li v-if="isSpirographType(result.image_type)">Number of notes: {{ formatSpirographNotes(result.spirograph_notes) }}</li>
            <li v-if="isSpirographType(result.image_type)">History length: {{ formatSpirographHistory(result.spirograph_history) }}</li>
            <li v-if="isSpirographType(result.image_type)">History fade: {{ formatSpirographFade(result.spirograph_fade) }}</li>
            <li v-if="usesHeldNotes(result.image_type)">Extra notes (k): {{ formatExtraNotes(result.extra_notes) }}</li>
            <li v-if="usesObjExport(result.image_type)">3D export: {{ formatExportObj(result.export_obj) }}</li>
            <li v-if="noteLayoutApplies(result.image_type)">Note layout: {{ noteLayoutLabel(result.note_layout) }}</li>
            <li v-if="beatColoringApplies(result.image_type)">Beat coloring: {{ formatBeatColoring(result.beat_coloring) }}</li>
            <li v-if="peakSettingsShown(result.image_type, result.beat_coloring)">Minimum distance: {{ formatPeakDistance(result.peak_distance) }}</li>
            <li v-if="result.image_type === 'contour' && result.beat_coloring">Wave count: {{ formatWaveCount(result.wave_count) }}</li>
            <li>Step: {{ Number(result.step_samples.toFixed(2)) }} samples</li>
            <li>Windows analyzed: {{ result.window_count }}</li>
          </ul>
        </section>
      </div>

      <div class="column">
        <SettingsForm :busy="status === 'busy'" :file="file" @submit="onSubmit" />
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
