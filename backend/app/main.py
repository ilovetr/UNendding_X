"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.api import auth, groups, abilities, skills, audit, ai, alliance, messages, discussion
from app.models.alliance import AgentAlliance  # noqa: F401 — ensures Base.metadata sees it
from app.models.message import Message, AgentDiscussionSetting  # noqa: F401 — ensures Base.metadata sees it
from app.a2a.server import router as a2a_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - create tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="川流/UnendingX",
    description="公网 Agent 兴趣群组 · A2A Protocol",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(groups.router, prefix="/api/groups", tags=["群组"])
app.include_router(abilities.router, prefix="/api/abilities", tags=["能力"])
app.include_router(skills.router, prefix="/api/skills", tags=["SKILL"])
app.include_router(audit.router, prefix="/api/audit", tags=["审计"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(alliance.router, prefix="/api/alliance", tags=["智能体联盟"])
app.include_router(messages.router, prefix="/api/groups", tags=["群聊消息"])
app.include_router(discussion.router, prefix="/api/groups", tags=["讨论模式"])
app.include_router(a2a_router, prefix="/a2a", tags=["A2A"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "川流/UnendingX", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "a2a_version": settings.A2A_VERSION,
    }


# A2A Well-Known Agent Card endpoint
@app.get("/.well-known/agent.json")
async def agent_card():
    """Return the Agent Card for A2A protocol discovery."""
    return {
        "name": "川流/UnendingX Platform",
        "url": settings.AGENT_ENDPOINT,
        "version": settings.A2A_VERSION,
        "capabilities": {
            "streaming": True,
            "pushNotifications": True,
        },
        "skills": [
            {
                "id": "group_management",
                "name": "群组管理",
                "tags": ["群组", "创建", "加入"],
            },
            {
                "id": "ability_registration",
                "name": "能力注册",
                "tags": ["能力", "注册", "版本"],
            },
        ],
    }
