# CodeSentinel AI — System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────┐
│                     CLIENTS                         │
│  Browser (Next.js)   │   REST API consumers         │
│  Webhook receivers   │   CI/CD integrations         │
└──────────┬──────────────────────────┬───────────────┘
           │  HTTPS                   │  HTTPS + API key
           ▼                          ▼
┌─────────────────────┐   ┌─────────────────────────┐
│   Vercel CDN /      │   │   FastAPI (Python 3.12)  │
│   Next.js Frontend  │   │   REST API + SSE         │
│                     │   │   JWT / API-key auth     │
└─────────────────────┘   └──────────┬──────────────┘
                                     │
              ┌──────────────────────┼─────────────────┐
              ▼                      ▼                  ▼
       ┌─────────────┐    ┌────────────────┐   ┌──────────────┐
       │ PostgreSQL  │    │  Redis 7       │   │ MinIO /      │
       │ (primary DB)│    │  Cache/Queue/  │   │ S3-compatible│
       │             │    │  SSE pub-sub   │   │ file storage  │
       └─────────────┘    └────────────────┘   └──────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Celery Workers      │
                          │  Review pipeline     │
                          │  Webhook delivery    │
                          │  Celery Beat (cron)  │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Google Gemini API   │
                          │  (gemini-1.5-pro)    │
                          └─────────────────────┘
```

## Review Pipeline Flow

```
POST /reviews (code + language)
       │
       ▼
FastAPI validates → creates DB row (status=pending)
       │
       ▼
Enqueues Celery task → returns {review_id}
       │
       ▼ (async worker)
1. tree-sitter parse     → publishes progress "parsing" via Redis
2. Static rule engine    → publishes progress "static_checks"
3. Gemini 1.5 Pro call   → publishes progress "ai_analysis"
4. Merge & deduplicate   → publishes progress "merging"
5. Generate fix diffs    → publishes progress "generating_fixes"
       │
       ▼
Findings written to DB → status=completed
       │
       ├─► SSE subscribers receive final flush
       └─► Webhook delivery triggered
```

## SSE Streaming Protocol

```
GET /reviews/{id}/stream
Content-Type: text/event-stream

event: progress
data: {"step": "parsing", "index": 0, "total": 5}

event: finding
data: {"severity": "critical", "title": "SQL Injection", ...}

event: progress
data: {"step": "completed", "score": 72}
```

## Frontend State Architecture

```
Zustand stores:
  reviewStore       — current review state, findings list
  editorStore       — Monaco instance ref, decorations, cursor
  chatStore         — chat history, streaming buffer
  uiStore           — command palette open, density, theme prefs
  filterStore       — active severity chips, search, sort order
  authStore         — current user, JWT tokens, plan tier

React Query:
  useReviews()      — paginated history list
  useReview(id)     — single review + findings
  useApiKeys()      — user's API keys
  useWebhooks()     — user's webhooks
```

## Monorepo Structure

```
codesentinel/
├── frontend/              # Next.js 14 app
│   ├── app/               # App Router pages
│   │   ├── (auth)/        # Login, register, callback
│   │   ├── review/        # Workbench page
│   │   ├── history/       # Review history
│   │   ├── playground/    # API Playground
│   │   ├── settings/      # API keys, webhooks, prefs
│   │   └── docs/          # API documentation
│   ├── components/
│   │   ├── editor/        # Monaco wrapper, decorations, diff
│   │   ├── findings/      # FindingCard, FilterBar, SortDropdown
│   │   ├── chat/          # AskCodeChat, MessageBubble
│   │   ├── dashboard/     # ScoreRing, RadarChart, DonutChart
│   │   ├── playground/    # EndpointPicker, RequestEditor
│   │   ├── webhooks/      # WebhookTimeline, DeliveryCard
│   │   ├── ui/            # Design system primitives
│   │   └── CommandPalette.tsx
│   ├── stores/            # Zustand stores
│   ├── hooks/             # Custom React hooks
│   ├── lib/               # API client, SSE client, utils
│   └── styles/            # Global CSS, design tokens
│
├── backend/               # FastAPI application
│   ├── api/
│   │   ├── routes/        # reviews, api_keys, webhooks, health
│   │   └── middleware/    # auth, rate_limit, cors
│   ├── core/
│   │   ├── review/        # pipeline, static rules, gemini client
│   │   ├── auth/          # JWT sign/verify, bcrypt, Google OAuth, email verify
│   │   └── streaming/     # SSE publisher, Redis pub-sub
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic schemas
│   ├── tasks/             # Celery tasks
│   ├── migrations/        # Alembic migrations
│   └── tests/
│
├── docker-compose.yml
├── .github/workflows/
└── README.md
```
