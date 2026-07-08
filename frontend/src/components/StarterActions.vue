<script setup lang="ts">
const emit = defineEmits<{
  select: [message: string];
}>();

const actions = [
  {
    label: "Ask an interview question",
    message: "Ask me one realistic technical interview question based on this video.",
  },
  {
    label: "Extract interview vocabulary",
    message:
      "Extract useful interview vocabulary and phrases from this video with examples.",
  },
  {
    label: "Run a mock interview",
    message:
      "Run a mock interview based on this video. Ask one question at a time.",
  },
  {
    label: "Improve my answer",
    message:
      "I want to practice improving an interview answer. Ask me for my answer first.",
  },
];
</script>

<template>
  <div class="starter-actions" aria-label="Practice starters">
    <button
      v-for="action in actions"
      :key="action.label"
      class="starter-actions__button"
      type="button"
      @click="emit('select', action.message)"
    >
      {{ action.label }}
    </button>
  </div>
</template>
