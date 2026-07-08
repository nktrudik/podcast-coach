<script setup lang="ts">
import type { VideoDetail } from "../types";
import StatusBadge from "./StatusBadge.vue";

defineProps<{
  video: VideoDetail | null;
  isLoading: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

function displayTitle(video: VideoDetail): string {
  return video.title ?? video.youtube_video_id ?? "Selected video";
}
</script>

<template>
  <section class="video-details">
    <div v-if="!video" class="empty-state">
      <p class="eyebrow">English Interview Coach for IT</p>
      <h1>AI-powered practice app for technical English interviews based on YouTube videos.</h1>
      <p>
        Add a technical talk, wait for processing, then practice interview answers
        with focused grammar, vocabulary, and answer-structure feedback.
      </p>
    </div>

    <template v-else>
      <div class="video-details__header">
        <div>
          <p class="eyebrow">Selected video</p>
          <h1>{{ displayTitle(video) }}</h1>
        </div>
        <StatusBadge :status="video.status" />
      </div>

      <div v-if="isLoading" class="notice notice--neutral">Loading video details...</div>

      <div
        v-if="video.status === 'queued' || video.status === 'processing'"
        class="processing-panel"
      >
        <div class="progress-bar" aria-hidden="true">
          <span />
        </div>
        <p>
          The backend is downloading audio, converting it with FFmpeg, and sending
          speech to the configured STT provider.
        </p>
      </div>

      <div v-if="video.status === 'failed'" class="notice notice--danger">
        {{ video.error_message ?? "Video processing failed. Try another link or retry later." }}
      </div>

      <div v-if="video.status === 'ready'" class="video-details__content">
        <div class="metric-row">
          <div>
            <span class="metric-row__label">Video ID</span>
            <strong>{{ video.youtube_video_id }}</strong>
          </div>
          <div>
            <span class="metric-row__label">Created</span>
            <strong>{{ video.created_at }}</strong>
          </div>
        </div>

        <div class="transcript-panel">
          <div class="section-heading">
            <h2>Transcript Preview</h2>
            <button class="button button--ghost" type="button" @click="emit('refresh')">
              Refresh
            </button>
          </div>
          <p>{{ video.transcript }}</p>
        </div>
      </div>
    </template>
  </section>
</template>
