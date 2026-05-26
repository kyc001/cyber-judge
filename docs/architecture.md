# Cyber Judge (赛博判官) — System Architecture

## Overview

Cyber Judge is a WeChat chat analysis and AI-powered report generation platform. It takes WeFlow JSON exports, performs 45+ statistical analyses, enriches with a multi-call LLM pipeline, and renders an interactive report with 19 section types and 25+ chart components.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Landing   │ │ Upload    │ │Analyzing │ │ Insights │ │ Report │  │
│  │ Page      │ │ Page      │ │Page      │ │ Page     │ │ Page   │  │
│  └─────┬─────┘ └─────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘  │
│        │              │             │            │           │        │
│  ┌─────┴──────────────┴─────────────┴────────────┴───────────┴─────┐ │
│  │                    FRONTEND (React 19 + TypeScript + Vite)       │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │ │
│  │  │ ThemeSystem  │ │ ReportRenderer│ │ Chart Components (25+)  │ │ │
│  │  │ (3 themes)   │ │ (19 section   │ │ (SVG/CSS/Recharts)      │ │ │
│  │  │              │ │  types)       │ │                          │ │ │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI + Uvicorn)                     │
│  POST /api/upload          — Upload WeFlow JSON, start analysis      │
│  GET  /api/report/:id      — Get report (202 while processing)       │
│  GET  /api/report/:id/progress — SSE stream of LLM sub-call progress │
│  POST /api/share/:id       — Create share link                       │
│  GET  /api/share/:slug     — Load shared report                      │
│  POST /api/export          — Export as json/csv/txt/html             │
│  GET  /api/health          — Health check                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ STATS ENGINE │    │   LLM SERVICE    │    │    PARSER        │
│              │    │                  │    │                  │
│ stats.py     │    │ Multi-call:      │    │ parser.py        │
│ stats_extra  │    │  hero+tags       │    │ (WeFlow JSON)    │
│              │    │  participants    │    │                  │
│ 45+ stats    │    │  quotes          │    │ Message types:   │
│ dimensions   │    │  sections        │    │ text/image/emoji │
│              │    │  predictions     │    │ file/system      │
│              │    │  chat_dna        │    │                  │
│              │    │                  │    │                  │
│              │    │ + JSON repair    │    │                  │
│              │    │ + retry/fallback │    │                  │
│              │    │ + SSE progress   │    │                  │
└──────────────┘    └──────────────────┘    └──────────────────┘
        │                         │
        └─────────────────────────┼─────────────────────────┐
                                  ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ SQLite       │  │ File System  │  │ Export Service           │  │
│  │ (reports,    │  │ (JSON cache) │  │ (json/csv/txt/html)      │  │
│  │  shares)     │  │              │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
cyber-judge/
├── backend/
│   ├── main.py              # FastAPI app (all endpoints)
│   ├── models.py            # Pydantic data models (40+ types)
│   ├── database.py          # SQLite persistence (WAL mode)
│   ├── parser.py            # WeFlow JSON parser
│   ├── stats.py             # Core stats engine (45+ dimensions)
│   ├── stats_extra.py       # Supplementary stats
│   ├── llm_service.py       # Multi-provider LLM with multi-call pipeline
│   ├── prompts.py           # Prompt templates + output validation
│   ├── fallback.py          # Rule-based fallback report generator
│   └── .env                 # Environment config (API keys, etc.)
├── frontend/
│   └── src/
│       ├── api/client.ts    # API client (upload, report, share, export)
│       ├── contracts/       # TypeScript type definitions
│       ├── components/
│       │   ├── report/      # ReportRenderer + Charts (25+ components)
│       │   └── ui/          # Shared UI primitives (Button, etc.)
│       ├── pages/           # LandingPage, UploadPage, AnalyzingPage, InsightsPage, ReportPage
│       ├── theme/           # ThemeSystem (dark/light/cyber, CSS custom properties)
│       └── styles.css       # Global styles + CSS variables
├── docs/
│   ├── architecture.md      # This document
│   └── feature-checklist.md # Complete feature checklist
├── texts/                   # Sample chat data for testing
└── references/              # Reference projects (10 repos)
```

## Data Flow

```
WeFlow JSON → Parser → ChatMessage[] → Stats Engine → ReportStats
                                               ↓
                                        LLM Service (multi-call)
                                        ┌─────────────────────┐
                                        │ 1. hero + tags      │
                                        │ 2. participants ─┐  │
                                        │ 3. quotes        │ parallel
                                        │ 4. sections       │  │
                                        │ 5. predictions    │  │
                                        │ 6. chat_dna       │  │
                                        └─────────────────────┘
                                               ↓
                                        Merge + Validate
                                               ↓
                                        ReportPayload → SQLite
                                               ↓
                                        Frontend Insights + Report Pages
                                        (19 section types, 25+ charts)
