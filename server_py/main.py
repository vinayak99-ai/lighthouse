"""FastAPI port of server/src/index.js -- same three endpoints, same JSON
shapes, so the existing React/JS frontend (client/) works against this
backend with zero changes. Run with:

    uvicorn server_py.main:app --port 8787 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .chat.fallback_router import route_offline
from .chat.orchestrator import active_model, active_provider, has_llm_client, run_conversation
from .data.db import ensure_schema, get_db
from .data.seed import seed_all
from .starters import STARTER_DOMAINS


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Seed on boot if the DB is empty, so a fresh checkout works with zero setup.
    db = ensure_schema(get_db())
    row = db.execute("SELECT COUNT(*) c FROM stablecoin_supply").fetchone()
    if row["c"] == 0:
        print("Empty database detected — seeding stub blockchain dataset...")
        seed_all()
    yield


app = FastAPI(lifespan=_lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "mode": "live" if has_llm_client() else "offline-demo",
        "provider": active_provider(),
        "model": active_model(),
    }


@app.get("/api/starters")
def starters() -> dict:
    return {"domains": STARTER_DOMAINS}


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = (body or {}).get("messages")
    if not isinstance(messages, list) or len(messages) == 0:
        return JSONResponse(status_code=400, content={"error": "Body must include a non-empty `messages` array."})

    try:
        if has_llm_client():
            result = run_conversation(messages)
            return {**result, "mode": "live"}
        last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        content = last_user.get("content") if last_user else ""
        text = " ".join(b.get("text", "") for b in content) if isinstance(content, list) else (content or "")
        result = route_offline(text)
        return {**result, "mode": "offline-demo"}
    except Exception as err:  # mirrors index.js's catch-all 500 handler
        print(err)
        return JSONResponse(status_code=500, content={"error": str(err) or "Something went wrong."})
