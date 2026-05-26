export type ReportType = "group_roast" | "relationship";

export type MessageType =
  | "text" | "image" | "emoji" | "file" | "link"
  | "system" | "red_packet" | "transfer" | "unknown";

export type SectionType =
  | "summary" | "dragon_rank" | "heatmap" | "keywords" | "radar"
  | "emoji" | "timeline" | "relationship"
  | "word_specificity" | "word_commonality" | "message_types"
  | "chat_dna" | "chronotype" | "sentiment" | "monthly"
  | "initiative" | "links" | "annual" | "personality_badges" | "predictions";

// ── Messages ───────────────────────────────────────────────────

export interface ChatMessage {
  msg_id: string;
  sender: string;
  ts: string;
  type: MessageType;
  content: string;
  reply_to?: string;
  meta?: Record<string, string | number | boolean>;
}

export interface AnalyzeRequest {
  report_type: ReportType;
  source: "wechat_txt" | "weflow_json" | "paste" | "mock";
  messages: ChatMessage[];
  privacy: { anonymized: boolean; alias_map?: Record<string, string> };
  client_meta: { schema_version: "2026-05-24"; locale: "zh-CN" };
}

export interface AnalyzeResponse {
  report_id: string;
  status: "queued" | "processing" | "done";
  estimated_seconds: number;
}

// ── Stats ──────────────────────────────────────────────────────

export interface ParticipantStat {
  id: string; name: string; avatar: string;
  message_count: number; character_count: number; emoji_count: number;
  image_count?: number; link_count?: number; red_packet_count?: number;
  average_length: number; roast: string;
}

export interface HeatmapCell { day: number; hour: number; value: number; }
export interface KeywordStat { word: string; count: number; tone: "hot" | "soft" | "sharp" | "calm"; }
export interface RadarMetric { label: string; value: number; }
export interface EmojiStat { label: string; value: number; owner?: string; url?: string | null; }
export interface TimelineEvent { id: string; time: string; title: string; body: string; }
export interface RelationshipEdge { from: string; to: string; weight: number; label: string; }
export interface RelationshipMetric { label: string; value: number; caption: string; }

// NEW types
export interface WordSpecificityItem {
  word: string; sender: string; count: number; specificity: number;
}
export interface WordCommonalityItem {
  word: string; count_a: number; count_b: number; commonality: number;
}
export interface MessageTypeBreakdown {
  type: string; label: string; count: number; percentage: number;
}
export interface ChatDNASummary {
  total_messages: number; total_words: number; active_days: number;
  active_months: number; date_range_days: number;
  first_date: string; last_date: string;
  top_hour: number; top_day: number;
  top_emoji: string; top_word: string;
  top_sender_name: string; top_sender_count: number;
  avg_daily_messages: number; longest_gap_days: number;
  late_night_ratio: number;
}
export interface ChronotypeInfo {
  name: string; chronotype: string; peak_hour: number;
  night_ratio: number; morning_ratio: number; label: string;
}
export interface SentimentOverview {
  positive_ratio: number; neutral_ratio: number; negative_ratio: number; label: string;
}
export interface MonthlyActivity { month: string; count: number; label: string; }
export interface InitiativeScore { name: string; score: number; initiations: number; label: string; }
export interface LinkStat { domain: string; count: number; top_sharer: string; }
export interface PersonalityBadge { id: string; name: string; icon: string; description: string; awarded_to: string; }
export interface Prediction { id: string; title: string; body: string; probability: string; }

// EXTRA types
export interface HourlyBin { hour: number; count: number; pct: number; }
export interface WeekdayBin { day: number; label: string; count: number; pct: number; }
export interface YearlyMonthBin { month: number; label: string; count: number; pct: number; }
export interface StreakInfo { length: number; start: string; end: string; }
export interface PeakDayInfo { date: string; count: number; top_sender: string; }
export interface NgramItem { phrase: string; count: number; }
export interface EmojiSpecificityItem { emoji: string; sender: string; count: number; specificity: number; }
export interface InteractionMatrixItem { from: string; to: string; count: number; from_idx: number; to_idx: number; }
export interface FirstChatInfo { first_date: string; first_sender: string; first_content: string; first_10: { sender: string; content: string; ts: string }[]; }
export interface MonthlySentimentItem { month: string; label: string; positive_ratio: number; negative_ratio: number; neutral_ratio: number; }
export interface AnnualSummary { year: string; total_messages: number; total_friends: number; first_date: string; last_date: string; active_days: number; top_friends: string[]; night_king: string; night_king_count: number; monthly_best: { month: string; friend: string; count: number }[]; total_chars: number; }

