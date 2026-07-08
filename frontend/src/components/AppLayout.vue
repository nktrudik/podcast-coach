<script setup lang="ts">
defineProps<{
  hasError: boolean;
  errorMessage: string | null;
}>();

const fallbackApiBaseUrl = "http://localhost:8000";
const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
const apiDocsUrl = `${(configuredApiBaseUrl ?? fallbackApiBaseUrl).replace(/\/$/, "")}/docs`;

const emit = defineEmits<{
  dismissError: [];
}>();
</script>

<template>
  <div class="app-shell">
    <header class="top-bar">
      <div>
        <span class="brand-mark">EIC</span>
        <span class="brand-name">English Interview Coach for IT</span>
      </div>
      <a class="top-bar__link" :href="apiDocsUrl" target="_blank" rel="noreferrer">
        API Docs
      </a>
    </header>

    <div v-if="hasError" class="global-error" role="alert">
      <span>{{ errorMessage }}</span>
      <button type="button" @click="emit('dismissError')">Dismiss</button>
    </div>

    <main class="workspace">
      <slot name="sidebar" />
      <slot />
    </main>
  </div>
</template>
