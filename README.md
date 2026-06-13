# Initiative Tracker

A full-stack leadership dashboard for tracking organizational initiatives — built for Executive and Operational leadership teams to monitor progress, surface risks, and post updates across all active initiatives.

## Features

- **Executive Dashboard** — Summary KPIs (total, on-track, at-risk, delayed, completed, avg progress), "Needs Attention" panel, by-department breakdown, real-time activity feed
- **Initiatives Table** — Searchable, filterable by status / department / priority with inline progress bars
- **Initiative Detail** — Full initiative info, chronological update log, inline "Add Update" form
- **Create / Edit Form** — Full form with progress slider, department picker, and all optional fields

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 7, Tailwind CSS v4, shadcn/ui, Wouter, TanStack Query |
| API | Express 5, TypeScript 5.9 |
| Database | PostgreSQL, Drizzle ORM |
| Validation | Zod v4, drizzle-zod |
| API codegen | Orval (OpenAPI 3.1 → React Query hooks + Zod schemas) |
| Monorepo | pnpm workspaces, Node.js 24 |

## Quick Start

### Prerequisites
- Node.js 24+
- pnpm 10+
- PostgreSQL database

### 1 — Install dependencies

```bash
pnpm install
```

### 2 — Configure the database

Set `DATABASE_URL` in your environment:

```bash
DATABASE_URL=postgres://user:pass@localhost:5432/initiative_tracker
```

On Replit, this is automatically provisioned — see the Secrets panel.

### 3 — Push the schema

```bash
pnpm --filter @workspace/db run push
```

### 4 — Start the servers

```bash
# API server (reads $PORT, dev default: 5000)
pnpm --filter @workspace/api-server run dev

# Frontend (reads $PORT)
pnpm --filter @workspace/initiative-tracker run dev
```

---

## Repo Structure

```
├── artifacts/
│   ├── api-server/           # Express 5 REST API
│   │   └── src/
│   │       ├── app.ts        # Express app factory
│   │       ├── index.ts      # Server entry point
│   │       ├── lib/          # Shared helpers (logger)
│   │       └── routes/       # Route handlers
│   └── initiative-tracker/   # React + Vite SPA
│       └── src/
│           ├── pages/        # Dashboard, Initiatives, Detail, Form
│           └── components/   # StatusBadge, ProgressBar, AppShell, ui/*
├── lib/
│   ├── api-spec/             # OpenAPI 3.1 contract (source of truth)
│   ├── api-zod/              # Generated Zod schemas (run codegen to update)
│   ├── api-client-react/     # Generated TanStack Query hooks
│   └── db/                   # Drizzle ORM schema + migrations
└── scripts/
    └── generate_excel.py     # Excel workbook export with VBA macros
```

---

## API Reference

All endpoints are prefixed with `/api`.

### Initiatives

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/initiatives` | List all (query: `status`, `department`, `priority`) |
| `POST` | `/initiatives` | Create an initiative |
| `GET` | `/initiatives/:id` | Get one initiative |
| `PATCH` | `/initiatives/:id` | Update fields on an initiative |
| `DELETE` | `/initiatives/:id` | Delete an initiative (cascades to updates) |
| `GET` | `/initiatives/:id/updates` | List progress updates |
| `POST` | `/initiatives/:id/updates` | Add a progress update |

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/dashboard/summary` | Aggregated KPI stats |
| `GET` | `/dashboard/recent-activity` | Activity feed (query: `limit`) |

### Other

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/departments` | List departments |
| `POST` | `/departments` | Create a department |
| `GET` | `/healthz` | Health check |

---

## Data Model

### Initiative

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | Auto-increment PK |
| `title` | string | Required |
| `description` | string? | Optional |
| `status` | enum | `on_track` \| `at_risk` \| `delayed` \| `completed` \| `not_started` |
| `progress` | integer | 0–100 |
| `priority` | enum | `high` \| `medium` \| `low` |
| `owner` | string? | Optional |
| `department` | string? | Optional |
| `startDate` | string? | ISO date `YYYY-MM-DD` |
| `endDate` | string? | ISO date `YYYY-MM-DD` |
| `createdAt` | timestamp | Auto-set |
| `updatedAt` | timestamp | Auto-updated |

### Initiative Update

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | Auto-increment PK |
| `initiativeId` | integer | FK → `initiatives.id` (cascade delete) |
| `note` | string | Progress note text |
| `author` | string | Who posted it |
| `createdAt` | timestamp | Auto-set |

---

## Running Tests

Unit tests cover all API route handlers with a mocked database layer.

```bash
pnpm --filter @workspace/api-server run test
```

---

## Development Workflows

**Regenerate API types after changing the OpenAPI spec:**
```bash
pnpm --filter @workspace/api-spec run codegen
```

**Apply DB schema changes:**
```bash
pnpm --filter @workspace/db run push
```

**Full typecheck:**
```bash
pnpm run typecheck
```

**Generate Excel export:**
```bash
python scripts/generate_excel.py
```

---

## Status Color System

| Status | Color | Meaning |
|--------|-------|---------|
| On Track | Emerald | Progress on schedule |
| At Risk | Amber | Needs attention |
| Delayed | Red | Behind schedule |
| Completed | Blue | Done |
| Not Started | Slate | Not yet begun |

---

## Excel Export

A companion workbook (`scripts/generate_excel.py`) generates a styled `.xlsx` file with VBA macros for full CRUD access to the API from Excel — useful for stakeholders who prefer spreadsheets. See the [initiative-tracker-excel](https://github.com/mwpetroff/initiative-tracker-excel) repo for setup instructions.
