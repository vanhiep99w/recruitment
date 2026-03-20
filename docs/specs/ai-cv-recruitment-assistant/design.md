# Design: AI CV & Recruitment Assistant

## Context

Agency recruiters receive high volumes of CVs per mandate, spend excessive time on manual parsing and scoring, and lack an affordable tool optimized for Vietnamese-language CVs and ZIP bulk processing. This system provides an AI-powered pipeline: ingest → parse → analyze JD → match → manage → export. It targets agency recruiters (headhunters, staffing consultants) in Vietnam as the primary persona, with English document support from day one.

## Architecture Overview

```
Browser (Next.js)
      │
      ▼
FastAPI (REST API)
      │
      ├── File Processor (PyMuPDF / python-docx / Tesseract OCR)
      │
      ├── ARQ Job Queue (Redis) ◄── async batch workers
      │         │
      │         ▼
      │    LLM Proxy Client (OpenAI-compatible)
      │         └── CV parsing, JD analysis, match rationale
      │
      ├── pgvector (PostgreSQL) ── semantic search + all relational data
      │
      └── Export Service (openpyxl / python-docx / reportlab)
```

Single-region deployment. All components in Docker Compose. No external parser dependency.

## Components

### Component 1: File Ingestion Service
- **Purpose**: Accept uploaded files (single or ZIP), validate format/size, extract ZIP contents, enqueue parse jobs per file
- **Interface**: `POST /api/upload` (multipart) → `{job_id, file_count, status}`; `GET /api/upload/{job_id}/status` → `{processed, total, errors[]}`
- **Dependencies**: ARQ job queue, Redis, Python `zipfile`

### Component 2: Document Extractor
- **Purpose**: Convert raw file bytes to plain text. Routes by file type: PyMuPDF for text-based PDFs, python-docx for DOCX, Tesseract OCR (with `vie` tessdata) for images and scanned PDFs. Returns text and confidence score.
- **Interface**: `extract(file_path, file_type) → (text: str, confidence: float)`
- **Dependencies**: PyMuPDF, python-docx, pdf2image, Tesseract (`vie` + `eng` tessdata)

### Component 3: LLM Parser
- **Purpose**: Send extracted text to LLM proxy with a JSON schema prompt; receive and validate structured CandidateProfile or JDProfile. Handles retries (×2) and Pydantic schema enforcement.
- **Interface**: `parse_cv(text: str) → CandidateProfile`, `parse_jd(text: str) → JDProfile`
- **Dependencies**: OpenAI-compatible proxy (configurable base URL + API key), Pydantic

### Component 4: Match Engine
- **Purpose**: Compute match scores (0–100) between a CandidateProfile and a JDProfile. Uses pgvector cosine similarity for initial ranking, LLM proxy for per-category scoring and natural-language rationale generation.
- **Interface**: `score(candidate_id, job_id) → Match`, `score_batch(candidate_ids[], job_id) → Match[]`
- **Dependencies**: pgvector, LLM proxy, PostgreSQL

### Component 5: Candidate Repository
- **Purpose**: CRUD for Candidate, CandidateProfile, CV, and TalentPool entities. Full-text search via PostgreSQL `tsvector`. Vector search via pgvector. Duplicate detection by email + name similarity.
- **Interface**: REST endpoints under `/api/candidates` and `/api/talent-pools`
- **Dependencies**: PostgreSQL + pgvector extension

### Component 6: Job Repository
- **Purpose**: CRUD for Job and JDProfile entities. Links to Match and Pipeline records.
- **Interface**: REST endpoints under `/api/jobs`
- **Dependencies**: PostgreSQL

### Component 7: Export Service
- **Purpose**: Generate downloadable CSV, JSON, or DOCX files from candidate profile + match data on demand.
- **Interface**: `POST /api/export` `{candidate_ids[], job_id?, format}` → file stream
- **Dependencies**: openpyxl (CSV/XLSX), python-docx (DOCX), reportlab (PDF)

## Data Model

