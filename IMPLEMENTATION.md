# Sakhi AI Backend Implementation Log

## Current Status

**All core features plus next-step enhancements are implemented and tested. 79 tests passing.**

---

## Completed Work

### Phase 1 — Foundation
- Created the initial FastAPI project structure.
- Added centralized app configuration with environment-based settings using `pydantic-settings` with a `SAKHI_` prefix.
- Added structured logging bootstrap.
- Added API routing for a versioned health endpoint.
- Added a root application entry point with CORS support.
- Added project metadata (`pyproject.toml`) and local development ignore rules.

### Phase 2 — Authentication & Authorization
- Added password hashing helpers (PBKDF2-SHA256, per-user salts) and signed HMAC-SHA256 token support.
- Added in-memory user storage with session issuance for register, login, and refresh flows.
- Added authenticated profile and admin-only routes with role-based authorization checks.
- Added a SQLite-backed auth persistence layer with schema bootstrap and reusable lookup methods.
- Added profile update support, preferred language storage (10 languages), and admin role management APIs.
- Added integration tests for registration, login, refresh, profile lookup, persistence across restarts, and role enforcement.

### Phase 3 — AI Conversations
- Added AI conversation schemas, a SQLite-backed conversation store, safe rule-based reply generation, and authenticated conversation endpoints.
- Added tests for conversation creation, message exchange, persistence, and private conversation access enforcement.

### Phase 4 — Educational Lessons
- Added lesson schemas, a SQLite-backed lesson catalog, seeded educational content (3 default lessons), and public/admin lesson APIs.
- Added multilingual lesson translations, language-aware retrieval with fallback to the base language.
- Added full-text search, category filtering, and language filtering on the lesson list endpoint.
- Added tests for the public lesson catalog, localized content with fallback, admin CRUD, and persistence.

### Phase 5 — Progress Tracking
- Added lesson progress schemas, a SQLite-backed progress store, authenticated progress endpoints, and persistence tests.
- Progress statuses: `not_started`, `in_progress`, `completed` with automatic normalization.
- Lesson completion triggers an automatic `lesson_completed` notification.

### Phase 6 — Notifications
- Added notification schemas, a SQLite-backed notification store, authenticated notification endpoints, and admin broadcast capabilities.
- Read/unread tracking with `read_at` timestamp; unread count endpoint.
- Admin can broadcast to all users or target a specific user.
- Notification types: `announcement`, `lesson_completed`, `reminder`, `system`.

### Phase 7 — Analytics
- Added analytics schemas, a SQLite-backed analytics store, event tracking, and user/admin analytics endpoints.
- 10 supported event types. User engagement metrics, platform overview, event breakdown, daily activity, top users, full analytics report.

### Phase 8 — Security Middleware
- Added rate limiting (60 req/min per client, configurable), request size limit (10 MB), and comprehensive security headers (HSTS, CSP-related, X-Frame-Options, Referrer-Policy, Permissions-Policy).
- Comprehensive middleware tests (security headers, rate limiting enforcement, per-user identifiers, HSTS, Referrer-Policy, Permissions-Policy).

### Phase 9 — Deployment & Production Hardening
- Added comprehensive `DEPLOYMENT.md` covering systemd, Docker, Nginx/HTTPS, backup strategy, scaling guidance, and a 12-point deployment checklist.
- Added Gunicorn as an optional `[production]` dependency.
- Wired all stores, services, and middleware together in the app factory.

