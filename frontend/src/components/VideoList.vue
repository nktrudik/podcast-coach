<script setup lang="ts">
import type { VideoListItem } from "../types";
import StatusBadge from "./StatusBadge.vue";

defineProps<{
  videos: VideoListItem[];
  selectedVideoId: number | null;
  isLoading: boolean;
}>();

const emit = defineEmits<{
  select: [videoId: number];
}>();

function videoTitle(video: VideoListItem): string {
  return video.title ?? video.youtube_video_id ?? "Untitled video";
}
</script>

<template>
  <section class="video-list" aria-label="Uploaded videos">
    <div class="section-heading">
      <h2>Video Library</h2>
      <span v-if="isLoading" class="subtle-text">Loading</span>
    </div>

    <div v-if="videos.length === 0" class="empty-list">
      Add a technical YouTube video to build an interview practice session.
    </div>

    <button
      v-for="video in videos"
      :key="video.id"
      class="video-list__item"
      :class="{ 'video-list__item--active': video.id === selectedVideoId }"
      type="button"
      @click="emit('select', video.id)"
    >
      <span class="video-list__title">{{ videoTitle(video) }}</span>
      <StatusBadge :status="video.status" />
    </button>
  </section>
</template>
