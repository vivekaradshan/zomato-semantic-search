# Zomato Semantic Search — Architecture

## Overview

A restaurant search engine that understands natural language queries like *"something warm and crispy on a rainy evening in Chennai"* — returning relevant results based on meaning, not just keyword matching.

---

## Data Pipeline

```
Raw Data → Delta Lake → OpenSearch
```

**Ingestion (Notebook 01)** — PySpark reads `zomato_with_dynamic_menu.csv` (~9,000 restaurants across global cities). Columns are cleaned, renamed to `snake_case`, and a `text_for_embedding` field is constructed combining restaurant name, cuisines, price tier, city, and menu items — e.g.:

```
"Murugan Idli Shop | South Indian | budget friendly | Chennai | Idli, Vada, Filter Coffee"
```

**Embedding (Notebook 02)** — The `text_for_embedding` field is sent in batches to OpenAI's `text-embedding-3-small` model, producing a 1024-dimensional vector per restaurant. These vectors capture semantic meaning — vada and fried snacks end up close together in vector space.

**Indexing (Notebook 03)** — Vectors and metadata are bulk-loaded into OpenSearch running in Docker. The index uses HNSW (Hierarchical Navigable Small World) graph structure for fast approximate nearest-neighbour search.

---

## Search API (FastAPI)

Every search request goes through a two-stage pipeline:

### Stage 1 — Query Understanding (GPT-4o-mini)

The raw query is sent to GPT-4o-mini with a culturally-aware Indian food context prompt. It returns two things:

- `food_terms` — intent-focused search terms (`"bajji bonda vada pakoda hot snacks chai"`)
- `location` — extracted city (`"Chennai"`) or `null`

### Stage 2 — Search Execution (OpenSearch)

Three search modes are available:

| Mode | How it works |
|------|-------------|
| **Semantic** | `food_terms` are embedded into a 1024-dim vector; when `location` is present, a `script_score` query pre-filters by city first, then ranks by cosine similarity |
| **Keyword** | BM25 full-text search with `location` as a hard filter via `bool.filter` |
| **Hybrid** | 70% semantic + 30% keyword combined via `bool.should` |

---

## React UI

Built with Vite + React. Users can switch between Semantic, Keyword, Hybrid, and Compare modes. Compare mode fires both semantic and keyword searches in parallel (`Promise.all`) and renders them side by side — making the quality difference immediately visible. A results slider controls how many results are returned (5–20).

---

## Key Design Decision

Query rewriting is the secret — it bridges the gap between how users speak and how restaurant data is structured, with Indian cultural context baked into the prompt.
