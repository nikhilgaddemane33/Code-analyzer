# GenAI-Powered Code Review SaaS — Master Build Prompt
> **Version:** 2.1 (Interactive UI, no third-party auth)  
> **Last updated:** 2026-11-26  
> This is the canonical prompt handed to the AI coding agent. Sections are numbered so individual sections can be replaced without rewriting the whole document.

---

## 1. PROJECT OVERVIEW

Build a production-ready, GenAI-powered **code review SaaS platform** called **CodeSentinel AI**.

The platform lets developers submit code (via UI, REST API, or webhook) and receive deep security, quality, and performance analysis powered by Google Gemini. Results include severity-ranked findings, AI-generated fix suggestions, and actionable insights.

**Core value proposition:** Faster, deeper code review than manual PR review, with the context-awareness of a senior engineer and the thoroughness of an automated scanner.

---

## 2. TECHNOLOGY STACK

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion, Monaco Editor |
| State management | Zustand + React Query (TanStack Query v5) |
| UI components | Radix UI primitives + custom design system |
| Charts | Recharts |
| Backend | FastAPI (Python 3.12) |
| AI / LLM | Google Gemini 1.5 Pro via `google-generativeai` SDK |
| Database | PostgreSQL 16 (primary) + Redis 7 (cache / rate-limit / SSE pub-sub) |
| Auth | Custom JWT (FastAPI + `python-jose`) — email/password + Google OAuth 2.0 |
| File storage | Local filesystem / S3-compatible store (MinIO for dev, any S3 bucket for prod) |
| Task queue | Celery + Redis broker |
| Containerisation | Docker + Docker Compose (dev) / Kubernetes (prod) |
| CI/CD | GitHub Actions |
| Monitoring | Sentry (errors) + Prometheus + Grafana (metrics) |
| Deployment | Vercel (frontend) + Railway / Render (backend) |

---

## 3. AUTHENTICATION & AUTHORISATION

### 3.1 Auth flows
- Email / password sign-up with email verification (token sent via SMTP / SendGrid)
- Google OAuth 2.0 (one-click, handled by FastAPI + `authlib`)
- JWT access tokens (15 min) + refresh tokens (7 days), stored in httpOnly cookies
- Passwords hashed with `bcrypt` before storage
- PKCE flow for OAuth

### 3.2 API key management
- Users generate named API keys from the dashboard
- Keys are hashed (SHA-256) before storage; shown in full exactly once at creation
- Scopes: `review:read`, `review:write`, `webhook:manage`, `admin`
- Rate limits enforced per key (configurable per plan tier)
- Key rotation and revocation UI

### 3.3 Role-based access control
| Role | Permissions |
|---|---|
| `free` | 10 reviews/month, single language, no API access |
| `pro` | 500 reviews/month, all languages, API + webhooks |
| `team` | Unlimited reviews, team seats, SSO, audit log |
| `admin` | Full platform access |

---

## 4. CODE REVIEW ENGINE

### 4.1 Review pipeline
```
Input (code + language + options)
  │
  ├─ 1. Parsing & tokenisation (tree-sitter)
  ├─ 2. Static analysis rules (custom rule engine)
  ├─ 3. AI analysis (Gemini 1.5 Pro — structured output)
  ├─ 4. Merge & deduplicate findings
  └─ 5. Generate fix suggestions (Gemini)
```

### 4.2 Finding schema
```json
{
  "id": "uuid",
  "severity": "critical|high|medium|low|info",
  "category": "security|quality|performance|style|documentation",
  "rule_id": "string",
  "title": "string",
  "description": "string",
  "line_start": 1,
  "line_end": 5,
  "column_start": 0,
  "column_end": 80,
  "code_snippet": "string",
  "fix_suggestion": "string",
  "fix_diff": "unified diff string",
  "confidence": 0.95,
  "references": ["CWE-89", "OWASP A03"]
}
```

### 4.3 Supported languages (MVP)
Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, PHP, Ruby, SQL