```sql
-- Organizations & Users
organizations      (id UUID PK, name, plan_tier, seats INT, created_at)
users              (id UUID PK, name, email UNIQUE, role, org_id FK, created_at)

-- Candidates
candidates         (id UUID PK, name, email, phone, location, org_id FK, created_at)
candidate_profiles (id UUID PK, candidate_id FK UNIQUE,
                    skills TEXT[],
                    work_experience JSONB,   -- [{title, company, start, end, description}]
                    education JSONB,         -- [{degree, institution, year}]
                    languages TEXT[],
                    certifications TEXT[],
                    embedding vector(1536),  -- pgvector
                    parse_status TEXT,       -- parsed|low_confidence|ocr_low_quality|manually_reviewed|parse_failed
                    parsed_at TIMESTAMPTZ)
cvs                (id UUID PK, candidate_id FK, file_url, file_type, upload_ts,
                    parse_status, raw_text TEXT)

-- Jobs
jobs               (id UUID PK, title, org_id FK, jd_text TEXT, status, created_at)
jd_profiles        (id UUID PK, job_id FK UNIQUE,
                    required_skills TEXT[],
                    nice_to_have_skills TEXT[],
                    seniority TEXT,          -- junior|mid|senior|lead|unspecified
                    experience_years_min INT,
                    experience_years_max INT,
                    responsibilities JSONB,
                    embedding vector(1536))  -- pgvector

-- Matching & Pipeline
matches            (id UUID PK, candidate_id FK, job_id FK,
                    overall_score INT,
                    skill_score INT,
                    experience_score INT,
                    education_score INT,
                    rationale TEXT,
                    created_at TIMESTAMPTZ,
                    UNIQUE(candidate_id, job_id))
pipelines          (id UUID PK, job_id FK, candidate_id FK,
                    stage TEXT,             -- sourced|screened|shortlisted|interviewed|offered|hired|rejected
                    updated_at TIMESTAMPTZ,
                    UNIQUE(job_id, candidate_id))

-- Talent Pools
talent_pools       (id UUID PK, name, org_id FK, created_at)
talent_pool_members(pool_id FK, candidate_id FK, PRIMARY KEY(pool_id, candidate_id))
```

## API Design

```
# File Upload
POST   /api/upload                        # Upload single CV or ZIP (multipart)
GET    /api/upload/{job_id}/status        # Batch processing progress

# Candidates
GET    /api/candidates                    # List with search/filter (skill, exp, score, pool)
GET    /api/candidates/{id}              # Candidate detail + profile
PATCH  /api/candidates/{id}/profile      # Manual profile correction

# Jobs
POST   /api/jobs                          # Create job + trigger JD analysis
GET    /api/jobs                          # List jobs
GET    /api/jobs/{id}                     # Job detail + JD profile
GET    /api/jobs/{id}/candidates          # Ranked match list for job
POST   /api/jobs/{id}/match               # Trigger / re-trigger match scoring

# Pipeline
PATCH  /api/pipelines/{id}               # Update stage (shortlist/reject/etc.)

# Export
POST   /api/export                        # {candidate_ids[], job_id?, format: csv|json|docx}

# Talent Pools
GET    /api/talent-pools                  # List pools
POST   /api/talent-pools                  # Create pool
POST   /api/talent-pools/{id}/members     # Add candidates to pool
DELETE /api/talent-pools/{id}/members/{candidate_id}
```

## Error Handling

| Error | HTTP | Response | UX Behavior |
|---|---|---|---|
| Unsupported file type | 422 | `{error: "unsupported_format", message: "..."}` | Inline error on upload zone |
| File > 10MB | 422 | `{error: "file_too_large"}` | Inline error on upload zone |
| ZIP > 200 files | 422 | `{error: "batch_limit_exceeded", count: N}` | Modal error before processing |
| LLM parse fails after 2 retries | 200 | `parse_status: parse_failed` | Warning badge; manual retry button |
| OCR low confidence | 200 | `parse_status: ocr_low_quality` | Warning badge on candidate card |
| Duplicate candidate detected | 200 | `{duplicate: true, existing_id: "..."}` | Merge / create new prompt |
| LLM match scoring timeout after 2 retries | 200 | `match_status: failed` | Error state on match row with retry button |
| ZIP extraction failure (malformed archive) | 422 | `{error: "zip_invalid"}` | Error message; no partial processing |

