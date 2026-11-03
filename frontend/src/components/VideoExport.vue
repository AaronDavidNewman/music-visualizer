<script setup lang="ts">
import { ref, watch } from "vue";
import { createVideo, videoUrl, type JobResult, type VideoResult } from "../api";

const props = defineProps<{ result: JobResult }>();

type Status = "idle" | "working" | "done" | "error";

const status = ref<Status>("idle");
const video = ref<VideoResult | null>(null);
const message = ref("");

// The job whose video is being made. A new render while it works must not show the old render's answer.
let current = props.result.job_id;

async function make() {
  if (status.value === "working") return;
  const job = props.result;
  current = job.job_id;
  status.value = "working";
  video.value = null;
  message.value = "";
  try {
    const made = await createVideo(job);
    if (current !== job.job_id) return;
    video.value = made;
    status.value = "done";
  } catch (error) {
    if (current !== job.job_id) return;
    message.value = error instanceof Error ? error.message : "Something went wrong while making the video.";
    status.value = "error";
  }
}

watch(
  () => props.result,
  (now) => {
    current = now.job_id;
    status.value = "idle";
    video.value = null;
    message.value = "";
  },
);
</script>

<template>
  <div class="video">
    <button type="button" :disabled="status === 'working'" @click="make">Create video</button>

    <p v-if="status === 'working'" class="working" role="status">
      Making the video… this can take a little while for long renders.
    </p>
    <p v-if="status === 'done' && video" class="done" role="status">
      Video saved to <span class="path">{{ video.path }}</span>
      <a :href="videoUrl(result)" download>Download</a>
    </p>
    <p v-if="status === 'error'" class="error-box" role="alert">{{ message }}</p>
  </div>
</template>

<style scoped>
.video {
  display: grid;
  gap: 0.5rem;
  justify-items: start;
}
.video button {
  min-width: 5rem;
  padding: 0.4rem 0.8rem;
}
.working {
  color: #333;
  margin: 0;
}
.done {
  margin: 0;
}
.path {
  font-family: monospace;
  overflow-wrap: anywhere;
}
.done a {
  margin-left: 0.75rem;
}
.error-box {
  margin: 0;
  color: #b00020;
  background: #fdecee;
  padding: 0.75rem 1rem;
  border-radius: 0.25rem;
}
</style>
