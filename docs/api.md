# API

Base URL for versioned routes:

```text
http://localhost:8000/api/v1
```

The backend also exposes legacy root routes for local backwards compatibility.

## Health

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "app": "ok",
  "database": "ok"
}
```

## Create Video Job

```http
POST /api/v1/videos
Content-Type: application/json
```

Request:

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=gO1Cm_A_pO8"
}
```

Response:

```json
{
  "job_id": "video-42",
  "video_id": 42,
  "status": "queued"
}
```

## List Videos

```http
GET /api/v1/videos
```

Response item:

```json
{
  "id": 42,
  "youtube_url": "https://www.youtube.com/watch?v=gO1Cm_A_pO8",
  "youtube_video_id": "gO1Cm_A_pO8",
  "title": "Example technical talk",
  "status": "ready",
  "error_message": null,
  "created_at": "2026-01-01 12:00:00",
  "updated_at": "2026-01-01 12:03:00"
}
```

## Get Video

```http
GET /api/v1/videos/{video_id}
```

`transcript` is `null` until the video is ready.

## Start Chat

```http
POST /api/v1/chat/start
Content-Type: application/json
```

Request:

```json
{
  "video_id": 42
}
```

Response:

```json
{
  "session_id": 7
}
```

The video must have `ready` status.

## Send Message

```http
POST /api/v1/chat/message
Content-Type: application/json
```

Request:

```json
{
  "session_id": 7,
  "message": "I would explain event-driven architecture as a way to decouple services."
}
```

Response:

```json
{
  "answer": "Quick score: 7/10\nWhat was good..."
}
```

## Admin Endpoints

Admin endpoints require the `X-Admin-Key` header.

```http
DELETE /api/v1/admin/videos/{video_id}
DELETE /api/v1/admin/chat/sessions/{session_id}
```

## Error Payload

```json
{
  "detail": "The video is not ready for interview practice yet",
  "error_code": "service_validation_error",
  "module": "services",
  "details": {
    "video_id": 42,
    "status": "processing"
  }
}
```
