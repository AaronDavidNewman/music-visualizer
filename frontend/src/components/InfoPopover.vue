<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useId } from "vue";
import { popoverPosition } from "../utilities/popover";

defineProps<{ label: string; text: string }>();

const id = useId();
const button = ref<HTMLButtonElement | null>(null);
const popover = ref<HTMLElement | null>(null);

// The browser opens, closes (Escape, click outside, the button again) and keeps one popover open at a time;
// this only places the box next to its button each time it opens.
function onToggle(event: Event) {
  const el = popover.value;
  const anchor = button.value;
  if (!el || !anchor || (event as ToggleEvent).newState !== "open") return;
  const rect = anchor.getBoundingClientRect();
  const pos = popoverPosition(
    { left: rect.left, top: rect.top, bottom: rect.bottom },
    { width: el.offsetWidth, height: el.offsetHeight },
    { width: document.documentElement.clientWidth, height: window.innerHeight },
  );
  el.style.left = `${pos.left}px`;
  el.style.top = `${pos.top}px`;
}

// A resize (or the layout switching between one and two columns) would leave the box in the wrong place.
function closeOnResize() {
  if (popover.value?.matches(":popover-open")) popover.value.hidePopover();
}

onMounted(() => window.addEventListener("resize", closeOnResize));
onBeforeUnmount(() => window.removeEventListener("resize", closeOnResize));
</script>

<template>
  <span class="info">
    <button ref="button" type="button" class="info-button" :aria-label="`About ${label}`" :popovertarget="id">
      i
    </button>
    <div :id="id" ref="popover" class="info-popover" popover="auto" role="note" @toggle="onToggle">{{ text }}</div>
  </span>
</template>

<style scoped>
.info-button {
  box-sizing: border-box;
  width: 1.25rem;
  height: 1.25rem;
  padding: 0;
  border: 1px solid #777;
  border-radius: 50%;
  background: #fff;
  color: #333;
  font: italic 700 0.8rem/1 Georgia, serif;
  cursor: pointer;
}
.info-button:hover {
  background: #eef3ff;
}
.info-button:focus-visible {
  outline: 2px solid #1a56db;
  outline-offset: 2px;
}
.info-popover {
  /* The browser centers a popover by default; it is placed next to its button when it opens. */
  position: fixed;
  inset: auto;
  margin: 0;
  /* Sized by its text, not by the space to its right, so measuring it before it is placed gives its real size. */
  width: max-content;
  max-width: min(18rem, calc(100vw - 1rem));
  box-sizing: border-box;
  padding: 0.5rem 0.75rem;
  border: 1px solid #aaa;
  border-radius: 0.25rem;
  background: #fff;
  color: #222;
  box-shadow: 0 2px 8px rgb(0 0 0 / 0.2);
  font-size: 0.9rem;
  font-weight: 400;
  line-height: 1.35;
  overflow-wrap: break-word;
}
</style>
