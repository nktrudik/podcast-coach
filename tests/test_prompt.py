from app.services.chat import build_interview_coach_system_prompt


def test_prompt_builder_includes_transcript_and_coaching_role() -> None:
    """Prompt builder keeps the product role and video transcript context."""
    transcript = "A staff engineer explains event-driven architecture."

    prompt = build_interview_coach_system_prompt(transcript)

    assert "English Interview Coach for IT specialists" in prompt
    assert transcript in prompt
    assert "Ask one interview-style question" in prompt
