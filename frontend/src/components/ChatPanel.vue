<script setup lang="ts">
import { computed, ref } from "vue";

import type { ChatMessage, VideoDetail } from "../types";
import MessageBubble from "./MessageBubble.vue";
import StarterActions from "./StarterActions.vue";

const props = defineProps<{
  video: VideoDetail | null;
  messages: ChatMessage[];
  currentSessionId: number | null;
  canStartPractice: boolean;
  canSendMessage: boolean;
  isStartingChat: boolean;
  isSendingMessage: boolean;
}>();

const emit = defineEmits<{
  start: [];
  send: [message: string];
}>();

const draft = ref("");

const isReady = computed(() => props.video?.status === "ready");

function submitMessage(): void {
  const normalizedDraft = draft.value.trim();
  if (!normalizedDraft) {
    return;
  }
  emit("send", normalizedDraft);
  draft.value = "";
}

function sendStarter(message: string): void {
  emit("send", message);
}
</script>

<template>
  <aside class="chat-panel">
    <div class="section-heading">
      <div>
        <p class="eyebrow">Practice</p>
        <h2>AI Coach</h2>
      </div>
      <span v-if="currentSessionId" class="session-pill">Session #{{ currentSessionId }}</span>
    </div>

    <div v-if="!video" class="notice notice--neutral">
      Select or add a video to start technical interview practice.
    </div>
    <div v-else-if="!isReady" class="notice notice--neutral">
      Practice unlocks when the transcript is ready.
    </div>
    <button
      v-else-if="canStartPractice"
      class="button button--primary button--wide"
      type="button"
      :disabled="isStartingChat"
      @click="emit('start')"
    >
      {{ isStartingChat ? "Starting..." : "Start practice session" }}
    </button>

    <template v-if="currentSessionId">
      <StarterActions v-if="messages.length === 0" @select="sendStarter" />

      <div class="message-list" aria-live="polite">
        <MessageBubble
          v-for="(message, index) in messages"
          :key="`${message.role}-${index}`"
          :message="message"
        />
        <div v-if="isSendingMessage" class="typing-indicator">AI Coach is thinking...</div>
      </div>

      <form class="chat-input" @submit.prevent="submitMessage">
        <textarea
          v-model="draft"
          rows="4"
          placeholder="Write your interview answer or ask for a practice prompt..."
          :disabled="!canSendMessage"
        />
        <button class="button button--primary" type="submit" :disabled="!canSendMessage">
          Send
        </button>
      </form>
    </template>
  </aside>
</template>
