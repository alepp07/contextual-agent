"""
main.py -- the FastAPI service.

This is what turns "a script I run on my laptop" into "a service someone
else can call." Run locally with:

    uvicorn app.main:app --reload

Visit http://127.0.0.1:8000/docs for interactive API documentation,
generated automatically from the type hints below -- this is one of
FastAPI's biggest practical advantages over plain Flask.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import run_agent
from app.embed_store import build_index, INDEX_DIR

app = FastAPI(
    title="RAG + Agent Service",
    description="An agent that can search your documents, search the web, or do math.",
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@app.on_event("startup")
def startup_event():
    # Build the index automatically if it doesn't exist yet, so the service
    # works immediately after a fresh deploy without a manual build step.
    if not (INDEX_DIR / "vectors.npy").exists():
        build_index(data_dir=str(DATA_DIR))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    answer = run_agent(payload.question)
    return {"answer": answer}


# Mounted LAST and deliberately at "/" -- FastAPI checks routes in the order
# they're registered, so /health and /ask above still match first. Anything
# that doesn't match an API route (including "/" itself) falls through to
# this static file server, which serves static/index.html as the frontend.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")