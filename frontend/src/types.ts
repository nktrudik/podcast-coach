export type VideoStatus = "queued" | "processing" | "ready" | "failed";

export interface UploadVideoResponse {
  job_id: string;
  video_id: number;
  status: VideoStatus;
}

export interface VideoListItem {
  id: number;
  youtube_url: string | null;
  youtube_video_id: string | null;
  title: string | null;
  status: VideoStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface VideoDetail extends VideoListItem {
  transcript: string | null;
}

export interface StartChatResponse {
  session_id: number;
}

export interface SendMessageResponse {
  answer: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

export interface ApiErrorPayload {
  detail?: string | Record<string, unknown>;
  error_code?: string;
  module?: string;
  details?: unknown;
}
