# PenArray (笔阵)

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
| **Librarian** | DeepSeek V3 | Retrieves quotes, facts, and examples via RAG |
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
  "image_url": "optional_image_url"
}

# Get task result
GET /api/task/{task_id}/result

# Stream task progress (SSE)
GET /api/task/{task_id}/stream

# Check task status
GET /api/task/{task_id}/status
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
    ├── Librarian → Retrieves materials
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

## License

This project is proprietary software. All rights reserved.
