# Podcast Coach

Podcast Coach is a local MVP service for practicing spoken English with YouTube podcast transcripts.

Backend: FastAPI. Frontend: Streamlit. DB: SQLite. YouTube ingestion: yt-dlp + ffmpeg. STT/LLM: OpenRouter.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Fill the required values in `.env`:

```env
API_KEY=your_openrouter_api_key
ADMIN_API_KEY=your_admin_key
```

Run the backend:

```powershell
.\.venv\Scripts\python.exe main.py
```

Run the frontend in another terminal:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/app.py
```

Backend docs: http://127.0.0.1:8000/docs

Frontend: http://127.0.0.1:8501

Health check: http://127.0.0.1:8000/health

## Docker Compose

Create `.env` from `.env.example`, fill the required values, then run:

```bash
docker compose up --build
```

Backend docs: http://localhost:8000/docs

Frontend: http://localhost:8501

The frontend container talks to the backend through `http://backend:8000`, not `127.0.0.1`.

## FFmpeg

For local Windows/macOS/Linux runs, install FFmpeg manually and make sure `ffmpeg` is available in `PATH`.

In Docker, the backend image installs FFmpeg with `apt-get`. Do not put `ffmpeg.exe`, `ffprobe.exe`, or other FFmpeg binaries into the repository.

## YouTube Cookies

Cookies are optional and only needed when YouTube blocks downloading.

Cookies are secrets. Do not commit them. For local runs, set a local path in `.env`:

```env
YOUTUBE_COOKIES_FILE=/path/to/youtube_cookies.txt
```

For Docker, mount the cookies file read-only and use the container path:

```yaml
./secrets/youtube_cookies.txt:/app/secrets/youtube_cookies.txt:ro
```

```env
YOUTUBE_COOKIES_FILE=/app/secrets/youtube_cookies.txt
```

The `secrets/` directory is ignored by Git and Docker build context.
