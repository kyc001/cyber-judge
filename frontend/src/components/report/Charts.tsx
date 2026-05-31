import type { CSSProperties } from "react";
import type {
  AnnualSummary, AtMentionStat,
  ChatDNASummary, ChronotypeInfo, ClockFingerprint,
  DualReportExtras, EmojiStat, EmojiSpecificityItem, EnhancedChatDNA,
  FamousQuote, FirstChatInfo, HeatmapCell, HourlyBin,
  InitiativeScore, InteractionMatrixItem, KeywordStat, LinkStat,
  MessageTypeBreakdown, Milestone, MonthlyActivity, MonthlySentimentItem,
  ParticipantStat, PeakDayInfo,
  PersonalityBadge, Prediction, RadarMetric,
  RecallStats, RedPacketOverview, RelationshipEdge, RelationshipMetric,
  SentimentOverview, StreakInfo, TimelineEvent, WeekdayBin,
  WordCommonalityItem, WordSpecificityItem, YearlyMonthBin,
} from "../../contracts/report";
import { clamp, formatCount } from "../../utils/format";

const panelGridStyle: CSSProperties = {
  display: "grid",
  gap: "0.85rem",
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
};

const panelCardStyle: CSSProperties = {
  background: "var(--report-panel, var(--bg-secondary))",
  border: "1px solid var(--report-line, var(--border-default))",
  borderRadius: "var(--radius-sm)",
  padding: "0.95rem",
};

const compactRowStyle: CSSProperties = {
  alignItems: "center",
  display: "flex",
  gap: "0.75rem",
  justifyContent: "space-between",
};

const miniBarTrackStyle: CSSProperties = {
  background: "var(--report-soft, var(--bg-tertiary))",
  borderRadius: 999,
  height: 8,
  overflow: "hidden",
};

// ── Original Charts ────────────────────────────────────────────

