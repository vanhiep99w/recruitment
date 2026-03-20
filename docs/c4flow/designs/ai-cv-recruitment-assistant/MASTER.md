# MASTER: AI CV & Recruitment Assistant Design System

## Design Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--background` | `#F7F8FB` | Page background (indigo-tinted warm neutral) |
| `--card` | `#FFFFFF` | Card / surface backgrounds |
| `--foreground` | `#141520` | Body text (deep navy, not pure black) |
| `--muted` | `#E8EAF4` | Muted backgrounds, table headers |
| `--muted-foreground` | `#6B6F8A` | Secondary text, placeholders, captions |
| `--border` | `#DDE0EE` | Borders and dividers (indigo-tinted) |
| `--primary` | `#3A5CCC` | CTAs, links, active states, primary actions |
| `--primary-foreground` | `#FFFFFF` | Text on primary backgrounds |
| `--secondary` | `#EEF0F8` | Secondary button backgrounds |
| `--secondary-foreground` | `#2A2D42` | Text on secondary backgrounds |
| `--input` | `#ECEEF7` | Input field backgrounds |
| `--destructive` | `#D63333` | Errors, delete actions |
| `--destructive-foreground` | `#FFFFFF` | Text on destructive backgrounds |
| `--success` | `#1D9C5A` | Confirmations, high match score |
| `--success-foreground` | `#FFFFFF` | Text on success backgrounds |
| `--warning` | `#C97D10` | Warnings, medium match score |
| `--warning-foreground` | `#FFFFFF` | Text on warning backgrounds |
| `--score-high` | `#1D9C5A` | Match score ≥ 80 |
| `--score-mid` | `#C97D10` | Match score 50-79 |
| `--score-low` | `#D63333` | Match score < 50 |
| `--sidebar` | `#1A1D30` | Sidebar background (deep navy) |
| `--sidebar-foreground` | `#D8DCF0` | Sidebar text |
| `--sidebar-active` | `#FFFFFF` | Active nav item text |
| `--sidebar-active-bg` | `#2D3254` | Active nav item background |
| `--sidebar-muted` | `#6B6F8A` | Sidebar secondary text |
| `--ring` | `#3A5CCC` | Focus ring color |

## Typography Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--font-primary` | `'Plus Jakarta Sans', sans-serif` | Headings, labels, navigation, buttons |
| `--font-secondary` | `'Onest', sans-serif` | Body text, descriptions, inputs |
| `--text-h1` | `36` | Page titles |
| `--text-h2` | `28` | Section headings |
| `--text-h3` | `20` | Card headings, top bar title |
| `--text-body` | `15` | Body text |
| `--text-small` | `13` | Labels, filter chips, captions |
| `--text-caption` | `11` | Timestamps, metadata |

## Spacing Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--space-xs` | `4` | Tight grouping |
| `--space-sm` | `8` | Standard gap |
| `--space-md` | `16` | Medium gap |
| `--space-lg` | `32` | Large gap / section padding |
| `--space-xl` | `64` | XL gap |

## Border Radius Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--radius-none` | `0` | Tables, sharp dividers |
| `--radius-sm` | `4` | Small elements |
| `--radius-md` | `8` | Buttons, inputs, chips |
| `--radius-lg` | `12` | Cards, table wrapper |
| `--radius-pill` | `999` | Badges, skill tags |

## Motion Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--duration-fast` | `150ms` | Button press, toggle |
| `--duration-normal` | `250ms` | Menu open, tooltip |
| `--duration-slow` | `400ms` | Drawer, accordion |
| `--ease-out` | `cubic-bezier(0.16,1,0.3,1)` | Elements entering |
| `--ease-in` | `cubic-bezier(0.7,0,1,1)` | Elements leaving |

## Reusable Components

| Component | Variants / Notes | Frame ID |
|-----------|-----------------|----------|
| Btn/Primary | Blue filled, white text | `tph4J` |
| Btn/Secondary | Muted fill, dark text | `RVxJi` |
| Btn/Outline | White fill, border, dark text | `KDUlM` |
| Btn/Destructive | Red fill, white text | `KUddM` |
| Btn/Ghost | Transparent, icon + text | `jZ3gK` |
| Input/Default | Search input with icon, border | `4hpxO` |
| Badge/Success | Green pill — Phù hợp cao | `M7MsQ` |
| Badge/Warning | Amber pill — Trung bình | `DV7Tk` |
| Badge/Error | Red pill — Không phù hợp | `koPcu` |
| Badge/Neutral | Gray pill — Đang xử lý | `EceA3` |
| Badge/Primary | Indigo pill — Shortlisted | `OxxHx` |
| ScoreRing | Circle with score number + label | `nBCAl` |
| Nav/Item | Sidebar nav item (default state) | `vfBgP` |
| Nav/Item Active | Sidebar nav item (active state) | `AbQCZ` |
| Sidebar | Full sidebar with logo + nav slot + footer | `W6QqX` |
| TableRow/Candidate | Candidate table row template | `wtiSB` |

## Screens

| Screen | Frame ID | Status |
|--------|----------|--------|
| Design System | `S1Jx6` | ✅ Complete |
| Screen — Ứng viên (Hero, Candidate List) | `GuUvs` | ✅ Complete |
| Screen — Đăng nhập (Login) | `WIWTu` | ✅ Complete |
| Screen — Tải lên CV (Upload) | `gYSax` | ✅ Complete |
| Screen — Chi tiết ứng viên (Candidate Detail) | `MmINW` | ✅ Complete |
| Screen — Ứng viên theo vị trí (Job Candidates Match) | `mLUTj` | ✅ Complete |

## Design System Frame

- Design System Frame ID: `S1Jx6`
- Pencil file: `docs/c4flow/designs/ai-cv-recruitment-assistant/ai-cv-recruitment-assistant.pen`
- Hero Screen exports: `GuUvs.png`, `S1Jx6.png`

## Visual Identity

- **Fonts:** Plus Jakarta Sans (headings) + Onest (body) — humanist, modern, not generic
- **Primary color:** Deep indigo `#3A5CCC` — professional, intelligent, trustworthy
- **Sidebar:** Deep navy `#1A1D30` — clear navigation authority, calm dark accent
- **Score colors:** Semantic green / amber / red — immediately readable without legend
- **Layout:** 1440×900 desktop, sidebar 240px fixed + fill_container content
- **Language:** Vietnamese-first labels throughout
