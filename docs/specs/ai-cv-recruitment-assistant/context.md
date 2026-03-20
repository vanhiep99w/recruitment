# Design Context

> Auto-generated from /c4flow:design — edit freely
> Spec: docs/specs/ai-cv-recruitment-assistant/spec.md
> Generated: 2026-03-20

## Product
- **Type:** SaaS web app — AI-powered CV & recruitment pipeline for agency recruiters
- **Target users:** Agency recruiters (headhunters, staffing consultants) in Vietnam — professional, high-volume CV workload, need speed and accuracy, not technically-savvy developers
- **Core value:** Replace manual CV review with an AI pipeline: upload → parse → JD match → manage pipeline → export

## Brand
- **Personality:** Efficient, intelligent, trustworthy
- **Emotional goal:** Users should feel in control and confident — the tool does the heavy lifting, they make the final call
- **Aesthetic direction:** Clean enterprise SaaS — high information density, calm palette with deep indigo sidebar, warm neutral surfaces, accent on AI/data intelligence moments (match scores, confidence indicators)
- **Anti-references:** No glassmorphism, no gradient-heavy AI aesthetics, no pure-gray neutrals, no hero metric layouts, no neon accents on dark

## Guiding Principles
- Data clarity first — scores, badges, progress bars must be immediately legible
- Vietnamese-first — all UI labels in Vietnamese (with English fallback in mockups where necessary)
- Information density without clutter — recruiter manages dozens of mandates; the UI must pack data efficiently without visual chaos
- Trust through transparency — match rationale must be visible and human-readable
- Calm intelligence — no alarm-bell reds, no anxious animations; calm, deliberate motion

## Technical Constraints
- **Platform:** Desktop-first web app (1440 × 900)
- **Framework:** Next.js 14 + Tailwind CSS + shadcn/ui
- **Styling approach:** Design native components mirroring shadcn patterns with bespoke visual identity
- **Accessibility:** WCAG AA
