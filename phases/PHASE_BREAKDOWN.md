# CodeSentinel AI — Phase-by-Phase Build Plan

> This document expands on the phase list in Master Prompt § 10.  
> Each phase maps to roughly one week of focused development.

---

## Phase 1 — Project Scaffold & Infrastructure (Week 1)

**Goal:** Everyone can run the full stack locally with one command.

### Tasks
- [ ] Monorepo init (`pnpm` workspaces): `frontend/` + `backend/`
- [ ] `docker-compose.yml`: PostgreSQL 16, Redis 7, FastAPI, Celery worker, Next.js dev
- [ ] Alembic: initial migration (all tables from § 9 — users, reviews, findings, api_keys, webhooks)
- [ ] Custom JWT auth setup: `python-jose` for token signing, `bcrypt` for password hashing, httpOnly cookie middleware
- [ ] `.env.example` with all required keys documented
- [ ] GitHub Actions: `ci.yml` (lint → type-check → test → build on PR)
- [ ] `GET /health` and `GET /ready` endpoints
- [ ] README with local setup instructions

### Deliverable
`docker compose up` → all services green, health check passes.

---

## Phase 2 — Core Review Pipeline + Interactive Workbench UI (Weeks 2–3)

**Goal:** A user can paste code, click Run, and see findings stream in live with a fully linked editor.

### Backend tasks
- [ ] Celery review task: tree-sitter → static rules → Gemini → merge → fix diffs
- [ ] Redis pub-sub: publish 5-step progress events + findings as they arrive
- [ ] SSE endpoint `GET /reviews/{id}/stream`
- [ ] `POST /reviews` → enqueue task → return `{review_id, stream_url}`
- [ ] `GET /reviews/{id}` → full results

### Frontend tasks
- [ ] Review Workbench layout: Monaco left, findings panel right (or stacked)
- [ ] **Live progress tracker:** animated 5-step stepper (Parsing → Static checks → AI analysis → Merging results → Generating fixes); findings stream into list via SSE as they arrive
- [ ] **Linked editor ↔ findings:** click finding → scroll + highlight lines in Monaco; gutter squiggle / decoration click → open finding card; severity-coloured inline markers + hover tooltips
- [ ] **Command palette (Ctrl/Cmd+K):** fuzzy search over pages, actions (Run Review, switch language, toggle density, copy API key prefix); Ctrl+Enter to trigger review; keyboard-shortcut hints in items
- [ ] Drag-and-drop upload zone: animated file chips, language auto-detect badge, sample-code dropdown ("Buggy Python", "SQL injection in PHP", "Memory leak in C++")
- [ ] Review History page: paginated, sortable table

### Deliverable
Paste code → click Run → watch stepper animate → findings appear live → click finding → editor scrolls to line.

---

## Phase 3 — Auth & API Key Management (Week 4)

**Goal:** Secure, role-gated access with self-service API keys.

### Tasks
- [ ] Custom JWT auth: `POST /auth/register` (email + bcrypt password), `POST /auth/login` → access + refresh tokens in httpOnly cookies
- [ ] Email verification: generate signed token, send via SMTP / SendGrid, `GET /auth/verify-email?token=`
- [ ] Google OAuth: `authlib` OAuth client → `/auth/google` → callback → upsert user → issue JWT
- [ ] FastAPI JWT middleware (decode + validate token on every protected route)
- [ ] API key hashing (SHA-256) + prefix storage
- [ ] API key middleware: validate, rate-limit (Redis sliding window), scope check
- [ ] API Keys page: list (prefix shown), create (full key shown once + copy button), revoke
- [ ] Plan gating: free limit enforcement on `POST /reviews`
- [ ] Rate-limit headers on all responses

### Deliverable
Sign up → create API key → `curl -H "X-API-Key: ..." POST /reviews` → rate-limited after 10 on free plan.

---

## Phase 4 — Webhooks & Background Jobs (Week 5)

**Goal:** External systems get notified of review events reliably.

### Tasks
- [ ] Webhook CRUD API (create, list, update, delete)
- [ ] Celery task: `deliver_webhook` with HMAC-SHA256 signing
- [ ] Celery Beat: retry sweep (exponential back-off, 3 attempts)
- [ ] Delivery log table + 30-day cleanup job
- [ ] Webhooks management page: register, list, toggle active, delete
- [ ] Signature verification snippet shown in UI (copy button)

### Deliverable
Create webhook → trigger review → `review.completed` POSTed to URL with valid signature.

---

## Phase 5 — AI-Powered Interactions (Weeks 6–7)

**Goal:** The UI becomes a conversational, fix-applying code assistant.

### Tasks
- [ ] **One-click fixes:**
  - "Apply fix" button on each finding card
  - Animated diff preview in Monaco (old → new side-by-side)
  - Accept (patches editor) / Reject (dismiss diff) buttons
  - Full Undo/Redo stack (Cmd/Ctrl+Z)
  - "Apply all safe fixes" batch action (medium/low only by default)
