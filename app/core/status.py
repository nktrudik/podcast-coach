from enum import StrEnum


class VideoStatus(StrEnum):
    """Processing state for a YouTube video ingestion job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


READY_STATUSES = {VideoStatus.READY.value}
ACTIVE_STATUSES = {VideoStatus.QUEUED.value, VideoStatus.PROCESSING.value}
