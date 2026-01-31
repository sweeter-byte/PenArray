# PenArray (笔阵)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#license)

A Multi-Agent AI System for generating high-quality Chinese Gaokao (高考) argumentative essays.

## Overview

PenArray solves the problem of generic LLMs producing essays that lack argumentative depth, have poor logical structure, use outdated materials, and don't meet Gaokao evaluation standards. It orchestrates **7 specialized AI agents** to collaboratively generate, evaluate, and refine essays in three distinct writing styles.

**Key Highlights:**
- Focused exclusively on argumentative essays (议论文)
- Uses China-compliant LLM APIs (DeepSeek)
- Generates 3 different writing styles from the same topic
- Includes scoring (0-60 points) and detailed critique following Gaokao standards
- Real-time progress streaming via SSE

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                       │
│                           Nginx / Port 80                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                             │
│                          Uvicorn / Port 8000                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────────────┐   │
│  │   Auth   │    │  Task    │    │      LangGraph Workflow      │   │
│  │   API    │    │   API    │───▶│                              │   │
│  └──────────┘    └──────────┘    │  Strategist → Librarian      │   │
│                                  │       ↓                       │   │
│                                  │    Outliner                   │   │
│                                  │       ↓                       │   │
│                                  │  ┌─────────┬─────────┬─────┐ │   │
│                                  │  │Profound │Rhetoric │Steady│ │   │
│                                  │  │ Writer  │ Writer  │Writer│ │   │
│                                  │  └────┬────┴────┬────┴──┬───┘ │   │
│                                  │       ↓         ↓       ↓     │   │
│                                  │  ┌─────────┬─────────┬─────┐ │   │
│                                  │  │ Grader  │ Grader  │Grader│ │   │
│                                  │  └────┬────┴────┬────┴──┬───┘ │   │
│                                  │       └─────────┼───────┘     │   │
│                                  │                 ↓             │   │
│                                  │            Aggregator         │   │
│                                  └──────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
          │                    │                      │
          ▼                    ▼                      ▼
    ┌──────────┐        ┌──────────┐          ┌──────────┐
    │PostgreSQL│        │  Redis   │          │ ChromaDB │
    │ Port 5432│        │Port 6379 │          │ Port 8001│
    └──────────┘        └──────────┘          └──────────┘
```

## Features

### Multi-Agent Workflow

| Agent | Model | Role |
|-------|-------|------|
| **Strategist** | DeepSeek R1 | Analyzes topic, determines writing angle and thesis |
| **Librarian** | DeepSeek V3 | Retrieves materials via tiered RAG (Local DB → LLM → Web) |
| **Outliner** | DeepSeek R1 | Creates structured essay outline |
| **WriterProfound** | DeepSeek R1 | Philosophical depth, complex reasoning |
| **WriterRhetorical** | DeepSeek V3 | Beautiful prose, literary devices |
| **WriterSteady** | DeepSeek V3 | Conservative structure, guaranteed minimum score |
| **Grader** | DeepSeek R1 | Scores (0-60) and critiques each essay |

### Three Essay Styles

- **Profound (深刻)** - Philosophical depth, complex reasoning
- **Rhetorical (文采)** - Beautiful prose, literary devices
- **Steady (稳健)** - Conservative structure, guaranteed minimum score

### Technical Features

- **Async Task Processing**: FastAPI → Redis Queue → Celery Worker
- **Real-Time Streaming**: Server-Sent Events for live agent progress
- **JWT Authentication**: Admin-issued tokens with expiration
- **Vector Search**: ChromaDB for material retrieval (RAG)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, TailwindCSS, Axios |
| Backend | Python 3.10, FastAPI, Uvicorn |
| AI Orchestration | LangGraph, LangChain |
| LLM Provider | DeepSeek API (V3 & R1 models) |
| Database | PostgreSQL 15, SQLAlchemy 2.0 |
| Cache/Queue | Redis 7, Celery 5.3 |
| Vector DB | ChromaDB |
| Deployment | Docker, Docker Compose |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- DeepSeek API Key ([Get one here](https://platform.deepseek.com/))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sweeter-byte/PenArray.git
   cd PenArray
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your DeepSeek API key
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Web UI: http://localhost
   - API Docs: http://localhost:8000/api/docs
   - ReDoc: http://localhost:8000/api/redoc

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 80 | React web application |
| Backend | 8000 | FastAPI REST API |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache & message broker |
| ChromaDB | 8001 | Vector database |

## Development

### Local Development (without Docker)

For local development, you can run the backend and frontend separately.

**Backend:**

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DEEPSEEK_API_KEY=your_key_here
export DB_URL=postgresql://user:pass@localhost:5432/bizhen
export REDIS_URL=redis://localhost:6379/0
export CHROMA_HOST=localhost
export CHROMA_PORT=8001

# Run the API server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# In a separate terminal, run the Celery worker
celery -A backend.worker worker --loglevel=info
```

