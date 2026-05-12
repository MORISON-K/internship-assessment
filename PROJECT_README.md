# Sunbird AI GenAI Pipeline App

A small web app that accepts either typed text or an uploaded audio file, then runs it through Sunbird AI:

Input → (STT if audio) → Summarise → Translate (Ugandan local language) → TTS → Output (text + playable audio)

## Architecture overview

- **Backend (FastAPI)**
  - STT: `POST https://api.sunbird.ai/tasks/stt`
  - Summarise: `POST https://api.sunbird.ai/tasks/sunflower_simple`
  - Translate: `POST https://api.sunbird.ai/tasks/sunflower_inference`
  - TTS: `POST https://api.sunbird.ai/tasks/tts`
- **Frontend (Next.js)**
  - Calls the backend endpoints and renders intermediate results.

## Local setup

### 1) Backend (FastAPI)

1. Create `.env` (copy from `.env.example`):
   - `SUNBIRD_API_TOKEN=...`

2. Install dependencies:
   - `python -m pip install -r requirements.txt`

3. Run the API:
   - `python -m uvicorn backend.main:app --reload --port 8000`

Backend endpoints:
- `GET  /api/v1/health`
- `GET  /api/v1/languages`
- `POST /api/v1/pipeline/text`
- `POST /api/v1/pipeline/audio`
- `GET  /api/v1/audio/{audio_id}` (backend-proxied audio)

### 2) Frontend (Next.js)

1. Configure backend URL (optional):
   - copy `frontend/.env.local.example` → `frontend/.env.local`

2. Install + run:
   - `cd frontend`
   - `npm install`
   - `npm run dev`

Then open: http://localhost:3000

## Environment variables

- `SUNBIRD_API_TOKEN` (required): Sunbird API bearer token used by the backend.
- `CORS_ORIGINS` (optional): comma-separated allowed origins for the frontend.
- `NEXT_PUBLIC_BACKEND_URL` (optional): frontend base URL for FastAPI (defaults to `http://localhost:8000`).

## Known limitations

- Audio files must be parseable by `mutagen` so the app can enforce the **5-minute** limit.
- The backend proxies generated audio via an in-memory TTL store (good for local/dev; not multi-worker safe).
