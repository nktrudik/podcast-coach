# Product

English Interview Coach for IT helps engineers turn technical video content into
technical English interview practice.

## Target User

The primary user is an IT specialist preparing for English-speaking interviews:
backend engineers, data engineers, ML engineers, DevOps engineers, QA engineers,
and technical leads.

## User Flow

1. The user finds a technical YouTube video related to a topic they want to
   discuss in interviews.
2. The user adds the URL to the app.
3. The backend extracts and transcribes the audio.
4. The user opens a ready video and starts a practice session.
5. The AI coach asks questions, reviews answers, improves wording, and extracts
   interview-ready phrases from the video.

## Coaching Modes

- Interview mode: asks realistic interview questions based on the transcript.
- Answer improvement: corrects grammar, vocabulary, structure, and clarity.
- Vocabulary mode: extracts useful technical phrases and collocations.
- Explanation mode: explains concepts from the transcript in clear English.
- Mock interview mode: evaluates technical clarity, English quality, and answer
  structure one question at a time.

## Current Scope

Implemented:

- YouTube URL ingestion.
- Background video processing with status polling.
- Transcript persistence.
- Chat sessions grounded in a video transcript.
- Vue frontend for upload, library, details, and practice chat.

Not implemented yet:

- User accounts.
- Durable job queue.
- Rich per-stage progress percentages.
- Stored screenshots or hosted demo media.
