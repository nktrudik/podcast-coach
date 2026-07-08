import type {
  ApiErrorPayload,
  ChatMessage,
  SendMessageResponse,
  StartChatResponse,
  UploadVideoResponse,
  VideoDetail,
  VideoListItem,
} from "../types";

const fallbackBaseUrl = "http://localhost:8000";
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
const apiBaseUrl = (configuredBaseUrl ?? fallbackBaseUrl).replace(/\/$/, "");

class ApiClientError extends Error {
  public readonly statusCode: number;
  public readonly payload: ApiErrorPayload | null;

  public constructor(message: string, statusCode: number, payload: ApiErrorPayload | null) {
    super(message);
    this.name = "ApiClientError";
    this.statusCode = statusCode;
    this.payload = payload;
  }
}

async function request<TResponse>(
  path: string,
  init: RequestInit = {},
): Promise<TResponse> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

async function buildApiError(response: Response): Promise<ApiClientError> {
  let payload: ApiErrorPayload | null = null;
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = null;
  }

  const detail = payload?.detail;
  const message =
    typeof detail === "string" && detail.trim()
      ? detail
      : `Request failed with status ${response.status}`;

  return new ApiClientError(message, response.status, payload);
}

export const apiClient = {
  listVideos(): Promise<VideoListItem[]> {
    return request<VideoListItem[]>("/videos");
  },

  getVideo(videoId: number): Promise<VideoDetail> {
    return request<VideoDetail>(`/videos/${videoId}`);
  },

  uploadVideo(youtubeUrl: string): Promise<UploadVideoResponse> {
    return request<UploadVideoResponse>("/videos", {
      method: "POST",
      body: JSON.stringify({ youtube_url: youtubeUrl }),
    });
  },

  startChat(videoId: number): Promise<StartChatResponse> {
    return request<StartChatResponse>("/chat/start", {
      method: "POST",
      body: JSON.stringify({ video_id: videoId }),
    });
  },

  sendMessage(sessionId: number, message: string): Promise<SendMessageResponse> {
    return request<SendMessageResponse>("/chat/message", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  },

  listMessages(sessionId: number): Promise<ChatMessage[]> {
    return request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
  },
};

export { ApiClientError };
