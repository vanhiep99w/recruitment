# Spec: AI CV & Recruitment Assistant

## ADDED Requirements

### Requirement: Single CV Upload
Recruiter uploads one CV file (PDF, DOCX, DOC, JPG, PNG) via drag-and-drop or file picker. System validates format and size, then queues for parsing.

**Priority**: MUST

#### Scenario: Successful PDF upload
- **GIVEN** a logged-in recruiter on the CV upload page
- **WHEN** they drag a `.pdf` file under 10MB onto the upload zone
- **THEN** the file is accepted, a processing status indicator appears, and the CV enters the parsing queue

#### Scenario: Unsupported format rejected
- **GIVEN** a recruiter uploads a `.xlsx` file
- **WHEN** the system validates the file type
- **THEN** an error message is shown: "Unsupported file type. Please upload PDF, DOCX, DOC, JPG, or PNG."

#### Scenario: File too large rejected
- **GIVEN** a recruiter uploads a PDF larger than 10MB
- **WHEN** the system checks file size
- **THEN** an error is shown: "File exceeds 10MB limit." The file is not queued.

---

### Requirement: ZIP Bulk Upload
Recruiter uploads a ZIP archive containing multiple CV files. System extracts, validates each file, and queues all valid CVs for async batch parsing with a progress indicator.

**Priority**: MUST

#### Scenario: Successful ZIP batch
- **GIVEN** a recruiter uploads a ZIP containing 50 PDF/DOCX files
- **WHEN** the system extracts the archive
- **THEN** all 50 files are queued, a progress bar shows "0/50 processed", and the count updates as each CV completes

#### Scenario: ZIP with unsupported files
- **GIVEN** a ZIP contains 45 PDFs and 5 `.txt` files
- **WHEN** the system validates each extracted file
- **THEN** 45 PDFs are queued; the 5 `.txt` files are skipped with a summary: "5 files skipped (unsupported format)"

#### Scenario: ZIP exceeds file count limit
- **GIVEN** a ZIP contains 250 files and the plan limit is 200
- **WHEN** the system counts extracted files
- **THEN** an error is shown: "ZIP contains 250 files. Maximum per batch is 200."

---

### Requirement: LLM-Powered Structured Profile Extraction
System sends extracted CV text to the LLM proxy and returns a structured candidate profile. Vietnamese and English CVs both supported.

**Priority**: MUST

#### Scenario: Successful Vietnamese CV parse
- **GIVEN** a Vietnamese-language PDF CV has been text-extracted
- **WHEN** the system sends the text to the LLM proxy with a structured output schema
- **THEN** a CandidateProfile is created with: full name, email, phone, location, work_experience[], education[], skills[], languages[], certifications[] — all Vietnamese diacritical marks preserved correctly

#### Scenario: Successful English CV parse
- **GIVEN** an English-language DOCX CV
- **WHEN** parsed by the LLM proxy
- **THEN** a CandidateProfile is created with all fields correctly extracted

#### Scenario: Low-confidence parse flagged
- **GIVEN** a CV where the LLM returns fewer than 3 required fields (name, email, at least 1 work experience)
- **WHEN** parsing completes
- **THEN** the candidate record is marked `parse_status: low_confidence` and the recruiter sees a warning badge with an option to manually review/correct

---

### Requirement: OCR for Scanned/Image CVs
For image files (JPG/PNG) and image-based PDFs, the system runs an OCR pipeline before LLM parsing.

**Priority**: MUST

#### Scenario: Image CV processed via OCR
- **GIVEN** a recruiter uploads a JPG photo of a CV
- **WHEN** the system detects it is an image file
- **THEN** OCR (Tesseract with Vietnamese `vie` tessdata) extracts text, which is then passed to the LLM parser — resulting in a structured CandidateProfile

#### Scenario: Low-quality image
- **GIVEN** an uploaded image has resolution below 150 DPI
- **WHEN** OCR completes with low confidence score
- **THEN** the candidate record is marked `parse_status: ocr_low_quality` and the recruiter is prompted: "Image quality may affect accuracy. Review extracted data."

---

### Requirement: Manual Profile Correction
Recruiter can review and inline-edit any parsed field before saving the final candidate record.

**Priority**: MUST

#### Scenario: Recruiter corrects a parsed field
- **GIVEN** a candidate profile shows an incorrect job title in work experience
- **WHEN** the recruiter clicks the field and types the correct value
- **THEN** the field updates in the database and `parse_status` changes to `manually_reviewed`

---

### Requirement: JD Input via Text Paste or File Upload
Recruiter submits a job description either by pasting raw text or uploading a PDF/DOCX file.

**Priority**: MUST

#### Scenario: JD submitted via text paste
- **GIVEN** a recruiter is on the "New Job" page
- **WHEN** they paste JD text into the text area and click "Analyze"
- **THEN** the raw text is saved and passed to the JD analysis pipeline

#### Scenario: JD submitted via file upload
- **GIVEN** a recruiter uploads a DOCX file containing a job description
- **WHEN** the system extracts text from the file
- **THEN** the extracted text is saved and passed to the JD analysis pipeline

---

### Requirement: LLM-Powered JD Structured Profile Extraction
System sends JD text to the LLM proxy and returns a structured JD profile: required skills, nice-to-have skills, responsibilities, seniority level, experience range.

**Priority**: MUST

#### Scenario: Successful JD analysis
- **GIVEN** a JD text for a "Senior Backend Engineer" role
- **WHEN** the LLM proxy processes it with a structured output schema
- **THEN** a JD profile is created with: title, seniority (`senior`), experience_years_min (3), experience_years_max (7), required_skills[], nice_to_have_skills[], responsibilities[]

