# Sakhi AI Backend Deployment Guide

This guide covers the deployment workflow for taking the Sakhi AI backend live in a production environment.

## 1. Pre-launch Checklist

Before initiating deployment, verify the following:

- [ ] **Infrastructure Provisioning**:
  - PostgreSQL database is provisioned and connection string is available.
  - Redis instance is running and accessible (for caching and rate-limiting).
- [ ] **API Keys & Quotas**:
  - OpenAI API key is active.
  - Usage limits are appropriately configured to avoid unexpected cutoffs.
- [ ] **Security Secrets**:
  - Generated a strong 32-byte `SAKHI_SECRET_KEY` for JWT signing.
  - `SAKHI_SENTRY_DSN` is generated from your Sentry project.

## 2. Deployment Instructions

### Option A: Render (Zero-config)
The repository includes a `render.yaml` infrastructure-as-code file.
1. Connect your GitHub repository to Render via the Dashboard.
2. Select **Blueprint** and point to the `render.yaml` file.
3. Add your secrets (`SAKHI_OPENAI_API_KEY`, `SAKHI_SECRET_KEY`, `SAKHI_SENTRY_DSN`) in the Render Dashboard when prompted.

### Option B: Railway / Generic Platform as a Service (PaaS)
The repository includes a `Procfile` and `scripts/start_production.sh`.
1. Link your repository.
2. Set the Environment Variables defined in `.env.example`.
3. The platform will automatically execute the `Procfile` `web` command.
4. Ensure the platform is routing traffic to the port specified in the `$PORT` environment variable.

### Option C: AWS / Docker Native
1. Build the multi-architecture image:
   ```bash
   docker buildx build -t sakhi-ai-backend:latest --push .
   ```
2. Pull and run the image on your instance:
   ```bash
   docker run -p 8000:8000 --env-file .env sakhi-ai-backend:latest
   ```

## 3. Post-Deployment Smoke Test

Once the application is live, run the following verification checklist:

1. **Health Check**:
   Navigate to `https://<your-deployment-url>/api/v1/health`. Ensure it returns HTTP `200 OK`.
2. **CORS Verification**:
   Attempt to access the API from your Next.js frontend (`https://sakhi-ai-frontend-delta.vercel.app`). Confirm there are no CORS preflight errors in the browser console.
3. **SSE / Chat Message API**:
   Open the frontend chat interface and send a message. Verify that responses are returned properly, matching the backend contract.
4. **Sentry Error Capture**:
   Trigger an intentional failure (e.g., passing invalid arguments to an endpoint) and verify that the error appears in your Sentry dashboard.
5. **Admin Access**:
   Log in with a user granted the `ADMIN` role. Navigate to `https://<your-deployment-url>/api/v1/admin/dashboard` to verify successful role-based access.
