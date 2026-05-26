# Cyber Judge — Feature Checklist & Status Tracker

Status: [x] Done  [-] Removed  [ ] Planned

---

## A. Data Import & Parsing

- [x] A1. WeFlow JSON export parsing (localType mapping: 1=text, 3/34/43=image, 47=emoji, 49=file, 10000=system)
- [x] A2. Message type auto-detection (text/image/emoji/file/link/system/red_packet/transfer)
- [x] A3. Anonymization / alias mapping (A同学, B同学, ...)
- [-] A4. WeChat PC TXT export parsing (removed — JSON only)
- [-] A5. Paste text input (removed — file upload only)
- [-] A6. Mock/demo mode (removed — real backend always)

## B. Core Stats Engine

### B1. Participant Stats
- [x] B1.1 Dragon ranking (message count + avatar + roast)
- [x] B1.2 Character count per person
- [x] B1.3 Emoji count per person
- [x] B1.4 Image/link/red packet count per person
- [x] B1.5 Average message length

### B2. Time Analysis
- [x] B2.1 7x24 heatmap (168 cells)
- [x] B2.2 Monthly activity trend
- [x] B2.3 Peak hour detection (top_hour)
- [x] B2.4 Favorite day of week (top_day)
- [x] B2.5 Late night ratio
- [x] B2.6 Hourly distribution (24 bins)
- [x] B2.7 Weekday distribution (7 days)
- [x] B2.8 Yearly monthly distribution
- [x] B2.9 Longest streak (consecutive chat days)
- [x] B2.10 Peak day (most messages in a single day)

### B3. Keyword / Text Analysis
- [x] B3.1 jieba Chinese tokenization
- [x] B3.2 High-frequency word cloud (4 tones: hot/sharp/soft/calm)
- [x] B3.3 Stopword filtering
- [x] B3.4 Word specificity (who says what — WechatVisualization pattern)
- [x] B3.5 Word commonality (shared vocabulary between two people)
- [x] B3.6 N-gram phrase extraction (2-5 char phrases)

### B4. Emoji Analysis
- [x] B4.1 Emoji usage ranking (with owner)
- [x] B4.2 Total/per-person emoji count
- [x] B4.3 Emoji specificity (who loves which emoji)
- [x] B4.4 Emoji commonality (shared emojis between two people)
- [x] B4.5 Emoji time distribution (when emojis are used)

### B5. Message Type Analysis
- [x] B5.1 Message type distribution (text/image/emoji/link/red_packet/system)
- [x] B5.2 Type percentages
- [x] B5.3 Message type evolution over time

