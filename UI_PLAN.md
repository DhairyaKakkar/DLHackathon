# EALE — UI/UX Design Plan

## Vision

Dark glassmorphism aesthetic unified across the frontend dashboard and Chrome extension. Professional, high-contrast, and sleek — matching the kind of tool people actually want to use. Every surface feels intentional: deep dark backgrounds, subtle glass cards, indigo/violet primary gradient, and semantic color coding for learning outcomes.

---

## Design System

### Color Palette

| Token | Value | Usage |
|---|---|---|
| Background | `#09090f` | Page body, overlay base |
| Surface | `rgba(255,255,255,0.04)` | Cards, panels, inputs |
| Border | `rgba(255,255,255,0.08)` | Card outlines, dividers |
| Border hover | `rgba(255,255,255,0.14)` | Interactive element hover |
| Text primary | `#f1f5f9` | Headings, key values |
| Text secondary | `#94a3b8` | Labels, descriptions |
| Text muted | `#475569` | Hints, placeholders |
| Text dim | `#334155` | Disabled, very subtle |
| Primary | `#6366f1` | Buttons, links, active states |
| Primary gradient | `from-indigo-600 to-violet-600` | CTAs, logo, badges |
| Durable (DUS ≥80) | `#10b981` | Emerald — strong retention |
| Partial (DUS 60–79) | `#f59e0b` | Amber — developing |
| Fragile (DUS <60) | `#f43f5e` | Rose-red — needs work |
| Success | `#10b981` | Correct answers, all-clear states |
| Warning | `#f59e0b` | Overdue tasks, calibration alerts |
| Danger | `#f43f5e` | Errors, incorrect answers |

### Typography

| Family | Use |
|---|---|
| `Space Grotesk` | Page headings (`font-display`) |
| `Inter` | Body text, labels, UI copy |
| `JetBrains Mono` | Code blocks, DUS formula |

### Glassmorphism Recipe

```css
/* Card */
background: rgba(255,255,255,0.04);
border: 1px solid rgba(255,255,255,0.08);
border-radius: 12–16px;
box-shadow: 0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.06);

/* Navbar */
background: rgba(9,9,15,0.80);
backdrop-filter: blur(24px);
border-bottom: 1px solid rgba(255,255,255,0.06);

/* Hover state */
border-color: rgba(255,255,255,0.14);
```

### Shadow Tokens (tailwind.config.ts)

| Token | Value | Usage |
|---|---|---|
| `shadow-card` | dark drop + 1px ring | All cards |
| `shadow-card-hover` | indigo glow + brighter ring | Card hover |
| `shadow-glow` | `0 0 24px rgba(99,102,241,0.3)` | Primary CTAs |
| `shadow-glow-sm` | `0 0 12px rgba(99,102,241,0.2)` | Small buttons |

### DUS Semantic Colors

| Level | Score | Color | Tailwind |
|---|---|---|---|
| Durable | ≥ 80 | `#10b981` | `text-emerald-400`, `bg-emerald-500/10`, `border-emerald-500/30` |
| Partial | 60–79 | `#f59e0b` | `text-amber-400`, `bg-amber-500/10`, `border-amber-500/30` |
| Fragile | < 60 | `#f43f5e` | `text-red-400`, `bg-red-500/10`, `border-red-500/30` |

---

## File-by-File Status

### Foundation

| File | Status | Changes |
|---|---|---|
| `frontend/src/app/globals.css` | ✅ Done | Dark CSS variables, dark scrollbar, dark range input, Space Grotesk import |
| `frontend/tailwind.config.ts` | ✅ Done | Dark shadow tokens, `font-display`, `pulse-ring` keyframe, updated DUS colors |
| `frontend/src/app/layout.tsx` | ✅ Done | Dark Sonner toaster (`#1e1e2e` bg, white border) |
| `frontend/src/lib/utils.ts` | ✅ Done | All color helpers updated for dark: `getDusColor`, `getDusBg`, `getDusBadgeClass`, `getDusTextClass`, `getMetricColor`, `getMetricBarColor` |

### Shared Components

