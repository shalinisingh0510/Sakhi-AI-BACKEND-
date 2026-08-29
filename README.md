# 🌸 Sakhi AI – Backend FastAPI Server

This repository contains the backend for **Sakhi AI**, an AI-powered multilingual women's health education platform designed to educate, support, and empower girls and women with trusted, culturally sensitive, and scientifically accurate health information.

## 🏗 Project Architecture & Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (via SQLAlchemy)
- **Caching & Sessions**: Redis
- **AI Integration**: AsyncOpenAI (SSE Streaming)
- **Deployment**: Docker & Docker Compose
- **Observability**: Sentry & Prometheus

## 🚀 Quickstart Guide

1. **Clone and setup environment**:
   ```bash
   git clone https://github.com/shalinisingh0510/Sakhi-AI-BACKEND-.git
   cd Sakhi-AI-BACKEND-
   cp .env.example .env
   ```

2. **Configure `.env`**:
   Ensure `SAKHI_OPENAI_API_KEY`, `SAKHI_DATABASE_PATH`, and `SAKHI_REDIS_URL` are set.

3. **Run with Docker Compose**:
   ```bash
   docker-compose up -d --build
   ```
   This will spin up PostgreSQL, Redis, and the FastAPI application on `http://localhost:8000`.

## 🔗 Frontend Integration (Next.js)

To connect the Next.js frontend to this backend:

1. In your frontend's `.env.local`, set:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```

2. **CORS Configuration**:
   The backend explicitly trusts `https://sakhi-ai-frontend-delta.vercel.app` and `http://localhost:3000`. It exposes the custom headers `X-Conversation-Id` and `X-Response-Time`.

3. **SSE Chat Streaming Example**:
   The `POST /api/v1/chat/stream` endpoint emits SSE events matching this contract:
   - `data: {"type": "metadata", "conversation_id": "uuid", "language": "hi"}`
   - `data: {"type": "chunk", "content": "..."}`
   - `data: {"type": "safety", "flagged": true, "helpline": "1091"}`
   - `data: {"type": "done", "suggested_questions": ["..."]}`

## 📖 API Contract & Documentation

FastAPI automatically generates interactive OpenAPI documentation. 
Once the server is running, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

You can download the raw OpenAPI schema from `http://localhost:8000/openapi.json` to generate typed TypeScript clients using tools like `openapi-typescript-codegen`.

### Key Endpoints

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/api/v1/health` | GET | Readiness probe (DB/Redis) | None | `200 OK` |
| `/api/v1/auth/register` | POST | Register a new user | `{email, password, full_name, language}` | `201 Created` |
| `/api/v1/auth/login` | POST | Login for JWT | `OAuth2 Form Data` | `{access_token, token_type}` |
| `/api/v1/chat/stream` | POST | Multilingual SSE AI Chat | `{message, language}` | `text/event-stream` |
| `/api/v1/admin/dashboard` | GET | Admin Analytics Overview | None (Requires Admin JWT) | `200 OK` |

## 🛠 Testing

We use `pytest` for automated integration tests, including end-to-end verification workflows:
```bash
python scripts/e2e_verify.py
pytest --cov=app tests/
```