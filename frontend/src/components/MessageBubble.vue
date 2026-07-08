<script setup lang="ts">
import type { ChatMessage } from "../types";

defineProps<{
  message: ChatMessage;
}>();
</script>

<template>
  <article class="message-bubble" :class="`message-bubble--${message.role}`">
    <div class="message-bubble__meta">
      {{ message.role === "user" ? "You" : "AI Coach" }}
    </div>
    <p>{{ message.content }}</p>
  </article>
</template>