export function DragonRanking({ participants }: { participants: ParticipantStat[] }) {
  const max = Math.max(...participants.map((item) => item.message_count), 1);
  return (
    <div className="ranking-list">
      {participants.map((item, index) => (
        <div className="ranking-row" key={item.id}>
          <div className={`avatar avatar-${index + 1}`}>{item.avatar}</div>
          <div className="ranking-copy">
            <div className="ranking-head">
              <strong>{item.name}</strong>
              <span>{formatCount(item.message_count)} 条</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(item.message_count / max) * 100}%` }} />
            </div>
            <p>{item.roast}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function Heatmap({ cells }: { cells: HeatmapCell[] }) {
  return (
    <div className="heatmap-wrap" aria-label="24小时x7天热力图">
      <div className="heatmap-axis"><span>周一</span><span>周三</span><span>周五</span><span>周日</span></div>
      <div className="heatmap-grid">
        {cells.map((cell) => (
          <span className="heat-cell" key={`${cell.day}-${cell.hour}`}
            style={{ opacity: 0.15 + clamp(cell.value, 0, 1) * 0.85 }}
            title={`${cell.day + 1} ${cell.hour}:00 — ${Math.round(cell.value * 100)}%`} />
        ))}
      </div>
      <div className="heatmap-hours"><span>00:00</span><span>12:00</span><span>23:00</span></div>
    </div>
  );
}

export function KeywordCloud({ keywords }: { keywords: KeywordStat[] }) {
  const max = Math.max(...keywords.map((item) => item.count), 1);
  return (
    <div className="keyword-cloud">
      {keywords.map((item) => (
        <span className={`keyword keyword-${item.tone}`} key={item.word}
          style={{ fontSize: `${0.92 + (item.count / max) * 1.55}rem` }}>
          {item.word}
        </span>
      ))}
    </div>
  );
}

export function RadarChart({ metrics }: { metrics: RadarMetric[] }) {
  if (metrics.length === 0) return <p className="muted">暂无特征数据。</p>;
  return (
    <div style={panelGridStyle}>
      {metrics.map((metric) => (
        <div key={metric.label} style={panelCardStyle}>
          <strong>{metric.label}</strong>
          <p className="muted" style={{ margin: "0.45rem 0 0" }}>聊天记录里有对应行为信号。</p>
        </div>
      ))}
    </div>
  );
}

// WeChat sticker shortcode → closest Unicode emoji for visual display.
// WeChat stickers are proprietary; these are the nearest platform-native emoji.
// Official WeChat sticker mappings. Source: WeChat system emoji catalog.
// Chinese bracket names are display aliases for the same English shortcodes.
// Normalize: Chinese name → English shortcode → Unicode emoji.
function stickerLabelToEmoji(label: string): string {
  const key = label.startsWith("[") ? label : `[${label}]`;

  // Normalize Chinese display names to English shortcodes (official mapping)
  const normalize: Record<string, string> = {
    "[微笑]": "[Smile]",   "[撇嘴]": "[Grimace]", "[色]": "[Drool]",
    "[发呆]": "[Scowl]",   "[得意]": "[CoolGuy]", "[流泪]": "[Sob]",
    "[害羞]": "[Shy]",     "[闭嘴]": "[Silent]",  "[睡]": "[Sleep]",
    "[大哭]": "[Cry]",     "[尴尬]": "[Awkward]", "[发怒]": "[Angry]",
    "[调皮]": "[Tongue]",  "[呲牙]": "[Grin]",    "[惊讶]": "[Surprise]",
    "[难过]": "[Frown]",   "[酷]": "[CoolGuy]",   "[冷汗]": "[Blush]",
    "[抓狂]": "[Scream]",  "[吐]": "[Puke]",      "[偷笑]": "[Chuckle]",
    "[愉快]": "[Joyful]",  "[白眼]": "[Slight]",   "[傲慢]": "[Smug]",
    "[困]": "[Drowsy]",    "[惊恐]": "[Panic]",    "[流汗]": "[Sweat]",
    "[憨笑]": "[Laugh]",   "[悠闲]": "[Commando]", "[奋斗]": "[Determined]",
    "[咒骂]": "[Scold]",   "[疑问]": "[Shocked]",  "[嘘]": "[Shhh]",
    "[晕]": "[Dizzy]",     "[衰]": "[Toasted]",    "[骷髅]": "[Skull]",
    "[敲打]": "[Hammer]",  "[再见]": "[Wave]",     "[擦汗]": "[Speechless]",
    "[抠鼻]": "[NosePick]","[鼓掌]": "[Clap]",     "[坏笑]": "[Trick]",
    "[左哼哼]": "[Bah！L]","[右哼哼]": "[Bah！R]",  "[哈欠]": "[Yawn]",
    "[鄙视]": "[Pooh-pooh]","[委屈]": "[Shrunken]","[快哭了]": "[TearingUp]",
    "[阴险]": "[Sly]",     "[亲亲]": "[Kiss]",     "[吓]": "[Wrath]",
    "[可怜]": "[Whimper]", "[菜刀]": "[Cleaver]",  "[西瓜]": "[Watermelon]",
    "[啤酒]": "[Beer]",    "[咖啡]": "[Coffee]",   "[饭]": "[Rice]",
    "[猪头]": "[Pig]",     "[玫瑰]": "[Rose]",     "[凋谢]": "[Wilt]",
    "[嘴唇]": "[Lips]",    "[爱心]": "[Heart]",    "[心碎]": "[BrokenHeart]",
    "[蛋糕]": "[Cake]",    "[闪电]": "[Lightning]","[炸弹]": "[Bomb]",
    "[便便]": "[Poop]",    "[月亮]": "[Moon]",     "[太阳]": "[Sun]",
    "[礼物]": "[Gift]",    "[拥抱]": "[Hug]",      "[强]": "[ThumbsUp]",
    "[弱]": "[ThumbsDown]","[握手]": "[Shake]",    "[胜利]": "[Peace]",
    "[抱拳]": "[Fight]",   "[勾引]": "[Beckon]",   "[拳头]": "[Fist]",
    "[OK]": "[OK]",        "[发抖]": "[Tremble]",  "[转圈]": "[Twirl]",
    "[怄火]": "[Aaagh!]",  "[跳跳]": "[Waddle]",
    // Later additions
    "[破涕为笑]": "[Joyful]","[奸笑]": "[Smirk]",  "[旺柴]": "[Doge]",
    "[无语]": "[Speechless]","[捂脸]": "[Facepalm]","[合十]": "[Worship]",
    "[吃瓜]": "[Onlooker]","[加油]": "[GoForIt]",  "[汗]": "[Sweat]",
    "[天啊]": "[OMG]",     "[好的]": "[OK]",       "[打脸]": "[MyBad]",
    "[哇]": "[Wow]",       "[红包]": "[Packet]",
  };
  const normalized = normalize[key] || key;

  // English shortcode → Unicode emoji
  const map: Record<string, string> = {
    "[Aaagh!]": "😫",    "[Angry]": "😠",      "[Awkward]": "😅",
    "[Bah！L]": "💢",    "[Bah！R]": "💢",     "[Beckon]": "🫴",
    "[Beer]": "🍺",      "[Blush]": "😳",       "[Bomb]": "💣",
    "[BrokenHeart]": "💔","[Cake]": "🎂",       "[Chuckle]": "🤭",
    "[Clap]": "👏",       "[Cleaver]": "🔪",     "[Coffee]": "☕",
    "[Commando]": "😌",  "[CoolGuy]": "😎",     "[Cry]": "😭",
    "[Determined]": "💪", "[Dizzy]": "😵",       "[Doge]": "🐶",
    "[Drool]": "😍",      "[Drowsy]": "😪",      "[Duh]": "🙄",
    "[Emm]": "🤨",       "[Facepalm]": "🤦",     "[Fight]": "💪",
    "[Fist]": "👊",       "[Frown]": "☹️",       "[Gift]": "🎁",
    "[GoForIt]": "💪",   "[Grimace]": "😕",     "[Grin]": "😁",
    "[Hammer]": "🤛",    "[Heart]": "❤️",       "[Hug]": "🫂",
    "[Joyful]": "😂",     "[Kiss]": "😘",        "[Laugh]": "😆",
    "[Lightning]": "⚡",  "[Lips]": "💋",        "[Lol]": "😆",
    "[Love]": "😍",       "[Luck]": "🤞",        "[Moon]": "🌙",
    "[MyBad]": "🤕",      "[NosePick]": "🫣",   "[OK]": "👌",          "[OMG]": "😱",
    "[Onlooker]": "🍉",   "[Packet]": "🧧",      "[Panic]": "😱",
    "[Party]": "🎉",      "[Peace]": "✌️",       "[Pig]": "🐷",
    "[Pooh-pooh]": "😒", "[Poop]": "💩",        "[Puke]": "🤮",
    "[Rice]": "🍚",       "[Rose]": "🌹",        "[Scold]": "😤",
    "[Scowl]": "😶",      "[Scream]": "😱",      "[Shake]": "🤝",
    "[Shame]": "😳",      "[Shhh]": "🤫",        "[Shocked]": "🤔",
    "[Shrunken]": "🥺",  "[Shy]": "😊",         "[Sick]": "🤒",
    "[Silent]": "🤐",     "[Skull]": "💀",       "[Sleep]": "😴",
    "[Slight]": "🙄",     "[Sly]": "😏",         "[Smile]": "🙂",
    "[Smirk]": "😏",      "[Smug]": "😤",        "[Sob]": "😢",
    "[Speechless]": "😶", "[Star]": "⭐",         "[Sun]": "☀️",
    "[Surprise]": "😲",   "[Sweat]": "😅",       "[TearingUp]": "🥲",
    "[ThumbsDown]": "👎", "[ThumbsUp]": "👍",    "[Toasted]": "😞",
    "[Tongue]": "😜",     "[Tremble]": "🫨",     "[Trick]": "😈",
    "[Twirl]": "💃",      "[Waddle]": "🐧",      "[Watermelon]": "🍉",
    "[Wave]": "👋",       "[Whimper]": "🥺",     "[Wilt]": "🥀",
    "[Wink]": "😉",       "[Worship]": "🙏",     "[Wow]": "😮",
    "[Wrath]": "😱",      "[Yawn]": "🥱",        "[Yeah!]": "✌️",
    "[Blessing]": "🧧",   "[Fireworks]": "🎉",
  };
  return map[normalized] || "";
}

function renderStickerLabel(label: string): string {
  const emoji = stickerLabelToEmoji(label);
  if (emoji) return emoji;
  if (label.startsWith("[") && label.endsWith("]")) return label.slice(1, -1);
  return label;
}

const NON_EMOJI_LABELS = new Set([
  "[图片]", "[视频]", "[语音]", "[文件]", "[链接]", "[聊天记录]", "[名片]", "[消息]",
  "[表情]", "[表情包]", "[动画表情]",
]);

function isDisplayableSticker(label: string, url?: string | null): boolean {
  return Boolean(url) || !NON_EMOJI_LABELS.has(label);
}

function stickerVisualKey(label: string, url?: string | null): string {
  const trimmedUrl = url?.trim();
  if (trimmedUrl) return `url:${trimmedUrl}`;
  return `text:${renderStickerLabel(label)}`;
}

function buildStickerUrlMaps(catalog: EmojiStat[]) {
  const byLabel = new Map<string, string>();
  const byDisplay = new Map<string, string>();
  for (const item of catalog) {
    if (!item.url) continue;
    byLabel.set(item.label, item.url);
    byDisplay.set(renderStickerLabel(item.label), item.url);
  }
  return { byDisplay, byLabel };
}

function resolveStickerUrl(
  label: string,
  url: string | null | undefined,
  maps?: ReturnType<typeof buildStickerUrlMaps>,
): string | null {
  if (url) return url;
  if (!maps) return null;
  return maps.byLabel.get(label) || maps.byDisplay.get(renderStickerLabel(label)) || null;
}

function StickerVisual({
  label,
  textClassName = "emoji-label-text",
  url,
  size = 64,
}: {
  label: string;
  textClassName?: string;
  url?: string | null;
  size?: number;
}) {
  if (url) {
    const sizeStyle = { height: size, width: size };
    return (
      <span className="emoji-sticker-wrap" style={sizeStyle}>
        <img
          className="emoji-sticker-img"
          src={url}
          alt={renderStickerLabel(label) || "表情包"}
          loading="lazy"
          referrerPolicy="no-referrer"
          style={sizeStyle}
        />
      </span>
    );
  }
  return <span className={textClassName}>{renderStickerLabel(label)}</span>;
}

export function EmojiBoard({ emojis }: { emojis: EmojiStat[] }) {
  if (!emojis || emojis.length === 0) {
    return <p className="muted">暂无表情包数据。</p>;
  }
  const merged = Array.from(emojis.filter((item) => isDisplayableSticker(item.label, item.url)).reduce((map, item) => {
    const key = stickerVisualKey(item.label, item.url);
    const current = map.get(key);
    if (current) {
      current.value += item.value;
      current.owner ||= item.owner;
      current.url ||= item.url;
    } else {
      map.set(key, { ...item });
    }
    return map;
  }, new Map<string, EmojiStat>()).values()).sort((a, b) => b.value - a.value);
  if (merged.length === 0) {
    return <p className="muted">暂无表情包数据。</p>;
  }
  return (
    <div className="emoji-board">
      {merged.map((item, index) => (
        <div className="emoji-tile" key={stickerVisualKey(item.label, item.url)}>
          <span className="emoji-rank">#{index + 1}</span>
          <StickerVisual label={item.label} url={item.url} />
          <p>{formatCount(item.value)} 次</p>
        </div>
      ))}
    </div>
  );
}

export function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="timeline">
      {events.map((event) => (
        <article className="timeline-item" key={event.id}>
          <time>{event.time}</time>
          <div><strong>{event.title}</strong><p>{event.body}</p></div>
        </article>
      ))}
    </div>
  );
}

export function RelationshipMap({ edges }: { edges: RelationshipEdge[] }) {
  if (edges.length === 0) return <p className="muted">暂无关系数据。</p>;
  return (
    <div className="relationship-map">
      {edges.map((edge) => (
        <div className="relationship-edge" key={`${edge.from}-${edge.to}-${edge.label}`}>
          <span>{edge.from}</span>
          <div className="edge-line" style={{ height: `${8 + edge.weight * 18}px` }} />
          <span>{edge.to}</span>
          <strong>{edge.label}</strong>
        </div>
      ))}
    </div>
  );
}

export function RelationshipScoreboard({ metrics }: { metrics: RelationshipMetric[] }) {
  if (metrics.length === 0) return null;
  return (
    <div className="relationship-scoreboard">
      {metrics.map((metric) => (
        <article className="relationship-score" key={metric.label}>
          <span>{metric.label}</span>
          <p>{metric.caption}</p>
        </article>
      ))}
    </div>
  );
}

// ── NEW: Word Specificity (WechatVisualization) ─────────────────

export function WordSpecificityChart({ items }: { items: WordSpecificityItem[] }) {
  if (items.length === 0) return <p className="muted">暂无词汇特异性数据。</p>;
  // Group by sender
  const bySender: Record<string, WordSpecificityItem[]> = {};
  for (const item of items) {
    if (!bySender[item.sender]) bySender[item.sender] = [];
    if (bySender[item.sender].length < 5) bySender[item.sender].push(item);
  }
  return (
    <div className="specificity-grid">
      {Object.entries(bySender).map(([sender, words]) => (
        <div className="specificity-card" key={sender}>
          <h4>{sender} 的口头禅</h4>
          {words.map((w) => (
            <div className="specificity-row" key={`${sender}-${w.word}`}>
              <span className="spec-word">{w.word}</span>
              <span className="spec-count">{w.count}次</span>
              <div className="spec-bar-track">
                <div className="spec-bar-fill" style={{
                  width: `${clamp(Math.abs(w.specificity) * 40, 0, 100)}%`,
                  background: w.specificity > 0 ? '#f26b5e' : '#1984c4'
                }} />
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ── NEW: Word Commonality (WechatVisualization) ─────────────────

export function WordCommonalityChart({ items }: { items: WordCommonalityItem[] }) {
  if (items.length === 0) return <p className="muted">暂无共同词汇数据。</p>;
  const max = Math.max(...items.map(i => i.commonality), 1);
  return (
    <div className="commonality-list">
      {items.slice(0, 10).map((item) => (
        <div className="commonality-row" key={item.word}>
          <span className="com-word">{item.word}</span>
          <div className="com-counts">
            <span>A: {item.count_a}</span>
            <div className="com-bar-track">
              <div className="com-bar-fill" style={{ width: `${(item.commonality / max) * 100}%` }} />
            </div>
            <span>B: {item.count_b}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── NEW: Message Type Breakdown (echotrace) ─────────────────────

export function MessageTypeChart({ types }: { types: MessageTypeBreakdown[] }) {
  if (types.length === 0) return <p className="muted">暂无消息类型数据。</p>;
  const max = Math.max(...types.map(t => t.count), 1);
  const colors: Record<string, string> = {
    text: '#1984c4', image: '#f26b5e', emoji: '#f9a825', link: '#7c4dff',
    file: '#4caf50', red_packet: '#e91e63', transfer: '#ff9800',
    system: '#9e9e9e', unknown: '#607d8b',
  };
  return (
    <div className="msg-type-chart">
      {types.map((t) => (
        <div className="msg-type-row" key={t.type}>
          <span className="type-label">{t.label}</span>
          <div className="type-bar-track">
            <div className="type-bar-fill" style={{
              width: `${(t.count / max) * 100}%`,
              background: colors[t.type] || '#1984c4'
            }} />
          </div>
          <span className="type-pct">{t.percentage}%</span>
          <span className="type-count">{formatCount(t.count)}</span>
        </div>
      ))}
    </div>
  );
}

// ── NEW: Chat DNA Card (welink, whatsapp-wrapped-v3) ────────────

export function ChatDNACard({ dna }: { dna: ChatDNASummary }) {
  const dayNames = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
  return (
    <div className="chat-dna-card">
      <div className="dna-hero">
        <span className="dna-big-number">{dna.total_messages.toLocaleString()}</span>
        <span className="dna-unit">条消息</span>
      </div>
      <div className="dna-stats">
        <div className="dna-stat">
          <strong>{dna.total_words.toLocaleString()}</strong>
          <span>总字数</span>
        </div>
        <div className="dna-stat">
          <strong>{dna.active_days}</strong>
          <span>活跃天数</span>
        </div>
        <div className="dna-stat">
          <strong>{dna.date_range_days}</strong>
          <span>跨越天数</span>
        </div>
        <div className="dna-stat">
          <strong>{dna.avg_daily_messages}</strong>
          <span>日均消息</span>
        </div>
      </div>
      <div className="dna-insights">
        <div className="dna-insight">
          🕐 黄金时段：<strong>{dna.top_hour}:00</strong>
        </div>
        <div className="dna-insight">
          📅 最爱：<strong>{dayNames[dna.top_day] || dna.top_day}</strong>
        </div>
        <div className="dna-insight">
          🌙 深夜占比：<strong>{dna.late_night_ratio}%</strong>
        </div>
        <div className="dna-insight">
          👑 龙王：<strong>{dna.top_sender_name}</strong>（{dna.top_sender_count}条）
        </div>
        <div className="dna-insight">
          💬 高频词：<strong>{dna.top_word || '—'}</strong>
        </div>
        <div className="dna-insight">
          😂 最爱表情：<strong>{dna.top_emoji || '—'}</strong>
        </div>
      </div>
      <div className="dna-timeline">
        <span>{dna.first_date}</span>
        <div className="dna-line" />
        <span>{dna.last_date}</span>
      </div>
    </div>
  );
}

// ── NEW: Chronotype (whatsapp-wrapped-v3) ───────────────────────

export function ChronotypeList({ chronotypes }: { chronotypes: ChronotypeInfo[] }) {
  if (chronotypes.length === 0) return <p className="muted">暂无作息数据。</p>;
  const icons: Record<string, string> = { night_owl: "🦉", early_bird: "🌅", afternoon_peak: "☀️", balanced: "🌤️" };
  return (
    <div className="chronotype-grid">
      {chronotypes.map((ch) => (
        <div className={`chronotype-card chronotype-${ch.chronotype}`} key={ch.name}>
          <span className="chrono-icon">{icons[ch.chronotype] || "🕐"}</span>
          <strong>{ch.name}</strong>
          <span className="chrono-badge">{ch.label}</span>
          <div className="chrono-stats">
            <span>高峰 {String(ch.peak_hour).padStart(2, "0")}:00</span>
            <span>🌙 {ch.night_ratio}%</span>
            <span>🌅 {ch.morning_ratio}%</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── NEW: Sentiment Gauge (chat-analytics) ───────────────────────

export function SentimentGauge({ sentiment }: { sentiment: SentimentOverview }) {
  const pos = sentiment.positive_ratio;
  const neu = sentiment.neutral_ratio;
  const neg = sentiment.negative_ratio;

  return (
    <div className="sentiment-gauge">
      <div className="sentiment-bar">
        <div className="sentiment-pos" style={{ width: `${Math.max(pos, pos > 0 ? 2 : 0)}%` }}
          title={`积极 ${pos}%`}>{pos > 0 ? `${pos}%` : ""}</div>
        <div className="sentiment-neu" style={{ width: `${Math.max(neu, neu > 0 ? 2 : 0)}%` }}
          title={`中性 ${neu}%`}>{neu > 0 ? `${neu}%` : ""}</div>
        <div className="sentiment-neg" style={{ width: `${Math.max(neg, neg > 0 ? 2 : 0)}%` }}
          title={`消极 ${neg}%`}>{neg > 0 ? `${neg}%` : ""}</div>
      </div>
      <div className="sentiment-labels">
        <span>😊 积极 {pos}%</span>
        <span>😐 中性 {neu}%</span>
        <span>😤 消极 {neg}%</span>
      </div>
      <p className="sentiment-verdict">{sentiment.label}</p>
    </div>
  );
}

// ── NEW: Monthly Activity (AnnualReport) ─────────────────────────

export function MonthlyActivityChart({ data }: { data: MonthlyActivity[] }) {
  if (data.length === 0) return <p className="muted">暂无月度数据。</p>;
  const max = Math.max(...data.map(d => d.count), 1);
  return (
    <div className="monthly-chart">
      {data.slice(-12).map((m) => (
        <div className="monthly-bar-col" key={m.month}>
          <span className="monthly-count">{m.count}</span>
          <div className="monthly-bar-track">
            <div className="monthly-bar-fill" style={{ height: `${(m.count / max) * 100}%` }} />
          </div>
          <span className="monthly-label">{m.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── NEW: Initiative Ranking (whatsapp-wrapped-v3) ───────────────

export function InitiativeRanking({ scores }: { scores: InitiativeScore[] }) {
  if (scores.length === 0) return <p className="muted">暂无话题发起数据。</p>;
  const max = Math.max(...scores.map(s => s.score), 1);
  return (
    <div className="initiative-list">
      {scores.slice(0, 8).map((s) => (
        <div className="initiative-row" key={s.name}>
          <span className="init-name">{s.name}</span>
          <div className="init-bar-track">
            <div className="init-bar-fill" style={{ width: `${(s.score / max) * 100}%` }} />
          </div>
          <span className="init-score">{s.initiations}次</span>
          <span className="init-label">{s.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── NEW: Link Stats (chat-analytics) ────────────────────────────

export function LinkStatsList({ links }: { links: LinkStat[] }) {
  if (links.length === 0) return <p className="muted">暂无链接分享数据。</p>;
  return (
    <div className="link-stats-list">
      {links.map((l) => (
        <div className="link-stat-row" key={l.domain}>
          <span className="link-domain">{l.domain}</span>
          <span className="link-count">{l.count}次</span>
          <span className="link-sharer">主力: {l.top_sharer}</span>
        </div>
      ))}
    </div>
  );
}

// ── NEW: Personality Badges (whatsapp-wrapped-v3) ───────────────

export function PersonalityBadgeGrid({ badges }: { badges: PersonalityBadge[] }) {
  if (badges.length === 0) return <p className="muted">暂无荣誉勋章。</p>;
  return (
    <div className="badge-grid">
      {badges.map((b) => (
        <div className="badge-card" key={b.id}>
          <span className="badge-icon">{b.icon}</span>
          <div className="badge-info">
            <strong>{b.name}</strong>
            <span className="badge-awardee">🏅 {b.awarded_to}</span>
            <p>{b.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── NEW: Predictions (whatsapp-wrapped-v3) ──────────────────────



// ── EXTRA: Streak Card ──────────────────────────────────────────

export function StreakCard({ streak }: { streak: StreakInfo }) {
  if (!streak || streak.length < 2) return null;
  return (
    <div className="streak-card">
      <span className="streak-number">{streak.length}</span>
      <span className="streak-unit">天连续聊天</span>
      <span className="streak-range">{streak.start} ~ {streak.end}</span>
    </div>
  );
}



// ── EXTRA: First Chat Card ──────────────────────────────────────

export function FirstChatCard({ data }: { data: FirstChatInfo }) {
  if (!data || !data.first_date) return null;
  return (
    <div className="first-chat-card">
      <div className="fc-date">{data.first_date}</div>
      <div className="fc-sender">{data.first_sender} 说了第一句话</div>
      <blockquote>「{data.first_content}」</blockquote>
      {data.first_10 && data.first_10.length > 0 && (
        <div className="fc-early">
          <span>最初的对话:</span>
          {data.first_10.slice(0, 5).map((m, i) => (
            <p key={i}><strong>{m.sender}:</strong> {m.content}</p>
          ))}
        </div>
      )}
    </div>
  );
}

// ── EXTRA: Monthly Sentiment Trend ──────────────────────────────

export function MonthlySentimentTrend({ data }: { data: MonthlySentimentItem[] }) {
  if (data.length === 0) return <p className="muted">暂无情绪趋势数据。</p>;
  const months = data.slice(-12);
  return (
    <div className="sentiment-trend">
      <div className="sentiment-trend-chart">
        {months.map((m) => (
          <div className="st-bar-group" key={m.month} title={`${m.label}: 积极${m.positive_ratio}% 消极${m.negative_ratio}%`}>
            <div className="st-pos" style={{ height: `${m.positive_ratio}%` }} />
            <div className="st-neg" style={{ height: `${m.negative_ratio}%` }} />
          </div>
        ))}
      </div>
      <div className="st-labels">
        {months.map((m) => <span key={m.month}>{m.label}</span>)}
      </div>
      <div className="st-legend">
        <span>🟢 积极</span><span>🔴 消极</span>
      </div>
    </div>
  );
}

// ── EXTRA: Annual Summary Card ──────────────────────────────────

// ── EXTRA: Emoji Specificity ────────────────────────────────────

export function EmojiSpecificityChart({ catalog = [], items }: { catalog?: EmojiStat[]; items: EmojiSpecificityItem[] }) {
  if (items.length === 0) return <p className="muted">暂无表情特异性数据。</p>;
  const urlMaps = buildStickerUrlMaps(catalog);
  const bySender: Record<string, EmojiSpecificityItem[]> = {};
  for (const item of items) {
    const url = resolveStickerUrl(item.emoji, item.url, urlMaps);
    if (!isDisplayableSticker(item.emoji, url)) continue;
    const key = stickerVisualKey(item.emoji, url);
    const senderItems = bySender[item.sender] || [];
    const current = senderItems.find((entry) =>
      stickerVisualKey(entry.emoji, resolveStickerUrl(entry.emoji, entry.url, urlMaps)) === key
    );
    if (current) {
      current.count += item.count;
      current.url ||= url;
      if (Math.abs(item.specificity) > Math.abs(current.specificity)) {
        current.specificity = item.specificity;
      }
    } else {
      senderItems.push({ ...item, url });
      bySender[item.sender] = senderItems;
    }
  }
  return (
    <div className="emoji-specificity-grid">
      {Object.entries(bySender).map(([sender, emojis]) => (
        <div className="emoji-spec-card" key={sender}>
          <h4>{sender} 的标志性表情</h4>
          <div className="emoji-spec-list">
            {emojis
              .sort((a, b) => Math.abs(b.specificity) - Math.abs(a.specificity) || b.count - a.count)
              .slice(0, 5)
              .map(e => {
                const url = resolveStickerUrl(e.emoji, e.url, urlMaps);
                return (
                  <span key={`${e.emoji}-${url || ""}`} className="emoji-spec-item" title={`${e.count}次, 特异性${e.specificity}`}>
                    <StickerVisual label={e.emoji} url={url} size={28} textClassName="" /> <small>×{e.count}</small>
                  </span>
                );
              })}
          </div>
        </div>
      ))}
    </div>
  );
}


// ── EXTRA v2: Enhanced DNA ──────────────────────────────────────

export function EnhancedDNACard({ dna }: { dna: EnhancedChatDNA }) {
  return (
    <div className="enhanced-dna">
      <div className="edna-row">
        <div className="edna-item"><strong>{dna.total_friends}</strong><span>联系人</span></div>
        <div className="edna-item"><strong>{(dna.total_chars / (dna.total_friends || 1)).toFixed(0)}</strong><span>字/人</span></div>
        <div className="edna-item"><strong>{dna.initiation_rate}%</strong><span>主动率</span></div>
        <div className="edna-item"><strong>{dna.avg_reply_seconds}s</strong><span>均回复</span></div>
      </div>
      <div className="edna-highlights">
        <span>🌙 深夜之王: <strong>{dna.night_king}</strong> ({dna.night_king_count}条凌晨消息, 占{dna.night_king_pct}%)</span>
        <span>⚡ 最快回复: <strong>{dna.fastest_friend}</strong> (均{dna.fastest_seconds}s)</span>
        <span>🚀 话题发动机: <strong>{dna.top_initiator}</strong> ({dna.top_initiator_count}次发起)</span>
        {dna.balanced_friend && <span>⚖️ 最均衡: <strong>{dna.balanced_friend}</strong></span>}
        {dna.lost_friend && <span>📉 降温预警: <strong>{dna.lost_friend}</strong> (活跃{dna.lost_friend_early}→{dna.lost_friend_late}条)</span>}
      </div>
    </div>
  );
}

// ── EXTRA v2: Clock Fingerprint Grid ────────────────────────────

export function ClockFingerprintGrid({ fingerprints }: { fingerprints: ClockFingerprint[] }) {
  if (fingerprints.length === 0) return <p className="muted">暂无指纹数据。</p>;
  return (
    <div className="fingerprint-grid">
      {fingerprints.slice(0, 6).map((fp) => {
        const max = Math.max(...fp.distribution.map(d => d.count), 1);
        return (
          <div className="fingerprint-card" key={fp.name}>
            <div className="fp-header">
              <strong>{fp.name}</strong>
              <span>高峰 {fp.peak_hour}:00</span>
            </div>
            <div className="fp-bars">
              {fp.distribution.map((d) => (
                <div className="fp-bar-col" key={d.hour} title={`${d.hour}:00 - ${d.count}条`}>
                  <div className="fp-bar-fill" style={{ height: `${(d.count / max) * 100}%` }} />
                </div>
              ))}
            </div>
            <div className="fp-labels"><span>0h</span><span>12h</span><span>23h</span></div>
          </div>
        );
      })}
    </div>
  );
}

// ── EXTRA v2: Famous Quotes ─────────────────────────────────────


export function MilestonesTimeline({ milestones }: { milestones: Milestone[] }) {
  if (milestones.length === 0) return null;
  return (
    <div className="ml-timeline">
      {milestones.map((ml, i) => (
        <article className="ml-item" key={i}>
          <time>{ml.time}</time>
          <div><strong>{ml.title}</strong><p>{ml.body}</p></div>
        </article>
      ))}
    </div>
  );
}

// ── EXTRA v2: @Mentions List ────────────────────────────────────


export function DualReportExtrasCard({ extras }: { extras: DualReportExtras }) {
  return (
    <div className="dual-extras">
      <div className="dual-monthly">
        <h4>逐月对话量</h4>
        <div className="dual-monthly-chart">
          {extras.monthly.slice(-12).map((m) => {
            const max = Math.max(m.p1_count, m.p2_count, 1);
            return (
              <div className="dual-month-col" key={m.month}>
                <div className="dual-month-bar" style={{ height: `${(m.p1_count / max) * 100}%`, background: '#f26b5e' }} />
                <div className="dual-month-bar" style={{ height: `${(m.p2_count / max) * 100}%`, background: '#1984c4' }} />
                <span>{m.label}</span>
              </div>
            );
          })}
        </div>
      </div>
      <p className="dual-stats">总消息: A {extras.p1_message_count} vs B {extras.p2_message_count} | 总字数: A {extras.p1_char_count} vs B {extras.p2_char_count}</p>
    </div>
  );
}

export function AnnualSummaryCard({ annual }: { annual?: AnnualSummary }) {
  if (!annual || !annual.total_messages) {
    return <p className="muted">聊天概览数据不足。</p>;
  }
  const metrics = [
    ["总消息", formatCount(annual.total_messages)],
    ["活跃天", `${annual.active_days}`],
    ["联系人", `${annual.total_friends}`],
    ["总字数", formatCount(annual.total_chars)],
    ["夜聊王", annual.night_king || "暂无"],
    ["时间跨度", `${annual.first_date} ~ ${annual.last_date}`],
  ];

  return (
    <div className="v2-stack">
      <div style={panelGridStyle}>
        {metrics.map(([label, value]) => (
          <div key={label} style={panelCardStyle}>
            <span className="muted">{label}</span>
            <strong style={{ display: "block", fontSize: "1.35rem", marginTop: 6 }}>{value}</strong>
          </div>
        ))}
      </div>
      <div style={panelCardStyle}>
        <strong>高频成员</strong>
        <p className="muted" style={{ margin: "0.45rem 0 0" }}>
          {annual.top_friends.length > 0 ? annual.top_friends.join("、") : "暂无稳定高频联系人"}
        </p>
      </div>
      {annual.monthly_best.length > 0 && (
        <div style={{ ...panelCardStyle, display: "grid", gap: "0.5rem" }}>
          <strong>每月最活跃</strong>
          {annual.monthly_best.slice(-6).map((item) => (
            <div key={item.month} style={compactRowStyle}>
              <span>{item.month}</span>
              <span className="muted">{item.friend} · {formatCount(item.count)}条</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function TimeProfilePanel({
  hourly,
  peakDay,
  weekday,
  yearly,
}: {
  hourly: HourlyBin[];
  peakDay?: PeakDayInfo;
  weekday: WeekdayBin[];
  yearly: YearlyMonthBin[];
}) {
  const maxHour = Math.max(...hourly.map((h) => h.count), 1);
  const maxWeekday = Math.max(...weekday.map((d) => d.count), 1);
  const maxMonth = Math.max(...yearly.map((m) => m.count), 1);

  return (
    <div className="v2-stack">
      {peakDay && peakDay.date && (
        <div style={panelCardStyle}>
          <strong>最高能量日：{peakDay.date}</strong>
          <p className="muted" style={{ margin: "0.4rem 0 0" }}>
            当天共 {formatCount(peakDay.count)} 条消息，主力输出是 {peakDay.top_sender || "未知"}。
          </p>
        </div>
      )}
      <div style={panelCardStyle}>
        <strong>24 小时活跃曲线</strong>
        <div style={{ alignItems: "end", display: "flex", gap: 2, height: 92, marginTop: 12 }}>
          {hourly.map((h) => (
            <div key={h.hour} title={`${h.hour}:00 · ${h.count}条`} style={{ flex: 1, minWidth: 4 }}>
              <div
                style={{
                  background: "var(--purple)",
                  borderRadius: "3px 3px 0 0",
                  height: `${Math.max(3, (h.count / maxHour) * 88)}px`,
                  opacity: h.count ? 0.78 : 0.18,
                }}
              />
            </div>
          ))}
        </div>
        <div className="muted" style={{ ...compactRowStyle, marginTop: 6 }}>
          <span>0点</span><span>12点</span><span>23点</span>
        </div>
      </div>
      <div style={panelGridStyle}>
        <div style={panelCardStyle}>
          <strong>星期分布</strong>
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            {weekday.map((d) => (
              <div key={d.day} style={{ display: "grid", gap: 5 }}>
                <div style={compactRowStyle}><span>{d.label}</span><span className="muted">{d.pct}%</span></div>
                <div style={miniBarTrackStyle}>
                  <div style={{ background: "var(--green)", height: "100%", width: `${(d.count / maxWeekday) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div style={panelCardStyle}>
          <strong>月份分布</strong>
          <div style={{ alignItems: "end", display: "flex", gap: 4, height: 132, marginTop: 12 }}>
            {yearly.map((m) => (
              <div key={m.month} title={`${m.label} · ${m.count}条`} style={{ alignItems: "center", display: "flex", flex: 1, flexDirection: "column", gap: 4, height: "100%", justifyContent: "end" }}>
                <div style={{ background: "var(--blue)", borderRadius: "3px 3px 0 0", height: `${Math.max(4, (m.count / maxMonth) * 102)}px`, opacity: m.count ? 0.76 : 0.18, width: "100%" }} />
                <span className="muted" style={{ fontSize: 10 }}>{m.month}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function InteractionMatrixPanel({
  items,
  mentions,
  sendRatio,
}: {
  items: InteractionMatrixItem[];
  mentions: AtMentionStat[];
  sendRatio: { name: string; count: number; pct: number; avatar: string }[];
}) {
  if (items.length === 0 && mentions.length === 0 && sendRatio.length === 0) {
    return <p className="muted">互动矩阵数据不足。</p>;
  }
  const maxEdge = Math.max(...items.map((i) => i.count), 1);
  const maxSend = Math.max(...sendRatio.map((i) => i.count), 1);

  return (
    <div className="v2-stack">
      {sendRatio.length > 0 && (
        <div style={panelCardStyle}>
          <strong>发言占比</strong>
          <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
            {sendRatio.slice(0, 8).map((item) => (
              <div key={item.name} style={{ display: "grid", gap: 5 }}>
                <div style={compactRowStyle}><span>{item.avatar} {item.name}</span><span className="muted">{item.pct}%</span></div>
                <div style={miniBarTrackStyle}>
                  <div style={{ background: "var(--coral)", height: "100%", width: `${(item.count / maxSend) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div style={panelGridStyle}>
        {items.slice(0, 10).map((item) => (
          <div key={`${item.from}-${item.to}`} style={panelCardStyle}>
            <div style={compactRowStyle}>
              <strong>{item.from} → {item.to}</strong>
              <span className="muted">{item.count} 次</span>
            </div>
            <div style={{ ...miniBarTrackStyle, marginTop: 10 }}>
              <div style={{ background: "var(--blue)", height: "100%", width: `${(item.count / maxEdge) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
      {mentions.length > 0 && (
        <div style={{ ...panelCardStyle, display: "grid", gap: "0.55rem" }}>
          <strong>@ 提及榜</strong>
          {mentions.slice(0, 6).map((item) => (
            <div key={item.name} style={compactRowStyle}>
              <span>@{item.name}</span>
              <span className="muted">{item.count} 次 · 常被 {item.top_mentioner || "大家"} 提到</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function FamousQuotesPanel({ quotes }: { quotes: FamousQuote[] }) {
  if (quotes.length === 0) return <p className="muted">暂无原话候选。</p>;
  return (
    <div style={panelGridStyle}>
      {quotes.slice(0, 6).map((quote) => (
        <article key={quote.msg_id} style={panelCardStyle}>
          <span className="muted">{quote.sender} · {quote.ts.slice(0, 16)}</span>
          <blockquote style={{ fontWeight: 800, lineHeight: 1.55, margin: "0.65rem 0" }}>
            「{quote.content}」
          </blockquote>
          <span className="muted">来自真实聊天记录</span>
        </article>
      ))}
    </div>
  );
}

export function EmojiCommonalityPanel({
  byHour,
  items,
}: {
  byHour: { hour: number; count: number; pct: number }[];
  items: { emoji: string; count_a: number; count_b: number; commonality: number; url?: string | null }[];
}) {
  if (items.length === 0 && byHour.every((item) => item.count === 0)) return null;
  const maxHour = Math.max(1, ...byHour.map((h) => h.count));
  const mergedItems = Array.from(items.reduce((map, item) => {
    if (!isDisplayableSticker(item.emoji, item.url)) return map;
    const key = stickerVisualKey(item.emoji, item.url);
    const current = map.get(key);
    if (current) {
      current.count_a += item.count_a;
      current.count_b += item.count_b;
      current.url ||= item.url;
      current.commonality = current.count_a > 0 && current.count_b > 0
        ? Math.round((2 / (1 / current.count_a + 1 / current.count_b)) * 100) / 100
        : Math.max(current.commonality, item.commonality);
    } else {
      map.set(key, { ...item });
    }
    return map;
  }, new Map<string, { emoji: string; count_a: number; count_b: number; commonality: number; url?: string | null }>()).values())
    .sort((a, b) => b.commonality - a.commonality);
  return (
    <div className="v2-stack">
      {mergedItems.length > 0 && (
        <div style={{ ...panelCardStyle, display: "grid", gap: "0.55rem" }}>
          <strong>共同表情暗号</strong>
          {mergedItems.slice(0, 8).map((item) => (
            <div key={stickerVisualKey(item.emoji, item.url)} style={compactRowStyle}>
              <StickerVisual label={item.emoji} url={item.url} size={28} textClassName="" />
              <span className="muted">A {item.count_a} / B {item.count_b} · 共性 {item.commonality}</span>
            </div>
          ))}
        </div>
      )}
      {byHour.some((item) => item.count > 0) && (
        <div style={panelCardStyle}>
          <strong>表情出现时间</strong>
          <div style={{ alignItems: "end", display: "flex", gap: 2, height: 76, marginTop: 12 }}>
            {byHour.map((h) => (
              <div key={h.hour} title={`${h.hour}:00 · ${h.count}次`} style={{ flex: 1, minWidth: 4 }}>
                <div style={{ background: "var(--yellow)", borderRadius: "3px 3px 0 0", height: `${Math.max(3, (h.count / maxHour) * 72)}px`, opacity: h.count ? 0.8 : 0.18 }} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function EmojiInlineList({
  items,
}: {
  items: { emoji: string; count: number; url?: string | null }[];
}) {
  const merged = Array.from(items.reduce((map, item) => {
    if (!isDisplayableSticker(item.emoji, item.url)) return map;
    const key = stickerVisualKey(item.emoji, item.url);
    const current = map.get(key);
    if (current) {
      current.count += item.count;
      current.url ||= item.url;
    } else {
      map.set(key, { ...item });
    }
    return map;
  }, new Map<string, { emoji: string; count: number; url?: string | null }>()).values());
  if (!merged.length) return <>暂无</>;
  return (
    <span style={{ alignItems: "center", display: "inline-flex", flexWrap: "wrap", gap: "0.45rem" }}>
      {merged.map((item) => (
        <span key={stickerVisualKey(item.emoji, item.url)} style={{ alignItems: "center", display: "inline-flex", gap: "0.2rem" }}>
          <StickerVisual label={item.emoji} url={item.url} size={28} textClassName="" />
          <small>×{item.count}</small>
        </span>
      ))}
    </span>
  );
}

export function MessageTypeEvolutionPanel({
  evolution,
  recall,
  redPacket,
}: {
  evolution: Record<string, any>[];
  recall?: RecallStats;
  redPacket?: RedPacketOverview;
}) {
  if (evolution.length === 0 && !redPacket?.total && !recall?.total_recalls) return null;
  return (
    <div className="v2-stack">
      <div style={panelGridStyle}>
        {redPacket && redPacket.total > 0 && (
          <div style={panelCardStyle}>
            <span className="muted">红包/转账</span>
            <strong style={{ display: "block", fontSize: "1.4rem", marginTop: 6 }}>{redPacket.total}</strong>
            <p className="muted" style={{ margin: "0.4rem 0 0" }}>{redPacket.top_sender} 贡献 {redPacket.top_count} 次</p>
          </div>
        )}
        {recall && recall.total_recalls > 0 && (
          <div style={panelCardStyle}>
            <span className="muted">撤回统计</span>
            <strong style={{ display: "block", fontSize: "1.4rem", marginTop: 6 }}>{recall.total_recalls}</strong>
            <p className="muted" style={{ margin: "0.4rem 0 0" }}>{recall.top_recaller || "有人"} 是撤回主力</p>
          </div>
        )}
      </div>
      {evolution.length > 0 && (
        <div style={{ ...panelCardStyle, display: "grid", gap: "0.55rem" }}>
          <strong>消息类型月度变化</strong>
          {evolution.slice(-8).map((item) => (
            <div key={item.month} style={{ display: "grid", gap: 5 }}>
              <div style={compactRowStyle}><span>{item.label}</span><span className="muted">{formatCount(item.total)} 条</span></div>
              <div style={{ ...miniBarTrackStyle, display: "flex" }}>
                <div title="文字" style={{ background: "var(--blue)", height: "100%", width: `${item.text_pct || 0}%` }} />
                <div title="图片" style={{ background: "var(--coral)", height: "100%", width: `${item.image_pct || 0}%` }} />
                <div title="表情" style={{ background: "var(--yellow)", height: "100%", width: `${item.emoji_pct || 0}%` }} />
                <div title="链接" style={{ background: "var(--purple)", height: "100%", width: `${item.link_pct || 0}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function PredictionsCard({ predictions }: { predictions: Prediction[] }) {
  if (predictions.length === 0) return <p className="muted">暂无预测数据。</p>;
  return (
    <div className="predictions-list">
      {predictions.map((p) => (
        <div className="prediction-card" key={p.id}>
          <div className="prediction-header">
            <strong>{p.title}</strong>
          </div>
          <p>{p.body}</p>
        </div>
      ))}
    </div>
  );
}
