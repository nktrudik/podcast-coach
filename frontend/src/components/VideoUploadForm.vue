<script setup lang="ts">
import { ref } from "vue";

defineProps<{
  isUploading: boolean;
}>();

const emit = defineEmits<{
  submit: [youtubeUrl: string];
}>();

const youtubeUrl = ref("");

function handleSubmit(): void {
  const normalizedUrl = youtubeUrl.value.trim();
  if (!normalizedUrl) {
    return;
  }
  emit("submit", normalizedUrl);
  youtubeUrl.value = "";
}
</script>

<template>
  <form class="upload-form" @submit.prevent="handleSubmit">
    <label class="field-label" for="youtube-url">Technical YouTube video</label>
    <div class="upload-form__row">
      <input
        id="youtube-url"
        v-model="youtubeUrl"
        class="text-input"
        type="url"
        placeholder="https://www.youtube.com/watch?v=..."
        :disabled="isUploading"
        required
      />
      <button class="button button--primary" type="submit" :disabled="isUploading">
        {{ isUploading ? "Adding..." : "Add" }}
      </button>
    </div>
  </form>
</template>
