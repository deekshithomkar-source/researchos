# ResearchOS: Autonomous Research Agent

A focused MCA final-year project that plans research questions, retrieves scholarly
metadata, scores source quality, generates traceable reports, and preserves research
history. It is designed as a research workflow—not a general-purpose chatbot.

## Tech Stack

- Backend: Python, FastAPI, SQLAlchemy, SQLite
- Frontend: React + Vite
- Agent Logic: Modular research pipeline
- Database: SQLite for development

## Features

- User submits a research topic
- Agent creates sub-questions
- Retrieves real scholarly records from Semantic Scholar
- Uses real scholarly-provider fallback and reports unavailable or partial evidence
- Deduplicates and scores sources using transparent metadata signals
- Generates academic reports, literature reviews, or project proposals
- Formats references in APA or IEEE style
- Exports the generated report as Markdown
- Saves authenticated, user-owned research runs with background progress
- Shows previous research history

## Folder Structure

```text
autonomous-research-agent/
  backend/
  frontend/
  docs/
```

## Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs on:

```text
http://127.0.0.1:8000
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on:

```text
http://localhost:5173
```

## Run locally in Chrome

From the project root on Windows:

```powershell
.\scripts\start-local.ps1
```

Then open:

```text
http://127.0.0.1:5173/
```

## Run on another phone/laptop on the same Wi-Fi

From the project root on Windows:

```powershell
.\scripts\start-lan.ps1
```

The script prints a URL like:

```text
http://192.168.1.10:5173/
```

Open that URL from another browser or device on the same network. If Windows Firewall asks, allow Python and Node.js on private networks.

## Deploy with a real domain

Backend environment:

```text
ALLOWED_ORIGINS=https://your-frontend-domain.com
DATABASE_URL=sqlite:///./research_agent.db
SEMANTIC_SCHOLAR_API_KEY=optional_key
```

Backend start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Frontend environment:

```text
VITE_API_URL=https://your-backend-domain.com/api
```

Frontend build command:

```bash
npm run build
```

Frontend publish directory:

```text
dist
```

### Render backend with Supabase PostgreSQL

For a Render Python web service, use the `backend` root directory,
`pip install -r requirements.txt` as the build command, and the backend start
command above. Use one application instance with the existing background-run
adapter.

- In Supabase, open **Connect** and copy the **Session pooler** PostgreSQL URI
  (port 5432). Set it as the secret `DATABASE_URL` in Render. Use the database
  password and URL-encode reserved characters in it. The backend defaults to
  `sslmode=require`; it also accepts explicit libpq TLS settings such as
  `verify-full` with a trusted CA certificate configured on the host.
- Set `APP_ENV=production`, `ALLOWED_ORIGINS=https://researchos.in`, and
  `SESSION_COOKIE_SECURE=true` in Render. Use `SESSION_COOKIE_SAMESITE=lax` with
  a Vercel rewrite from `/api/*` on the frontend domain to the Render API, as
  the browser then uses same-site cookies.
- The database role must be able to create the `researchos` schema on first
  startup and own its tables. Leave this schema out of Supabase's Data API
  exposed schemas. Startup refuses an existing, unrecognized or incompatible
  `researchos` schema. Review any collision before deploying. Existing tables
  in `public`, `auth`, and other schemas remain outside ResearchOS's database
  operations. Local SQLite data is not transferred automatically.
- For a same-origin Vercel rewrite, set `VITE_API_URL=https://researchos.in`
  after the rewrite is configured. While signed out, `/api/auth/me` on the
  frontend domain should return JSON with HTTP 401.

To run the PostgreSQL integration tests, set `RESEARCHOS_TEST_POSTGRES_URL`
to a **disposable loopback PostgreSQL server** using a role that can create
test databases. From `backend`, run
`python -m unittest discover -s tests -p test_postgresql.py -v`.
Integration tests skip when the test URL is unset.

## API Docs

After backend starts, open:

```text
http://127.0.0.1:8000/docs
```

## Optional configuration

Copy `backend/.env.example` to `backend/.env`. Most Semantic Scholar endpoints can
be used without authentication, but an API key improves reliability:

```text
SEMANTIC_SCHOLAR_API_KEY=your_key
```

## Deliberate MVP boundary

The current version prioritizes source provenance and a usable report workflow.
Durable production queues, vector databases, full-text PDF extraction,
plagiarism checking, and PPT generation are later phases—not dependencies of the MVP.


## Research engine foundation

Cookie authentication, owned research runs, background processing, progress polling,
additive migrations, agent contracts and verification are documented in
[docs/engine-foundation.md](docs/engine-foundation.md). The local background adapter
is for a single development process; a durable worker is required for multiworker production.