- [ ] **Ask-the-code chat:**
  - Slide-in side panel (Cmd/Ctrl+Shift+C or via finding card)
  - `POST /reviews/{id}/chat` with streaming response
  - Suggested-question chips: "Why is this a bug?", "Show a safer version", "Explain line {n}"
  - Full conversation history within session
  - Markdown rendering in AI responses; code blocks with copy button
- [ ] Animated dashboard (shown after review completes):
  - Score ring: count-up animation from 0 → score
  - Category radar chart (Recharts `RadarChart`)
  - Severity donut chart; hover segment → filter findings list
- [ ] Filter / sort panel:
  - Severity chips (toggle, multi-select, live count badge)
  - Category toggles
  - Text search box (debounced)
  - Sort dropdown (severity, category, line number, confidence)
  - Framer Motion `AnimatePresence` for list reorder

### Deliverable
Click "Apply fix" → see animated diff → accept → editor updates. Open chat → ask "why?" → see streaming AI answer.

---

## Phase 6 — Developer Tools Pages (Week 8)

**Goal:** Developers can explore and test the API without leaving the app.

### Tasks
- [ ] **API Playground:**
  - Endpoint picker (dropdown of all v1 routes)
  - Monaco JSON body editor (auto-formatted, schema-validated)
  - API key input field (masked, with eye toggle)
  - Send button → live status code badge, response headers table, timing ms, pretty-printed JSON response in Monaco
  - Snippet tabs: `curl`, Python (`requests`), JavaScript (`fetch`); one-click copy per snippet
- [ ] **Live webhook timeline:**
  - SSE stream of `webhook_deliveries` for the user's webhooks
  - Timeline rows: timestamp, event name, status badge (200 green / 4xx amber / 5xx red), signature-verified tick (✓ / ✗), expandable JSON payload accordion
  - "Send test event" button → triggers `POST /webhooks/{id}/test` → result appears in timeline instantly
- [ ] API Docs page: OpenAPI spec rendered (Scalar or Redoc) + hand-written quickstart guide
- [ ] Micro-interactions pass:
  - Toast notifications with Undo action (3 s auto-dismiss)
  - Skeleton loaders on all data-fetching states
  - Hover lift + accent glow on cards
  - Animated tab indicator
  - Confetti / subtle violet glow when review score = 100 or 0 critical findings
  - Clipboard copy → icon morphs to checkmark for 1.5 s

### Deliverable
Open Playground → pick `/reviews` → paste key → Send → see 202 response with timing → copy curl snippet.

---

## Phase 7 — Personalisation, Accessibility & Polish (Week 9)

**Goal:** The app feels crafted and welcoming to all users.

### Tasks
- [ ] Settings page:
  - Density toggle (compact / comfortable) — changes padding/font-size via CSS class
  - Editor font size slider (12–20 px)
  - Accent colour picker (violet default + 5 alternatives)
  - Split-view toggle (side-by-side / stacked)
  - All persisted to `localStorage` and applied on mount
- [ ] First-run guided tour (using Intro.js or custom Framer Motion overlay):
  - Step 1: Highlight drag-and-drop / editor area
  - Step 2: Highlight Run button
  - Step 3: Highlight findings panel
  - Step 4: Highlight chat button
  - Skip option, persisted to `localStorage`
- [ ] Offline banner: `navigator.onLine` listener → amber banner "You're offline. Reviews will resume when connection is restored."
- [ ] Rate-limit banner: shown when API returns 429 → "Rate limit reached. Resets in mm:ss." with live countdown
- [ ] WCAG AA audit:
  - All colour pairs ≥ 4.5:1 contrast ratio (use `color-contrast` tool)
  - Full keyboard navigation (Tab through all interactive elements)
  - Visible focus rings on all focusable elements (`:focus-visible`)
  - ARIA labels on icon buttons, charts, and Monaco editor wrapper
  - `aria-live="polite"` region for review progress updates (screen reader)
- [ ] Lighthouse CI checks: Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95
- [ ] `@media (prefers-reduced-motion: reduce)` applied globally

### Deliverable
Lighthouse Accessibility score ≥ 95. All 14 interactive behaviours from § 8 checked off.

---

## Phase 8 — Production Hardening & Launch (Week 10)

**Goal:** Ship to real users with confidence.

### Tasks
- [ ] Kubernetes manifests (or Railway / Render service definitions)
- [ ] Vercel deployment config + preview URLs per PR
- [ ] Sentry: DSN wired in frontend (`@sentry/nextjs`) and backend (`sentry-sdk`)
- [ ] Prometheus metrics endpoint `/metrics` + Grafana dashboard (review rate, latency p95, error rate)
- [ ] Load test with Locust: 100 concurrent review submissions, p95 < 60 s
- [ ] Security audit:
  - OWASP Top-10 checklist
  - `pip-audit` + `npm audit` dependency scan
  - GitHub Secret Scanning enabled
  - CSP headers, CORS whitelist, rate-limit headers
- [ ] Documentation:
  - `README.md`: architecture diagram, local setup, env vars
  - API reference (linked from `/docs`)
  - Self-hosting guide (Docker Compose prod)
- [ ] Beta launch checklist sign-off

### Deliverable
Production URL live. Zero P0 security findings. Sentry capturing errors.