// EXTRA v2 types
export interface RedPacketOverview { total: number; top_sender: string; top_count: number; participant_count: number; }
export interface RecallStats { total_recalls: number; top_recaller: string; top_count: number; }
export interface AtMentionStat { name: string; count: number; top_mentioner: string; }
export interface FamousQuote { msg_id: string; sender: string; content: string; ts: string; score: number; }
export interface Milestone { type: string; time: string; title: string; body: string; }
export interface EnhancedChatDNA { core_friends: string[]; night_king: string; night_king_count: number; night_king_pct: number; balanced_friend: string; monthly_best: { month: string; friend: string; count: number }[]; top_initiator: string; top_initiator_count: number; initiation_rate: number; avg_reply_seconds: number; fastest_friend: string; fastest_seconds: number; lost_friend: string; lost_friend_early: number; lost_friend_late: number; total_friends: number; total_chars: number; }
export interface ClockFingerprint { name: string; distribution: { hour: number; count: number; pct: number }[]; peak_hour: number; total_msgs: number; }
export interface PerContactSentiment { name: string; positive_count: number; negative_count: number; positive_ratio: number; negative_ratio: number; label: string; }
export interface ExtraBadgeCriteria { badge_id: string; awarded_to: string; value: number; }
export interface DualReportExtras { p1_exclusive_emojis: { emoji: string; count: number }[]; p2_exclusive_emojis: { emoji: string; count: number }[]; p1_message_count: number; p2_message_count: number; p1_char_count: number; p2_char_count: number; monthly: { month: string; label: string; p1_count: number; p2_count: number }[]; first_year_chat: string; }

export interface ReportStats {
  participants: ParticipantStat[];
  heatmap: HeatmapCell[];
  keywords: KeywordStat[];
  radar: RadarMetric[];
  emojis: EmojiStat[];
  timeline: TimelineEvent[];
  relationship_edges: RelationshipEdge[];
  relationship_metrics?: RelationshipMetric[];
  // NEW
  word_specificity: WordSpecificityItem[];
  word_commonality: WordCommonalityItem[];
  message_type_breakdown: MessageTypeBreakdown[];
  chat_dna?: ChatDNASummary;
  chronotypes: ChronotypeInfo[];
  sentiment_overview?: SentimentOverview;
  monthly_activity: MonthlyActivity[];
  initiative_scores: InitiativeScore[];
  link_stats: LinkStat[];
  personality_badges: PersonalityBadge[];
  predictions: Prediction[];
  // EXTRA
  hourly_distribution: HourlyBin[];
  weekday_distribution: WeekdayBin[];
  yearly_monthly: YearlyMonthBin[];
  streak?: StreakInfo;
  peak_day?: PeakDayInfo;
  ngrams: NgramItem[];
  emoji_specificity: EmojiSpecificityItem[];
  interaction_matrix: InteractionMatrixItem[];
  first_chat?: FirstChatInfo;
  monthly_sentiment: MonthlySentimentItem[];
  annual_summary?: AnnualSummary;
  // EXTRA v2
  emoji_commonality: { emoji: string; count_a: number; count_b: number; commonality: number }[];
  emoji_time_distribution: { hour: number; count: number; pct: number }[];
  message_type_evolution: Record<string, any>[];
  red_packet_overview?: RedPacketOverview;
  link_time_trends: { month: string; label: string; count: number }[];
  enhanced_chat_dna?: EnhancedChatDNA;
  clock_fingerprints: ClockFingerprint[];
  per_contact_sentiment: PerContactSentiment[];
  extra_badge_criteria: ExtraBadgeCriteria[];
  relationship_milestones: Milestone[];
  recall_stats?: RecallStats;
  famous_quotes: FamousQuote[];
  dual_report_extras?: DualReportExtras;
  at_mention_stats: AtMentionStat[];
  send_ratio: { name: string; count: number; pct: number; avatar: string }[];
}

// ── Report ─────────────────────────────────────────────────────

export interface ReportSection {
  id: string; type: SectionType; heading: string; body: string;
  chart_ref?: keyof ReportStats;
}
export interface QuoteItem { id: string; speaker: string; text: string; comment: string; icon: string; }

export interface ReportPayload {
  report_id: string; report_type: ReportType; created_at: string;
  title: string; tagline: string;
  hero: { kicker: string; quote: string; visual: string };
  tags: string[]; sections: ReportSection[]; quotes: QuoteItem[];
  stats: ReportStats;
  share: { slug?: string; hook: string; watermark: string };
}

export interface SharePayload { slug: string; url: string; report: ReportPayload; }

export type ExportFormat = "json" | "txt" | "html" | "csv" | "xlsx";
export interface ExportPayload { content: string; content_type: string; filename: string; }