### 4.4 AI prompting strategy
- System prompt: senior security engineer persona with OWASP / SANS top-25 awareness
- Few-shot examples per language and category
- Structured output mode (Gemini JSON schema enforcement)
- Chain-of-thought for complex vulnerability explanations
- Temperature 0.1 for deterministic analysis; 0.7 for fix suggestion creativity

---

## 5. REST API

Base URL: `https://api.codesentinel.ai/v1`

### 5.1 Core endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/reviews` | Submit code for review |
| `GET` | `/reviews/{id}` | Fetch a review result |
| `GET` | `/reviews` | List reviews (paginated) |
| `DELETE` | `/reviews/{id}` | Delete a review |
| `GET` | `/reviews/{id}/stream` | SSE stream of live findings |
| `POST` | `/reviews/{id}/fix` | Apply a fix and return patched code |
| `POST` | `/reviews/{id}/chat` | Ask a question about the review (streaming) |
| `GET` | `/languages` | List supported languages |
| `GET` | `/health` | Health check |

### 5.2 API key endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api-keys` | List your API keys |
| `POST` | `/api-keys` | Create a new key |
| `DELETE` | `/api-keys/{id}` | Revoke a key |

### 5.3 Webhook endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/webhooks` | List webhooks |
| `POST` | `/webhooks` | Register a webhook |
| `PUT` | `/webhooks/{id}` | Update a webhook |
| `DELETE` | `/webhooks/{id}` | Delete a webhook |
| `POST` | `/webhooks/{id}/test` | Send a test payload |

### 5.4 Request / response format
- `Content-Type: application/json`
- API key via `Authorization: Bearer <key>` or `X-API-Key: <key>` header
- All errors follow RFC 7807 Problem Details
- Pagination: cursor-based (`?cursor=<token>&limit=20`)

---

## 6. WEBHOOKS

### 6.1 Events
| Event | Payload trigger |
|---|---|
| `review.started` | Review job accepted |
| `review.completed` | All findings ready |
| `review.failed` | Pipeline error |
| `finding.critical` | A critical severity finding found |

### 6.2 Delivery
- HTTP POST to configured URL
- Signed with HMAC-SHA256 (`X-Sentinel-Signature` header, `sha256=<hex>`)
- Retry with exponential back-off (3 retries, max 5 min)
- Delivery log retained for 30 days

### 6.3 Payload envelope
```json
{
  "event": "review.completed",
  "timestamp": "ISO-8601",
  "review_id": "uuid",
  "data": { ... }
}
```

---

## 7. BACKGROUND JOBS & STREAMING

- Review pipeline runs as a Celery task (async, up to 60 s timeout)
- Progress published to Redis pub/sub channel per review ID
- Frontend subscribes via SSE (`/reviews/{id}/stream`) or falls back to polling (3 s interval)
- Chat responses streamed via chunked HTTP (Gemini streaming SDK)
- Celery Beat for scheduled jobs: usage rollup, webhook retry sweep, old-review cleanup

---

## 8. DARK-THEME UI / UX (INTERACTIVE)

Design system: background `#0B0F17`, surface `#111827`, elevated `#1A2233`, border `#263045`, primary accent violet (`#7C6CFF`), cyan secondary, severity colours (critical red, high orange, medium amber, low blue, info slate). Fonts: Inter (UI) and JetBrains Mono (code). Use CSS variables, glassmorphism cards, and Framer Motion for animation. Respect `prefers-reduced-motion`.

**Pages:** Landing, Review Workbench, History, API Keys, Webhooks, API Docs, Playground, Settings.

### Interactive behaviour (all required)

1. **Live review progress:** when a review runs, show a step-by-step animated tracker (`Parsing → Static checks → AI analysis → Merging results → Generating fixes`). Stream partial findings into the list as they arrive (use Server-Sent Events or polling), instead of a single spinner.

2. **Editor and findings linked both ways:** click a finding to scroll to and highlight its lines in Monaco; click a squiggle or gutter icon in the editor to open that finding. Show severity-coloured inline markers and hover tooltips with the short explanation.

