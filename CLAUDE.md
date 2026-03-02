# EALE — Evidence-Aligned Learning Engine

## Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (sync), psycopg2-binary, APScheduler
- **Database**: PostgreSQL (Docker: `eale:eale_secret@localhost:5432/eale`)
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS, TanStack Query, Recharts
- **Chrome Extension**: MV3, Shadow DOM overlay, chrome.storage.sync
- **Config**: Pydantic v2 + pydantic-settings

## Key Paths
- `backend/app/main.py` — FastAPI app, lifespan (tables + seed + scheduler)
- `backend/app/models.py` — SQLAlchemy models (Student, Topic, Question, Attempt, ScheduledTask)
- `backend/app/services/metrics_service.py` — DUS formula computations
- `backend/app/services/seed.py` — Demo data seed
- `backend/app/services/scheduler_service.py` — APScheduler spaced-retest logic
- `backend/app/services/llm_service.py` — OpenAI: question gen, grading, vision, Sora video, TTS-1-HD
- `backend/app/services/youtube_service.py` — YouTube transcript fetching (youtube-transcript-api v1.x)
- `backend/app/routers/extension.py` — Chrome extension endpoints (/context, /submit, /learn, /assess-video)
- `chrome-extension/content.js` — Shadow DOM quiz overlay (state machine), Learn It, attention monitoring
- `frontend/src/` — Next.js pages and components

## Run Commands

### Start everything (first time or after requirements.txt changes)
```bash
docker compose up --build -d
```

### Start everything (subsequent runs, no code changes)
```bash
docker compose up -d
```

### Start only backend + DB (skip frontend/compvis)
```bash
docker compose up --build -d db backend
```

### Watch logs
```bash
docker compose logs -f backend       # backend logs
docker compose logs -f compvis       # YOLOv8 inference logs
```

### Stop all services
```bash
docker compose down
```

### ⚠️ Critical: env var changes require `up -d`, NOT `restart`
```bash
# WRONG — does NOT re-read docker-compose.yml environment vars:
docker compose restart backend

# CORRECT — recreates container with new env vars:
docker compose up -d backend
```

### After changing requirements.txt
```bash
docker compose up --build -d backend
```

### Run tests
```bash
cd backend && PYTHONPATH=. python3.11 -m pytest tests/ -v
```

### Reset seed data
```bash
curl -X POST http://localhost:8000/api/v1/admin/reset
```

## Service URLs
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Frontend: http://localhost:3000
- CompVis (YOLOv8): http://localhost:8001
- Fake LMS testbench: open `testbench/fake-lms.html` in Chrome

## Demo API Keys (seed data)
- Alice Chen (fragile mastery): `student-alice-key`
- Bob Martinez (overconfident): `student-bob-key`
- Dana Faculty: `faculty-dana-key`

## DUS Formula
```
DUS = 0.30 × mastery + 0.30 × retention + 0.25 × transfer + 0.15 × calibration
```

## Chrome Extension Setup
```bash
cd chrome-extension && python3 generate_icons.py
# Then: chrome://extensions → Developer mode → Load unpacked → chrome-extension/
# Options page: set Student API Key = student-alice-key, Backend URL = http://localhost:8000
```

After any change to `content.js` or `manifest.json`:
→ `chrome://extensions` → click **Reload** on the EALE card

## CompVis / YOLOv8 Attention Monitoring
The CompVis service starts with a ResNet50 classification model. To enable person detection (required for attention monitoring), call after `docker compose up`:

```bash
curl -X POST http://localhost:8001/switch-model \
  -H "Content-Type: application/json" \
  -d '{"model_name": "yolov8n", "config_overrides": {"task": "detection"}}'
```

Without `config_overrides: {"task": "detection"}`, the model stays in classification mode and `boxes` is always null → attention button never recovers from red.

## LLM Mode
Set in `docker-compose.yml` backend environment (then `docker compose up -d backend`):
```yaml
OPENAI_API_KEY: "sk-..."
OPENAI_MODEL: "gpt-4o"
USE_LLM_CONTEXT: "true"
USE_LLM_GRADING: "true"
```

⚠️ Never commit `OPENAI_API_KEY` — GitHub push protection will block the push. Keep it only in the local `docker-compose.yml`.

## Learn It — Sora Video Lesson Flow
1. Extension POST `/api/v1/extension/learn` with `{topic, page_url, page_context}`
2. Backend fetches YouTube transcript if URL is YouTube
3. `generate_video_lesson()` in `llm_service.py`:
   - Tries Sora: GPT-4o writes cinematic prompt → `client.video.generations.create(model="sora", size="1280x720")` → polls every 6s (max 150s) → downloads MP4 → base64
   - Falls back silently to GPT-4o HTML canvas animation if Sora unavailable
   - Always runs: GPT-4o narration+quiz JSON → TTS-1-HD audio
4. Returns `{topic, html, audio_b64, quiz_questions, video_b64, video_type}`
5. Extension: if `video_type === "sora_mp4"` → native `<video>` element with fullscreen; else → sandboxed iframe
6. Timeout in content.js: 180s (Sora can take 60–90s)

## Extension Question Selection Priority (/context endpoint)
1. LLM-generated (USE_LLM_CONTEXT=true + not rate-limited) — always fresh
2. Keyword-matched from topic bank
3. Random question fallback
Note: Due-task retests are intentionally excluded from the extension — they appear only in the student dashboard.

## YouTube Transcript API
Uses `youtube-transcript-api>=1.2.4` (v0.6.2 is broken — ParseError).
Instance method API: `YouTubeTranscriptApi().fetch(video_id, languages=["en"])` returns `FetchedTranscriptSnippet` objects with `.text` attribute.
