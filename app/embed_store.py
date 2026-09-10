"""
embed_store.py -- local embeddings, a plain numpy vector index, and cosine search.

Carried over from the learn-rag project. Runs entirely locally -- no API
key, no cost -- using sentence-transformers.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from app.ingest import load_and_chunk_directory

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_DIR = Path(__file__).resolve().parent.parent / "index"

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    model = get_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.astype(np.float32)


def build_index(data_dir: str = "data") -> None:
    chunks = load_and_chunk_directory(data_dir)
    if not chunks:
        raise ValueError(f"No .txt/.md/.pdf files found in {data_dir}/")

    vectors = embed_texts([c.text for c in chunks])

    INDEX_DIR.mkdir(exist_ok=True)
    np.save(INDEX_DIR / "vectors.npy", vectors)
    with open(INDEX_DIR / "chunks.json", "w") as f:
        json.dump(
            [{"text": c.text, "source": c.source, "chunk_id": c.chunk_id} for c in chunks],
            f,
        )


def load_index() -> tuple[np.ndarray, list[dict]]:
    vectors = np.load(INDEX_DIR / "vectors.npy")
    with open(INDEX_DIR / "chunks.json") as f:
        chunks = json.load(f)
    return vectors, chunks


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query_norm = query_vec / np.linalg.norm(query_vec)
    matrix_norm = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix_norm @ query_norm


def search(query: str, k: int = 4) -> list[dict]:
    vectors, chunks = load_index()
    query_vec = embed_texts([query])[0]
    scores = cosine_similarity(query_vec, vectors)
    top_k_idx = np.argsort(scores)[::-1][:k]
    return [{**chunks[i], "score": float(scores[i])} for i in top_k_idx]
