import { computed, reactive } from "vue";

import { ApiClientError, apiClient } from "../api/client";
import type { ChatMessage, VideoDetail, VideoListItem, VideoStatus } from "../types";

interface CoachState {
  videos: VideoListItem[];
  selectedVideo: VideoDetail | null;
  currentSessionId: number | null;
  messages: ChatMessage[];
  isLoadingVideos: boolean;
  isLoadingVideo: boolean;
  isUploading: boolean;
  isStartingChat: boolean;
  isSendingMessage: boolean;
  globalError: string | null;
}

const state = reactive<CoachState>({
  videos: [],
  selectedVideo: null,
  currentSessionId: null,
  messages: [],
  isLoadingVideos: false,
  isLoadingVideo: false,
  isUploading: false,
  isStartingChat: false,
  isSendingMessage: false,
  globalError: null,
});

const pollTimers = new Map<number, number>();

const selectedVideoStatus = computed<VideoStatus | null>(
  () => state.selectedVideo?.status ?? null,
);
const canStartPractice = computed(
  () => state.selectedVideo?.status === "ready" && !state.currentSessionId,
);
const canSendMessage = computed(
  () =>
    state.selectedVideo?.status === "ready" &&
    Boolean(state.currentSessionId) &&
    !state.isSendingMessage,
);

export function useCoachStore() {
  async function loadVideos(): Promise<void> {
    state.isLoadingVideos = true;
    state.globalError = null;
    try {
      state.videos = await apiClient.listVideos();
      for (const video of state.videos) {
        if (video.status === "queued" || video.status === "processing") {
          pollVideo(video.id);
        }
      }

      if (!state.selectedVideo && state.videos.length > 0) {
        await selectVideo(state.videos[0].id);
      }
    } catch (error) {
      state.globalError = toErrorMessage(error);
    } finally {
      state.isLoadingVideos = false;
    }
  }

  async function selectVideo(videoId: number): Promise<void> {
    state.isLoadingVideo = true;
    state.globalError = null;
    state.currentSessionId = null;
    state.messages = [];
    try {
      const video = await apiClient.getVideo(videoId);
      state.selectedVideo = video;
      upsertVideo(video);
      if (video.status === "queued" || video.status === "processing") {
        pollVideo(video.id);
      }
    } catch (error) {
      state.globalError = toErrorMessage(error);
    } finally {
      state.isLoadingVideo = false;
    }
  }

  async function uploadVideo(youtubeUrl: string): Promise<void> {
    state.isUploading = true;
    state.globalError = null;
    try {
      const response = await apiClient.uploadVideo(youtubeUrl);
      await loadVideos();
      await selectVideo(response.video_id);
      if (response.status === "queued" || response.status === "processing") {
        pollVideo(response.video_id);
      }
    } catch (error) {
      state.globalError = toErrorMessage(error);
    } finally {
      state.isUploading = false;
    }
  }

  async function refreshSelectedVideo(): Promise<void> {
    if (!state.selectedVideo) {
      return;
    }
    await selectVideo(state.selectedVideo.id);
  }

  async function startPractice(): Promise<void> {
    if (!state.selectedVideo || state.selectedVideo.status !== "ready") {
      return;
    }

    state.isStartingChat = true;
    state.globalError = null;
    try {
      const response = await apiClient.startChat(state.selectedVideo.id);
      state.currentSessionId = response.session_id;
      state.messages = [];
    } catch (error) {
      state.globalError = toErrorMessage(error);
    } finally {
      state.isStartingChat = false;
    }
  }

  async function sendMessage(content: string): Promise<void> {
    const normalizedContent = content.trim();
    if (!normalizedContent || !state.currentSessionId || !canSendMessage.value) {
      return;
    }

    state.isSendingMessage = true;
    state.globalError = null;
    state.messages.push({ role: "user", content: normalizedContent });
    try {
      const response = await apiClient.sendMessage(
        state.currentSessionId,
        normalizedContent,
      );
      state.messages.push({ role: "assistant", content: response.answer });
    } catch (error) {
      state.globalError = toErrorMessage(error);
    } finally {
      state.isSendingMessage = false;
    }
  }

  function clearError(): void {
    state.globalError = null;
  }

  return {
    state,
    selectedVideoStatus,
    canStartPractice,
    canSendMessage,
    loadVideos,
    selectVideo,
    uploadVideo,
    refreshSelectedVideo,
    startPractice,
    sendMessage,
    clearError,
  };
}

async function pollVideo(videoId: number): Promise<void> {
  if (pollTimers.has(videoId)) {
    return;
  }

  const tick = async (): Promise<void> => {
    try {
      const video = await apiClient.getVideo(videoId);
      upsertVideo(video);
      if (state.selectedVideo?.id === videoId) {
        state.selectedVideo = video;
      }

      if (video.status === "queued" || video.status === "processing") {
        const timerId = window.setTimeout(tick, 3000);
        pollTimers.set(videoId, timerId);
        return;
      }
    } catch (error) {
      state.globalError = toErrorMessage(error);
    }

    const timerId = pollTimers.get(videoId);
    if (timerId) {
      window.clearTimeout(timerId);
      pollTimers.delete(videoId);
    }
  };

  const timerId = window.setTimeout(tick, 1000);
  pollTimers.set(videoId, timerId);
}

function upsertVideo(video: VideoListItem): void {
  const index = state.videos.findIndex((item) => item.id === video.id);
  if (index >= 0) {
    state.videos[index] = { ...state.videos[index], ...video };
    return;
  }
  state.videos = [video, ...state.videos];
}

function toErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected application error";
}
