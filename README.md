# QuizzVN Admin Platform

QuizzVN is a full-stack quiz and e-learning management platform built with a FastAPI backend, a React/Vite admin dashboard, and a dedicated AI Agent service for background exam generation workflows.

The project focuses on practical education operations: managing teachers, students, classes, exams, documents, analytics, realtime chat, notifications, AI-assisted question generation, and payment-based AI credit usage.

## Demo Admin Account

Use this account for interview or demo testing after the local database is configured:

| Field    | Value             |
| -------- | ----------------- |
| Email    | `admin@gmail.com` |
| Password | `123456`          |

For a fresh local database, create or update the demo administrator with:

```powershell
.\venv\Scripts\python.exe -m app.scripts.create_admin --email admin@gmail.com --full-name "Demo Administrator" --password 123456 --role administrator
```

> This account is intended for demo or staging usage only. Change the password before connecting the project to production data.

## Key Features

- Role-based authentication for administrator, admin, teacher, and student users.
- Admin dashboard for CRM metrics, realtime traffic analytics, payment analytics, and platform monitoring.
- Teacher, student, class, exam, and document management from a centralized admin web app.
- Exam authoring with manual creation, text-based creation, image uploads, publishing controls, and class assignment.
- AI-assisted exam generation with background job tracking, draft editing, and save-to-quiz workflow.
- Student learning flow with class joining, exam discovery, attempt saving, submission, scoring, and results.
- Realtime chat, file attachments, message sharing, notifications, and online presence.
- Billing workflow for QC/AI credits with SePay order creation, wallet balance, ledger transactions, and webhook handling.
- Separate AI Agent service with Celery/Redis, dataset export, artifact archiving, model registry, and internal callback security.

## Tech Stack

| Layer       | Technology                                                       |
| ----------- | ---------------------------------------------------------------- |
| Backend API | Python, FastAPI, SQLAlchemy, Uvicorn                             |
| Database    | PostgreSQL-compatible database                                   |
| Realtime    | WebSocket, Redis pub/sub                                         |
| Admin Web   | React 19, TypeScript, Vite, Tailwind CSS, Recharts, lucide-react |
| AI Workflow | Gemini provider integration, AI Agent service, Celery, Redis     |
| Media       | Cloudinary-ready upload configuration                            |
| Payments    | SePay API and signed webhook verification                        |
| Testing     | Pytest test suites for backend and AI workflows                  |

## Repository Structure

```text
.
|-- app/                 # Main FastAPI application
|   |-- core/            # Config and security helpers
|   |-- models/          # SQLAlchemy models
|   |-- routers/         # API route modules
|   |-- schemas/         # Pydantic request/response schemas
|   |-- scripts/         # Operational scripts, including admin creation
|   `-- services/        # Business logic and storage bootstrap code
|-- admin-web/           # React/Vite admin dashboard
|-- ai-agent/            # Background AI generation and ML workflow service
|-- docs/                # Feature documentation and integration notes
|-- tests/               # Backend test suite
|-- Dockerfile           # API container definition
|-- requirements.txt     # Backend Python dependencies
`-- start.py             # Production API entrypoint
```

## Local Setup

### 1. Backend API

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create or update `.env` in the repository root:

```env
APP_NAME=QuizzVN API
DEBUG=true
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/quizzvn
SESSION_SECRET_KEY=change_this_for_local_dev
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
ADMIN_WEB_URL=http://localhost:3000
INCLUDE_LOCAL_DEV_CORS_ORIGINS=true
EMAIL_DELIVERY_MODE=log
```

Optional integrations can be enabled with variables such as `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `CLOUDINARY_URL`, `REDIS_URL`, `GEMINI_API_KEY`, `SEPAY_API_TOKEN`, and `SEPAY_WEBHOOK_SECRET`.

Prepare the demo administrator account:

```powershell
.\venv\Scripts\python.exe -m app.scripts.create_admin --email admin@gmail.com --full-name "Demo Administrator" --password 123456 --role administrator
```

Start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful backend URLs:

- Health check: `http://127.0.0.1:8000/health`
- Swagger docs: `http://127.0.0.1:8000/docs`

### 2. Admin Web

```powershell
cd admin-web
npm install
npm run dev
```

The admin web defaults to `http://127.0.0.1:8000` in development. To override it, create `admin-web/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Open the dashboard at:

```text
http://localhost:3000/login
```

### 3. AI Agent Service

The main backend can generate AI exams directly or dispatch work to the separate AI Agent service, depending on `AI_EXECUTION_MODE` and `AI_AGENT_URL`.

```powershell
cd ai-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
uvicorn ai_agent.main:app --reload --host 127.0.0.1 --port 8010
```

Common AI Agent variables:

```env
AI_AGENT_DATABASE_URL=sqlite:///./ai_agent.db
REDIS_URL=redis://localhost:6379/0
AI_AGENT_SHARED_SECRET=change_this_shared_secret
```

## Running Checks

Backend tests:

```powershell
.\venv\Scripts\python.exe -m pytest tests
```

Admin web type check and production build:

```powershell
cd admin-web
npm run lint
npm run build
```

AI Agent tests:

```powershell
cd ai-agent
$env:PYTHONPATH = "src"
python -m pytest tests
```

## API Areas

- `POST /auth/login` - local email/password login.
- `GET /auth/me` - current authenticated user and session.
- `/admin/*` - admin CRM, users, teachers, students, classes, exams, documents, invitations, and permissions.
- `/teacher/*` - teacher classes, students, documents, exams, assignments, and results.
- `/student/*` - student dashboard, classes, documents, exams, attempts, and results.
- `/chat/*` - contacts, conversations, messages, attachments, sharing, and WebSocket chat.
- `/api/ai-exams/*` - AI exam generation jobs, draft question editing, and saving generated exams.
- `/api/billing/*` - plans, orders, wallet, transactions, AI cost estimates, and SePay webhook handling.
- `/analytics/*` - page view and heartbeat tracking.

## Documentation

- `docs/email-verification.md` - email verification and OTP behavior.
- `docs/admin-invitations.md` - admin invitation and approval flow.
- `docs/sepay-billing.md` - SePay setup, QR payment flow, and webhook requirements.
- `docs/new api.md` - additional API notes.

## Deployment Notes

- The backend exposes `start.py` for process managers and platforms that provide a `PORT` environment variable.
- The API Dockerfile builds the FastAPI service from the repository root.
- The admin web uses Vite and can be deployed separately to a static hosting platform.
- Production deployments should provide secure values for database, session, OAuth, Redis, media, AI, and payment secrets.