**Frontend:**

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Configuration

### Environment Variables

```ini
# DeepSeek API (Required)
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat
DEEPSEEK_REASONER_MODEL=deepseek-reasoner

# Database
DB_URL=postgresql://bizhen_user:bizhen_pass@postgres:5432/bizhen

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ChromaDB
CHROMA_HOST=chroma
CHROMA_PORT=8000

# Security
SECRET_KEY=your_super_secret_key_change_in_production
ACCESS_TOKEN_EXPIRE_HOURS=24
```

## Vector Database Management

The Librarian agent uses ChromaDB for RAG (Retrieval-Augmented Generation) to retrieve quotes, facts, and examples. Two utility scripts are provided for managing the vector database:

### Check Database Status

```bash
cd backend
python check_vector_db.py
```

This script:
- Connects to ChromaDB and reports connection status
- Shows total document count in `materials_collection`
- Displays category breakdown (quote, fact, theory, literature)
- Shows sample documents if the collection is not empty

### Seed Sample Data

```bash
cd backend
python seed_vector_db.py          # Add new documents
python seed_vector_db.py --clear  # Clear and reseed
```

Materials are loaded from `backend/data/materials.json`, which contains **41 high-quality Chinese essay materials** covering:

| Theme | Count | Examples |
|-------|-------|----------|
| **Perseverance (坚持)** | 5 | 荀子《劝学》, 屠呦呦青蒿素研发, 曹雪芹《红楼梦》 |
| **Innovation (创新)** | 6 | 朱熹《观书有感》, 华为5G专利, 中国高铁 |
| **Patriotism (爱国)** | 5 | 林则徐, 钱学森, 文天祥《过零丁洋》 |
| **Technology (科技)** | 4 | 嫦娥五号, 天宫空间站, 人工智能 |
| **Youth (青年)** | 3 | 梁启超《少年中国说》, 毛泽东诗词 |
| **Learning (学习)** | 3 | 孔子《论语》, 《中庸》, 陆游 |
| **Other themes** | 15 | Environment, integrity, struggle, optimism, etc. |

**Categories:** quotes (17), facts (12), literature (9), theories (3)

### Adding Custom Materials

Edit `backend/data/materials.json` to add your own materials:

```json
{
  "materials": [
    {
      "id": "quote_custom_001",
      "content": "Your quote content here.——Author",
      "category": "quote",
      "author": "Author Name",
      "tags": ["tag1", "tag2"],
      "theme": "your_theme"
    }
  ]
}
```

### Environment Variables

Both scripts support:
```bash
CHROMA_HOST=chroma CHROMA_PORT=8000 python check_vector_db.py
```

## Tiered Retrieval Strategy

The Librarian agent implements a robust hybrid retrieval strategy to ensure high-quality materials are always available, even with a sparse local database:

```
┌─────────────────────────────────────────────────────────────┐
│                    Tiered Retrieval Flow                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ TIER 1: Vector DB Search (Preferred)                  │   │
│  │ • Query ChromaDB for relevant materials               │   │
│  │ • Goal: Retrieve at least 5 items                     │   │
│  │ • Source: "vector_db"                                 │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                  │
│                    if count < 5                              │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ TIER 2: LLM Generation (Fallback)                     │   │
│  │ • Uses DeepSeek V3 to generate supplementary quotes   │   │
│  │ • Avoids duplicating existing materials               │   │
│  │ • Source: "llm_generated"                             │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                  │
│                    if count < 3                              │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ TIER 3: Web Search (Last Resort)                      │   │
│  │ • Tavily API (if TAVILY_API_KEY set)                  │   │
│  │ • SerpAPI (if SERPAPI_API_KEY set)                    │   │
│  │ • DuckDuckGo (no API key required)                    │   │
│  │ • Source: "web_search_*"                              │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                  │
│                    if still < 3                              │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ FALLBACK: Hardcoded Materials (Emergency)             │   │
│  │ • Classic quotes that always work                     │   │
│  │ • Ensures system never returns empty                  │   │
│  │ • Source: "fallback"                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Configuration

To enable web search (Tier 3), set one of these environment variables:

```bash
# Tavily (recommended for quality)
TAVILY_API_KEY=your_tavily_key

# Or SerpAPI
SERPAPI_API_KEY=your_serpapi_key