### Phase 10 — Next-Step Enhancements (this session)
- **Pluggable AI provider**: Added `app/services/ai_providers.py` with `RuleBasedProvider` (default, no API key) and `OpenAIProvider` (GPT-4o-mini with full conversation history context, automatic fallback to rule-based on error or missing `openai` package).
- **OpenAI settings**: Added `SAKHI_AI_PROVIDER_NAME`, `SAKHI_OPENAI_API_KEY`, `SAKHI_OPENAI_MODEL` to `Settings` and documented them in `.env.example`.
- **`openai` optional dependency**: Added `openai>=1.30` as `[ai]` extras in `pyproject.toml`.
- **Password change endpoint**: `POST /api/v1/auth/me/change-password` — verifies current password, rejects same-as-current, returns 204, persists across restarts.
- **`ChangePasswordRequest` schema** added to `app/schemas/auth.py`.
- **`change_password` method** added to `AuthService`, `InMemoryAuthStore`, and `SQLiteAuthStore`.
- **Pagination**: Added `page` / `page_size` query params to conversations and notifications list endpoints via shared `pagination_params` dependency. Added `SAKHI_DEFAULT_PAGE_SIZE` and `SAKHI_MAX_PAGE_SIZE` settings.
- **WebSocket real-time notifications**: `wss://.../api/v1/ws/notifications?token=<access_token>` — authenticates via token query param, sends welcome on connect, pushes JSON notification payloads instantly, echoes pong to client pings, sends server heartbeat pings every 30 seconds.
- **`WebSocketManager`** singleton (`app/core/websocket_manager.py`) tracks per-user connections and supports broadcast.
- **`NotificationService.create_notification`** now fire-and-forgets a WebSocket push for any connected user.
- **Enhanced health check**: `/api/v1/health` now probes SQLite connectivity and returns a `database` field; status becomes `"degraded"` if the DB is unreachable.
- **Admin dashboard stats**: `GET /api/v1/admin/stats` returns user counts (total, 7-day active, 30-day active), lesson counts (total, published, unpublished, categories), and platform engagement totals in a single request.
- **`requirements.txt`**: Created (referenced by DEPLOYMENT.md but previously missing).
- **GitHub Actions CI/CD**: `.github/workflows/ci.yml` — lint (ruff check + format), tests on Python 3.11 and 3.12, security audit (pip-audit).
- **New tests**: `test_ai_providers.py` (13), `test_password_change.py` (5), `test_pagination.py` (5), `test_websocket.py` (5), `test_admin_stats.py` (8). Total: **79 tests passing**.

---

## Files Created or Modified

### Configuration & Project
- `.env.example`
- `.gitignore`
- `pyproject.toml`
- `requirements.txt` *(new)*
- `.github/workflows/ci.yml` *(new)*

### Documentation
- `DEPLOYMENT.md`
- `IMPLEMENTATION.md`

### Application Core
- `app/__init__.py`
- `app/main.py`
- `app/core/__init__.py`
- `app/core/config.py`
- `app/core/logging.py`
- `app/core/middleware.py`
- `app/core/security.py`
- `app/core/websocket_manager.py` *(new)*

### API Layer
- `app/api/__init__.py`
- `app/api/dependencies.py`
- `app/api/router.py`
- `app/api/v1/__init__.py`
- `app/api/v1/endpoints/__init__.py`
- `app/api/v1/endpoints/admin.py`
- `app/api/v1/endpoints/analytics.py`
- `app/api/v1/endpoints/auth.py`
- `app/api/v1/endpoints/conversations.py`
- `app/api/v1/endpoints/health.py`
- `app/api/v1/endpoints/lessons.py`
- `app/api/v1/endpoints/notifications.py`
- `app/api/v1/endpoints/progress.py`
- `app/api/v1/endpoints/ws.py` *(new)*

### Database Layer
- `app/db/__init__.py`
- `app/db/ai_store.py`
- `app/db/analytics_store.py`
- `app/db/auth_store.py`
- `app/db/lesson_store.py`
- `app/db/notification_store.py`
- `app/db/progress_store.py`

### Schemas
- `app/schemas/__init__.py`
- `app/schemas/ai.py`
- `app/schemas/analytics.py`
- `app/schemas/auth.py`
- `app/schemas/lesson.py`
- `app/schemas/notification.py`
- `app/schemas/progress.py`

### Services
- `app/services/__init__.py`
- `app/services/ai.py`
- `app/services/ai_providers.py` *(new)*
- `app/services/analytics.py`
- `app/services/auth.py`
- `app/services/lessons.py`
- `app/services/notifications.py`
- `app/services/progress.py`

### Tests
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_admin_stats.py` *(new)*
- `tests/test_ai_providers.py` *(new)*
- `tests/test_analytics.py`
- `tests/test_auth.py`
- `tests/test_conversations.py`
- `tests/test_health.py`
- `tests/test_lessons.py`
- `tests/test_middleware.py`
- `tests/test_notifications.py`
- `tests/test_pagination.py` *(new)*
- `tests/test_password_change.py` *(new)*
- `tests/test_progress.py`
- `tests/test_websocket.py` *(new)*

---

## Functionality Implemented

### Application Foundation
- FastAPI app factory (`create_app`) with a root status route and full dependency injection via `app.state`.
- Versioned health check at `/api/v1/health` with SQLite DB connectivity probe; returns `database: ok/error/unknown` and `status: ok/degraded`.
- Environment-driven settings with `SAKHI_` prefix. Pagination, AI provider, and rate-limit settings all configurable.
- CORS middleware with configurable allowed origins. Structured logging on startup.

### Security
- HMAC-SHA256 signed access and refresh tokens (no third-party JWT library).
- PBKDF2-SHA256 password hashing with per-user random salts (390,000 iterations).
- Rate limiting: 60 req/min per client (configurable), token-hash for authenticated users, IP for anonymous. Health/root exempt.
- Request size limit: 10 MB max body, HTTP 413 on excess.
- Security headers on all responses: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, HSTS (1 year + includeSubDomains), `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (geolocation/microphone/camera blocked).
- Role-based authorization via `require_roles()` FastAPI dependency.

