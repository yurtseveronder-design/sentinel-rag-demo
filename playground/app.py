"""FastAPI app for the public playground. Stateless: no prompt text is stored or logged."""
import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from rag_demo import corpus

from .engine import Playground
from .examples import EXAMPLES

ROOT = Path(__file__).resolve().parent
DOCS = Path(os.getenv("PLAYGROUND_DOCS", ROOT.parent / "docs"))
MAX_CHARS = int(os.getenv("PLAYGROUND_MAX_CHARS", "2000"))
PER_IP_PER_MIN = int(os.getenv("PLAYGROUND_PER_IP_PER_MIN", "30"))
GLOBAL_PER_MIN = int(os.getenv("PLAYGROUND_GLOBAL_PER_MIN", "600"))

app = FastAPI(title="Sentinel playground", docs_url=None, redoc_url=None)
state = {"pg": None}
_hits = defaultdict(deque)
_global = deque()


def pg() -> Playground:
    if state["pg"] is None:
        modes = os.getenv("PLAYGROUND_MODES")
        state["pg"] = Playground.create(modes.split(",") if modes else None)
    return state["pg"]


def _limited(request: Request) -> bool:
    """Per-visitor and global caps. Behind a proxy the visitor is the first X-Forwarded-For entry."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    who = forwarded or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    if len(_hits) > 10_000:  # bound memory under a flood of distinct addresses
        _hits.clear()
    for q in (_hits[who], _global):
        while q and now - q[0] > 60:
            q.popleft()
    if len(_hits[who]) >= PER_IP_PER_MIN or len(_global) >= GLOBAL_PER_MIN:
        return True
    _hits[who].append(now)
    _global.append(now)
    return False


class CheckRequest(BaseModel):
    text: str = Field(..., max_length=MAX_CHARS)
    mode: str = "rules"


class RagRequest(BaseModel):
    document: str
    mode: str = "rules"


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {"modes": pg().modes(), "examples": EXAMPLES, "max_chars": MAX_CHARS,
            "documents": corpus.poisoned_names(DOCS)}


def _check(request: Request, text: str, mode: str) -> dict:
    try:
        return pg().check(text, mode)
    except ValueError:
        raise HTTPException(status_code=422, detail="Unknown mode.")
    except LookupError:
        raise HTTPException(status_code=503, detail="That detector is not available on this server.")


@app.post("/api/check")
def check(payload: CheckRequest, request: Request):
    if _limited(request):
        return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)
    return _check(request, payload.text, payload.mode)


@app.post("/api/rag")
def rag(payload: RagRequest, request: Request):
    """Runs every paragraph of one of the bundled poisoned documents through the same checks."""
    if _limited(request):
        return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)
    if payload.document not in corpus.poisoned_names(DOCS):
        raise HTTPException(status_code=404, detail="Unknown document.")
    chunks = corpus.load_poisoned(DOCS, payload.document)
    out = []
    for chunk in chunks:
        result = _check(request, chunk.text, payload.mode)
        out.append({"text": chunk.text, "action": result["action"], "caught_by": result["caught_by"]})
    return {"document": payload.document, "paragraphs": out,
            "blocked": sum(p["action"] == "BLOCK" for p in out), "total": len(out)}
