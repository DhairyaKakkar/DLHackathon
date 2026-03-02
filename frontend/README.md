# EALE Frontend

React/Next.js frontend for the Evidence-Aligned Learning Engine.

## Stack

- **Next.js 14** (App Router) + TypeScript
- **Tailwind CSS** — styling
- **TanStack Query** — data fetching + cache invalidation
- **Recharts** — DUS histogram
- **Sonner** — toast notifications
- **Lucide React** — icons

## Prerequisites

- Node.js 18+
- EALE backend running at `http://localhost:8000` (see `../README.md`)

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Environment

Copy `.env.example` → `.env.local` and set the API URL:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The default is already `http://localhost:8000` — no changes needed for local dev.

## Demo URLs

| URL | What you see |
|-----|-------------|
| http://localhost:3000 | Landing page with demo buttons |
| http://localhost:3000/student/1 | Alice Chen — Fragile Mastery |
| http://localhost:3000/student/1/tasks | Alice's due tasks + attempt form |
| http://localhost:3000/student/2 | Bob Martinez — Overconfident |
| http://localhost:3000/faculty | Faculty cohort dashboard |

## Pages

### Landing `/`
- EALE tagline + DUS formula
- Three demo buttons (Alice, Bob, Faculty)
- Three-pillar explanation (Retention, Transfer, Calibration)

### Student Dashboard `/student/:id`
- Semi-circle DUS gauge
- Four metric cards (Mastery, Retention, Transfer, Calibration) with expandable explanations
- Per-topic table with DUS, mini bars, and top risk flag
- Per-topic detail cards
- "Go to Tasks" CTA

### Student Tasks `/student/:id/tasks`
- Compact DUS strip
- Due task list (RETEST / TRANSFER badges)
- Click-to-expand attempt panel with:
  - MCQ radio buttons or short-text input
  - Confidence slider (1–10) with label
  - Optional reasoning textarea
  - Submit → toast (correct/incorrect) → cache invalidation

### Faculty Dashboard `/faculty`
- Stats: students, topics, avg DUS
- Risk cards: low-retention, transfer-failure, overconfidence hotspots
- DUS histogram (colour-coded by score range)
- Full topic breakdown table with avg metrics + flag badges
- Quick links to individual student dashboards

## Build

```bash
npm run build
npm run start
```