### Authentication & Users
- Register, login, token refresh, get profile, update profile, **change password** (new).
- Preferred language per user (10 supported: english, hindi, bengali, marathi, tamil, telugu, kannada, gujarati, punjabi, odia).
- Admin: list users, update user role (user/admin/moderator).
- All auth data persists in SQLite across app restarts.

### AI Conversations
- Pluggable AI provider architecture:
  - `RuleBasedProvider` — keyword-matched educational responses, no API key, always available, used in tests.
  - `OpenAIProvider` — calls GPT-4o-mini with full conversation history as context, system prompt enforcing educational scope. Automatically falls back to rule-based on API error, missing key, or missing `openai` package.
- Select provider via `SAKHI_AI_PROVIDER_NAME=rule-based|openai`.
- Conversation history capped at `SAKHI_CONVERSATION_HISTORY_LIMIT` messages (default 8) when sent to OpenAI.
- Private ownership enforced — users cannot access other users' conversations.
- List endpoint now supports **pagination** (`page`, `page_size`).

### Educational Lessons
- Seeded catalog (3 default lessons). Full admin CRUD.
- Public filtering by category, language, free-text search, and content language.
- Multilingual translations stored per lesson; automatic fallback to base language.
- Category list endpoint.

### Progress Tracking
- Upsert semantics (one record per user per lesson). Statuses: `not_started`, `in_progress`, `completed`.
- Progress summary: totals, completion rate, average percent.
- Lesson completion auto-creates a `lesson_completed` notification.

### Notifications
- User inbox with read/unread tracking and `read_at` timestamp.
- Unread count endpoint.
- Admin broadcast to all users or a specific user.
- **Real-time push via WebSocket**: when a notification is created for a connected user it is instantly delivered over their WebSocket connection.
- List endpoint now supports **pagination** (`page`, `page_size`).

### WebSocket Real-Time Notifications *(new)*
- Endpoint: `wss://.../api/v1/ws/notifications?token=<access_token>`
- Authentication via token query param; rejects with close code 4001 on invalid token.
- Sends `{"type":"connected","user_id":"..."}` on successful connect.
- Pushes `{"type":"notification","data":{...NotificationItem}}` instantly when a notification is created.
- Echoes `{"type":"pong"}` to any client ping/keep-alive message.
- Server sends `{"type":"ping"}` heartbeat every 30 seconds.
- `WebSocketManager` singleton tracks per-user connections and supports broadcast to all connected users.

### Analytics
- 10 event types tracked. User engagement metrics.
- Admin: platform overview, event breakdown with percentages, daily activity (configurable window), top users by engagement, full analytics report.

### Admin Dashboard *(enhanced)*
- `GET /api/v1/admin/overview` — simple access check.
- `GET /api/v1/admin/stats` *(new)* — combined dashboard: user counts (total, 7d active, 30d active), lesson counts (total, published, unpublished, categories), engagement totals (events, lesson views/completions, conversations, messages). Single request.
- `GET /api/v1/admin/users` — list all users.
- `PATCH /api/v1/admin/users/{id}/role` — change role.
- `POST /api/v1/admin/notifications` — broadcast or targeted notification.
- Full lesson CRUD (`GET`, `POST`, `PATCH`, `DELETE`).

### Automated Tests (79 total)
| File | Tests | Coverage |
|------|-------|----------|
| `test_health.py` | 1 | Health endpoint |
| `test_admin_stats.py` | 8 | Enhanced health check, admin stats dashboard |
| `test_ai_providers.py` | 13 | Provider factory, rule-based content, OpenAI fallback, conversation history |
| `test_analytics.py` | 12 | Event tracking, metrics, platform analytics, access control, persistence |
| `test_auth.py` | 5 | Registration, login, refresh, RBAC, admin role management |
| `test_conversations.py` | 2 | Creation, persistence, privacy |
| `test_lessons.py` | 4 | Seeded catalog, localization/fallback, admin CRUD, persistence |
| `test_middleware.py` | 10 | Security headers, rate limiting, request size, HSTS, Referrer-Policy |
| `test_notifications.py` | 8 | Inbox, mark-as-read, broadcast, isolation, lesson trigger, metadata |
| `test_pagination.py` | 5 | Conversations/notifications pagination, boundary conditions |
| `test_password_change.py` | 5 | Change password, wrong password, same password, auth required, persistence |
| `test_progress.py` | 1 | Full progress flow with persistence |
| `test_websocket.py` | 5 | Auth rejection, welcome message, pong echo, manager lifecycle |

