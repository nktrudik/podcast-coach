from app.core.youtube import normalize_youtube_url


def test_normalize_youtube_url_returns_canonical_watch_url() -> None:
    """YouTube URL normalization returns a canonical watch URL and video id."""
    canonical_url, video_id = normalize_youtube_url(
        "https://youtu.be/gO1Cm_A_pO8?si=abc"
    )

    assert canonical_url == "https://www.youtube.com/watch?v=gO1Cm_A_pO8"
    assert video_id == "gO1Cm_A_pO8"