3. **One-click fixes:** an "Apply fix" button on each finding that patches the editor with an animated diff preview, with Accept / Reject and full Undo/Redo. Include "Apply all safe fixes".

4. **Filters and sorting:** severity chips, category toggles, a search box, and a sort dropdown. The list animates smoothly as filters change, and the counts update live.

5. **Animated dashboard:** a score ring that counts up, a category radar chart, and a severity breakdown donut. Hovering a segment filters the findings list.

6. **Ask-the-code chat:** a side panel where the user asks follow-up questions about a finding or the code ("why is this a bug?", "show a safer version", "explain line 24"). Use streaming responses through the same Gemini integration, with suggested-question chips.

7. **Command palette (Ctrl/Cmd+K):** jump to pages, run a review, switch mode or language, copy the API key prefix, toggle density. Show keyboard-shortcut hints, with Ctrl+Enter to run a review.

8. **Drag-and-drop zone** with animated file chips, language auto-detect badges, and a sample-code dropdown ("Buggy Python", "SQL injection in PHP", "Memory leak in C++") for instant demos.

9. **API Playground:** pick an endpoint, edit the JSON body in an editor, paste an API key, press Send, and see the live status code, headers, timing and pretty-printed response. A tab generates matching curl / Python / JavaScript snippets with a copy button.

10. **Live webhook demo:** the Webhook Tester shows incoming deliveries in real time as a streaming timeline with status badges, signature-verified tick, and expandable JSON payloads. A "Send test event" button triggers one.

11. **Micro-interactions:** toasts with Undo, skeleton loaders, hover lift on cards, animated tabs, confetti or a subtle glow when a review finds zero critical issues, and a copy-to-clipboard check animation.

12. **Personalisation:** density (compact/comfortable), editor font size, accent colour picker, and a split-view toggle (side-by-side or stacked). Persist these choices in `localStorage`.

13. **Resilient UX:** friendly empty states, inline validation, offline and rate-limit banners with a visible countdown, and a guided first-run tour that highlights the editor, run button and results panel.

14. **Accessibility:** WCAG AA contrast, full keyboard navigation, visible focus rings, ARIA labels, and screen-reader announcements for live review progress.

---

## 9. DATA MODELS (DATABASE)

### Core tables

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT,                        -- NULL for OAuth users
  google_id TEXT UNIQUE,                     -- populated for Google OAuth
  email_verified BOOLEAN DEFAULT FALSE,
  plan TEXT NOT NULL DEFAULT 'free',
  reviews_this_month INT NOT NULL DEFAULT 0,
  preferences JSONB DEFAULT '{}'
);

-- Code reviews
CREATE TABLE reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  language TEXT NOT NULL,
  code TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed
  score INT,  -- 0–100
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Individual findings
CREATE TABLE findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  severity TEXT NOT NULL,
  category TEXT NOT NULL,
  rule_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  line_start INT,
  line_end INT,
  fix_diff TEXT,
  confidence FLOAT
);

-- API keys (hashed)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  key_prefix TEXT NOT NULL,  -- first 8 chars, shown in UI
  scopes TEXT[] NOT NULL DEFAULT '{}',
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

-- Webhooks
CREATE TABLE webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  url TEXT NOT NULL,
  secret TEXT NOT NULL,
  events TEXT[] NOT NULL,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Webhook delivery log