# DuckDuckGo works without any API key (fallback)
```

### Retrieval Metadata

Each response includes metadata about material sources:

```json
{
  "materials": { ... },
  "retrieval_metadata": {
    "total": 12,
    "sources": {
      "vector_db": 8,
      "llm_generated": 4,
      "web_search": 0,
      "fallback": 0
    }
  }
}
```

## API Reference

### Authentication

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}
```

### Task Management

```http
# Create a new essay generation task
POST /api/task/create
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt": "Essay topic here...",
  "image_url": "optional_image_url",
  "custom_structure": "parallel|hierarchical|sequential (optional)"
}

# Get task result
GET /api/task/{task_id}/result

# Stream task progress (SSE)
GET /api/task/{task_id}/stream

# Check task status
GET /api/task/{task_id}/status
```

### Document Export

```http
# Download essay as Word document
GET /api/export/{essay_id}/docx
Authorization: Bearer <token>

# Download essay as PDF
GET /api/export/{essay_id}/pdf
Authorization: Bearer <token>
```

## Project Structure

```
PenArray/
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── pages/              # Page components
│   │   ├── api/                # API client
│   │   └── styles/             # TailwindCSS
│   ├── Dockerfile
│   └── nginx.conf
│
├── backend/                     # FastAPI backend
│   ├── backend/
│   │   ├── main.py             # Entry point
│   │   ├── worker.py           # Celery worker
│   │   ├── config.py           # Settings
│   │   ├── core/
│   │   │   ├── graph.py        # LangGraph workflow
│   │   │   ├── state.py        # State management
│   │   │   └── agents/         # Agent implementations
│   │   ├── api/                # REST endpoints
│   │   ├── db/                 # Database models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── prompts/            # YAML prompt templates
│   ├── data/
│   │   └── materials.json      # Essay materials database (41 items)
│   ├── check_vector_db.py      # Vector DB status checker
│   ├── seed_vector_db.py       # Vector DB seeding script
│   ├── requirements.txt
│   └── Dockerfile
│
├── doc/                         # Documentation
│   ├── SRS_BiZhen.md           # Requirements spec
│   ├── HLD_BiZhen.md           # High-level design
│   └── LLD_BiZhen.md           # Low-level design
│
├── docker-compose.yml
├── .env.example
└── README.md
```

## Workflow

```
User Input (Topic)
       ↓
    POST /api/task/create
       ↓
    Redis Queue (Task ID returned immediately)
       ↓
    Celery Worker picks up task
       ↓
    LangGraph Execution
    ├── Strategist → Analyzes topic
    ├── Librarian → Retrieves materials (Tiered: DB → LLM → Web)
    ├── Outliner → Creates outline
    ├── Writers (Parallel)
    │   ├── WriterProfound
    │   ├── WriterRhetorical
    │   └── WriterSteady
    ├── Graders (Parallel)
    │   ├── GraderProfound
    │   ├── GraderRhetorical
    │   └── GraderSteady
    └── Aggregator → Merges results
       ↓
    PostgreSQL (Store essays + scores)
       ↓
    Frontend displays 3 essays with scores
```

## Documentation

Detailed documentation is available in the `doc/` directory:

- **SRS_BiZhen.md** - Software Requirements Specification
- **HLD_BiZhen.md** - High-Level Design
- **LLD_BiZhen.md** - Low-Level Design

## Troubleshooting

### Common Issues

**1. DeepSeek API errors**
```
Error: Invalid API key or rate limit exceeded
```
- Verify your `DEEPSEEK_API_KEY` is correct in `.env`
- Check your API quota at [DeepSeek Platform](https://platform.deepseek.com/)

**2. ChromaDB connection failed**
```
Error: Could not connect to ChromaDB
```
- Ensure ChromaDB container is running: `docker-compose ps chroma`
- Check if port 8001 is available
- Verify `CHROMA_HOST` and `CHROMA_PORT` environment variables

**3. SSE streaming not working**
```
Error: EventSource connection failed
```
- Ensure Redis is running: `docker-compose ps redis`
- Check browser console for CORS errors
- Verify the JWT token is valid and not expired

**4. Database migration issues**
```
Error: Relation does not exist
```
- Run database initialization: `docker-compose exec backend python -c "from backend.db.init_db import init_db; init_db()"`
- Or restart the backend container: `docker-compose restart backend`

**5. Celery worker not processing tasks**
```
Tasks stuck in "queued" status
```
- Check worker logs: `docker-compose logs worker`
- Ensure Redis is accessible from the worker container
- Restart the worker: `docker-compose restart worker`

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f frontend
```

## License

This project is proprietary software. All rights reserved.
