# Zomato Semantic Restaurant Search

End-to-end semantic search system built on local PySpark (Databricks-compatible), Delta Lake, OpenSearch, and FastAPI.

## Architecture

```
Raw CSV (Kaggle)
     ↓
Local PySpark (mirrors Databricks)
     ↓
HuggingFace Sentence Transformers (all-MiniLM-L6-v2, 384 dims)
     ↓
Local Delta Lake (Parquet + transaction log)
     ↓
OpenSearch in Docker (HNSW kNN index)
     ↓
FastAPI  ←→  React UI
```

## Project Structure

```
semantic-search/
├── docker-compose.yml          # OpenSearch + Dashboards
├── requirements.txt
├── data/
│   └── zomato.csv              # Kaggle dataset (add manually)
├── notebooks/
│   ├── 01_data_prep.ipynb      # PySpark cleaning → Delta Lake
│   ├── 02_embeddings.ipynb     # Vector generation → Delta Lake
│   └── 03_ingestion.ipynb      # Delta Lake → OpenSearch
├── delta_lake/
│   ├── raw/                    # Cleaned restaurant data
│   └── embeddings/             # Vectors + metadata
├── api/
│   └── main.py                 # FastAPI (semantic / keyword / hybrid)
└── ui/                         # React frontend (separate setup)
```

## Setup

### Prerequisites

- Python 3.10+
- Java 11 (required by Spark) — `brew install openjdk@11`
- Docker Desktop (give it ≥ 6 GB RAM)

### 1. Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add to `~/.zshrc`:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 11)
export PYSPARK_PYTHON=python3
```

### 2. Start OpenSearch

```bash
docker-compose up -d
```

- OpenSearch API: http://localhost:9200
- OpenSearch Dashboards: http://localhost:5601

### 3. Get the dataset

```bash
kaggle datasets download -d shrutimehta/zomato-restaurants-data
unzip zomato-restaurants-data.zip -d data/
```

### 4. Run notebooks in order

```bash
jupyter notebook notebooks/
```

| Notebook | What it does | Typical runtime |
|----------|-------------|-----------------|
| `01_data_prep` | Clean CSV → Delta Lake | ~2 min |
| `02_embeddings` | Generate 384-dim vectors → Delta Lake | ~1-2 hr (full), ~5 min (50K sample) |
| `03_ingestion` | Bulk load into OpenSearch | ~5-15 min |

### 5. Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

## API Reference

All search endpoints accept:

```json
{ "query": "string", "top_k": 10 }
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search/semantic` | POST | kNN vector search |
| `/search/keyword`  | POST | BM25 full-text search |
| `/search/hybrid`   | POST | 70% semantic + 30% keyword |
| `/health`          | GET  | Liveness check |

## Ingestion Tuning Results

Varying `BATCH_SIZE` in `03_ingestion.ipynb` (fill in your results):

| batch_size | elapsed (s) | docs/s |
|-----------|------------|--------|
| 100       |            |        |
| 500       |            |        |
| 1000      |            |        |
| 2000      |            |        |

## HNSW Parameters

| Parameter | Value | Effect |
|-----------|-------|--------|
| `m` | 16 | Connections per node — higher = better recall, more memory |
| `ef_construction` | 128 | Build-time candidate list — higher = better graph, slower build |
| `ef_search` | 100 | Query-time candidate list — tune without rebuilding |

## Environment Variables (API)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSEARCH_HOST` | `localhost` | OpenSearch hostname |
| `OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `INDEX_NAME` | `restaurants` | Index name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model |
