<script setup lang="ts">
// A titled section of the settings that can be collapsed on its own. It is the browser's own <details> element: it is operated
// with the keyboard, tells assistive technology whether it is expanded, and a collapsed body stays in the document, so no value
// in it is lost. The controls given to it are laid out two to a row (see the style below).
defineProps<{ id: string; title: string; open: boolean; problem: boolean }>();
const emit = defineEmits<{ toggle: [open: boolean] }>();

function onToggle(event: Event) {
  emit("toggle", (event.target as HTMLDetailsElement).open);
}
</script>

<template>
  <details class="settings-group" :data-group="id" :open="open" @toggle="onToggle">
    <summary class="settings-group-title">
      {{ title }}
      <span v-if="problem" class="settings-group-problem">needs attention</span>
    </summary>
    <div class="settings-group-body">
      <slot />
    </div>
  </details>
</template>

<style>
/* Not scoped: the cells are the form's elements, passed in through the slot. */
.settings-group {
  --group-gap: 0.75rem;
  border: 1px solid #d0d0d0;
  border-radius: 0.35rem;
  padding: 0 0.75rem;
}
.settings-group[open] {
  padding-bottom: 0.75rem;
}
.settings-group-title {
  cursor: pointer;
  font-family: var(--label-font);
  font-size: var(--label-size);
  font-weight: 700;
  padding: 0.5rem 0;
}
.settings-group-problem {
  margin-left: 0.5rem;
  color: #b00020;
  font-weight: 600;
  font-size: 0.85rem;
}
.settings-group-body {
  display: flex;
  flex-wrap: wrap;
  gap: var(--group-gap);
  margin-top: 0.25rem;
}
/* two cells to a row; an odd last cell takes the whole row */
.settings-group-body > .field {
  flex: 1 1 calc(50% - var(--group-gap) / 2);
  min-width: 0;
}
.settings-group-body > .field:last-child:nth-child(odd) {
  flex-basis: 100%;
}
/* a very narrow screen: one cell to a row so that nothing is cut off */
@media (max-width: 26rem) {
  .settings-group-body > .field {
    flex-basis: 100%;
  }
}
</style>