## Goals / Non-Goals

**Goals:**
- Parse Vietnamese and English CVs with ≥90% field extraction accuracy on PDF/DOCX
- Process a 50-CV ZIP batch end-to-end in under 3 minutes
- Return match scores + rationale within 10 seconds for 50 candidates
- Support full-text and semantic search across the candidate database
- Correct Vietnamese diacritical marks in all parsing, search, and display contexts

**Non-Goals:**
- Content generation (outreach emails, candidate reports)
- Custom scoring criterion weights per JD
- PII masking / anonymized export
- ATS integrations (Greenhouse, Lever, Workday)
- REST API for external consumers
- Bias audit reporting

## Decisions

### 1. LLM Proxy over Affinda
- **Chosen**: OpenAI-compatible proxy (configurable base URL + API key)
- **Alternative**: Affinda API ($99+/month, proven accuracy, 56-language support)
- **Rationale**: Single AI abstraction for parsing + matching + rationale generation; lower cost; no vendor lock-in; user preference
- **Trade-off**: Requires structured output prompt engineering; Vietnamese parsing quality depends on LLM capability
- **Mitigation**: JSON schema enforcement (structured output mode); confidence scoring; manual correction UI for low-confidence parses

### 2. pgvector over dedicated vector DB
- **Chosen**: PostgreSQL + pgvector extension
- **Alternative**: Qdrant, Pinecone
- **Rationale**: Reduces infrastructure components at MVP scale; candidate data is relational-first; vector search is supplementary
- **Trade-off**: Lower vector search throughput at very large scale (>1M vectors)
- **Mitigation**: Sufficient for MVP; well-defined migration path to Qdrant post-scale

### 3. ARQ over Celery
- **Chosen**: ARQ (Redis-backed async job queue)
- **Alternative**: Celery + Redis/RabbitMQ
- **Rationale**: Simpler setup, fewer moving parts, sufficient concurrency for ZIP batch processing at MVP scale
- **Trade-off**: Less feature-rich (limited scheduling, fewer retry strategies)
- **Mitigation**: ARQ covers retry + concurrency for this workload; upgrade path to Celery exists

### 4. FastAPI over Django/Flask
- **Chosen**: FastAPI
- **Rationale**: Async-native critical for concurrent LLM calls and file I/O; automatic OpenAPI docs; Pydantic-native schema validation matches LLM structured output workflow

## Risks / Trade-offs

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM parsing accuracy on Vietnamese CVs below 90% target | Medium | High | Structured output schema enforcement; confidence scoring; manual correction UI; test with real Vietnamese CV samples pre-launch |
| OCR quality failures on photographed/scanned CVs | High | Medium | Tesseract `vie` tessdata; confidence threshold; Google Cloud Document AI fallback for complex layouts |
| LLM API cost overrun at scale | Medium | High | Response caching (Redis); batch embedding calls; monitor cost-per-CV; tiered pricing pass-through |
| LLM proxy vendor dependency (price/availability changes) | Medium | Medium | Configurable base URL + API key abstraction; supports switching providers without code changes |
| ZIP processing failures on malformed archives | Medium | Low | Per-file error isolation; partial success reporting; graceful skip with summary |
| Match scoring SLA breach at high concurrency | Low | Medium | ARQ worker concurrency tuning; pgvector ANN index (IVFFlat); LLM batch calls where supported |

## Testing Strategy

| Layer | Scope | Tooling |
|---|---|---|
| Unit | Document extractor (PDF/DOCX/OCR routing), LLM parser schema validation, match score calculation logic, export file generation | pytest |
| Integration | Upload → parse → database pipeline; JD analysis → match scoring pipeline; ZIP batch queue processing; duplicate detection | pytest + Docker Compose (test DB + Redis) |
| E2E | Full recruiter workflow: upload ZIP → view parsed candidates → create job + JD → match → view ranked list → export CSV | Playwright |
