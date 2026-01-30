# 详细设计文档 (LLD) - 笔阵 (BiZhen)

**版本**: 1.0  
**日期**: 2026-01-30  
**状态**: Draft  

---

## 1. 数据模型详细设计 (Data Models)

### 1.1 SQLAlchemy 数据模型 (ORM)

```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tokens = relationship("Token", back_populates="user")
    tasks = relationship("Task", back_populates="user")

class Token(Base):
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="tokens")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    input_prompt = Column(Text, nullable=False)
    image_url = Column(String(255), nullable=True)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.QUEUED)
    # 存储中间大纲或策略，使用 SQLAlchemy Generic JSON (Postgres=JSONB, SQLite=JSON)
    meta_info = Column(JSON, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="tasks")
    essays = relationship("EssayResult", back_populates="task")

class EssayResult(Base):
    __tablename__ = "essays"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    style = Column(String(20), nullable=False) # 'profound', 'rhetorical', 'steady'
    title = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    score = Column(Integer, nullable=True)
    critique = Column(Text, nullable=True)
    
    task = relationship("Task", back_populates="essays")
```

### 1.2 Pydantic 交互模型 (Schemas)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class TaskCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="作文题目或话题")
    image_url: Optional[str] = Field(None, description="题目图片URL")

class EssayResponse(BaseModel):
    style: str
    title: Optional[str]
    content: str
    score: Optional[int]
    critique: Optional[str]

class TaskResponse(BaseModel):
    task_id: int
    status: str
    created_at: datetime
    essays: List[EssayResponse] = []

    class Config:
        orm_mode = True
```

### 1.3 Agent Graph State 定义

为了支持 **Fan-in** (并行分支合并)，我们需要在 `State` 中定义 Reducer 函数。当多个 Agent 并行写入 `drafts` 字典时，默认行为是覆盖，使用 Reducer 可以实现合并。

```python
from typing import TypedDict, Annotated, List, Dict, Any
import operator

def merge_dicts(a: Dict, b: Dict) -> Dict:
    """合并字典，用于并行分支的数据汇总"""
    return {**a, **b}

class EssayState(TypedDict):
    # 基础上下文
    topic: str
    angle: str                  # 策划角度
    materials: List[str]        # 检索到的素材
    outline: Dict               # 大纲结构
    
    # 并行生成结果字段，使用 Annotated + merge_dicts 实现 Fan-in 合并
    # 当 WriterA 返回 {"profound": "A内容"}，WriterB 返回 {"rhetorical": "B内容"}
    # State 更新时会自动合并为 {"profound": "...", "rhetorical": "..."}
    drafts: Annotated[Dict[str, str], merge_dicts]
    
    scores: Annotated[Dict[str, int], merge_dicts]
    critiques: Annotated[Dict[str, str], merge_dicts]
    
    # 错误处理标志
    errors: Annotated[List[str], operator.add]
```

---

## 2. 核心代码逻辑设计 (Core Logic)

### 2.1 Agent Workflow (StateGraph 构建)

```python
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

# --- Node Implementation Placeholders ---
def strategist_node(state: EssayState):
    # Model: DEEPSEEK_REASONER_MODEL (DeepSeek R1) for deep intent analysis
    # ... logic ...
    return {"angle": "...", "style_param": {...}}

def librarian_node(state: EssayState):
    # Model: DEEPSEEK_CHAT_MODEL (DeepSeek V3) for Tool Calling
    # RAG: Retrieve Top-K=5 to prevent context overflow
    return {"materials": ["引用1", "引用2"]}

def outliner_node(state: EssayState):
    # [Restored Node]
    # Model: DEEPSEEK_REASONER_MODEL (DeepSeek R1) for logical structure
    # Input: Materials, Angle -> Output: Structured Outline
    return {"outline": {"introduction": "...", "body": [...]}}

def writer_profound_node(state: EssayState):
    # Model: DEEPSEEK_REASONER_MODEL (DeepSeek R1) for philosophical depth
    try:
        return {"drafts": {"profound": "深刻的文章内容..."}}
    except Exception as e:
        return {"errors": [f"WriterProfound Failed: {str(e)}"]}

def writer_rhetorical_node(state: EssayState):
    # Model: DEEPSEEK_CHAT_MODEL (DeepSeek V3) for creative flair
    try:
        return {"drafts": {"rhetorical": "文采的文章内容..."}}
    except Exception as e:
        return {"errors": [f"WriterRhetorical Failed: {str(e)}"]}

def writer_steady_node(state: EssayState):
    # Model: DEEPSEEK_CHAT_MODEL (DeepSeek V3) for standardized output
    try:
        return {"drafts": {"steady": "稳健的文章内容..."}}
    except Exception as e:
        return {"errors": [f"WriterSteady Failed: {str(e)}"]}

def aggregator_node(state: EssayState):
    # Partial Failure Handling:
    # If we have at least one draft, we consider it a partial success rather than a total failure.
    drafts = state.get("drafts", {})
    if not drafts and state.get("errors"):
        # No drafts generated and errors exist -> Total Failure
        raise Exception(f"All writers failed: {state['errors']}")
    
    # Otherwise, proceed with whatever drafts we have
    if state.get("errors"):
        print(f"Partial success with warning: {state['errors']}")
    
    return {}

# --- Graph Construction ---
workflow = StateGraph(EssayState)

# 1. 串行阶段
workflow.add_node("strategist", strategist_node)
workflow.add_node("librarian", librarian_node)
workflow.add_node("outliner", outliner_node) # Restored Outliner

# 2. 并行阶段 (Fan-out)
workflow.add_node("writer_profound", writer_profound_node)
workflow.add_node("writer_rhetorical", writer_rhetorical_node)
workflow.add_node("writer_steady", writer_steady_node)

