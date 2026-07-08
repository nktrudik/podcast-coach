<script setup lang="ts">
import type { VideoStatus } from "../types";

defineProps<{
  status: VideoStatus;
}>();

const labels: Record<VideoStatus, string> = {
  queued: "Queued",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};
</script>

<template>
  <span class="status-badge" :class="`status-badge--${status}`">
    <span class="status-badge__dot" />
    {{ labels[status] }}
  </span>
</template>