CREATE TABLE webhook_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  webhook_id UUID NOT NULL REFERENCES webhooks(id),
  event TEXT NOT NULL,
  status_code INT,
  request_body JSONB,
  response_body TEXT,
  delivered_at TIMESTAMPTZ DEFAULT NOW(),
  success BOOLEAN
);
```

---

## 10. BUILD PHASES

### Phase 1 — Project scaffold & infrastructure (Week 1)
- Monorepo with `frontend/` and `backend/` packages
- Docker Compose: PostgreSQL, Redis, FastAPI, Celery worker, Next.js dev server
- Alembic: DB migrations for all tables (users, reviews, findings, api_keys, webhooks)
- Custom JWT auth setup (`python-jose`, `bcrypt`, httpOnly cookie middleware)
- GitHub Actions: lint, type-check, test, build on PR
- Environment variable management (`.env.example`)
- Health-check and readiness probe endpoints

### Phase 2 — Core review pipeline + interactive workbench UI (Weeks 2–3)
- Celery review task: tree-sitter parsing → static rules → Gemini analysis → merge
- SSE streaming endpoint (`/reviews/{id}/stream`)
- Review Workbench page:
  - Monaco Editor with syntax highlighting
  - **Live progress tracker** (step-by-step animated stepper, streams findings via SSE)
  - **Linked editor ↔ findings** (click finding → scroll/highlight; gutter squiggles → open finding)
  - **Command palette (Ctrl/Cmd+K)** with page jump, run review, language switch, Ctrl+Enter shortcut
  - Severity-coloured inline markers + hover tooltips in Monaco
- Drag-and-drop upload zone with language auto-detect + sample-code dropdown
- Review History page (paginated list)

### Phase 3 — Auth & API key management (Week 4)
- Custom JWT auth: register, login, email-verification flow, Google OAuth (`authlib`)
- `bcrypt` password hashing; JWT middleware in FastAPI
- API Keys page: create, list, revoke; full key shown once; prefix shown permanently
- Role-based plan gating (free / pro / team)
- Rate-limiter middleware (Redis sliding window, per API key)

### Phase 4 — Webhooks & background jobs (Week 5)
- Webhook CRUD API
- HMAC-SHA256 signing on delivery
- Celery Beat retry sweep with exponential back-off
- Webhook delivery log (30-day retention)
- Webhooks management page

### Phase 5 — AI-powered interactions (Weeks 6–7)
- **One-click fixes:** "Apply fix" button → animated diff preview → Accept / Reject / Undo/Redo; "Apply all safe fixes" batch action
- **Ask-the-code chat:** streaming side panel via `/reviews/{id}/chat`; suggested-question chips; full conversation context
- Animated dashboard: score ring (count-up), radar chart (Recharts), severity donut; hover-segment → filter findings list
- Filter / sort panel: severity chips, category toggles, search box, sort dropdown; Framer Motion list animation

### Phase 6 — Developer tools pages (Week 8)
- **API Playground:** endpoint picker, Monaco JSON body editor, API key field, Send button; live status/headers/timing; curl / Python / JS snippet tabs with copy button
- **Live webhook timeline:** real-time SSE delivery stream; status badges, signature-verified tick, expandable JSON payloads; "Send test event" button
- API Docs page (auto-generated from OpenAPI spec + hand-written guides)
- Micro-interactions pass: toasts with Undo, skeleton loaders, hover lift, confetti/glow on zero-critical

### Phase 7 — Personalisation, accessibility & polish (Week 9)
- Settings page: density (compact/comfortable), editor font size, accent colour picker, split-view toggle — all persisted in `localStorage`
- First-run guided tour (highlights editor, run button, results panel)
- Offline + rate-limit banners with visible countdown
- WCAG AA audit: contrast, keyboard navigation, visible focus rings, ARIA labels, screen-reader live-region announcements
- Lighthouse CI: Performance ≥ 90, Accessibility ≥ 95
- `prefers-reduced-motion` respecting all animations

### Phase 8 — Production hardening & launch (Week 10)
- Kubernetes manifests (or Railway/Render config)
- Vercel deployment with preview URLs per PR
- Sentry error tracking (frontend + backend)
- Prometheus metrics + Grafana dashboard
- Load testing (Locust): 100 concurrent reviews
- Security audit: OWASP top-10 checklist, dependency scan, secret scanning
- Documentation: README, API reference, self-hosting guide
- Beta launch checklist

---

*End of master prompt. For individual section edits, replace only the relevant section above.*
