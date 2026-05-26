# Task 5 Handover — LLM Pipeline & Report Generation

**Role**: Backend + LLM integration + Frontend integration
**Date**: 2026-05-26
**Status**: Complete

---

## 1. What Was Built

The complete analysis pipeline from JSON ingestion to interactive report display:

```
WeFlow JSON → Parser → Stats (45+ dimensions) → Multi-call LLM → Report → Frontend
```

### Backend (Python/FastAPI)
- `parser.py` — WeFlow JSON parser (localType → message type mapping)
- `stats.py` — Core stats engine (participants, heatmap, keywords, radar, emoji, timeline, relationships, sentiment, badges, predictions, etc.)
- `stats_extra.py` — Supplementary stats (hourly/weekday/yearly distributions, streaks, ngrams, emoji specificity, interaction matrix, etc.)
- `llm_service.py` — Multi-provider LLM client with 6-call pipeline, JSON repair, retry/fallback
- `prompts.py` — Prompt templates (group roast + relationship), output validation, PII checks
- `fallback.py` — Rule-based report generator (used when all LLM calls fail)
- `main.py` — FastAPI server with all endpoints + SSE progress streaming
- `models.py` — Pydantic models (40+ types matching frontend contract)
- `database.py` — SQLite persistence (WAL mode)

### Frontend (React 19/TypeScript/Vite)
- `UploadPage.tsx` — JSON file upload (drag-drop + file picker, anonymize toggle)
- `AnalyzingPage.tsx` — Progress display with polling
- `ReportPage.tsx` — Full report with toolbar (copy link, export JSON, system share)
- `ReportRenderer.tsx` — 19 section types dispatched to 29 chart components
- `Charts.tsx` — All visualization components
- `client.ts` — API client (upload, report polling, share, export)
- `ThemeSystem.tsx` — 3 themes (dark/light/cyber) via CSS custom properties
- `vite.config.ts` — Auto-start backend plugin + API proxy

---

## 2. JSON Input Contract — WeFlow Export Format

The system accepts **one format only**: the JSON export produced by WeFlow.

This is NOT a custom format. It is the native output of WeFlow's chat export feature.
The JSON provider role must deliver files in this exact WeFlow export schema.

### 2.1 Top-Level Structure (WeFlow Export)

```json
{
  "weflow": { ... },
  "session": { ... },
  "messages": [
    { ... },
    { ... }
  ],
  "avatars": { ... }
}
```

Only the `"messages"` array is read. Other top-level keys (`weflow`, `session`, `avatars`) are produced by WeFlow and are ignored by the parser.

### 2.2 WeFlow Message Object — Required Fields

These fields are produced by WeFlow and MUST be present in each message object:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `localId` | integer | WeFlow | Unique message ID within the chat |
| `formattedTime` | string | WeFlow | `"YYYY-MM-DD HH:MM:SS"` format |
| `localType` | integer | WeFlow | WeFlow message type code (see §2.3) |
| `content` | string or null | WeFlow | Message body text (null for images/video) |
| `senderDisplayName` | string | WeFlow | Human-readable sender nickname |
| `senderUsername` | string | WeFlow | WeChat username/chatroom ID (secondary ID) |

### 2.3 WeFlow localType → Message Type Mapping

| localType | Message Type | Notes |
|-----------|-------------|-------|
| 1 | text | Standard text message |
| 3 | image | Picture message (content is null) |
| 34 | image | Picture (alternate code) |
| 43 | image | Video message (content is null) |
| 47 | emoji | Animated sticker; `source` field contains CDN URL if available |
| 48 | emoji | Sticker (alternate code) |
| 49 | file | File attachment |
| 10000 | system | System notification (member join/leave, recall, etc.) |
| *other* | text | Unknown types treated as text, content passed through |

### 2.4 Message Object — Optional Fields Used

| Field | Type | Used For |
|-------|------|----------|
| `source` | string | Emoji CDN URL for localType=47 |
| `emojiCdnUrl` | string | Alternate emoji URL source |
| `quotedContent` | string | Reply chain detection |
| `quotedSender` | string | Reply chain detection |

### 2.5 Minimal Valid WeFlow Input

```json
{
  "messages": [
    {
      "localId": 1,
      "formattedTime": "2026-05-01 12:00:00",
      "localType": 1,
      "content": "Hello",
      "senderDisplayName": "Alice",
      "senderUsername": "wxid_alice"
    },
    {
      "localId": 2,
      "formattedTime": "2026-05-01 12:01:00",
      "localType": 1,
      "content": "Hi!",
      "senderDisplayName": "Bob",
      "senderUsername": "wxid_bob"
    }
  ]
}
```

### 2.6 Constraints

- File must be valid JSON (UTF-8 encoding)
- Max file size: 8MB (frontend limit, configurable in backend via `MAX_MESSAGES_PER_REQUEST`)
- Minimum 20 characters of content (frontend validation)
- Messages are processed in `localId` order

