"""Pydantic models matching frontend contracts/report.ts — complete edition."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ── Enums / Unions ──────────────────────────────────────────────

ReportType = Literal["group_roast", "relationship"]
MessageType = Literal["text", "image", "emoji", "file", "link", "system", "red_packet", "transfer", "unknown"]
SourceType = Literal["wechat_txt", "weflow_json", "paste", "mock"]
ToneType = Literal["hot", "soft", "sharp", "calm"]
SectionType = Literal[
    "summary", "dragon_rank", "heatmap", "keywords", "radar", "emoji", "timeline",
    "relationship", "word_specificity", "word_commonality", "message_types",
    "chat_dna", "chronotype", "sentiment", "monthly", "initiative",
    "links", "annual", "personality_badges", "predictions",
]
AnalyzeStatus = Literal["queued", "processing", "done"]


# ── Chat Message ─────────────────────────────────────────────────

class ChatMessage(BaseModel):
    msg_id: str
    sender: str
    ts: str  # ISO 8601
    type: MessageType = "text"
    content: str
    reply_to: Optional[str] = None
    meta: Optional[dict[str, str | int | bool]] = None


# ── Privacy ──────────────────────────────────────────────────────

class PrivacyConfig(BaseModel):
    anonymized: bool = True
    alias_map: Optional[dict[str, str]] = None


class ClientMeta(BaseModel):
    schema_version: str = "2026-05-24"
    locale: str = "zh-CN"


# ── API Request ──────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    report_type: ReportType
    source: SourceType = "wechat_txt"
    messages: list[ChatMessage]
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    client_meta: ClientMeta = Field(default_factory=ClientMeta)


# ── API Response ─────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    report_id: str
    status: AnalyzeStatus
    estimated_seconds: int


# ── Report Stats (comprehensive) ─────────────────────────────────

class ParticipantStat(BaseModel):
    id: str
    name: str
    avatar: str
    message_count: int
    character_count: int
    emoji_count: int
    image_count: int = 0
    link_count: int = 0
    red_packet_count: int = 0
    average_length: float
    roast: str


class HeatmapCell(BaseModel):
    day: int  # 0=Mon..6=Sun
    hour: int  # 0-23
    value: float  # 0-1


class KeywordStat(BaseModel):
    word: str
    count: int
    tone: ToneType


class RadarMetric(BaseModel):
    label: str
    value: float  # 0-100


class EmojiStat(BaseModel):
    label: str
    value: int
    owner: Optional[str] = None
    url: Optional[str] = None


class TimelineEvent(BaseModel):
    id: str
    time: str
    title: str
    body: str


class RelationshipEdge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    weight: float  # 0-1
    label: str

    class Config:
        populate_by_name = True


class RelationshipMetric(BaseModel):
    label: str
    value: float  # 0-100
    caption: str


# ── New stat types from reference projects ───────────────────────

class WordSpecificityItem(BaseModel):
    """Who says what — word uniqueness per person (WechatVisualization)."""
    word: str
    sender: str
    count: int
    specificity: float  # (x-y)/(x+y) * max(x,y), range -1..1


class WordCommonalityItem(BaseModel):
    """Shared vocabulary — words both people use (WechatVisualization)."""
    word: str
    count_a: int
    count_b: int
    commonality: float  # harmonic mean, 0-1


class MessageTypeBreakdown(BaseModel):
    """Distribution of message types (echotrace radar basis)."""
    type: str
    label: str
    count: int
    percentage: float  # 0-100


class ChatDNASummary(BaseModel):
    """Spotify Wrapped style summary card (welink, whatsapp-wrapped-v3)."""
    total_messages: int
    total_words: int
    active_days: int
    active_months: int
    date_range_days: int
    first_date: str
    last_date: str
    top_hour: int
    top_day: int  # 0=Mon..6=Sun
    top_emoji: str
    top_word: str
    top_sender_name: str
    top_sender_count: int
    avg_daily_messages: float
    longest_gap_days: int
    late_night_ratio: float  # 0-100


class ChronotypeInfo(BaseModel):
    """Night owl vs early bird per person (whatsapp-wrapped-v3)."""
    name: str
    chronotype: str  # "night_owl" | "early_bird" | "afternoon_peak" | "balanced"
    peak_hour: int
    night_ratio: float  # % messages 22:00-05:00
    morning_ratio: float  # % messages 05:00-09:00
    label: str  # human-readable like "深夜战神" or "早起鸟"


class SentimentOverview(BaseModel):
    """Proxy sentiment distribution (chat-analytics)."""
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    label: str  # "总体积极" | "中性偏暖" | "嘴上不饶人" etc.


class MonthlyActivity(BaseModel):
    """Messages per month (AnnualReport, WeFlow)."""
    month: str  # "2024-01"
    count: int
    label: str  # "1月"


class InitiativeScore(BaseModel):
    """Who starts conversations after silence (whatsapp-wrapped-v3)."""
    name: str
    score: float  # 0-100
    initiations: int  # raw count
    label: str


class LinkStat(BaseModel):
    """Shared links analysis (chat-analytics)."""
    domain: str
    count: int
    top_sharer: str


class PersonalityBadge(BaseModel):
    """Personality badge (whatsapp-wrapped-v3)."""
    id: str
    name: str
    icon: str  # emoji or icon name
    description: str
    awarded_to: str


class Prediction(BaseModel):
    """AI prediction for the group/relationship (whatsapp-wrapped-v3)."""
    id: str
    title: str
    body: str
    probability: str  # "高" | "中" | "低"


# ── Complete ReportStats ─────────────────────────────────────────

class ReportStats(BaseModel):
    # Original fields
    participants: list[ParticipantStat]
    heatmap: list[HeatmapCell]
    keywords: list[KeywordStat]
    radar: list[RadarMetric]
    emojis: list[EmojiStat]
    timeline: list[TimelineEvent]
    relationship_edges: list[RelationshipEdge]
    relationship_metrics: Optional[list[RelationshipMetric]] = None

    # New fields from reference projects
    word_specificity: list[WordSpecificityItem] = []
    word_commonality: list[WordCommonalityItem] = []
    message_type_breakdown: list[MessageTypeBreakdown] = []
    chat_dna: Optional[ChatDNASummary] = None
    chronotypes: list[ChronotypeInfo] = []
    sentiment_overview: Optional[SentimentOverview] = None
    monthly_activity: list[MonthlyActivity] = []
    initiative_scores: list[InitiativeScore] = []
    link_stats: list[LinkStat] = []
    personality_badges: list[PersonalityBadge] = []
    predictions: list[Prediction] = []

    # Extra stats from stats_extra.py
    hourly_distribution: list[HourlyBin] = []
    weekday_distribution: list[WeekdayBin] = []
    yearly_monthly: list[YearlyMonthBin] = []
    streak: Optional[StreakInfo] = None
    peak_day: Optional[PeakDayInfo] = None
    ngrams: list[NgramItem] = []
    emoji_specificity: list[EmojiSpecificityItem] = []
    interaction_matrix: list[InteractionMatrixItem] = []
    first_chat: Optional[FirstChatInfo] = None
    monthly_sentiment: list[MonthlySentimentItem] = []
    annual_summary: Optional[AnnualSummary] = None

    # Extra v2 fields
    emoji_commonality: list[dict] = []
    emoji_time_distribution: list[dict] = []
    message_type_evolution: list[dict] = []
    red_packet_overview: Optional[dict] = None
    link_time_trends: list[dict] = []
    enhanced_chat_dna: Optional[dict] = None
    clock_fingerprints: list[dict] = []
    per_contact_sentiment: list[dict] = []
    extra_badge_criteria: list[dict] = []
    relationship_milestones: list[dict] = []
    recall_stats: Optional[dict] = None
    famous_quotes: list[dict] = []
    dual_report_extras: Optional[dict] = None
    at_mention_stats: list[dict] = []
    send_ratio: list[dict] = []


# ── Report Sections & Quotes ─────────────────────────────────────

class ReportSection(BaseModel):
    id: str
    type: SectionType
    heading: str
    body: str
    chart_ref: Optional[str] = None


class QuoteItem(BaseModel):
    id: str
    speaker: str
    text: str
    comment: str
    icon: str = "sparkles"


class HeroBlock(BaseModel):
    kicker: str
    quote: str
    visual: str


class ShareBlock(BaseModel):
    slug: Optional[str] = None
    hook: str
    watermark: str


# ── Full Report ──────────────────────────────────────────────────

class ReportPayload(BaseModel):
    report_id: str
    report_type: ReportType
    created_at: str
    title: str
    tagline: str
    hero: HeroBlock
    tags: list[str]
    sections: list[ReportSection]
    quotes: list[QuoteItem]
    stats: ReportStats
    share: ShareBlock


class SharePayload(BaseModel):
    slug: str
    url: str
    report: ReportPayload


# ── Export types ─────────────────────────────────────────────────

ExportFormat = Literal["json", "txt", "html", "csv", "xlsx"]


class ExportRequest(BaseModel):
    report_id: str
    format: ExportFormat = "json"


class ExportResponse(BaseModel):
    content: str
    content_type: str
    filename: str


# ── Extra stats types (stats_extra.py) ──────────────────────────

class HourlyBin(BaseModel):
    hour: int
    count: int
    pct: float

class WeekdayBin(BaseModel):
    day: int
    label: str
    count: int
    pct: float

class YearlyMonthBin(BaseModel):
    month: int
    label: str
    count: int
    pct: float

class StreakInfo(BaseModel):
    length: int
    start: str
    end: str

class PeakDayInfo(BaseModel):
    date: str
    count: int
    top_sender: str

class NgramItem(BaseModel):
    phrase: str
    count: int

class EmojiSpecificityItem(BaseModel):
    emoji: str
    sender: str
    count: int
    specificity: float
    url: Optional[str] = None

class InteractionMatrixItem(BaseModel):
    from_: str = Field(alias="from")
    to: str
    count: int
    from_idx: int
    to_idx: int
    class Config: populate_by_name = True

class FirstChatInfo(BaseModel):
    first_date: str
    first_sender: str
    first_content: str
    first_10: list[dict] = []

class MonthlySentimentItem(BaseModel):
    month: str
    label: str
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float

class AnnualSummary(BaseModel):
    year: str = ""
    total_messages: int = 0
    total_friends: int = 0
    first_date: str = ""
    last_date: str = ""
    active_days: int = 0
    top_friends: list[str] = []
    night_king: str = ""
    night_king_count: int = 0
    monthly_best: list[dict] = []
    total_chars: int = 0


# ── Helpers ──────────────────────────────────────────────────────

def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
