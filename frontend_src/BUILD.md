# TaoForge Frontend — Build Specification

> Hand this file to Claude Code along with the component files. It contains everything needed to scaffold, build, and wire the full TaoForge frontend to the backend.

---

## Project Overview

TaoForge is a recursive self-improvement protocol for autonomous AI agents, built on Bittensor. This spec covers the frontend: a marketing site + live dashboard + documentation, built as a single React app.

**Stack:** Vite + React + TypeScript
**Styling:** CSS Modules or Tailwind (builder's choice), but must match the design tokens below exactly
**Deployment:** Static export (Vercel/Netlify) — no SSR required
**Backend:** FastAPI at `localhost:8091` (miner) and `localhost:8092` (validator) — see API section

---

## Design System

### Brand Identity
- **Name:** TaoForge (one word, capital T and F)
- **Tagline:** "Intelligence forged on τAO"
- **Positioning:** Open protocol on Bittensor (NOT a subnet)
- **Voice:** Direct, technical, zero fluff. Speaks to builders.
- **Aesthetic:** Stark white, black type, monochrome with ember-red sparks only on the forge icon and primary CTAs

### Color Tokens

```typescript
export const colors = {
  // Backgrounds
  bg:         "#FFFFFF",   // Primary background (light mode default)
  bgDark:     "#000000",   // Dark mode background
  surface:    "#F5F5F5",   // Card backgrounds, sections
  
  // Text
  black:      "#000000",   // Headings, primary text
  dark:       "#1A1A1A",   // Body text
  mid:        "#666666",   // Captions, secondary text
  light:      "#999999",   // Placeholders, muted text, labels
  
  // Borders
  border:     "#E0E0E0",   // Dividers, card borders
  
  // Accent — RESTRICTED USE
  ember:      "#E63B2E",   // Sparks in icon, CTAs, streaming indicators ONLY
  emberLight: "#F4D0CC",   // Hover states
  emberDim:   "rgba(230,59,46,0.06)", // Subtle backgrounds
  
  // Semantic
  success:    "#16a34a",   // Positive scores, improvements
};
```

### Typography

```typescript
export const fonts = {
  display: "'Manrope', sans-serif",  // Headings, wordmark, hero text
  mono:    "'IBM Plex Mono', monospace", // Labels, code, technical text, badges
  body:    "'Manrope', sans-serif",  // Body text, buttons, nav
};

// Google Fonts import:
// https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Manrope:wght@400;500;600;700;800&display=swap

export const type = {
  hero:     { size: 72, weight: 700, letterSpacing: -2.5, lineHeight: 1.02 },
  h1:       { size: 40, weight: 700, letterSpacing: -1, lineHeight: 1.1 },
  h2:       { size: 36, weight: 700, letterSpacing: -1, lineHeight: 1.15 },
  h3:       { size: 28, weight: 700, letterSpacing: -0.5, lineHeight: 1.2 },
  h4:       { size: 18, weight: 700, letterSpacing: 0, lineHeight: 1.3 },
  body:     { size: 15, weight: 400, letterSpacing: 0, lineHeight: 1.7 },
  small:    { size: 13, weight: 400, letterSpacing: 0, lineHeight: 1.6 },
  label:    { size: 10, weight: 400, letterSpacing: 3, lineHeight: 1, textTransform: "uppercase", fontFamily: "mono" },
  code:     { size: 13, weight: 400, letterSpacing: 0, lineHeight: 1.7, fontFamily: "mono" },
};
```

### Logo / Icon

The TaoForge icon is an anvil (black or white depending on background) with ember-red spark lines and dots rising from it, and a τ symbol embedded in the anvil face.

**Icon rules:**
- Anvil body: `#000000` on light bg, `#FFFFFF` on dark bg
- Spark lines and dots: always `#E63B2E` (ember)
- τ symbol inside anvil: inverse of anvil color
- Min size: 24×24px

**Wordmark:** "TaoForge" in Manrope 700, color matches context (black on light, white on dark). Always one word.

**Lockup variants:**
- Horizontal: Icon + Wordmark side by side
- Stacked: Icon above Wordmark
- Icon only: For small contexts / favicons

The full SVG icon and lockup components are in `taoforge-brand.jsx`.

### Animation Principles

1. **Fire particles** — Reusable `<FireParticles>` component with configurable `intensity`, `height`, and `spread`. Appears at different intensities across sections. Uses CSS `@keyframes sparkRise` with randomized size, opacity, drift, and duration per particle.

2. **Scroll reveals** — `useInView()` hook using IntersectionObserver (threshold 0.15). Elements fade-up on first scroll into view. Stagger children with incremental delays.

3. **Loop diagram** — SVG circle with 6 nodes that auto-advance on a 2.5s interval. Progress arc animates via `stroke-dashoffset`. Clickable nodes.

4. **Score counters** — `useCounter()` hook that counts from 0 to target with cubic ease-out over 1.2s. Triggered by scroll visibility.

5. **Mutation micro-animations** — Each mutation type has a unique SVG animation activated on hover:
   - Prompt Chain: text lines appearing in brackets
   - Inference Pipeline: sweeping dial needle
   - Tool Graph: node connection lines drawing in
   - LoRA Merge: layers compressing together
   - Memory Index: scanning line sweeping across rows

6. **Navbar** — Frosted glass: `background: rgba(255,255,255,0.92)`, `backdrop-filter: blur(12px)`

---

## Page Structure

### 1. Landing Page (`/`)

```
[Nav — sticky, frosted glass]
[Hero — sparks (intensity 2.5), staggered text reveal, ember underline on "τAO"]
[Divider]
[Loop Section — sparks (0.6), interactive circle diagram, step detail panel]
[Divider]
[Scoring Section — sparks (0.4), 3+2 grid of ScoreCards with counters/glow bars, formula block]
[Divider]
[Mutations Section — sparks (0.5), 5 hover-activated mutation cards with SVG micro-anims]
[Divider]
[CTA Section — sparks (1.8), pulsing icon, "Watch agents evolve", dashboard button]
[Footer]
```

### 2. Dashboard (`/dashboard`)

```
[Nav]
[Stats Row — 4 cards: Active Agents, Total Cycles, Verified Improvements, Avg Δ]
[Two-column layout:]
  [Left: Live Feed — streaming events with colored dot indicators, auto-scroll]
  [Right: Leaderboard table + Mutation Distribution bars]
[Footer]
```

**Real-time data:** Dashboard should connect to the backend via WebSocket or polling. See API section below.

### 3. Docs (`/docs`)

```
[Nav]
[Two-column layout:]
  [Left: Sticky sidebar TOC with hover states]
  [Right: Content sections — Overview, Architecture, Self-Improvement Loop, Mutations, Scoring, Running, Data]
[Footer]
```

Docs content is sourced from `PROTOCOL.md` in the repo root.

---

## Component Inventory

### Shared Components

| Component | Props | Description |
|-----------|-------|-------------|
| `ForgeIcon` | `size`, `dark` | SVG anvil icon with ember sparks |
| `Wordmark` | `size`, `dark` | "TaoForge" text in Manrope 700 |
| `Lockup` | `variant`, `size`, `dark` | Icon + Wordmark combo |
| `Label` | `children` | Uppercase mono micro-label |
| `Badge` | `children`, `color` | Outlined mono badge |
| `StatCard` | `label`, `value`, `sub` | Metric card with label and large number |
| `FireParticles` | `intensity`, `height`, `spread`, `tint` | Particle emitter |
| `CodeBlock` | `children` | Black background code block |

### Landing Page Components

| Component | Description |
|-----------|-------------|
| `HeroSparks` | Fire particle system for hero section |
| `LoopDiagram` | Interactive SVG circle with auto-advancing steps |
| `ScoreCard` | Animated counter + glow bar + description |
| `MutationAnim` | Per-type SVG micro-animation (5 variants) |

### Dashboard Components

| Component | Description |
|-----------|-------------|
| `LiveFeed` | Streaming event list with colored type indicators |
| `Leaderboard` | Sorted agent table with rank, score, streak |
| `MutationDistribution` | Horizontal bar breakdown by mutation type |
| `EventIcon` | Colored dot by event type |

### Hooks

| Hook | Description |
|------|-------------|
| `useInView(threshold)` | Returns `[ref, isVisible]` — IntersectionObserver, fires once |
| `useCounter(target, duration, start)` | Animated number counter with ease-out |

---

## Backend API

The TaoForge backend exposes these endpoints. Wire the dashboard to these instead of the simulated data.

### Miner (`localhost:8091`)

```
GET  /health              → { status: "ok", agent_id: "..." }
GET  /info                → { agent_id, model, provider, mutations_applied, current_cycle }
POST /tasks/submit        → Submit evaluation task to miner
GET  /tasks/{id}/result   → Get task result
```

### Validator (`localhost:8092`)

```
GET  /health              → { status: "ok", validator_id: "..." }
GET  /network/peers       → List of connected peers
GET  /scores              → Current agent scores and rankings
GET  /events              → Recent events (mutations, evaluations, improvements)
GET  /events/stream       → SSE stream of real-time events (preferred for dashboard)
GET  /dag                 → Improvement DAG structure
GET  /reputation          → Agent reputation scores with decay info
GET  /stats               → Aggregate stats (agents, cycles, improvements, avg delta)
```

### Event Schema

```typescript
interface AgentEvent {
  id: string;
  type: "mutation" | "evaluation" | "improvement" | "registration";
  agent: string;
  timestamp: string; // ISO 8601
  
  // mutation events
  mutation_type?: string;
  
  // evaluation events
  score?: number;
  subnet?: string;
  breakdown?: { specificity: number; accuracy: number; depth: number; calibration: number; followthrough: number };
  
  // improvement events
  delta?: number;
  mutation_type?: string;
  parent_id?: string; // DAG parent
  
  // registration events
  cycle?: number;
  reputation?: number;
}
```

### Leaderboard Schema

```typescript
interface AgentRanking {
  agent_id: string;
  name: string;
  score: number;          // composite score
  improvements: number;   // total verified improvements
  streak: number;         // consecutive improvement cycles
  top_mutation: string;   // most successful mutation type
  reputation: number;     // current reputation score
}
```

### Stats Schema

```typescript
interface ProtocolStats {
  active_agents: number;
  total_cycles: number;
  verified_improvements: number;
  avg_delta: number;
  uptime_seconds: number;
}
```

---

## File Structure (suggested)

```
taoforge-web/
├── public/
│   ├── favicon.svg          # ForgeIcon as favicon
│   └── og-image.png         # OG card (export from brand file)
├── src/
│   ├── main.tsx
│   ├── App.tsx              # Router + layout
│   ├── design/
│   │   ├── tokens.ts        # Colors, fonts, type scale
│   │   ├── components.tsx   # Shared components (ForgeIcon, Label, Badge, etc.)
│   │   ├── FireParticles.tsx
│   │   └── hooks.ts         # useInView, useCounter
│   ├── pages/
│   │   ├── Landing.tsx      # Full landing page with all sections
│   │   ├── Dashboard.tsx    # Live dashboard
│   │   └── Docs.tsx         # Documentation
│   ├── components/
│   │   ├── landing/
│   │   │   ├── LoopDiagram.tsx
│   │   │   ├── ScoreCard.tsx
│   │   │   └── MutationAnim.tsx
│   │   ├── dashboard/
│   │   │   ├── LiveFeed.tsx
│   │   │   ├── Leaderboard.tsx
│   │   │   └── MutationDistribution.tsx
│   │   └── layout/
│   │       ├── Nav.tsx
│   │       └── Footer.tsx
│   ├── api/
│   │   ├── client.ts        # Fetch wrapper for backend
│   │   ├── events.ts        # SSE connection for live feed
│   │   └── types.ts         # TypeScript interfaces
│   └── styles/
│       └── global.css       # Keyframes, base resets
├── package.json
├── vite.config.ts
├── tsconfig.json
└── PROTOCOL.md              # Protocol documentation (source for docs page)
```

---

## Build Instructions for Claude Code

1. **Scaffold** — `npm create vite@latest taoforge-web -- --template react-ts`
2. **Install** — No heavy deps needed. Just `react-router-dom` for routing.
3. **Extract tokens** — Copy the design tokens above into `src/design/tokens.ts`
4. **Port components** — The reference implementations are in the attached `.jsx` files. Convert to TypeScript, split into the file structure above.
5. **Wire API** — Replace simulated data generators in Dashboard with real fetch calls to the validator endpoints. Use SSE (`EventSource`) for `/events/stream`.
6. **Add routing** — `react-router-dom` with routes: `/` (landing), `/dashboard`, `/docs`
7. **Global CSS** — Extract all `@keyframes` from the STYLES constant into `global.css`
8. **Responsive** — The current design is desktop-first. Add mobile breakpoints for nav (hamburger), hero (smaller type), grid layouts (stack to single column), and dashboard (stack feed above sidebar).
9. **SEO** — Add meta tags, OG image, title per page
10. **Deploy** — `vite build` → static output, deploy to Vercel/Netlify

---

## Reference Files

These files contain the full working implementations. They are single-file React artifacts that need to be decomposed into the file structure above.

| File | Contains |
|------|----------|
| `taoforge-app.jsx` | Full app: landing page (with all animations), dashboard, docs, nav, footer |
| `taoforge-brand.jsx` | Brand system: logo components, color swatches, typography samples, social assets, guidelines |
| `rsir-architecture.jsx` | Protocol architecture deep-dive (7 tabs): overview, architecture diagram, agent flow, validation, ZK layer, incentives, launch plan |
| `font-compare.jsx` | Font comparison tool (can be discarded — Manrope was selected) |
| `PROTOCOL.md` | Protocol documentation (source of truth for the docs page) |

---

## Key Design Rules

1. **White-first** — `#FFFFFF` is the default background. Dark mode is secondary.
2. **Ember red only on sparks and CTAs** — Never in text, backgrounds, or decorative elements.
3. **Generous whitespace** — Match bittensor.com's spacious feel.
4. **Monospace for technical content** — Labels, badges, code, stats all use IBM Plex Mono.
5. **Manrope for everything else** — Display and body text.
6. **TaoForge is a protocol, NOT a subnet** — It uses Bittensor subnet data but is not itself a subnet.
7. **Fire is atmospheric** — Present throughout the landing page at varying intensities, but never overwhelming. The fire is the one organic element in an otherwise stark design.
