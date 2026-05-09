from typing import Annotated

from fastapi import APIRouter, Path

from app.api.errors import APINotFoundError
from app.api.schemas import (
    UploadVideoRequest,
    UploadVideoResponse,
    VideoDetailResponse,
    VideoListItem,
)
from app.core.logger import get_logger
from app.db.repositories.videos import get_video, list_videos
from app.services.video_processing import process_video

router = APIRouter()
logger = get_logger(__name__)


@router.post("/videos")
def upload_video(payload: UploadVideoRequest) -> UploadVideoResponse:
    """Принимает ссылку на YouTube и запускает обработку видео."""
    logger.info("Получен запрос на обработку видео")
    video_id = process_video(payload.youtube_url)
    logger.info("Видео обработано успешно: video_id=%s", video_id)

    return UploadVideoResponse(video_id=video_id)


@router.get("/videos", response_model=list[VideoListItem])
def get_videos() -> list[VideoListItem]:
    """Возвращает список загруженных видео для интерфейса фронта."""
    return [VideoListItem(**video) for video in list_videos()]


@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
def get_video_by_id(video_id: Annotated[int, Path(gt=0)]) -> VideoDetailResponse:
    """Возвращает полные данные конкретного видео по его id."""
    video = get_video(video_id)
    if not video:
        raise APINotFoundError("Видео не найдено")

    return VideoDetailResponse(**video)