### Deployment & Production
- `DEPLOYMENT.md`: systemd, Docker, Nginx/HTTPS, backup, scaling, troubleshooting, 12-point checklist.
- `requirements.txt` for standard `pip install -r` workflow.
- `pyproject.toml` optional extras: `[dev]`, `[production]` (gunicorn), `[ai]` (openai).
- `.github/workflows/ci.yml`: lint → multi-Python tests → security audit on every push/PR.

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | None | Root status |
| GET | `/api/v1/health` | None | Health + DB probe |
| POST | `/api/v1/auth/register` | None | Register |
| POST | `/api/v1/auth/login` | None | Login |
| POST | `/api/v1/auth/refresh` | None | Refresh token |
| GET | `/api/v1/auth/me` | User | Get profile |
| PATCH | `/api/v1/auth/me` | User | Update profile |
| POST | `/api/v1/auth/me/change-password` | User | **Change password** |
| GET | `/api/v1/conversations` | User | List (paginated) |
| POST | `/api/v1/conversations` | User | Create conversation |
| GET | `/api/v1/conversations/{id}` | User | Get conversation |
| POST | `/api/v1/conversations/{id}/messages` | User | Send message |
| GET | `/api/v1/lessons` | None | List lessons |
| GET | `/api/v1/lessons/categories` | None | List categories |
| GET | `/api/v1/lessons/{slug}` | None | Get lesson |
| GET | `/api/v1/progress` | User | List progress |
| GET | `/api/v1/progress/summary` | User | Progress summary |
| GET | `/api/v1/progress/lessons/{slug}` | User | Get lesson progress |
| PUT | `/api/v1/progress/lessons/{slug}` | User | Update progress |
| GET | `/api/v1/notifications` | User | List (paginated) |
| GET | `/api/v1/notifications/unread-count` | User | Unread count |
| PATCH | `/api/v1/notifications/{id}/read` | User | Mark as read |
| WS | `/api/v1/ws/notifications?token=…` | User | **Real-time push** |
| POST | `/api/v1/analytics/events` | User | Track event |
| GET | `/api/v1/analytics/events` | User | List user events |
| GET | `/api/v1/analytics/engagement` | User | Engagement metrics |
| GET | `/api/v1/analytics/platform/overview` | Admin | Platform overview |
| GET | `/api/v1/analytics/platform/event-breakdown` | Admin | Event breakdown |
| GET | `/api/v1/analytics/platform/daily-activity` | Admin | Daily activity |
| GET | `/api/v1/analytics/platform/top-users` | Admin | Top users |
| GET | `/api/v1/analytics/platform/report` | Admin | Full analytics report |
| GET | `/api/v1/admin/overview` | Admin | Admin access check |
| GET | `/api/v1/admin/stats` | Admin | **Combined dashboard stats** |
| GET | `/api/v1/admin/users` | Admin | List all users |
| PATCH | `/api/v1/admin/users/{id}/role` | Admin | Update role |
| POST | `/api/v1/admin/notifications` | Admin | Broadcast notification |
| GET | `/api/v1/admin/lessons` | Admin | All lessons (incl. unpublished) |
| GET | `/api/v1/admin/lessons/{id}` | Admin | Get lesson by ID |
| POST | `/api/v1/admin/lessons` | Admin | Create lesson |
| PATCH | `/api/v1/admin/lessons/{id}` | Admin | Update lesson |
| DELETE | `/api/v1/admin/lessons/{id}` | Admin | Delete lesson |

---

## Remaining Work

All planned and next-step features are complete.

### Potential Future Enhancements
- **PostgreSQL migration** — for production-scale multi-instance deployments (SQLite is single-writer).
- **Redis caching** — cache lesson catalog, user sessions, and analytics aggregates.
- **Voice assistant** — voice input/output via speech-to-text and TTS APIs.
- **Video lessons** — cloud storage (S3/GCS) integration for video content.
- **Doctor consultation module** — appointment booking, teleconsultation, professional profiles.
- **Personalized learning paths** — recommendation engine based on progress, preferences, and engagement.
- **Community features** — moderated discussion boards or peer support groups.
- **Wearable integration** — health metric ingestion from wearable device APIs.
- **Token revocation / logout** — server-side token blacklist for immediate session invalidation.
- **Email notifications** — send notification emails via SendGrid/SES as a fallback when users are offline.
- **OpenAPI documentation export** — generate and host a Swagger/Redoc UI or export the spec for frontend teams.
- **Soft delete** — mark users/lessons as deleted rather than hard-removing them for audit trail support.
- **Full-text search upgrade** — replace in-memory string search with SQLite FTS5 or an external search engine.
