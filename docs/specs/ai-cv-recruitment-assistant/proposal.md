# Proposal: AI CV & Recruitment Assistant

## Why

Agency recruiters — headhunters and staffing consultants — spend the majority of their working hours on low-value manual tasks: reading CVs, copy-pasting candidate data, manually scoring fit against job requirements, and formatting candidate information for client review. Recruiters scan a resume in 6–11 seconds on average, yet manage dozens of concurrent mandates with hundreds of CVs per role. There is no affordable, standalone SaaS tool that handles the full agency workflow — bulk CV ingestion, Vietnamese-language parsing, JD-driven matching — without requiring ATS vendor lock-in or developer integration. This product builds that tool, Vietnam-first, targeting the gap left by enterprise incumbents (Workday $35K+/yr, Greenhouse $6–25K/yr) and API-only solutions (Affinda, Textkernel) that serve developers, not recruiters.

## What Changes

A new standalone web application for agency recruiters that replaces manual CV review with an AI-powered pipeline: upload CVs (individually or as a ZIP batch) → get structured candidate profiles → upload a JD → get ranked candidates with match scores and rationale → search and export the candidate database.

## Capabilities

### New Capabilities
- `cv-ingestion`: Upload CV files (PDF/DOCX/image) individually or as ZIP batches up to 200 files; async processing with progress tracking
- `cv-parsing`: LLM-powered extraction of structured candidate profiles from raw CV content, Vietnamese-first with English support
- `jd-analysis`: Parse job descriptions (text paste or file upload) into structured requirement profiles
- `candidate-matching`: Semantic JD-CV match scoring (0–100) with category breakdown (skills, experience, education) and LLM-generated rationale
- `candidate-database`: Searchable, filterable candidate repository with tagging and talent pool grouping
- `data-export`: Export candidate profiles and match results as CSV, JSON, or DOCX

### Modified Capabilities
N/A — greenfield product.

## Scope

### In Scope
- CV upload: PDF, DOCX, DOC, image (JPG/PNG), ZIP archive
- Async batch processing with progress indicator
- LLM-based CV parsing (OpenAI-compatible proxy) → structured candidate profile
- JD upload/paste → structured JD profile
- Candidate-JD match scoring with breakdown (skills, experience, education) + natural-language rationale
- Candidate database with full-text search, skill filter, score filter
- Structured export: CSV, JSON, DOCX
- Vietnamese-first UI with English document support

### Out of Scope (Non-Goals)
- Outreach email generation, candidate summary/report generation
- Custom scoring criterion weights per JD
- PII masking / anonymized export
- ATS integration (Greenhouse, Lever, Workday)
- Agency CRM (client/placement tracking)
- REST API for external consumers
- Bias audit reporting

## Success Criteria
- Agency recruiter can upload a 50-CV ZIP and have all candidates parsed and available for matching in under 3 minutes
- Match scoring returns ranked candidates with breakdown + rationale within 10 seconds of JD submission
- Recruiter can find a specific candidate by skill + experience filter in under 30 seconds
- CV parsing accuracy ≥90% on Vietnamese PDF/DOCX CVs (measured by field extraction correctness on test set)
- System supports Vietnamese diacritical marks correctly in all search and display contexts

## Impact

Positions against Manatal ($15–55/user/month, limited Vietnamese NLP, no ZIP bulk UX) and Affinda (API-only, no recruiter UI). Directly addresses Gap 1 (Vietnamese NLP), Gap 3 (affordable agency SaaS), and Gap 4 (ZIP bulk UX) from research. New system introduces: LLM proxy dependency (OpenAI-compatible), async job queue for bulk processing, vector search for candidate matching, PostgreSQL for candidate/job data storage.