### B6. Interaction / Relationship
- [x] B6.1 Directed interaction edges (who → whom)
- [x] B6.2 Relationship signal cards (two-way interaction, initiative, reply stability, care expression)
- [x] B6.3 Topic-start counts (who breaks silence first)
- [x] B6.4 Interaction matrix (per-pair reply counts)
- [x] B6.5 @mention stats (who gets @'d most)
- [x] B6.6 Send/receive ratio per person

### B7. Link Analysis
- [x] B7.1 Link domain ranking (with top sharer)
- [x] B7.2 Link time trends

## C. Chat DNA (Spotify Wrapped Style)

- [x] C1. Total messages / total words / active days
- [x] C2. Date range (first/last date, span in days)
- [x] C3. Peak hour / favorite weekday
- [x] C4. Late night ratio
- [x] C5. Top sender (dragon king/queen)
- [x] C6. Top emoji / top word
- [x] C7. Average daily messages
- [x] C8. Longest streak (consecutive days)
- [x] C9. Peak day (most messages in one day + top sender)
- [x] C10. Enhanced chat DNA (additional metrics)
- [x] C11. LLM-generated DNA paragraph (150 chars, Spotify Wrapped narrative)

## D. Chronotype (Sleep Schedule)

- [x] D1. Per-person chronotype classification (night_owl / early_bird / afternoon_peak / balanced)
- [x] D2. Per-person peak hour
- [x] D3. Night/morning message ratio per person
- [x] D4. Clock fingerprints (24-hour distribution per person)
- [x] D5. Human-readable labels ("深夜战神", "早起冠军", etc.)

## E. Sentiment / Emotion

- [x] E1. Positive/neutral/negative ratio
- [x] E2. Overall sentiment label
- [x] E3. Monthly sentiment trend
- [x] E4. Per-contact sentiment profiles
- [x] E5. LLM-generated sentiment section body

## F. Personality Badges

- [x] F1. Night owl (深夜战神)
- [x] F2. Early bird (早起冠军)
- [x] F3. Emoji king (表情包之王)
- [x] F4. Long text master (小作文大师)
- [x] F5. Speed replier (秒回机器)
- [x] F6. Goodnight fraud (晚安诈骗犯)
- [x] F7. Lurker (潜水专家)
- [x] F8. Red packet god (红包仙人)
- [x] F9. Extra badge criteria (extended rules)

## G. AI Predictions

- [x] G1. Prediction cards (title + body)
- [x] G2. Group predictions (dragon king, topics, new memes)
- [x] G3. Relationship predictions (trends, milestones)
- [x] G4. LLM-generated prediction content (separate sub-call)

## H. Timeline / Key Moments

- [x] H1. Burst detection (message burst in 5-min window)
- [x] H2. Goodnight detection (goodnight ritual patterns)
- [x] H3. Longest message detection
- [x] H4. First record / latest record
- [x] H5. First chat interaction (first messages between two people)
- [x] H6. Relationship milestones (first late-night chat, most active week, longest gap, reconnect)
- [x] H7. Famous quotes (most notable messages)

## I. Relationship Analysis (Dual Report)

- [x] I1. Relationship summary
- [x] I2. Who's more proactive
- [x] I3. Two-way interaction summary
- [x] I4. Relationship feature tags (共同语言/主动/稳定/陪伴等)
- [x] I5. Tsundere detection (嘴硬关心 pattern)
- [x] I6. Shared vocabulary
- [x] I7. First chat + first 10 messages
- [x] I8. Dual report extras

## J. LLM Pipeline

- [x] J1. Multi-provider support (DeepSeek, Qwen, OpenAI, compatible APIs)
- [x] J2. Exponential backoff retry (2 retries + fallback provider)
- [x] J3. Timeout control (configurable)
- [x] J4. JSON mode enforcement (response_format: json_object)
- [x] J5. JSON repair (close unclosed strings, balance braces/brackets, strip code fences)
- [x] J6. JSON extraction fallback chain (direct → repair → code fence → brace search)
- [x] J7. Few-shot examples (group + relationship)
- [x] J8. Safety validation (phone number / ID number regex, discrimination checks)
- [x] J9. Rule-based fallback (complete report when LLM fails)
- [x] J10. Token budget control (~3k input + 4k output)
- [x] J11. **Multi-call architecture** — 6 targeted sub-calls:
  - hero + tags + title
  - participants (roasts + personality)
  - quotes (from real messages)
  - sections (body text per section)
  - predictions (3 with probabilities)
  - chat_dna (Spotify Wrapped paragraph)
- [x] J12. Parallel sub-call execution (participants || quotes via asyncio.gather)
- [x] J13. SSE progress streaming (real-time per-sub-call status)
- [x] J14. 250 message samples sent to LLM for authentic quote extraction
- [x] J15. Section type/chart_ref mapping (backend enforces correct types regardless of LLM output)

## K. Frontend Report Sections & Charts

- [x] K1. Dragon ranking (horizontal bar chart)
- [x] K2. Heatmap (7x24 grid)
- [x] K3. Keyword cloud (font size + color coded by tone)
- [x] K4. Radar chart (SVG 6-dimension)
- [x] K5. Emoji board (grid with owner labels)
- [x] K6. Timeline (vertical event list)
- [x] K7. Relationship directed graph
- [x] K8. Relationship signal cards
- [x] K9. Word specificity chart (per-person cards + bars)
- [x] K10. Word commonality chart (shared word list)
- [x] K11. Message type bar chart
- [x] K12. Chat DNA card
- [x] K13. Chronotype list
- [x] K14. Sentiment gauge (3-color bar)
- [x] K15. Monthly activity bar chart
- [x] K16. Initiative ranking
- [x] K17. Link stats list
- [x] K18. Personality badge grid
- [x] K19. Predictions card
- [x] K20. Enhanced DNA card
- [x] K21. Clock fingerprint grid
- [x] K22. Emoji specificity chart
- [x] K23. Monthly sentiment trend
- [x] K24. Per-contact sentiment cards
- [x] K25. Streak card
- [x] K26. First chat card
- [x] K27. Milestones timeline
- [x] K28. Interaction matrix
- [x] K29. Quote gallery (hero cards with speaker + commentary)

## L. Export System

- [x] L1. JSON export (full ReportPayload)
- [x] L2. TXT export (plain text report)
- [x] L3. HTML export (self-contained + dark theme)
- [x] L4. CSV export (stats_extra data)
- [x] L5. XLS export (TSV participant table)

## M. Share System

- [x] M1. Share link generation (8-char slug)
- [x] M2. Share page (read-only display + CTA)
- [x] M3. Share data safety (no raw messages leaked)
- [x] M4. System share API integration

## N. Privacy & Security

- [x] N1. Frontend anonymization toggle
- [x] N2. Alias mapping (real name → code name)
- [x] N3. Backend does not persist raw messages
- [x] N4. Share page does not expose alias map
- [x] N5. LLM safety rules (no personal info, no discrimination)
- [x] N6. Output regex validation (phone/ID number checks)

## O. App Experience

- [x] O1. Landing page (hero + features + CTA)
- [x] O2. Upload page (drag-drop + file picker + JSON validation + anonymize toggle)
- [x] O3. Analyzing page (progress animation + polling + status text)
- [x] O4. Report page (full content + scroll progress + toolbar + export)
- [x] O5. Share page (read-only + CTA)
- [x] O6. 3 themes (dark / light / cyber) via CSS custom properties
- [x] O7. Auto-start backend (Vite plugin spawns Python, single `npm run dev`)
- [x] O8. Frontend-backend proxy (Vite proxies /api → localhost:8000)

## P. Dev Experience

- [x] P1. Single command startup (`npm run dev` in frontend/)
- [x] P2. Vite HMR for frontend
- [x] P3. Uvicorn auto-reload for backend
- [x] P4. TypeScript strict mode
- [x] P5. Python type hints throughout
- [x] P6. English docstrings on all modules and public functions

---

## Summary

| Category | Done | Planned | Removed |
|----------|------|---------|---------|
| A. Data Import | 3 | 0 | 3 |
| B. Core Stats | 29 | 0 | 0 |
| C. Chat DNA | 11 | 0 | 0 |
| D. Chronotype | 5 | 0 | 0 |
| E. Sentiment | 5 | 0 | 0 |
| F. Badges | 9 | 0 | 0 |
| G. Predictions | 4 | 0 | 0 |
| H. Timeline | 7 | 0 | 0 |
| I. Relationship | 8 | 0 | 0 |
| J. LLM Pipeline | 15 | 0 | 0 |
| K. Charts | 29 | 0 | 0 |
| L. Export | 5 | 0 | 0 |
| M. Share | 4 | 0 | 0 |
| N. Privacy | 6 | 0 | 0 |
| O. App Experience | 8 | 0 | 0 |
| P. Dev Experience | 6 | 0 | 0 |
| **Total** | **154** | **0** | **3** |

*Last updated: 2026-05-26*
