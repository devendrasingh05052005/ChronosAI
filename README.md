# ChronosAI — Intelligent Timetable & Agentic Proxy Management System

A production-grade Django web application for digitizing college timetables via OCR,
managing faculty schedules, and assigning proxy teachers using an AI agent.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ChronosAI System                         │
├──────────────┬──────────────────────────┬───────────────────────┤
│  Frontend    │      Django Backend       │    Background Worker  │
│  (Vanilla JS │                           │                       │
│  + Tailwind) │  ┌─────────────────────┐  │  ┌─────────────────┐ │
│              │  │  Phase 1: OCR       │  │  │  Celery Worker  │ │
│  Upload Zone │→ │  EasyOCR + Groq LLM │  │  │  Redis Broker   │ │
│              │  └─────────────────────┘  │  │  Email Alerts   │ │
│  Edit Table  │  ┌─────────────────────┐  │  └─────────────────┘ │
│              │→ │  Phase 2: Confirm   │  │                       │
│              │  │  Bulk DB Insert     │  │                       │
│  Chat UI     │  └─────────────────────┘  │                       │
│              │  ┌─────────────────────┐  │                       │
│              │→ │  Phase 3: Agent     │  │                       │
│              │  │  Fail-Safe Router   │  │                       │
│              │  │  LangGraph + Groq   │  │                       │
│              │  └─────────────────────┘  │                       │
└──────────────┴──────────────────────────┴───────────────────────┘
```

---

## Prerequisites

- Python 3.10+
- Redis (for Celery message broker)
- A Groq Cloud API key (free at https://console.groq.com)

---

## Quick Start

### 1. Clone and set up virtual environment

```bash
cd chronosai
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note on EasyOCR**: First run downloads ~100MB of model weights. If you skip EasyOCR
> installation, the system automatically uses realistic mock data for demos.

### 3. Set your Groq API key

```bash
# Windows (PowerShell)
$env:GROQ_API_KEY = "gsk_your_key_here"

# macOS / Linux
export GROQ_API_KEY="gsk_your_key_here"
```

### 4. Run database migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Start Redis (required for Celery)

```bash
# Using Docker (easiest)
docker run -d -p 6379:6379 redis:alpine

# Or install Redis natively and run:
redis-server
```

### 6. Start the Celery worker (separate terminal)

```bash
# Windows (--pool=solo for stability)
celery -A core worker --loglevel=info --pool=solo

# macOS / Linux
celery -A core worker --loglevel=info
```

### 7. Start the Django development server

```bash
python manage.py runserver
```

### 8. Open the app

Navigate to: **http://127.0.0.1:8000**

---

## How to Use

### Phase 1 — Upload & Digitize
1. Drag and drop a college timetable image (PNG/JPG) into the left panel upload zone.
2. The system runs EasyOCR to extract text, then sends it to Groq's `llama-3.3-70b-versatile`.
3. A structured editable table appears with all extracted schedule entries.

### Phase 2 — Verify & Save
1. Review the extracted data in the table. Click any cell to edit it.
2. Add missing rows with the "+ Add Row" button.
3. Click **"Confirm & Save to Database"** to bulk-save everything.

### Phase 3 — Chat with ChronosAI
Use the chat panel on the right to query schedules and assign proxies:

| Query Example | Action |
|--------------|--------|
| `Show me the Thursday schedule` | Fast-path ORM query (< 2s) |
| `What can you do?` | Bot capability description |
| `Who is free Monday at 10:00?` | LangGraph → find_free_faculties_tool |
| `Dr. Sharma is absent Friday at 9 AM, assign a proxy` | LangGraph → find + assign tools |
| `What does Prof. Kumar teach on Wednesday?` | LangGraph → get_faculty_schedule_tool |

### Phase 4 — Async Alerts
When a proxy is assigned (via chat or API), a Celery task is triggered.
Watch the **Celery worker terminal** for the formatted email notification log.

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/` | Main dashboard |
| `POST` | `/api/upload/` | Upload timetable image |
| `POST` | `/api/confirm/` | Save verified schedule to DB |
| `POST` | `/api/chat/` | Chat with ChronosAI agent |
| `POST` | `/api/proxy/` | Direct proxy assignment |

---

## Directory Structure

```
chronosai/
├── core/
│   ├── __init__.py          # Celery app loader
│   ├── celery.py            # Celery configuration
│   ├── settings.py          # Django settings
│   ├── urls.py              # Root URL config
│   └── wsgi.py
├── scheduler_api/
│   ├── templates/
│   │   └── index.html       # Full dashboard UI
│   ├── __init__.py
│   ├── admin.py             # Admin registrations
│   ├── agent_graph.py       # LangGraph StateGraph
│   ├── agent_tools.py       # 4 LangChain @tool functions
│   ├── models.py            # Employee, Schedule, TimetableFile
│   ├── tasks.py             # Celery proxy alert task
│   ├── urls.py              # App URL patterns
│   ├── utils.py             # EasyOCR + Groq pipeline
│   └── views.py             # All Django views
├── media/                   # Uploaded timetable images
├── manage.py
└── requirements.txt
```

---

## Configuration

Edit `core/settings.py` to change:
- `GROQ_API_KEY` — your Groq Cloud API key
- `CELERY_BROKER_URL` — Redis connection string
- `DATABASES` — switch to PostgreSQL for production

---

## Running Without Redis/Groq

The system has graceful fallbacks:
- **No GROQ_API_KEY**: Uses realistic mock schedule data (20 entries across 5 days)
- **No Redis**: Remove Celery task calls; proxies still save to DB
- **No EasyOCR**: Falls back to mock OCR text

This ensures full demo capability even without external services.

---

## Fail-Safe Router Logic

The `ChatAssistantView` implements a two-tier routing strategy:

1. **Fast Path (< 2s guaranteed)**: Intercepts queries containing day keywords
   (`monday`, `tuesday`, etc.) combined with schedule intent words, OR bot
   description queries (`what can you do`). Served directly from Django ORM.

2. **Agent Path**: All other queries route through the full LangGraph circuit
   with `llama-3.1-8b-instant`, which selects and executes the appropriate tool.

This prevents rate-limit lockouts and ensures reliable demo performance.