---

## 3. API Endpoints

### 3.1 POST /api/upload
Submit raw WeFlow JSON text for analysis.

**Request:**
```json
{
  "text": "<raw JSON string content>",
  "report_type": "group_roast",
  "anonymized": true
}
```

- `report_type`: `"group_roast"` | `"relationship"`
- `anonymized`: if true, senders are renamed to A同学, B同学, C同学...

**Response (200):**
```json
{
  "report_id": "a1b2c3d4e5f6",
  "status": "processing",
  "estimated_seconds": 8
}
```

### 3.2 GET /api/report/:id
Poll for report completion.

- **200**: Report ready, returns full `ReportPayload`
- **202**: Still processing, retry after 2s
- **404**: Report not found
- **500**: Generation failed

### 3.3 GET /api/report/:id/progress
SSE stream of LLM sub-call progress. Events:

```json
{"type": "progress", "step": "hero", "status": "started"}
{"type": "progress", "step": "hero", "status": "done"}
{"type": "progress", "step": "participants", "status": "started"}
{"type": "progress", "step": "quotes", "status": "started"}
...
{"type": "done"}
```

Steps: `hero` → `participants` + `quotes` (parallel) → `sections` → `predictions` → `chat_dna`

### 3.4 POST /api/share/:id
Create share link. Returns `{ slug, url, report }`.

### 3.5 GET /api/share/:slug
Load shared report.

### 3.6 POST /api/export
Export report. Body: `{ report_id, format: "json"|"csv"|"txt"|"html"|"xlsx" }`.

---

## 4. Architecture Decisions

### 4.1 Multi-Call LLM (Not Monolithic)
Instead of one giant prompt → one output, the pipeline makes 6 targeted sub-calls:
1. **hero** — title, tagline, hero block, tags
2. **participants** — per-person roast + personality label (receives per-person message samples)
3. **quotes** — real quotes extracted from 250 message samples (receives full transcript)
4. **sections** — body text for each of the 17 report sections
5. **predictions** — 3 predictions with probabilities
6. **chat_dna** — 150-char Spotify Wrapped style paragraph

Calls 2 and 3 run in parallel via `asyncio.gather`. Each call has a focused system prompt and receives only the data relevant to its task.

### 4.2 JSON Repair
LLM output is repaired before parsing: unclosed strings get closing quotes, unbalanced braces/brackets are balanced, markdown code fences are stripped. The extraction chain is: direct parse → repair → code fence extraction → brace extraction.

### 4.3 Section Type Enforcement
LLM-generated sections have their `type` and `chart_ref` fields enforced by a server-side mapping (`SECTION_TYPE_MAP` in `main.py`). The LLM cannot produce wrong types — the backend corrects them.

### 4.4 Fallback Generator
If all LLM calls fail (both primary and fallback providers), `fallback.py` produces a complete report from stats alone. No report ever fails to generate.

### 4.5 Auto-Start Backend
The Vite dev server (`npm run dev`) automatically spawns the Python backend. No manual backend startup needed. The Vite plugin:
- Detects `backend/venv/Scripts/python.exe` → falls back to system `python`
- Pipes backend stdout/stderr to the Vite console
- Auto-restarts on crash
- Kills backend when Vite stops

---

## 5. What Other Roles Need to Provide

### 5.1 JSON Provider (WeFlow / Extraction Role)
The JSON file must:
1. Be a valid UTF-8 JSON file
2. Have a `"messages"` array at the top level
3. Each message object must have the required fields from section 2.2
4. `formattedTime` must be `"YYYY-MM-DD HH:MM:SS"` format
5. `localType` integers must follow the mapping in section 2.3

The system tolerates additional fields and unknown `localType` values — they are passed through as text.

### 5.2 Testing
Sample data is available in `texts/群聊_5A💧群.json` (5,846 messages, 3.15MB, 26 participants). This file works end-to-end.

---

## 6. Configuration

### Backend (.env)
```
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_API_KEY=your-fallback-key
LLM_FALLBACK_API_BASE=https://api.openai.com/v1
LLM_FALLBACK_MODEL=gpt-4o-mini
LLM_MULTI_CALL=true          # enable multi-call pipeline
LLM_TIMEOUT_SECONDS=120
LLM_MAX_RETRIES=2
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173
DATABASE_PATH=./data/cyber_judge.db
```

### Frontend
- No `.env` needed (defaults work)
- `VITE_API_BASE_URL` can override API base (default: `""` — uses Vite proxy)

---

## 7. Running the System

```bash
cd frontend
npm run dev
# → Vite starts on :5173
# → Backend auto-starts on :8000
# → Open http://localhost:5173
```

Or start separately:
```bash
# Terminal 1
cd backend && python main.py    # :8000

# Terminal 2
cd frontend && npm run dev      # :5173
```
