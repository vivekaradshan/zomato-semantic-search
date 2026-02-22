# Zomato Semantic Restaurant Search

A restaurant search engine that understands natural language — *"something warm and crispy on a rainy evening in Chennai"* returns South Indian snack places, not Italian desserts.

Built with PySpark, Delta Lake, OpenSearch, FastAPI, and React.

---

## Architecture

```
zomato_with_dynamic_menu.csv
         ↓
  PySpark (01_data_prep)
  Clean + build text_for_embedding
  (name | cuisines | price tier | city | menu items)
         ↓
  Delta Lake  ──  raw/restaurants
         ↓
  OpenAI text-embedding-3-small (02_embeddings)
  1024-dim vectors per restaurant
         ↓
  Delta Lake  ──  embeddings/restaurants
         ↓
  OpenSearch in Docker (03_ingestion)
  HNSW kNN index (nmslib engine)
         ↓
  FastAPI  ←→  React UI
```

### Query Pipeline

```
User query: "It's raining in Chennai, I want something warm"
         ↓
  GPT-4o-mini (query rewriting)
  → food_terms: "bajji bonda vada pakoda hot snacks chai South Indian"
  → location: "Chennai"
         ↓
  OpenAI text-embedding-3-small
  → 1024-dim query vector
         ↓
  OpenSearch
  Pre-filter by location → rank by cosine similarity
         ↓
  Results: South Indian snack restaurants in Chennai
```

---

## Project Structure

```
restaurant-semantic-search/
├── docker-compose.yml              # OpenSearch + Dashboards
├── requirements.txt
├── .env                            # OPENAI_API_KEY (never commit)
├── data/
│   └── zomato_with_dynamic_menu.csv
├── notebooks/
│   ├── 01_data_prep.ipynb          # PySpark cleaning → Delta Lake
│   ├── 02_embeddings.ipynb         # OpenAI embeddings → Delta Lake
│   └── 03_ingestion.ipynb          # Delta Lake → OpenSearch
├── delta_lake/
│   ├── raw/                        # Cleaned restaurant data
│   └── embeddings/                 # Vectors + metadata
├── api/
│   └── main.py                     # FastAPI — semantic / keyword / hybrid
└── ui/                             # React + Vite frontend
    └── src/
        ├── components/             # SearchBar, ResultCard, ComparisonView
        ├── hooks/useSearch.js
        └── api/searchApi.js
```

---

## Setup

### Prerequisites

- Python 3.12
- Java 17 — `brew install openjdk@17`
- Docker Desktop (allocate ≥ 6 GB RAM)
- OpenAI API key

### 1. Virtual environment

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python -m ipykernel install --user --name restaurant-search --display-name "Restaurant Search (3.12)"
```

### 2. API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
```

### 3. Start OpenSearch

```bash
docker-compose up -d
```

| Service | URL |
|---------|-----|
| OpenSearch API | http://localhost:9200 |
| OpenSearch Dashboards | http://localhost:5601 |

### 4. Run notebooks in order

```bash
jupyter lab
```

| Notebook | What it does |
|----------|-------------|
| `01_data_prep` | Clean CSV → Delta Lake |
| `02_embeddings` | Generate 1024-dim vectors via OpenAI → Delta Lake |
| `03_ingestion` | Bulk load into OpenSearch HNSW index |

> `02_embeddings` runs on a 50K sample by default (`SAMPLE = True`). Cost ≈ $0.03. Set `SAMPLE = False` for the full dataset ≈ $0.30.

### 5. Start the API

```bash
# Run from project root so .env is loaded
uvicorn api.main:app --reload
```

Interactive docs: http://localhost:8000/docs

### 6. Start the React UI

```bash
cd ui
npm install
npm run dev
```

Open http://localhost:5173

---

## API Reference

All search endpoints accept:

```json
{ "query": "string", "top_k": 10 }
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search/semantic` | POST | GPT rewrite → kNN vector search |
| `/search/keyword` | POST | GPT location extract → BM25 full-text |
| `/search/hybrid` | POST | 70% semantic + 30% keyword |
| `/health` | GET | Liveness check |

---

## Search Modes

| Mode | How it works | Best for |
|------|-------------|---------|
| **Semantic** | Rewrites query with GPT → embeds → cosine similarity | Mood, occasion, vibe queries |
| **Keyword** | BM25 exact term matching + location filter | Restaurant name, specific cuisine |
| **Hybrid** | 70% semantic + 30% keyword | General use |
| **Compare** | Side-by-side semantic vs keyword | Demos, understanding the difference |

---

## HNSW Index Parameters

| Parameter | Value | Effect |
|-----------|-------|--------|
| `engine` | `nmslib` | Supports vectors up to 16k dims |
| `m` | 16 | Connections per node — higher = better recall, more memory |
| `ef_construction` | 128 | Build-time candidate list — higher = better graph, slower build |
| `ef_search` | 100 | Query-time candidate list — tunable without rebuilding |
| `space_type` | `cosinesimil` | Cosine similarity for text embeddings |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required. Set in `.env` |
| `OPENSEARCH_HOST` | `localhost` | OpenSearch hostname |
| `OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `INDEX_NAME` | `restaurants` | Index name |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |

---

## Test Queries

These queries demonstrate semantic search over keyword search:

| Query | What semantic finds |
|-------|-------------------|
| `It's raining in Chennai, I want something warm` | South Indian snack places — bajji, bonda, vada |
| `First date, not too expensive, Mumbai` | Mid-range romantic Continental/North Indian |
| `Sunday morning lazy breakfast with family` | Breakfast cafes, South Indian tiffin |
| `Something light after a long day` | Salads, soups, juices, light Continental |
| `Quick lunch under 200 in Bangalore` | Budget tiffin, darshini, fast casual |
