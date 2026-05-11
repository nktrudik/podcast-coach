# Podcast Coach

Podcast Coach - MVP-сервис для практики английской речи по YouTube-подкастам и длинным видео.

Стек проекта:

- Backend: FastAPI
- Frontend: Streamlit
- База данных: SQLite
- Загрузка YouTube: yt-dlp
- Конвертация аудио: FFmpeg
- STT/LLM: OpenRouter
- Конфиг: pydantic-settings через `.env`

## Что нужно для запуска

Минимально нужно заполнить `.env`:

```env
API_KEY=your_openrouter_api_key
ADMIN_API_KEY=your_admin_key
```

Готовый шаблон лежит в `.env.example`.

Важно:

- `.env` нельзя коммитить
- cookies нельзя коммитить
- `storage/`, `temp/`, `secrets/` нельзя коммитить
- `ffmpeg.exe` и другие бинарники FFmpeg нельзя класть в репозиторий

## YouTube cookies

Если YouTube отвечает `Sign in to confirm you're not a bot`, добавь cookies-файл,
экспортированный из авторизованного браузера, и укажи его в конфиге:

```env
YOUTUBE_COOKIES_FILE=cookies_www.youtube.com.txt
```

Backend ищет относительное имя файла в рабочей директории, затем в `/etc/secrets`
(Render Secret Files), затем в `/app/secrets` (Docker Compose). На Render файл
`cookies_www.youtube.com.txt` должен лежать как Secret File по пути:

```text
/etc/secrets/cookies_www.youtube.com.txt
```

Можно также указать абсолютный путь:

```env
YOUTUBE_COOKIES_FILE=/etc/secrets/cookies_www.youtube.com.txt
```

## Локальный запуск без Docker

Создать окружение и поставить зависимости:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Заполнить `.env`, затем запустить backend:

```powershell
.\.venv\Scripts\python.exe main.py
```

В другом терминале запустить frontend:

```powershell
.\.venv\Scripts\streamlit.exe run frontend/app.py
```

Адреса:

- Backend Swagger: http://127.0.0.1:8000/docs
- Frontend: http://127.0.0.1:8501
- Health-check: http://127.0.0.1:8000/health

## Запуск через Docker Compose

Создать `.env` из шаблона:

```bash
cp .env.example .env
```

Заполнить `API_KEY` и `ADMIN_API_KEY`, затем запустить:

```bash
docker compose up --build
```

После запуска:

- Backend Swagger: http://localhost:8000/docs
- Frontend: http://localhost:8501
- Health-check: http://localhost:8000/health

Внутри Docker Compose frontend обращается к backend по адресу:

```env
FRONTEND_BACKEND_BASE_URL=http://backend:8000
```
