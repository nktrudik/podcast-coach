# English Interview Coach for IT

English Interview Coach for IT is an MVP service for practicing spoken technical
English for IT job interviews with any technical YouTube video.

Upload a video about Python, ML, LLMs, backend, system design, algorithms,
databases, DevOps, or another technical topic. The service prepares a transcript,
then an AI coach helps you discuss the topic in English like in an interview:
it asks interview-style questions, corrects grammar and vocabulary, suggests
useful phrases, and helps turn your answers into stronger interview-ready
responses.

## How It Works

1. The user uploads a technical YouTube video.
2. The backend downloads audio and transcribes it.
3. The user starts an interview practice session.
4. The AI coach asks interview-style questions, gives feedback, corrects English,
   and helps improve the answer structure.

## Stack

- Backend: FastAPI
- Frontend: Streamlit
- Database: PostgreSQL
- YouTube ingestion: yt-dlp
- Audio conversion: FFmpeg
- STT/LLM: OpenRouter
- Config: pydantic-settings via `.env`
- Runtime/deploy: Docker and Docker Compose

The default database/user names may still use `podcast_coach` for compatibility
with existing local and Docker environments.

## Required Env

Copy `.env.example` to `.env` and fill the required values:

```env
API_KEY=your_openrouter_api_key
ADMIN_API_KEY=your_admin_key
```

Do not commit `.env`, cookies, `storage/`, `temp/`, `secrets/`, PostgreSQL data,
or FFmpeg binaries.

## YouTube Cookies

If YouTube responds with `Sign in to confirm you're not a bot`, add a cookies
file exported from an authorized browser and point the config to it:

```env
YOUTUBE_COOKIES_FILE=cookies_www.youtube.com.txt
```

The backend looks for a relative filename in the working directory, then in
`/etc/secrets` for Render Secret Files, then in `/app/secrets` for Docker Compose.

For Render, upload the file as a Secret File at:

```text
/etc/secrets/cookies_www.youtube.com.txt
```

For Docker Compose, keep the local filename in `YOUTUBE_COOKIES_FILE`; Compose
mounts it into `/app/secrets` read-only without copying it into the image.

## Local Run Without Docker

Create a virtual environment, install dependencies, and prepare `.env`:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

For local run without Docker, PostgreSQL must be available. If the database runs
on the host, set `DATABASE_URL`, for example:

```env
DATABASE_URL=postgresql://podcast_coach:podcast_coach@localhost:5432/podcast_coach
```

Start the backend:

```powershell
.\.venv\Scripts\python.exe main.py
```

Start the frontend in another terminal:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/app.py
```

URLs:

- Backend Swagger: http://127.0.0.1:8000/docs
- Frontend: http://127.0.0.1:8501
- Health-check: http://127.0.0.1:8000/health

## Docker Compose

Create `.env` from the template:

```bash
cp .env.example .env
```

Fill `API_KEY` and `ADMIN_API_KEY`, then run:

```bash
docker compose up --build
```

Docker Compose starts PostgreSQL automatically and stores data in the named volume
`postgres_data`, so data survives backend/frontend rebuilds.

After startup:

- Backend Swagger: http://localhost:8000/docs
- Frontend: http://localhost:8501
- Health-check: http://localhost:8000/health

Inside Docker Compose, the frontend talks to the backend through:

```env
FRONTEND_BACKEND_BASE_URL=http://backend:8000
```
