<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { frameUrl, type JobResult } from "../api";
import { frameAtElapsed, frameTime, preloadRange } from "../lib/playback";

const PRELOAD_AHEAD = 30;

const props = defineProps<{ result: JobResult }>();

const index = ref(0);
const playing = ref(false);
const loop = ref(false);

const lastIndex = computed(() => props.result.frame_count - 1);
const seconds = computed(() => frameTime(index.value, props.result.frame_rate));
const src = computed(() => frameUrl(props.result, index.value));

let rafId = 0;
let startedAt = 0;
let startFrame = 0;
// Kept so the browser holds on to preloaded images until they are shown.
let preloaded: HTMLImageElement[] = [];

function preload(from: number) {
  preloaded = preloadRange(from, props.result.frame_count, PRELOAD_AHEAD).map((i) => {
    const img = new Image();
    img.src = frameUrl(props.result, i);
    return img;
  });
}

function tick(now: number) {
  const pos = frameAtElapsed(
    startFrame,
    (now - startedAt) / 1000,
    props.result.frame_rate,
    props.result.frame_count,
    loop.value,
  );
  if (pos.index !== index.value) {
    index.value = pos.index;
    preload(pos.index);
  }
  if (pos.finished) {
    playing.value = false;
    return;
  }
  rafId = requestAnimationFrame(tick);
}

function play() {
  if (playing.value) return;
  if (!loop.value && index.value >= lastIndex.value) index.value = 0;
  startFrame = index.value;
  startedAt = performance.now();
  playing.value = true;
  rafId = requestAnimationFrame(tick);
}

function pause() {
  cancelAnimationFrame(rafId);
  playing.value = false;
}

function toggle() {
  if (playing.value) pause();
  else play();
}

function onSlider(event: Event) {
  const wasPlaying = playing.value;
  pause();
  index.value = Number((event.target as HTMLInputElement).value);
  preload(index.value);
  if (wasPlaying) play();
}

function onLoop() {
  // Restart the clock from the current frame so the new loop setting applies cleanly.
  if (playing.value) {
    pause();
    play();
  }
}

watch(
  () => props.result,
  () => {
    pause();
    index.value = 0;
    preload(0);
  },
  { immediate: true },
);

onBeforeUnmount(pause);
</script>

<template>
  <div class="player">
    <img class="frame" :src="src" :alt="`Frame ${index + 1} of ${result.frame_count}`" />

    <div class="controls">
      <button type="button" @click="toggle">{{ playing ? "Pause" : "Play" }}</button>
      <label class="loop">
        <input v-model="loop" type="checkbox" @change="onLoop" />
        Loop
      </label>
      <output class="time">{{ seconds.toFixed(2) }} s</output>
      <span class="count">frame {{ index + 1 }} / {{ result.frame_count }}</span>
    </div>

    <input
      class="slider"
      type="range"
      min="0"
      :max="lastIndex"
      step="1"
      :value="index"
      aria-label="Frame position"
      @input="onSlider"
    />
  </div>
</template>

<style scoped>
.player {
  display: grid;
  gap: 0.75rem;
}
.frame {
  width: min(100%, 660px);
  /* Frames are 252 x 168 pixels (12 x 7 tiles of 21 x 24). Declaring the ratio reserves the right
     space before a frame loads, so the image keeps 3:2 at any width and never changes size between frames. */
  aspect-ratio: 3 / 2;
  image-rendering: pixelated;
  border: 1px solid #ccc;
  background: #000;
}
.controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}
.controls button {
  min-width: 5rem;
  padding: 0.4rem 0.8rem;
}
.time {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.count {
  color: #555;
}
.slider {
  width: min(100%, 660px);
}
</style>
