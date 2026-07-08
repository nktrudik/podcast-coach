from collections.abc import Mapping, Sequence

import pytest
from app.clients.llm import MemoryMessage
from app.core.config import Settings
from app.core.status import VideoStatus
from app.core.types import DatabaseRecord
from app.services import chat as chat_module
from app.services import video_processing as video_module
from app.services.chat import ChatService
from app.services.video_processing import VideoProcessingService


def test_video_processing_service_uses_mocked_stt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Video processing can be tested with mocked media and STT dependencies."""
    stored: dict[str, object] = {}
    app_settings = Settings(
        api_key="test",
        admin_api_key="admin",
        uploaded_videos_limit=10,
        max_video_duration_minutes=5,
    )

    def fake_existing_video(youtube_video_id: str) -> DatabaseRecord | None:
        assert youtube_video_id == "gO1Cm_A_pO8"
        return None

    def fake_count_videos() -> int:
        return 0

    def fake_create_video_job(
        youtube_url: str,
        youtube_video_id: str,
        status: VideoStatus = VideoStatus.QUEUED,
    ) -> int:
        stored["created_url"] = youtube_url
        stored["created_video_id"] = youtube_video_id
        stored["created_status"] = status.value
        return 12

    def fake_get_video(video_id: int) -> DatabaseRecord | None:
        return {
            "id": video_id,
            "youtube_url": "https://www.youtube.com/watch?v=gO1Cm_A_pO8",
            "youtube_video_id": "gO1Cm_A_pO8",
            "title": None,
            "transcript": None,
            "status": "queued",
            "error_message": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }

    def fake_mark_processing(video_id: int) -> None:
        stored["processing_id"] = video_id

    def fake_mark_ready(
        *,
        video_id: int,
        transcript: str,
        youtube_url: str,
        youtube_video_id: str,
        title: str | None,
    ) -> None:
        stored["ready_id"] = video_id
        stored["transcript"] = transcript
        stored["ready_url"] = youtube_url
        stored["ready_video_id"] = youtube_video_id
        stored["title"] = title

    monkeypatch.setattr(
        video_module,
        "get_video_by_youtube_video_id",
        fake_existing_video,
    )
    monkeypatch.setattr(video_module, "count_videos", fake_count_videos)
    monkeypatch.setattr(video_module, "create_video_job", fake_create_video_job)
    monkeypatch.setattr(video_module, "get_video", fake_get_video)
    monkeypatch.setattr(video_module, "mark_video_processing", fake_mark_processing)
    monkeypatch.setattr(video_module, "mark_video_ready", fake_mark_ready)

    service = VideoProcessingService(
        app_settings=app_settings,
        metadata_provider=lambda _: {
            "title": "Event-driven systems",
            "duration_seconds": 120,
        },
        audio_downloader=lambda _: "audio.mp3",
        transcriber=lambda _: "Clean transcript from mocked STT",
    )

    job = service.create_job("https://youtu.be/gO1Cm_A_pO8")
    service.process_job(job.video_id)

    assert job.video_id == 12
    assert job.status == VideoStatus.QUEUED
    assert stored["processing_id"] == 12
    assert stored["transcript"] == "Clean transcript from mocked STT"
    assert stored["title"] == "Event-driven systems"


def test_chat_service_uses_mocked_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chat service can be tested with mocked repositories and LLM responder."""
    stored_messages: list[tuple[int, str, str]] = []
    app_settings = Settings(
        api_key="test",
        admin_api_key="admin",
        chat_sessions_per_video_limit=5,
        llm_memory_messages_limit=4,
    )

    def fake_get_video(video_id: int) -> DatabaseRecord | None:
        return {
            "id": video_id,
            "youtube_url": "https://www.youtube.com/watch?v=gO1Cm_A_pO8",
            "youtube_video_id": "gO1Cm_A_pO8",
            "title": "Architecture talk",
            "transcript": "Transcript about system design tradeoffs.",
            "status": "ready",
            "error_message": None,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }

    def fake_count_sessions(video_id: int) -> int:
        assert video_id == 7
        return 0

    def fake_create_session(
        video_id: int | None = None,
        title: str | None = None,
    ) -> int:
        assert video_id == 7
        assert title == "Architecture talk"
        return 21

    def fake_get_session(session_id: int) -> DatabaseRecord | None:
        assert session_id == 21
        return {
            "id": 21,
            "video_id": 7,
            "title": "Architecture talk",
            "created_at": "now",
        }

    def fake_get_messages(
        session_id: int,
        limit: int | None = None,
    ) -> list[DatabaseRecord]:
        assert session_id == 21
        assert limit == 4
        return []

    def fake_add_message(session_id: int, role: str, content: str) -> int:
        stored_messages.append((session_id, role, content))
        return len(stored_messages)

    def fake_responder(
        system_prompt: str,
        message: str,
        memory: Sequence[Mapping[str, object]] | None,
    ) -> tuple[str, list[MemoryMessage]]:
        assert "Transcript about system design tradeoffs." in system_prompt
        assert message == "My answer"
        assert memory == []
        return "Mocked coaching feedback", []

    monkeypatch.setattr(chat_module, "get_video", fake_get_video)
    monkeypatch.setattr(
        chat_module,
        "count_chat_sessions_by_video",
        fake_count_sessions,
    )
    monkeypatch.setattr(chat_module, "create_chat_session", fake_create_session)
    monkeypatch.setattr(chat_module, "get_chat_session", fake_get_session)
    monkeypatch.setattr(chat_module, "get_messages", fake_get_messages)
    monkeypatch.setattr(chat_module, "add_message", fake_add_message)

    service = ChatService(app_settings=app_settings, responder=fake_responder)

    assert service.start_chat(7) == 21
    answer = service.send_message(21, "My answer")

    assert answer.answer == "Mocked coaching feedback"
    assert stored_messages == [
        (21, "user", "My answer"),
        (21, "assistant", "Mocked coaching feedback"),
    ]
