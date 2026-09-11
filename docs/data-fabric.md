# AURORA Data Fabric

## Overview

The Data Fabric provides news, macroeconomic, and research data to AURORA's intelligence pipeline. All provider access occurs backend-side — no API keys are ever exposed to the frontend, logs, or provenance records.

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   NewsAPI   │    │    FRED     │    │    arXiv    │
│   Provider  │    │   Provider  │    │   Provider  │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                   ┌──────▼──────┐
                   │   Registry  │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │  API Router │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │   Terminal  │
                   │   Status    │
                   └─────────────┘
```

## Providers

### NewsProvider

**Status**: `NOT_CONFIGURED` (default)

**Configuration**:
```bash
AURORA_NEWS_PROVIDER=newsapi
AURORA_NEWS_API_KEY=<your-newsapi-key>
```

**Implementation**: `src/aurora/data/news_provider.py`

### MacroProvider

**Status**: `NOT_CONFIGURED` (default)

**Configuration**:
```bash
AURORA_MACRO_PROVIDER=fred
AURORA_FRED_API_KEY=<your-fred-key>
```

**Implementation**: `src/aurora/data/macro_provider.py`

### ResearchProvider

**Status**: `NOT_CONFIGURED` (default)

**Configuration**:
```bash
AURORA_RESEARCH_PROVIDER=arxiv
```

**Implementation**: `src/aurora/data/research_provider.py`

## Security

- All provider access is backend-only
- API keys are never exposed to frontend/logs/provenance
- Research provider uses allowlisted endpoints only
- Query length bounded to 200 characters
- Result count bounded (1-50)
- Request timeout 15s
- Response size limited to 5MB
- No executable content processed
- SSRF protection via URL validation

## API Endpoints

### News

- `GET /api/v1/news/status` — Provider status
- `GET /api/v1/news/search?q=<query>` — Search news

### Macro

- `GET /api/v1/macro/status` — Provider status
- `GET /api/v1/macro/series/<series_id>` — Get series data
- `GET /api/v1/macro/search?q=<query>` — Search series

### Research

- `GET /api/v1/research/status` — Provider status
- `GET /api/v1/research/search?q=<query>` — Search research

### Overview

- `GET /api/v1/data/status` — Combined provider status

## Provenance

Every data point includes:
- `source`: Provider name (newsapi, fred, arxiv)
- `published_at`: Source publication timestamp
- `retrieved_at`: When AURORA retrieved the data
- `content_hash`: Hash of source content for deduplication

## Failure States

| State | Meaning |
|-------|---------|
| `NOT_CONFIGURED` | No provider configured |
| `CONNECTING` | Attempting connection |
| `READY` | Verified and operational |
| `DEGRADED` | Partial failure |
| `ERROR` | Complete failure |
| `DISCONNECTED` | Lost connection |

## Terminal Integration

Terminal shows provider status:
- `RESEARCH` → arXiv status
- `NEWS` → NewsAPI status
- `MACRO` → FRED status

Status shows `DATA_UNAVAILABLE` when providers are not configured.
