export type ReportType = "group_roast" | "relationship";

export type MessageType =
  | "text"
  | "image"
  | "emoji"
  | "file"
  | "link"
  | "system"
  | "red_packet"
  | "transfer"
  | "unknown";

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
  source: "wechat_txt" | "paste" | "mock";
  messages: ChatMessage[];
  privacy: {
    anonymized: boolean;
    alias_map?: Record<string, string>;
  };
  client_meta: {
    schema_version: "2026-05-24";
    locale: "zh-CN";
  };
}

export interface AnalyzeResponse {
  report_id: string;
  status: "queued" | "processing" | "done";
  estimated_seconds: number;
}

export interface ParticipantStat {
  id: string;
  name: string;
  avatar: string;
  message_count: number;
  character_count: number;
  emoji_count: number;
  average_length: number;
  roast: string;
}

export interface HeatmapCell {
  day: number;
  hour: number;
  value: number;
}

export interface KeywordStat {
  word: string;
  count: number;
  tone: "hot" | "soft" | "sharp" | "calm";
}

export interface RadarMetric {
  label: string;
  value: number;
}

export interface EmojiStat {
  label: string;
  value: number;
  owner?: string;
}

export interface TimelineEvent {
  id: string;
  time: string;
  title: string;
  body: string;
}

export interface RelationshipEdge {
  from: string;
  to: string;
  weight: number;
  label: string;
}

export interface RelationshipMetric {
  label: string;
  value: number;
  caption: string;
}

export interface QuoteItem {
  id: string;
  speaker: string;
  text: string;
  comment: string;
  icon: string;
}

export interface ReportSection {
  id: string;
  type:
    | "summary"
    | "dragon_rank"
    | "heatmap"
    | "keywords"
    | "radar"
    | "emoji"
    | "timeline"
    | "relationship";
  heading: string;
  body: string;
  chart_ref?: keyof ReportStats;
}

export interface ReportStats {
  participants: ParticipantStat[];
  heatmap: HeatmapCell[];
  keywords: KeywordStat[];
  radar: RadarMetric[];
  emojis: EmojiStat[];
  timeline: TimelineEvent[];
  relationship_edges: RelationshipEdge[];
  relationship_metrics?: RelationshipMetric[];
}

export interface ReportPayload {
  report_id: string;
  report_type: ReportType;
  created_at: string;
  title: string;
  tagline: string;
  hero: {
    kicker: string;
    quote: string;
    visual: string;
  };
  tags: string[];
  sections: ReportSection[];
  quotes: QuoteItem[];
  stats: ReportStats;
  share: {
    slug?: string;
    hook: string;
    watermark: string;
  };
}

export interface SharePayload {
  slug: string;
  url: string;
  report: ReportPayload;
}