| File | Status | Changes |
|---|---|---|
| `frontend/src/components/Navbar.tsx` | ✅ Done | `bg-[#09090f]/80 backdrop-blur-xl`, gradient logo box, dark text |
| `frontend/src/components/ErrorState.tsx` | ✅ Done | `bg-red-500/10 border-red-500/20`, dark text colors |
| `frontend/src/components/Skeletons.tsx` | ✅ Done | `bg-white/[0.06]` pulse, dark card containers |
| `frontend/src/components/DUSGauge.tsx` | ✅ Done | Dark arc track `rgba(255,255,255,0.08)`, glow filter on progress arc |

### Feature Components

| File | Status | Changes |
|---|---|---|
| `frontend/src/components/MetricCard.tsx` | ✅ Done | Dark surface card, `bg-white/[0.08]` progress track, dark expand button |
| `frontend/src/components/DUSHistogram.tsx` | ✅ Done | Dark Recharts tooltip (`#1e1e2e` bg), dark axis tick colors |
| `frontend/src/components/TaskCard.tsx` | ✅ Done | Dark card, dark type badges (`bg-blue-500/10`, `bg-violet-500/10`), dark expanded area |
| `frontend/src/components/TopicTable.tsx` | ✅ Done | Dark table, `bg-white/[0.03]` header, dark hover, dark risk badge |
| `frontend/src/components/AttemptPanel.tsx` | ✅ Done | Dark MCQ options, dark text inputs, gradient submit button, dark result panels |

### Pages

| File | Status | Changes |
|---|---|---|
| `frontend/src/app/page.tsx` | ✅ Done | Ambient background blobs, gradient hero heading, dark demo cards with color glow on hover, dark pillar cards with icon glow |
| `frontend/src/app/student/[id]/page.tsx` | ✅ Done | Dark background, dark DUS hero card, gradient Tasks button, dark tooltip, dark per-topic sections |
| `frontend/src/app/student/[id]/tasks/page.tsx` | ✅ Done | Dark mini dashboard strip, dark toggle, dark empty state |
| `frontend/src/app/faculty/page.tsx` | ✅ Done | Dark StatCard, updated RiskCard (no light `bg-red-50` etc.), dark histogram container, dark topic table, dark quick-links section |

### Chrome Extension

| File | Status | Changes |
|---|---|---|
| `chrome-extension/popup.html` | ✅ Done | Full dark redesign — gradient logo, dark surface cards, gradient quiz button, dark link buttons, fixed port 3000 → 3001 |
| `chrome-extension/options.html` | ⏳ Pending | Light form UI needs full dark redesign |
| `chrome-extension/content.js` | ✅ Done (prior session) | Shadow DOM overlay already fully redesigned with dark glassmorphism |
| `chrome-extension/popup.js` | N/A | Logic only, no styling |
| `chrome-extension/options.js` | N/A | Logic only, no styling |

---

## Remaining Work

### `chrome-extension/options.html`

The only file not yet redesigned. Needs:

- Body: `background: #09090f; color: #f1f5f9`
- Header logo: gradient `linear-gradient(135deg, #6366f1, #8b5cf6)`
- Cards: `background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08)`
- Inputs: dark surface + `border: 1.5px solid rgba(255,255,255,0.1); color: #f1f5f9`
- Toggle sliders: checked state `background: #6366f1`
- Save button: gradient + glow shadow
- Demo keys box: `rgba(99,102,241,0.08)` tinted
- LLM note: `rgba(16,185,129,0.08)` tinted green
- Allowlist items: dark surface rows

---

## Design Principles Applied

1. **No pure white surfaces** — everything uses translucent dark layers
2. **Semantic color throughout** — green/amber/red always means durable/partial/fragile
3. **Layered depth** — background → surface (`/0.04`) → header (`/0.03`) → hover (`/0.06`)
4. **Glow reserved for intent** — only primary actions and the DUS arc get glow effects
5. **Backdrop blur on sticky elements** — navbar and overlays use `backdrop-blur-xl`
6. **Consistent border opacity** — resting `/0.08`, hover `/0.14`, active `/0.20`
7. **No feature changes** — all logic, data fetching, and routing untouched

---

## Running the Redesigned App

```bash
# Start full stack
docker compose up --build

# Frontend only (hot reload)
cd frontend && npm run dev -- --port 3001
```

URLs after boot:
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000/docs
- Student Alice: http://localhost:3001/student/1
- Student Bob: http://localhost:3001/student/2
- Faculty: http://localhost:3001/faculty
