# Screen Map: AI CV & Recruitment Assistant

## Auth Flow (2 screens)

### Đăng nhập — `screen-login`
- **Components:** Input (email), Input (password), Btn/Primary (Đăng nhập), link (quên mật khẩu)
- **Spec refs:** spec.md (implicit — recruiter must be logged in)
- **Notes:** Clean centered card, no sidebar; brand mark top-left

### Đăng ký — `screen-register`
- **Components:** Input (name, email, password, org), Btn/Primary (Tạo tài khoản), Btn/Outline (Hủy)
- **Notes:** Same centered layout as login

---

## Dashboard / Tổng quan (1 screen)

### Tổng quan — `screen-dashboard` *(HERO SCREEN)*
- **Components:** Sidebar, TopBar, FilterBar (search + dropdowns), Table with 4 candidate rows, pagination footer
- **Spec refs:** spec.md#candidate-matching, spec.md#candidate-database
- **Notes:** Primary data screen — sidebar nav active on "Ứng viên". Score column uses semantic green/amber/red. Status badge column. Frame ID: `GuUvs`

---

## CV Upload Flow (2 screens)

### Tải lên CV — `screen-upload`
- **Components:** Sidebar, TopBar, Upload Zone (drag-drop), toggle (Single / ZIP Batch), Btn/Primary (Tải lên), file type chips
- **Spec refs:** spec.md#single-cv-upload, spec.md#zip-bulk-upload
- **Notes:** Upload zone is center-dominant element. Accepts PDF, DOCX, DOC, JPG, PNG, ZIP.

### Đang xử lý — `screen-upload-progress`
- **Components:** Sidebar, TopBar, Progress bar (0/50 processed), file list with status icons, error summary badge, Btn/Ghost (hủy)
- **Spec refs:** spec.md#zip-bulk-upload
- **Notes:** Real-time counter "N/50 đã xử lý". Error items need visual distinction.

---

## Ứng viên (2 screens)

### Danh sách ứng viên — `screen-candidates` *(Already built as hero)*
- Frame ID: `GuUvs`
- See hero screen above

### Chi tiết ứng viên — `screen-candidate-detail`
- **Components:** Sidebar, TopBar with breadcrumb (Ứng viên > Nguyễn Văn Hùng), Profile header (name, email, phone, location), Tabs (Hồ sơ | Lịch sử phỏng vấn | Ghi chú), Editable field sections (Work Experience, Education, Skills), Btn/Primary (Lưu chỉnh sửa), Badge/Warning (low_confidence), Btn/Outline (Xuất DOCX)
- **Spec refs:** spec.md#manual-profile-correction, spec.md#structured-candidate-export
- **Notes:** Inline edit mode — click field to edit. Parse status warning shown if low_confidence.

---

## Vị trí tuyển dụng / Jobs (3 screens)

### Danh sách vị trí — `screen-jobs`
- **Components:** Sidebar, TopBar, Btn/Primary (Tạo vị trí mới), Table (title, seniority, candidates, created date, status), Btn/Outline (Xem chi tiết)
- **Spec refs:** spec.md (jobs flow)
- **Notes:** Status badge: Đang tuyển / Đã đóng

### Tạo vị trí / Phân tích JD — `screen-job-create`
- **Components:** Sidebar, TopBar (breadcrumb), Tabs (Dán văn bản | Tải file), Textarea (JD text), Btn/Primary (Phân tích JD), JD Profile result panel (required skills, nice-to-have, seniority, experience range)
- **Spec refs:** spec.md#jd-input-via-text-paste-or-file-upload, spec.md#llm-powered-jd-structured-profile-extraction
- **Notes:** JD analysis result shown inline after submission. Seniority dropdown when `unspecified`.

### Ứng viên cho vị trí — `screen-job-candidates`
- **Components:** Sidebar, TopBar (breadcrumb), Score summary panel, Ranked Table (rank, name, skills, overall score, skill score, exp score, edu score, stage), Rationale panel (slide-in), Btn/Ghost (Shortlist), Btn/Outline (Xem lý do), Pipeline stage dropdown
- **Spec refs:** spec.md#match-score-computation, spec.md#match-rationale-display, spec.md#pipeline-stage-management
- **Notes:** Most data-dense screen. Rationale panel opens on row click. Color-coded score columns.

---

## Talent Pool (1 screen)

### Talent Pool — `screen-talent-pools`
- **Components:** Sidebar, TopBar, Pool list (sidebar-style), Pool member list (candidate table), Btn/Primary (Tạo Pool mới), Btn/Ghost (Thêm ứng viên vào pool)
- **Spec refs:** spec.md#talent-pool-management
- **Notes:** Split layout: pool list left (240px), members right.

---

## Cài đặt (1 screen)

### Cài đặt — `screen-settings`
- **Components:** Sidebar, TopBar, Settings card (LLM API Key input, Base URL input), Btn/Primary (Lưu), Org info section
- **Spec refs:** design.md#llm-proxy
- **Notes:** Simple form screen.

---

## Shared Components

| Component | Reusable ID | Variants |
|-----------|-------------|----------|
| Btn/Primary | `tph4J` | — |
| Btn/Secondary | `RVxJi` | — |
| Btn/Outline | `KDUlM` | — |
| Btn/Destructive | `KUddM` | — |
| Btn/Ghost | `jZ3gK` | — |
| Input/Default | `4hpxO` | — |
| Badge/Success | `M7MsQ` | — |
| Badge/Warning | `DV7Tk` | — |
| Badge/Error | `koPcu` | — |
| Badge/Neutral | `EceA3` | — |
| Badge/Primary | `OxxHx` | — |
| ScoreRing | `nBCAl` | — |
| Nav/Item | `vfBgP` | — |
| Nav/Item Active | `AbQCZ` | — |
| Sidebar | `W6QqX` | — |
| TableRow/Candidate | `wtiSB` | — |