# 3. 汇聚阶段 (Fan-in)
workflow.add_node("aggregator", aggregator_node)

# --- Edges ---
workflow.set_entry_point("strategist")
workflow.add_edge("strategist", "librarian")
workflow.add_edge("librarian", "outliner") # Connected to Outliner

# 扇出：从 Outliner (而不是 Librarian) 完成后，同时触发三个 Writer
workflow.add_edge("outliner", "writer_profound")
workflow.add_edge("outliner", "writer_rhetorical")
workflow.add_edge("outliner", "writer_steady")

# 扇入：三个 Writer 完成后，都汇聚到 Aggregator
workflow.add_edge("writer_profound", "aggregator")
workflow.add_edge("writer_rhetorical", "aggregator")
workflow.add_edge("writer_steady", "aggregator")

workflow.add_edge("aggregator", END)

# Compile
app = workflow.compile()
```

### 2.2 异步任务 Worker (Celery)

Worker 负责执行上述 Graph，并处理状态更新。

```python
# backend/worker.py
from celery import Celery
from .core.graph import app as langgraph_app
from .db.session import SessionLocal
from .models import Task, EssayResult, TaskStatus
import redis
import json

celery_app = Celery("bizhen_worker", broker="redis://redis:6379/0", backend="redis://redis:6379/1")
redis_client = redis.Redis(host='redis', port=6379, db=2)

@celery_app.task(bind=True)
def run_generation_task(self, task_id: int):
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        return
    
    try:
        # 更新状态为 Processing
        task.status = TaskStatus.PROCESSING
        db.commit()
        
        # 准备初始状态
        initial_state = {
            "topic": task.input_prompt,
            "drafts": {},
            "errors": []
        }
        
        # LangGraph 回调用于 SSE 推送
        # 在实际代码中，需要实现自定义 CallbackHandler 将事件 publish 到 Redis
        
        # 执行 Graph
        final_state = langgraph_app.invoke(initial_state)
        
        # 处理结果并入库
        drafts = final_state.get("drafts", {})
        for style, content in drafts.items():
            essay = EssayResult(
                task_id=task.id,
                style=style,
                content=content,
                # title, score, critique 也从 final_state 获取
            )
            db.add(essay)
            
        task.status = TaskStatus.COMPLETED
        db.commit()
        
        # 推送完成消息
        redis_client.publish(f"task_stream:{task_id}", json.dumps({"type": "end", "status": "completed"}))

    except Exception as e:
        task.status = TaskStatus.FAILED
        db.commit()
        redis_client.publish(f"task_stream:{task_id}", json.dumps({"type": "error", "msg": str(e)}))
    finally:
        db.close()
```

### 2.3 SSE Generator & Redis Pub/Sub

API 端通过订阅 Redis 频道来实现 SSE。

```python
# backend/api/endpoints/task.py
import asyncio
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis

router = APIRouter()

async def event_generator(task_id: int):
    redis = aioredis.from_url("redis://redis:6379/2")
    pubsub = redis.pubsub()
    channel = f"task_stream:{task_id}"
    await pubsub.subscribe(channel)
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode("utf-8")
                # 检查是否结束信号
                if "completed" in data or "failed" in data:
                    yield data
                    break
                yield data
    finally:
        await pubsub.unsubscribe(channel)
        await redis.close()

@router.get("/task/{task_id}/stream")
async def stream_task_progress(task_id: int):
    return EventSourceResponse(event_generator(task_id))
```

---

## 3. 接口与数据库定义 (API & DB)

### 3.1 API Endpoints

**POST /api/task/create**
- **Logic**:
  1. 验证 Token。
  2. 在 Postgres 创建 Task 记录，Status=Queued。
  3. `run_generation_task.delay(task.id)` 投递 Celery 任务。
  4. 返回 `{"task_id": 123, "status": "queued"}`。

**GET /api/task/{id}/result**
- **Logic**: 查询数据库 `Essays` 表，返回该任务的所有作文结果。

### 3.2 数据库 Schema (SQL DDL)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role VARCHAR(10) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    input_prompt TEXT NOT NULL,
    image_url VARCHAR(255),
    status VARCHAR(20) DEFAULT 'queued',
    meta_info JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE essays (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    style VARCHAR(20) NOT NULL,
    title VARCHAR(100),
    content TEXT NOT NULL,
    score INTEGER,
    critique TEXT
);
```

---

## 4. 部署配置 (Deployment)

### 4.1 Dockerfile (Backend & Worker)

使用多阶段构建减小体积。

```dockerfile
# Dockerfile
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.10-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

# 默认为 API 启动命令，Worker 可在 compose 中覆盖
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 docker-compose.yml (完整配置)

在此处修正 HLD 中的遗漏，显式添加 `celery_worker` 服务。

```yaml
version: '3.8'

services:
  # 1. 前端服务
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  # 2. 后端 API 服务
  backend:
    build: ./backend
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DB_URL=postgresql://user:pass@postgres:5432/bizhen
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app/backend

  # 3. Celery Worker (LangGraph 执行器)
  celery_worker:
    build: ./backend  # 复用后端镜像
    command: celery -A backend.worker.celery_app worker --loglevel=info
    environment:
      - DB_URL=postgresql://user:pass@postgres:5432/bizhen
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
      # 必须注入 API Key 供 Agent 调用 LLM
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DEEPSEEK_CHAT_MODEL=deepseek-chat
      - DEEPSEEK_REASONER_MODEL=deepseek-reasoner
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app/backend

  # 4. 基础服务
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=bizhen
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  pg_data:
  chroma_data:
```
