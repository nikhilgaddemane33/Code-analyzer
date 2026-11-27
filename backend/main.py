"""main.py — CodeLens FastAPI backend"""
import os, json, uuid, hashlib, secrets, asyncio
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load .env from parent folder
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, Depends, HTTPException, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import engine, get_db, Base
import models, schemas, auth, gemini_client, frontend_html

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CodeLens", version="1.0.0", docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory SSE queues: review_id -> asyncio.Queue
_sse_queues: dict[str, asyncio.Queue] = {}


# ════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════

@app.post("/api/auth/register", response_model=schemas.TokenOut, tags=["Auth"])
def register(body: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    user = models.User(
        id=str(uuid.uuid4()),
        email=body.email,
        password_hash=auth.hash_password(body.password),
        plan="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = auth.create_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.post("/api/auth/login", response_model=schemas.TokenOut, tags=["Auth"])
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not auth.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = auth.create_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/api/auth/me", response_model=schemas.UserOut, tags=["Auth"])
def me(user: models.User = Depends(auth.require_user)):
    return user


# ════════════════════════════════════════════════════════════════
#  REVIEWS
# ════════════════════════════════════════════════════════════════

@app.post("/api/reviews", tags=["Reviews"])
async def create_review(
    body: schemas.ReviewCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    review_id = str(uuid.uuid4())
    user_id = user.id if user else "anonymous"

    review = models.Review(
        id=review_id,
        user_id=user_id,
        language=body.language,
        code=body.code,
        status="pending",
    )
    db.add(review)
    db.commit()

    queue: asyncio.Queue = asyncio.Queue()
    _sse_queues[review_id] = queue

    # On Vercel serverless, run inline so response includes full results (no cross-instance /tmp loss)
    if os.getenv("VERCEL"):
        await _run_pipeline(review_id, body.code, body.language, queue)
        rev = db.query(models.Review).filter(models.Review.id == review_id).first()
        return {
            "id": review_id,
            "status": rev.status if rev else "completed",
            "score": rev.score if rev else 50,
            "summary": rev.summary if rev else "",
            "findings": json.loads(rev.findings_json or "[]") if rev else [],
            "stream_url": f"/api/reviews/{review_id}/stream",
        }

    background_tasks.add_task(
        _run_pipeline, review_id, body.code, body.language, queue
    )

    return {
        "id": review_id,
        "status": "pending",
        "stream_url": f"/api/reviews/{review_id}/stream",
    }


async def _run_pipeline(review_id: str, code: str, language: str, queue: asyncio.Queue):
    """Background task: runs the review pipeline and pushes SSE events."""
    from database import SessionLocal
    db = SessionLocal()
    score = 50
    findings = []
    summary = ""

    try:
        steps = [
            ("Parsing", 0.6),
            ("Static checks", 0.8),
            ("AI analysis", 0),      # actual Gemini call
            ("Merging results", 0.5),
            ("Generating fixes", 0.4),
        ]

        # Update DB status
        rev = db.query(models.Review).filter(models.Review.id == review_id).first()
        if rev:
            rev.status = "running"
            db.commit()

        for i, (step, delay) in enumerate(steps):
            await queue.put({"type": "progress", "step": step, "index": i, "total": len(steps)})

            if step == "AI analysis":
                result = await gemini_client.analyze_code(code, language)
                findings = result.get("findings", [])
                score = result.get("score", 50)
                summary = result.get("summary", "")
                # Stream each finding as it "arrives"
                for f in findings:
                    f.setdefault("id", str(uuid.uuid4()))
                    await queue.put({"type": "finding", **f})
                    await asyncio.sleep(0.15)
            else:
                await asyncio.sleep(delay)

        # Save results
        rev = db.query(models.Review).filter(models.Review.id == review_id).first()
        if rev:
            rev.status = "completed"
            rev.score = score
            rev.summary = summary
            rev.findings_json = json.dumps(findings)
            rev.completed_at = datetime.utcnow()
            db.commit()

        await queue.put({"type": "complete", "score": score, "summary": summary, "total": len(findings)})

    except Exception as exc:
        await queue.put({"type": "error", "message": str(exc)})
        rev = db.query(models.Review).filter(models.Review.id == review_id).first()
        if rev:
            rev.status = "failed"
            db.commit()
    finally:
        db.close()
        if not os.getenv("VERCEL"):
            # Keep queue for 60 s for SSE reconnects, then clean up
            await asyncio.sleep(60)
        _sse_queues.pop(review_id, None)


@app.get("/api/reviews/{review_id}/stream", tags=["Reviews"])
async def stream_review(review_id: str):
    queue = _sse_queues.get(review_id)

    async def generator():
        if queue is None:
            # Review already complete — replay from DB
            from database import SessionLocal
            db = SessionLocal()
            rev = db.query(models.Review).filter(models.Review.id == review_id).first()
            db.close()
            if rev and rev.status == "completed":
                for f in json.loads(rev.findings_json or "[]"):
                    yield f"data: {json.dumps({'type': 'finding', **f})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'score': rev.score, 'summary': rev.summary})}\n\n"
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield "data: {\"type\":\"ping\"}\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/api/reviews", response_model=list[schemas.ReviewOut], tags=["Reviews"])
def list_reviews(
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    q = db.query(models.Review).order_by(models.Review.created_at.desc())
    if user:
        q = q.filter(models.Review.user_id == user.id)
    return q.limit(50).all()


@app.get("/api/reviews/{review_id}", tags=["Reviews"])
def get_review(review_id: str, db: Session = Depends(get_db)):
    rev = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not rev:
        raise HTTPException(404, "Review not found")
    return {
        "id": rev.id,
        "status": rev.status,
        "language": rev.language,
        "score": rev.score,
        "summary": rev.summary,
        "findings": json.loads(rev.findings_json or "[]"),
        "created_at": rev.created_at,
        "completed_at": rev.completed_at,
    }


# ════════════════════════════════════════════════════════════════
#  API KEYS
# ════════════════════════════════════════════════════════════════

@app.get("/api/api-keys", tags=["API Keys"])
def list_api_keys(db: Session = Depends(get_db), user: models.User = Depends(auth.require_user)):
    keys = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.user_id == user.id, models.ApiKey.revoked_at == None)
        .all()
    )
    return [{"id": k.id, "name": k.name, "prefix": k.prefix, "created_at": k.created_at} for k in keys]


@app.post("/api/api-keys", tags=["API Keys"])
def create_api_key(
    body: schemas.ApiKeyCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    raw_key = "sk-" + secrets.token_urlsafe(32)
    key = models.ApiKey(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=body.name,
        key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
        prefix=raw_key[:10],
    )
    db.add(key)
    db.commit()
    return {"id": key.id, "name": key.name, "key": raw_key, "prefix": key.prefix}


@app.delete("/api/api-keys/{key_id}", tags=["API Keys"])
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_user),
):
    key = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.id == key_id, models.ApiKey.user_id == user.id)
        .first()
    )
    if not key:
        raise HTTPException(404, "Key not found")
    key.revoked_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════
#  HEALTH
# ════════════════════════════════════════════════════════════════

@app.get("/api/health", tags=["System"])
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ════════════════════════════════════════════════════════════════
#  SERVE FRONTEND (must be last)
# ════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_index():
    local_html = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.isfile(local_html):
        with open(local_html, "r", encoding="utf-8") as f:
            return f.read()
    return frontend_html.INDEX_HTML

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
static_path = os.path.join(os.path.dirname(__file__), "static")
serve_dir = frontend_path if os.path.isdir(frontend_path) else static_path
if os.path.isdir(serve_dir):
    app.mount("/", StaticFiles(directory=serve_dir, html=True), name="frontend")
