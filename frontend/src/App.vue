<script setup lang="ts">
import { onMounted } from "vue";

import AppLayout from "./components/AppLayout.vue";
import ChatPanel from "./components/ChatPanel.vue";
import VideoDetails from "./components/VideoDetails.vue";
import VideoList from "./components/VideoList.vue";
import VideoUploadForm from "./components/VideoUploadForm.vue";
import { useCoachStore } from "./composables/useCoachStore";

const {
  state,
  canStartPractice,
  canSendMessage,
  loadVideos,
  selectVideo,
  uploadVideo,
  refreshSelectedVideo,
  startPractice,
  sendMessage,
  clearError,
} = useCoachStore();

onMounted(() => {
  void loadVideos();
});
</script>

<template>
  <AppLayout
    :has-error="Boolean(state.globalError)"
    :error-message="state.globalError"
    @dismiss-error="clearError"
  >
    <template #sidebar>
      <aside class="sidebar">
        <VideoUploadForm :is-uploading="state.isUploading" @submit="uploadVideo" />
        <VideoList
          :videos="state.videos"
          :selected-video-id="state.selectedVideo?.id ?? null"
          :is-loading="state.isLoadingVideos"
          @select="selectVideo"
        />
      </aside>
    </template>

    <section class="content-grid">
      <VideoDetails
        :video="state.selectedVideo"
        :is-loading="state.isLoadingVideo"
        @refresh="refreshSelectedVideo"
      />
      <ChatPanel
        :video="state.selectedVideo"
        :messages="state.messages"
        :current-session-id="state.currentSessionId"
        :can-start-practice="canStartPractice"
        :can-send-message="canSendMessage"
        :is-starting-chat="state.isStartingChat"
        :is-sending-message="state.isSendingMessage"
        @start="startPractice"
        @send="sendMessage"
      />
    </section>
  </AppLayout>
</template>
