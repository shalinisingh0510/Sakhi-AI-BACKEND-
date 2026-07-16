# Sakhi AI Backend Implementation Log

## Current Task

User profiles and role management.

## Completed Work

- Created the initial FastAPI project structure.
- Added centralized app configuration with environment-based settings.
- Hardened settings loading with a project-specific `SAKHI_` environment prefix.
- Added structured logging bootstrap.
- Added API routing for a versioned health endpoint.
- Added a root application entry point with CORS support.
- Added a basic health check test.
- Added project metadata and local development ignore rules.
- Added ignore rules for generated packaging artifacts and the pre-existing lowercase `implementation` file.
- Added password hashing helpers and signed token support using the standard library.
- Added in-memory user storage with session issuance for register, login, and refresh flows.
- Added authenticated profile and admin-only routes with role-based authorization checks.
- Added integration tests for registration, login, refresh, profile lookup, and role enforcement.
- Added a SQLite-backed auth persistence layer with schema bootstrap and reusable lookup methods.
- Added a configurable database path setting and wired app startup to use the SQLite store.
- Added an integration test that verifies users survive across app instances when the same database file is reused.
- Added profile update support, preferred language storage, and admin role management APIs.
- Added tests for user profile updates, persistent login state, admin user listing, and role changes.
- Updated this implementation log after completing the profile and role-management step.

## Files Created or Modified

- `.env.example`
- `.gitignore`
- `IMPLEMENTATION.md`
- `app/__init__.py`
- `app/api/__init__.py`
- `app/api/dependencies.py`
- `app/api/router.py`
- `app/api/v1/__init__.py`
- `app/api/v1/endpoints/__init__.py`
- `app/api/v1/endpoints/admin.py`
- `app/api/v1/endpoints/auth.py`
- `app/api/v1/endpoints/health.py`
- `app/core/__init__.py`
- `app/core/config.py`
- `app/core/logging.py`
- `app/core/security.py`
- `app/db/__init__.py`
- `app/db/auth_store.py`
- `app/main.py`
- `app/schemas/__init__.py`
- `app/schemas/auth.py`
- `app/services/__init__.py`
- `app/services/auth.py`
- `tests/__init__.py`
- `tests/test_auth.py`
- `tests/test_health.py`
- `pyproject.toml`

## Functionality Implemented

- FastAPI app factory with a root status route.
- Versioned health check endpoint at `/api/v1/health`.
- Environment-driven app settings and CORS configuration.
- Safer environment resolution that avoids collisions with unrelated machine variables.
- Logging configuration placeholder for future structured logging.
- JWT-style signed access and refresh tokens using HMAC-SHA256.
- Password hashing with PBKDF2 and per-user salts.
- SQLite-backed user registration, login, refresh, profile lookup, and profile updates.
- Preferred language storage for multilingual user preferences.
- Role-based authorization helpers and admin-only user listing and role update endpoints.
- Automated test coverage for health, auth, persistence, profile, and role-management flows.

## Current Progress

- User profile fields and role updates are now backed by SQLite and exposed through the API.
- The next step is to expand beyond auth and profiles into AI conversation and content modules.

## Remaining Work

- AI conversation services.
- Lessons and educational content APIs.
- Multilingual content support.
- Progress tracking.
- Notifications.
- Analytics and admin APIs.
- Input validation hardening and security middleware.
- Expanded automated tests.
- Deployment and production hardening.