```

## Reference-Grounded Intermediate Pages

The intermediate theme pages are implemented from capabilities present in `references/`. These notes are for implementation traceability only; reference project names are not shown in the user-facing UI.
After analysis, the frontend enters the first theme page directly and advances through the fixed sequence below. There is no user-facing theme selector; the last theme transitions to the final report.

| Theme page | Reference basis | Integrated capability |
|------------|-----------------|-----------------------|
| 聊天总览 | `AnnualReport`, `WeFlow`, `welink` | Time-range total messages, active days, peak moments, streaks, chat DNA |
| 时间与作息 | `whatsapp-wrapped-v3`, `welink` | Hourly/weekday heatmap, chronotypes, late-night ratio, clock fingerprints |
| 语言与梗 | `WechatVisualization`, `ChatLab` | Word cloud, word specificity/commonality, n-gram phrases, keyword search style insights |
| 表情包档案 | `WechatVisualization`, `WeFlow` | Emoji ranking, owner labels, specificity/commonality, time distribution, English-to-Chinese WeChat sticker alias merge such as `[Facepalm]` → `[捂脸]` |
| 互动网络 | `chat-analytics`, `ChatLab`, `welink` | Reply matrix, directed edges, topic starts, @ mentions, link sharing |
| 情绪温度 | `chat-analytics` | Sentiment overview, monthly sentiment, per-contact emotion profile |
| 消息结构 | `echotrace`, `WechatExporter` | Message type breakdown and evolution for text, image, emoji, file, link, recall, red packet |
| 关系走势 | `relationship-candlestick-lab`, `WeFlow DualReport` | Monthly interaction trend, balance by message counts, milestones, first-chat replay |
| 名场面回放 | `ChatLab`, `whatsapp-wrapped-v3` | Real quote extraction, memorable moments, first conversation replay |
| 赛博占卜 | `PromptFill`, existing LLM pipeline | Pattern-based predictions, personality badges, LLM-generated short interpretation on every theme page |

## Key Design Decisions

1. **JSON-only input** — WeFlow JSON format only, backend handles parsing and validation
2. **Multi-call LLM** — 6 targeted sub-calls (hero, participants, quotes, sections, predictions, chat_dna) for higher quality than a single monolithic prompt
3. **SSE progress** — Server-Sent Events stream real-time sub-call progress to the frontend
4. **JSON repair** — Truncated LLM output is repaired before parsing (close strings, balance braces/brackets, strip code fences)
5. **Auto-start backend** — Vite plugin spawns the Python backend on `npm run dev`, no manual steps
6. **CSS custom properties for theming** — 3 themes (dark/light/cyber) via CSS variables, zero runtime cost
7. **Recharts + custom SVG/CSS** — Charts use Recharts where practical, custom SVG/CSS for bespoke visuals
8. **SQLite WAL** — Zero-config persistence with concurrent read support
9. **Rule-based fallback** — If all LLM calls fail, a template-based report generator produces a complete report
10. **No mock mode** — All API calls go to the real backend; Vite proxy forwards /api to localhost:8000

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite 6 |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Database | SQLite (WAL mode) |
| AI/LLM | DeepSeek, Qwen, OpenAI, OpenAI-compatible APIs, optional fallback provider |
| NLP | jieba (Chinese tokenization) |
| Charts | Recharts + custom SVG/CSS |
| Export | JSON, CSV, TXT, HTML |
| Dev Experience | Vite proxy + auto-start backend, single `npm run dev` |

## Performance

- Backend: Async background tasks for LLM, connection pooling for SQLite
- Frontend: `content-visibility: auto` for off-screen report sections
- LLM: Participants + quotes calls run in parallel via `asyncio.gather`
- Database: WAL mode for concurrent reads during polling
- Export: Streaming JSON for large responses
