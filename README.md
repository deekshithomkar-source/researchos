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
- Falls back to clearly labelled demo evidence when the provider is unavailable
- Deduplicates and scores sources using transparent metadata signals
- Generates academic reports, literature reviews, or project proposals
- Formats references in APA or IEEE style
- Exports the generated report as Markdown
- Saves research sessions
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
Authentication, vector databases, background queues, full-text PDF extraction,
plagiarism checking, and PPT generation are later phases—not dependencies of the MVP.
