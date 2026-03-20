# Tech Stack: AI CV & Recruitment Assistant

## Frontend
- **Framework**: Next.js 14 (App Router) — SSR for fast initial load, file upload UX, Vietnamese locale support
- **Styling**: Tailwind CSS + shadcn/ui — rapid UI development, consistent component library
- **State Management**: Zustand — lightweight, sufficient for candidate list + upload progress state

## Backend
- **Framework**: FastAPI (Python) — async-native, ideal for LLM API calls and file processing; strong Python ecosystem for PDF/OCR libraries
- **Database**: PostgreSQL + pgvector extension — relational data for candidates/jobs/matches + vector embeddings for semantic search
- **Cache**: Redis — job queue state, upload session tracking, LLM response caching
- **Message Queue**: Redis + ARQ (async job queue) — async batch CV processing; lightweight alternative to Celery for this scale

## AI / LLM
- **LLM Proxy**: OpenAI-compatible proxy (configurable base URL + API key) — CV parsing structured output, JD analysis, match rationale generation
- **Embeddings**: OpenAI-compatible embeddings endpoint (same proxy) — candidate profile + JD vectors for pgvector similarity search
- **OCR**: pdf2image + Tesseract (Vietnamese `vie` tessdata) — scanned/image CV extraction; Google Cloud Document AI as fallback for complex layouts

## File Processing
- **PDF text extraction**: PyMuPDF (fitz) — fast, accurate text-based PDF parsing
- **DOCX extraction**: python-docx
- **ZIP handling**: Python stdlib `zipfile`
- **Export**: openpyxl (CSV/XLSX), python-docx (DOCX), reportlab (PDF)

## Infrastructure
- **Cloud Provider**: TBD / self-hosted — Docker Compose for local dev; VPS or Railway/Render for MVP
- **Container Runtime**: Docker + Docker Compose
- **IaC**: Docker Compose (MVP); Terraform when scaling

## CI/CD
- **Pipeline**: GitHub Actions — lint, test, build, deploy on push to main

## Monitoring & Logging
- **APM**: Sentry — error tracking, free tier sufficient for MVP
- **Logging**: structlog (Python) + standard Next.js logging
- **Alerting**: Sentry alerts (MVP); Grafana post-MVP

## Deployment Strategy
- **Strategy**: Rolling (MVP — single instance)
- **Environments**: `local` (Docker Compose), `staging`, `production`

## Key Decisions

### LLM Proxy over Affinda
- **Chosen**: OpenAI-compatible proxy (configurable base URL + API key)
- **Alternative considered**: Affinda API ($99+/month, 56-language support, proven accuracy)
- **Rationale**: Lower cost, no vendor dependency, single AI abstraction handles parsing + matching + generation in one integration
- **Trade-off**: Requires structured output prompt engineering for parsing accuracy; Vietnamese CV quality depends on LLM multilingual capability
- **Mitigation**: JSON schema enforcement (structured output), confidence scoring, human correction UI for low-confidence parses

### pgvector over dedicated vector DB
- **Chosen**: PostgreSQL + pgvector
- **Alternative considered**: Qdrant, Pinecone
- **Rationale**: Reduces infrastructure components at MVP scale; candidate database is relational-first; vector search is supplementary
- **Trade-off**: Lower vector search performance at very large scale (>1M vectors)
- **Mitigation**: Sufficient for MVP; migrate to dedicated vector DB post-scale

### ARQ over Celery
- **Chosen**: ARQ (Redis-backed async job queue)
- **Alternative considered**: Celery + Redis/RabbitMQ
- **Rationale**: Simpler setup, fewer moving parts, sufficient for ZIP batch processing workloads at MVP scale
- **Trade-off**: Less feature-rich than Celery; limited retry/scheduling options
- **Mitigation**: ARQ covers retry + concurrency; upgrade path to Celery if needed
