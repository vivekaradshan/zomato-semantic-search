"""
FastAPI search service for Zomato Semantic Search.

Endpoints
---------
POST /search/semantic   — kNN vector search
POST /search/keyword    — BM25 full-text search
POST /search/hybrid     — weighted combination of both
GET  /health            — liveness check
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
load_dotenv()  # loads .env from project root
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from opensearchpy import OpenSearch, NotFoundError
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config (override with env vars)
# ---------------------------------------------------------------------------
OS_HOST    = os.getenv("OPENSEARCH_HOST", "localhost")
OS_PORT    = int(os.getenv("OPENSEARCH_PORT", "9200"))
INDEX_NAME = os.getenv("INDEX_NAME", "restaurants")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ---------------------------------------------------------------------------
# Singletons — loaded once at startup
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_openai() -> OpenAI:
    return OpenAI()   # Reads OPENAI_API_KEY from env


@lru_cache(maxsize=1)
def get_client() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": OS_HOST, "port": OS_PORT}],
        http_compress=True,
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Zomato Semantic Search API",
    description="Semantic, keyword, and hybrid restaurant search powered by OpenSearch + OpenAI text-embedding-3-small",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, example="spicy north Indian food")
    top_k: int = Field(default=10, ge=1, le=50)


class Restaurant(BaseModel):
    restaurant_id: str
    name: str
    cuisines: str
    location: str
    rating: float
    cost_for_two: int
    text_for_embedding: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _hits_to_restaurants(hits: list[dict[str, Any]]) -> list[dict]:
    results = []
    for hit in hits:
        src = hit["_source"]
        results.append({
            "restaurant_id":      src.get("restaurant_id", ""),
            "name":               src.get("name", ""),
            "cuisines":           src.get("cuisines", ""),
            "location":           src.get("location", ""),
            "rating":             src.get("rating", 0.0),
            "cost_for_two":       src.get("cost_for_two", 0),
            "text_for_embedding": src.get("text_for_embedding", ""),
            "_score":             hit.get("_score"),
        })
    return results


VECTOR_DIM = 1024  # OpenSearch index dimension

_REWRITE_SYSTEM_PROMPT = """You are a food search assistant for an Indian restaurant app with deep knowledge of Indian food culture and regional eating habits.

Parse the user's message and return a JSON object with two fields:
- "food_terms": concise food-focused search terms (cuisine type, specific dishes, mood). Max 15 words. No location.
- "location": the city or area mentioned, or null if none.

Indian cultural food context you must apply:
- Rainy/monsoon weather → hot deep-fried snacks: bajji, pakoda, bonda, vada, samosa, bhajiya, bread pakora. Pair with chai or filter coffee. NOT desserts or salads.
- Chennai rain/evening → South Indian snacks: bajji, bonda, vada, idli, filter coffee, masala chai
- Mumbai rain/evening → vada pav, pav bhaji, pakoda, chai
- Delhi/North India rain → pakoda, samosa, chai, maggi, momos
- Morning → idli, dosa, poha, upma, paratha, chai
- Late night → biryani, kebabs, rolls, street food
- Comfort food (India) → dal rice, khichdi, rasam rice, curd rice
- Hunger craving spicy → Briyani, Kebab, chicken
- Romantic/date → North Indian, Continental, rooftop restaurant, fine dining
- Quick/budget → chaat, street food, tiffin, darshini, fast food
- Healthy → salads, juices, multigrain, South Indian tiffin

Examples:
"It's raining in the evening and I want to eat something in Chennai" → {"food_terms": "bajji bonda vada pakoda hot fried snacks chai South Indian", "location": "Chennai"}
"rainy evening Mumbai" → {"food_terms": "vada pav pakoda chai hot street food fried snacks", "location": "Mumbai"}
"date night in Mumbai" → {"food_terms": "romantic fine dining upscale North Indian Continental", "location": "Mumbai"}
"something spicy" → {"food_terms": "spicy curry chilli tandoori hot", "location": null}
"quick lunch under 200 in Bangalore" → {"food_terms": "quick budget tiffin darshini affordable fast casual", "location": "Bangalore"}
"Sunday morning breakfast Delhi" → {"food_terms": "breakfast paratha poha chole bhature morning", "location": "Delhi"}

