from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, status

from app.api.errors import APINotFoundError
from app.api.schemas import (
    UploadVideoRequest,
    UploadVideoResponse,
    VideoDetailResponse,
    VideoListItem,
)
from app.core.logger import get_logger
from app.core.status import VideoStatus
from app.db.repositories.videos import get_video, list_videos
from app.services.video_processing import (
    VideoProcessingService,
    get_video_processing_service,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/videos",
    response_model=UploadVideoResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_video(
    payload: UploadVideoRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[
        VideoProcessingService,
        Depends(get_video_processing_service),
    ],
) -> UploadVideoResponse:
    """Create a YouTube video processing job."""
    logger.info("Video processing job requested")
    job = service.create_job(payload.youtube_url)

    if job.status == VideoStatus.QUEUED:
        background_tasks.add_task(service.process_job, job.video_id)

    return UploadVideoResponse(
        job_id=job.job_id,
        video_id=job.video_id,
        status=job.status,
    )


@router.get("/videos", response_model=list[VideoListItem])
def get_videos() -> list[VideoListItem]:
    """Return uploaded videos for the frontend."""
    return [VideoListItem(**video) for video in list_videos()]


@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
def get_video_by_id(video_id: Annotated[int, Path(gt=0)]) -> VideoDetailResponse:
    """Return a single video by id."""
    video = get_video(video_id)
    if not video:
        raise APINotFoundError("Video was not found")

    return VideoDetailResponse(**video)
