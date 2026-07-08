from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import require_admin
from app.api.errors import APINotFoundError
from app.core.logger import get_logger
from app.db.repositories.sessions import delete_chat_session
from app.db.repositories.videos import delete_video

router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin)],
)
logger = get_logger(__name__)


@router.delete("/videos/{video_id}")
def remove_video(video_id: Annotated[int, Path(gt=0)]) -> dict[str, int]:
    """Delete a video by id through the administrative API."""
    deleted = delete_video(video_id)
    if not deleted:
        raise APINotFoundError("Video was not found")

    logger.info("Admin deleted video: video_id=%s", video_id)
    return {"deleted_video_id": video_id}


@router.delete("/chat/sessions/{session_id}")
def remove_chat_session(session_id: Annotated[int, Path(gt=0)]) -> dict[str, int]:
    """Delete a chat session by id through the administrative API."""
    deleted = delete_chat_session(session_id)
    if not deleted:
        raise APINotFoundError("Chat session was not found")

    logger.info("Admin deleted chat session: session_id=%s", session_id)
    return {"deleted_session_id": session_id}