#### Scenario: Vietnamese JD analyzed correctly
- **GIVEN** a JD written in Vietnamese
- **WHEN** the LLM proxy processes it
- **THEN** JD profile fields are correctly extracted, with skill names normalized to English taxonomy where applicable (e.g., "Lập trình Python" → skill: "Python")

#### Scenario: Ambiguous seniority
- **GIVEN** a JD that does not specify seniority level
- **WHEN** the LLM cannot determine seniority from context
- **THEN** seniority is set to `unspecified` and the recruiter can set it manually from a dropdown

---

### Requirement: Match Score Computation
Given a Job, system computes a match score (0–100) for each candidate with a category breakdown and natural-language rationale.

**Priority**: MUST

#### Scenario: Match scoring for a single candidate
- **GIVEN** a recruiter selects a Job with a structured JD profile and a candidate with a structured CandidateProfile
- **WHEN** the recruiter triggers "Match" or the system auto-scores on upload
- **THEN** a Match record is created with: overall_score (0–100), skill_score, experience_score, education_score, and a rationale string

#### Scenario: Ranked candidate list
- **GIVEN** a Job has 30 candidates in its pool
- **WHEN** the recruiter opens the "Candidates" tab for that job
- **THEN** candidates are listed ranked by overall_score descending, with score breakdown visible per row

#### Scenario: Match completes within SLA
- **GIVEN** a recruiter submits a JD and has 50 candidates in the pool
- **WHEN** match scoring runs
- **THEN** all 50 match scores and rationales are returned within 10 seconds

---

### Requirement: Match Rationale Display
Every match score must display a human-readable explanation. No black-box scores permitted.

**Priority**: MUST

#### Scenario: Recruiter reads rationale
- **GIVEN** a candidate has overall_score 72
- **WHEN** the recruiter clicks "View Rationale"
- **THEN** a panel shows the natural-language rationale plus the three category scores with labels (Skills: 85, Experience: 70, Education: 60)

---

### Requirement: Pipeline Stage Management
Recruiter moves candidates through hiring stages: shortlisted → interviewed → offered → hired / rejected.

**Priority**: MUST

#### Scenario: Move candidate to shortlist
- **GIVEN** a ranked candidate list for a Job
- **WHEN** the recruiter clicks "Shortlist" on a candidate row
- **THEN** the candidate's Pipeline stage updates to `shortlisted` and they appear in the "Shortlist" filtered view

#### Scenario: Reject candidate
- **GIVEN** a candidate is in the `screened` stage
- **WHEN** the recruiter clicks "Reject"
- **THEN** the Pipeline stage updates to `rejected`; the candidate is hidden from the default view but accessible via "Show rejected" filter

---

### Requirement: Candidate Search & Filter
Recruiter searches the full candidate database by keyword, skill, location, experience, or semantic query.

**Priority**: MUST

#### Scenario: Search by skill
- **GIVEN** a recruiter types "React" in the search bar
- **WHEN** the system queries the candidate database
- **THEN** all candidates with "React" in their skills[] are returned, ranked by relevance, with Vietnamese diacritics handled correctly

#### Scenario: Filter by minimum experience
- **GIVEN** a recruiter sets filter "Experience ≥ 3 years"
- **WHEN** the filter is applied
- **THEN** only candidates with total work experience ≥ 3 years are shown

#### Scenario: Semantic search
- **GIVEN** a recruiter types "backend developer with database experience"
- **WHEN** the system performs vector similarity search against candidate profile embeddings
- **THEN** candidates with semantically relevant profiles are returned even if keywords don't match exactly

---

### Requirement: Duplicate Detection
System checks for existing candidates before creating a new record. Recruiter is prompted to merge or create new.

**Priority**: MUST

#### Scenario: Duplicate detected on upload
- **GIVEN** a recruiter uploads a CV for "Nguyễn Văn A" with email `a@example.com`
- **WHEN** parsing completes and the system checks for duplicates by email + name similarity
- **THEN** a prompt appears: "A candidate with this email already exists. Merge with existing record or create new?"

#### Scenario: No duplicate found
- **GIVEN** no existing candidate matches the email or name
- **WHEN** the system completes duplicate check
- **THEN** a new Candidate record is created without prompt

---

### Requirement: Talent Pool Management
Recruiter creates named talent pools and adds candidates for future reuse across job openings.

**Priority**: MUST

#### Scenario: Create talent pool
- **GIVEN** a recruiter is viewing the candidate database
- **WHEN** they click "New Pool", enter a name, and save
- **THEN** an empty TalentPool is created and appears in the sidebar

#### Scenario: Add candidate to pool
- **GIVEN** an existing talent pool
- **WHEN** the recruiter selects a candidate and clicks "Add to Pool" → selects the pool
- **THEN** the candidate is added to that pool and visible when filtering by pool

---

### Requirement: Structured Candidate Export
Recruiter exports one or more candidate profiles with match scores as CSV, JSON, or DOCX.

**Priority**: MUST

#### Scenario: Export selected candidates as CSV
- **GIVEN** a recruiter selects 10 candidates from a ranked list
- **WHEN** they click "Export → CSV"
- **THEN** a CSV file downloads with columns: name, email, phone, skills, experience_years, education, overall_score, skill_score, experience_score, education_score, rationale

#### Scenario: Export single candidate as DOCX
- **GIVEN** a recruiter views a single candidate profile
- **WHEN** they click "Export → DOCX"
- **THEN** a formatted Word document downloads with the candidate's full structured profile

#### Scenario: Export all candidates for a job as JSON
- **GIVEN** a job has 30 matched candidates
- **WHEN** the recruiter clicks "Export All → JSON"
- **THEN** a JSON file downloads containing an array of all candidate objects with match data
