"""
API REST routes for UO-News.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search text")


class SearchResult(BaseModel):
    rank: int
    score: float
    titulo: str
    fecha: str
    etiquetas: str
    text: str


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    results: list[SearchResult]


class ReindexResponse(BaseModel):
    status: str
    total_documents: int
    total_news: int


class HealthResponse(BaseModel):
    status: str
    chromadb: str
    documents_indexed: int



# ── Rutas ────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
def health(request: Request):
    collection = getattr(request.app.state, "chroma_collection", None)
    if collection is None:
        return HealthResponse(status="starting", chromadb="not_ready", documents_indexed=0)
    return HealthResponse(status="ok", chromadb="ready", documents_indexed=collection.count())


@router.post("/search", response_model=SearchResponse, tags=["Search"])
def search(body: SearchRequest, request: Request):
    print(f"TODO: Searching for '{body.query}' in ChromaDB...")


@router.post("/reindex", response_model=ReindexResponse, tags=["System"])
def reindex(request: Request):
    print("TODO: Reindexing...")
