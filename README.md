# StoryCast

StoryCast extracts permitted news articles, creates an evidence-backed script with Gemini, generates Kokoro narration and Wan scene clips through Hugging Face hosted inference, and combines them into a captioned vertical MP4 with FFmpeg.

The application intentionally does not include authentication or automatic publishing.

## Pipeline

```text
RSS/site -> article extraction -> Gemini script -> editorial review
         -> hosted Kokoro audio -> hosted Wan clips -> FFmpeg MP4 -> download
```

LangGraph runs two workflows:

- `load_article -> generate -> ground -> persist`
- `prepare -> narrate -> captions -> visuals -> render -> finalize`

## Main components

- FastAPI and Swagger API
- Next.js frontend
- Feedparser and Trafilatura news collection
- Gemini structured script generation
- Hugging Face hosted Kokoro narration
- Hugging Face hosted Wan video generation
- FFmpeg captioning and final composition
- Celery and Redis background jobs
- SQLite locally or PostgreSQL with Docker
- Local or S3-compatible output storage

The laptop does not download Kokoro or Wan weights. Hosted inference requires an `HF_TOKEN`, and usage is subject to the selected Hugging Face provider's quota or billing.

## Run with Docker

1. Copy `.env.example` to `.env`.
2. Set `GEMINI_API_KEY` and `HF_TOKEN`.
3. Start the stack:

```cmd
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

Only FFmpeg and Chromium run inside the backend container. AI model inference runs in the cloud.

## Deploy to AWS

The repository includes an EC2 production stack with automatic HTTPS, private
S3 exports, ECR images, IAM-role credentials, and GitHub Actions deployment.
See [`deploy/aws/README.md`](deploy/aws/README.md) for the complete setup.

## Lightweight backend development

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[test]"
alembic upgrade head
uvicorn app.main:app --reload
```

Redis and Celery workers are still needed for collection, script, and rendering jobs. Docker Compose is the easiest way to start them together.

## Required environment variables

```env
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.5-flash-lite
HF_TOKEN=your_hugging_face_token

TTS_PROVIDER=huggingface
HF_TTS_MODEL=hexgrad/Kokoro-82M

VIDEO_PROVIDER=huggingface
HF_VIDEO_PROVIDER=fal-ai
HF_VIDEO_MODEL=Wan-AI/Wan2.2-TI2V-5B
```

Create a Hugging Face token at https://huggingface.co/settings/tokens with Inference Providers permission.

## Tests

Tests use fixtures and do not call Gemini or Hugging Face:

```cmd
.venv\Scripts\python -m pytest
```

## Important constraints

- Collect only sources you are allowed to access.
- Review and approve every generated script before rendering.
- Generated visuals are prompted as editorial illustrations, not genuine footage of a reported event.
- Do not expose this unauthenticated application directly to the public internet.

## Layout

```text
app/
  core/          settings and database
  models/        SQLAlchemy entities
  schemas/       API contracts
  repositories/ persistence
  services/      collection, Gemini, hosted media, FFmpeg, storage
  workflows/     LangGraph workflows
  tasks/         Celery jobs
  routers/       FastAPI routes
frontend/        Next.js studio
migrations/      Alembic migrations
tests/           backend tests
```
