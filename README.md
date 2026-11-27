# CodeSentinel AI — Project Proposal

> **GenAI CIA-P submission**  
> An AI-powered code review SaaS platform built on Google Gemini 1.5 Pro.

---

## What is CodeSentinel AI?

CodeSentinel AI is a production-ready SaaS that lets developers submit code and receive deep security, quality, and performance analysis — powered by Google Gemini — in seconds. It combines classical static analysis with LLM-powered reasoning, streams findings live, and lets users apply AI-generated fixes with one click.

---

## Repository Layout

```
gen ai prop/
│
├── README.md                      ← You are here
│
├── prompts/
│   └── MASTER_PROMPT.md           ← Full AI coding-agent build prompt (all 10 sections)
│
├── architecture/
│   └── ARCHITECTURE.md            ← System diagrams, monorepo layout, state architecture
│
├── specs/
│   ├── API_SPEC.md                ← Endpoint reference, request/response schemas
│   └── WEBHOOKS_SPEC.md           ← Events, payload format, signing, retry policy
│
├── phases/
│   └── PHASE_BREAKDOWN.md         ← 8-week build plan with detailed per-phase task lists
│
└── ui-ux/
    └── DESIGN_SYSTEM.md           ← Colour tokens, typography, component patterns, animation conventions
```

---

## Quick Reference

| What | Where |
|---|---|
| Full prompt (hand to AI agent) | [`prompts/MASTER_PROMPT.md`](prompts/MASTER_PROMPT.md) |
| UI / UX design spec | [`ui-ux/DESIGN_SYSTEM.md`](ui-ux/DESIGN_SYSTEM.md) |
| API endpoint reference | [`specs/API_SPEC.md`](specs/API_SPEC.md) |
| Webhook events & signing | [`specs/WEBHOOKS_SPEC.md`](specs/WEBHOOKS_SPEC.md) |
| 8-week build roadmap | [`phases/PHASE_BREAKDOWN.md`](phases/PHASE_BREAKDOWN.md) |
| System architecture | [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| AI model | Gemini 1.5 Pro | Long context window (1 M tokens), structured output mode, free tier for prototyping |
| Streaming | Server-Sent Events | Simpler than WebSockets for one-way push; native browser support |
| Editor | Monaco | Same engine as VS Code; first-class diff, decorations, and gutter API |
| Auth | Custom JWT (`python-jose` + `bcrypt`) + Google OAuth (`authlib`) | No third-party auth dependency; full control over token lifecycle |
| Task queue | Celery + Redis | Battle-tested; Redis already needed for SSE pub-sub and rate limiting |
| Animations | Framer Motion | Declarative, respects `prefers-reduced-motion`, works seamlessly with Next.js |

---

## 14 Interactive Behaviours (§ 8)

The UI is not a wrapper — it is the product. Every behaviour below is required:

1. Live review progress tracker (SSE stepper)
2. Bidirectionally linked editor ↔ findings
3. One-click fixes with animated diff + Undo/Redo
4. Animated filter / sort panel
5. Animated dashboard: score ring, radar chart, severity donut
6. Ask-the-code streaming chat
7. Command palette (Ctrl/Cmd+K)
8. Drag-and-drop zone with sample-code dropdown
9. API Playground with snippet generator
10. Live webhook delivery timeline
11. Micro-interactions (toasts, skeletons, confetti, copy animation)
12. Personalisation settings (density, font, accent, split-view)
13. Resilient UX (empty states, offline banner, guided tour)
14. Full WCAG AA accessibility

---

## Tech Stack (summary)

**Frontend:** Next.js 14, TypeScript, Tailwind, Framer Motion, Monaco Editor, Recharts, Zustand, TanStack Query  
**Backend:** FastAPI, Python 3.12, Celery, Redis, PostgreSQL 16, custom JWT (`python-jose` + `bcrypt`), Google Gemini 1.5 Pro  
**Infra:** Docker, Kubernetes, Vercel, GitHub Actions, Sentry, Prometheus
