# CodeSentinel AI — Design System Reference
> Extracted from Master Prompt § 8. Use this as the single source of truth for all UI work.

---

## Colour Tokens

| Token | Hex | Usage |
|---|---|---|
| `--bg` | `#0B0F17` | App background |
| `--surface` | `#111827` | Cards, panels |
| `--elevated` | `#1A2233` | Modals, dropdowns, tooltips |
| `--border` | `#263045` | Dividers, card outlines |
| `--accent-violet` | `#7C6CFF` | Primary CTA, active states, focus rings |
| `--accent-cyan` | `#22D3EE` | Secondary highlights, links |
| `--sev-critical` | `#EF4444` | Critical severity (red) |
| `--sev-high` | `#F97316` | High severity (orange) |
| `--sev-medium` | `#F59E0B` | Medium severity (amber) |
| `--sev-low` | `#3B82F6` | Low severity (blue) |
| `--sev-info` | `#64748B` | Info / style (slate) |

### CSS variable declaration (`:root`)
```css
:root {
  --bg:            #0B0F17;
  --surface:       #111827;
  --elevated:      #1A2233;
  --border:        #263045;
  --accent:        #7C6CFF;
  --accent-cyan:   #22D3EE;
  --sev-critical:  #EF4444;
  --sev-high:      #F97316;
  --sev-medium:    #F59E0B;
  --sev-low:       #3B82F6;
  --sev-info:      #64748B;
}
```

---

## Typography

| Role | Font | Weight | Size |
|---|---|---|---|
| UI text | Inter | 400 / 500 / 600 | 12–16 px |
| Headings | Inter | 700 | 20–36 px |
| Code / mono | JetBrains Mono | 400 | 13–14 px |

---

## Component Patterns

### Glassmorphism card
```css
.glass-card {
  background: rgba(17, 24, 39, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: 12px;
}
```

### Hover lift (micro-interaction)
```css
.card-hover {
  transition: transform 150ms ease, box-shadow 150ms ease;
}
.card-hover:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(124, 108, 255, 0.15);
}
```

### `prefers-reduced-motion` guard
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Pages & Routes

| Page | Route | Description |
|---|---|---|
| Landing | `/` | Marketing hero, feature highlights, demo |
| Review Workbench | `/review` | Main code-review editor and results panel |
| History | `/history` | Paginated list of past reviews |
| API Keys | `/settings/api-keys` | Key management |
| Webhooks | `/settings/webhooks` | Webhook CRUD + live tester |
| API Docs | `/docs` | Auto-generated OpenAPI + guides |
| Playground | `/playground` | Live API request builder |
| Settings | `/settings` | Personalisation preferences |

---

## Animation Library — Framer Motion Conventions

```ts
// Standard fade-in
export const fadeIn = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -8 },
  transition: { duration: 0.2 }
};

// Stagger children
export const staggerContainer = {
  animate: { transition: { staggerChildren: 0.05 } }
};

// List item
export const listItem = {
  initial: { opacity: 0, x: -12 },
  animate: { opacity: 1, x: 0 },
  exit:    { opacity: 0, x: 12 }
};
```

---

## Interactive Behaviour Checklist

- [ ] 1. Live review progress tracker (SSE stepper)
- [ ] 2. Linked editor ↔ findings (bidirectional)
- [ ] 3. One-click fixes with diff preview + Undo/Redo
- [ ] 4. Filters & sorting with animated list
- [ ] 5. Animated dashboard (score ring, radar, donut)
- [ ] 6. Ask-the-code chat (streaming, side panel)
- [ ] 7. Command palette (Ctrl/Cmd+K)
- [ ] 8. Drag-and-drop zone + sample-code dropdown
- [ ] 9. API Playground
- [ ] 10. Live webhook timeline
- [ ] 11. Micro-interactions (toasts, skeletons, confetti)
- [ ] 12. Personalisation (density, font, accent, split-view)
- [ ] 13. Resilient UX (empty states, offline banner, guided tour)
- [ ] 14. Accessibility (WCAG AA, keyboard, ARIA)