Return only valid JSON. No explanation."""

def _rewrite_query(query: str) -> tuple[str, str | None]:
    """Returns (food_terms, location_or_None)."""
    import json
    response = get_openai().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        max_tokens=60,
        temperature=0,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(response.choices[0].message.content)
    food_terms = parsed.get("food_terms", query)
    location   = parsed.get("location") or None
    print(f"[query rewrite] '{query}' → food='{food_terms}' location='{location}'")
    return food_terms, location


def _embed(text: str) -> list[float]:
    response = get_openai().embeddings.create(model=MODEL_NAME, input=[text], dimensions=VECTOR_DIM)
    return response.data[0].embedding


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    try:
        info = get_client().info()
        return {"status": "ok", "opensearch": info["version"]["number"]}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/search/semantic", response_model=list[dict])
def semantic_search(req: SearchRequest):
    """Pure kNN vector search — finds semantically similar restaurants."""
    food_terms, location = _rewrite_query(req.query)
    query_vector = _embed(food_terms)

    if location:
        # Pre-filter by city, then rank survivors by vector similarity
        body = {
            "size": req.top_k,
            "query": {
                "script_score": {
                    "query": {"match": {"location": location}},
                    "script": {
                        "lang": "knn",
                        "source": "knn_score",
                        "params": {"field": "embedding", "query_value": query_vector, "space_type": "cosinesimil"},
                    },
                }
            },
            "_source": {"excludes": ["embedding"]},
        }
    else:
        body = {
            "size": req.top_k,
            "query": {"knn": {"embedding": {"vector": query_vector, "k": req.top_k}}},
            "_source": {"excludes": ["embedding"]},
        }

    try:
        resp = get_client().search(index=INDEX_NAME, body=body)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Index '{INDEX_NAME}' not found. Run notebook 03_ingestion first.")

    return _hits_to_restaurants(resp["hits"]["hits"])


@app.post("/search/keyword", response_model=list[dict])
def keyword_search(req: SearchRequest):
    """BM25 full-text search across name, cuisines, and location."""
    _, location = _rewrite_query(req.query)

    bm25_clause = {
        "multi_match": {
            "query": req.query,
            "fields": ["name^2", "cuisines^1.5", "location"],
            "type": "best_fields",
            "fuzziness": "AUTO",
        }
    }
    query_body = (
        {"bool": {"must": [bm25_clause], "filter": [{"match": {"location": location}}]}}
        if location else bm25_clause
    )

    try:
        resp = get_client().search(
            index=INDEX_NAME,
            body={"size": req.top_k, "query": query_body, "_source": {"excludes": ["embedding"]}},
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Index '{INDEX_NAME}' not found.")

    return _hits_to_restaurants(resp["hits"]["hits"])


@app.post("/search/hybrid", response_model=list[dict])
def hybrid_search(req: SearchRequest):
    """
    Weighted combination: 70% semantic + 30% keyword.
    Uses OpenSearch bool/should to combine kNN and BM25.
    """
    food_terms, location = _rewrite_query(req.query)
    query_vector = _embed(food_terms)

    if location:
        body: dict = {
            "size": req.top_k,
            "query": {
                "script_score": {
                    "query": {
                        "bool": {
                            "must": {"match": {"location": location}},
                            "should": [{"multi_match": {"query": food_terms, "fields": ["name^2", "cuisines^1.5"], "boost": 0.3}}],
                        }
                    },
                    "script": {
                        "lang": "knn",
                        "source": "knn_score",
                        "params": {"field": "embedding", "query_value": query_vector, "space_type": "cosinesimil"},
                    },
                }
            },
            "_source": {"excludes": ["embedding"]},
        }
    else:
        body: dict = {
            "size": req.top_k,
            "query": {
                "bool": {
                    "should": [
                        {"multi_match": {"query": food_terms, "fields": ["name^2", "cuisines^1.5", "location"], "boost": 0.3}},
                        {"knn": {"embedding": {"vector": query_vector, "k": req.top_k, "boost": 0.7}}},
                    ]
                }
            },
            "_source": {"excludes": ["embedding"]},
        }

    try:
        resp = get_client().search(index=INDEX_NAME, body=body)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Index '{INDEX_NAME}' not found.")

    return _hits_to_restaurants(resp["hits"]["hits"])


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
