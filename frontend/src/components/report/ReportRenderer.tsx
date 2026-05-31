import { BarChart3, Brain, Clock3, HeartHandshake, MessageSquareQuote, Sparkles, UsersRound } from "lucide-react";
import { Link } from "react-router-dom";
import type { ReportPayload, ReportSection } from "../../contracts/report";
import {
  AnnualSummaryCard,
  ChatDNACard, ChronotypeList, ClockFingerprintGrid,
  DragonRanking, DualReportExtrasCard, EmojiBoard, EmojiSpecificityChart,
  EmojiCommonalityPanel, EnhancedDNACard, FamousQuotesPanel, FirstChatCard,
  Heatmap, InitiativeRanking, InteractionMatrixPanel, KeywordCloud,
  LinkStatsList, MessageTypeChart, MessageTypeEvolutionPanel, MilestonesTimeline,
  MonthlyActivityChart, MonthlySentimentTrend,
  PersonalityBadgeGrid, PredictionsCard, RadarChart, RelationshipMap,
  RelationshipScoreboard, SentimentGauge, StreakCard,
  TimeProfilePanel, Timeline, WordCommonalityChart, WordSpecificityChart,
} from "./Charts";
import { ContentHighlightsPanel } from "./ContentHighlights";
import { ShareCard } from "./ShareCard";

interface ReportRendererProps { report: ReportPayload; shareUrl: string; }

function renderChart(report: ReportPayload, section: ReportSection) {
  const s = report.stats;
  if (section.id === "annual") {
    return <AnnualSummaryCard annual={s.annual_summary} />;
  }
  if (section.id === "time-profile") {
    return (
      <TimeProfilePanel
        hourly={s.hourly_distribution}
        peakDay={s.peak_day}
        weekday={s.weekday_distribution}
        yearly={s.yearly_monthly}
      />
    );
  }
  if (section.id === "interaction") {
    return (
      <InteractionMatrixPanel
        items={s.interaction_matrix}
        mentions={s.at_mention_stats}
        sendRatio={s.send_ratio}
      />
    );
  }
  if (section.id === "famous-quotes") {
    return <FamousQuotesPanel quotes={s.famous_quotes} />;
  }
  switch (section.type) {
    case "dragon_rank":
      return <DragonRanking participants={s.participants} />;
    case "heatmap":
      return <Heatmap cells={s.heatmap} />;
    case "keywords":
      return <KeywordCloud keywords={s.keywords} />;
    case "radar":
      return <RadarChart metrics={s.radar} />;
    case "emoji":
      return (
        <div className="v2-stack">
          <EmojiBoard emojis={s.emojis} />
          {s.emoji_specificity.length > 0 && <EmojiSpecificityChart catalog={s.emojis} items={s.emoji_specificity} />}
          <EmojiCommonalityPanel byHour={s.emoji_time_distribution} items={s.emoji_commonality} />
        </div>
      );
    case "timeline":
      return (
        <div className="v2-stack">
          <Timeline events={s.timeline} />
          {s.relationship_milestones.length > 0 && <MilestonesTimeline milestones={s.relationship_milestones} />}
        </div>
      );
    case "relationship":
      return (
        <div className="relationship-stack">
          <RelationshipMap edges={s.relationship_edges} />
          <RelationshipScoreboard metrics={s.relationship_metrics ?? []} />
          {s.dual_report_extras && <DualReportExtrasCard extras={s.dual_report_extras} />}
          {s.first_chat && s.first_chat.first_date && <FirstChatCard data={s.first_chat} />}
        </div>
      );
    // ── NEW section types ──────────────────────────────────────
    case "word_specificity":
      return <WordSpecificityChart items={s.word_specificity} />;
    case "word_commonality":
      return <WordCommonalityChart items={s.word_commonality} />;
    case "message_types":
      return (
        <div className="v2-stack">
          <MessageTypeChart types={s.message_type_breakdown} />
          <MessageTypeEvolutionPanel
            evolution={s.message_type_evolution}
            recall={s.recall_stats}
            redPacket={s.red_packet_overview}
          />
        </div>
      );
    case "chat_dna":
      return (
        <div className="v2-stack">
          {s.chat_dna && <ChatDNACard dna={s.chat_dna} />}
          {s.enhanced_chat_dna && <EnhancedDNACard dna={s.enhanced_chat_dna} />}
          {s.streak && s.streak.length > 1 && <StreakCard streak={s.streak} />}
        </div>
      );
    case "chronotype":
      return (
        <div className="v2-stack">
          <ChronotypeList chronotypes={s.chronotypes} />
          {s.clock_fingerprints.length > 0 && <ClockFingerprintGrid fingerprints={s.clock_fingerprints} />}
        </div>
      );
    case "sentiment":
      return (
        <div className="v2-stack">
          {s.sentiment_overview ? <SentimentGauge sentiment={s.sentiment_overview} /> : <p className="muted">情绪数据收集中...</p>}
          {s.monthly_sentiment.length > 0 && <MonthlySentimentTrend data={s.monthly_sentiment} />}
          {s.per_contact_sentiment.length > 0 && (
            <div className="pc-sentiment-grid">
              {s.per_contact_sentiment.map(pc => (
                <div className="pc-sentiment-card" key={pc.name}>
                  <strong>{pc.name}</strong>
                  <span className={`pc-label ${pc.label === '阳光开朗' ? 'pc-positive' : pc.label === '嘴上不饶人' ? 'pc-negative' : ''}`}>{pc.label}</span>
                  <div className="pc-bar">
                    <div className="pc-pos" style={{ width: `${pc.positive_ratio}%` }} />
                    <div className="pc-neg" style={{ width: `${pc.negative_ratio}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    case "monthly":
      return <MonthlyActivityChart data={s.monthly_activity} />;
    case "initiative":
      return <InitiativeRanking scores={s.initiative_scores} />;
    case "links":
      return <LinkStatsList links={s.link_stats} />;
    case "personality_badges":
      return <PersonalityBadgeGrid badges={s.personality_badges} />;
    case "predictions":
      return <PredictionsCard predictions={s.predictions} />;
    case "annual":
      return <AnnualSummaryCard annual={s.annual_summary} />;
    default:
      return null;
  }
}

function quoteIcon(icon: string) {
  const icons: Record<string, string> = {
    coffee: "☕",
    flame: "🔥",
    heart: "♥",
    message: "💬",
    "message-circle": "💬",
    moon: "🌙",
    sparkles: "✦",
    star: "★",
    sun: "☀",
    zap: "⚡",
  };
  return icons[icon] ?? icon;
}

function formatCompactNumber(value: number | undefined) {
  if (!Number.isFinite(value)) return "待分析";
  if ((value ?? 0) >= 10000) return `${((value ?? 0) / 10000).toFixed(1)} 万`;
  return `${value}`;
}

function getReportModeLabel(report: ReportPayload) {
  return report.report_type === "relationship" ? "双人报告" : "群聊报告";
}

export function ReportRenderer({ report, shareUrl }: ReportRendererProps) {
  const stats = report.stats;
  const totalMessages = stats.chat_dna?.total_messages;
  const activeDays = stats.chat_dna?.active_days;
  const topSender = stats.chat_dna?.top_sender_name || stats.participants[0]?.name || "待分析";
  const peakHour = Number.isFinite(stats.chat_dna?.top_hour) ? `${stats.chat_dna?.top_hour}:00` : "待分析";
  const insightCards = [
    {
      icon: Brain,
      title: "报告摘要",
      body: report.sections[0]?.body || report.tagline,
      to: `/insights/${report.report_id}/summary`,
    },
    {
      icon: Clock3,
      title: "作息与节奏",
      body: `高峰时段 ${peakHour}，展示聊天更活跃的时间。`,
      to: `/insights/${report.report_id}/time`,
    },
    {
      icon: report.report_type === "relationship" ? HeartHandshake : UsersRound,
      title: report.report_type === "relationship" ? "双人关系" : "群聊结构",
      body: report.report_type === "relationship"
        ? "主动程度、回复节奏、共同语言和关系里程碑放在一屏看。"
        : `先看 ${topSender} 和其他成员之间的互动强弱。`,
      to: `/insights/${report.report_id}/relationship`,
    },
    {
      icon: MessageSquareQuote,
      title: "代表片段",
      body: `${report.quotes.length || stats.famous_quotes.length} 条真实聊天片段会被优先展示。`,
      to: `/insights/${report.report_id}/quotes`,
    },
    {
      icon: Sparkles,
      title: "趋势预测",
      body: "基于活跃趋势、共同语言和情绪底色给下一阶段预测。",
      to: `/insights/${report.report_id}/predictions`,
    },
  ];

  return (
    <article className="report-renderer">
      <section className="report-hero">
        <div className="report-mark">{report.hero.visual}</div>
        <p className="eyebrow">{report.hero.kicker}</p>
        <h1>{report.title}</h1>
        <p className="report-tagline">{report.tagline}</p>
        <blockquote>{report.hero.quote}</blockquote>
        <div className="tag-row">
          {report.tags.map((tag) => <span key={tag}>{tag}</span>)}
        </div>
      </section>

      <section className="report-section ai-summary-section">
        <div className="section-copy">
          <p className="eyebrow">报告概览</p>
          <h2>先看报告摘要</h2>
          <p>
            {getReportModeLabel(report)}已经生成。你可以按完整报告往下读，也可以直接跳到
            时间、关系、代表片段和趋势预测页查看判断依据。
          </p>
        </div>
        <div className="ai-metric-strip" aria-label="报告关键数据">
          <div>
            <span>消息量</span>
            <strong>{formatCompactNumber(totalMessages)}</strong>
          </div>
          <div>
            <span>{report.report_type === "relationship" ? "双方" : "成员"}</span>
            <strong>{stats.participants.length}</strong>
          </div>
          <div>
            <span>活跃天数</span>
            <strong>{formatCompactNumber(activeDays)}</strong>
          </div>
          <div>
            <span>高峰时段</span>
            <strong>{peakHour}</strong>
          </div>
        </div>
        <div className="ai-route-grid">
          {insightCards.map((card) => {
            const Icon = card.icon;
            return (
              <Link className="ai-route-card" key={card.title} to={card.to}>
                <span><Icon size={18} /></span>
                <strong>{card.title}</strong>
                <em>{card.body}</em>
              </Link>
            );
          })}
        </div>
        <Link className="btn btn-primary ai-summary-cta" to={`/insights/${report.report_id}/summary`}>
          <BarChart3 size={18} />
          <span>进入中间分析页</span>
        </Link>
      </section>

      <ContentHighlightsPanel highlights={report.content_highlights} />

      {report.sections.map((section) => (
        <section className={`report-section report-section-${section.type}`} id={`section-${section.id}`} key={section.id}>
          <div className="section-copy">
            <p className="eyebrow">{section.type.replace(/_/g, " ")}</p>
            <h2>{section.heading}</h2>
            <p>{section.body}</p>
          </div>
          {renderChart(report, section)}
        </section>
      ))}

      <section className="quote-gallery">
        <div className="section-copy">
          <p className="eyebrow">代表片段</p>
          <h2>{report.report_type === "relationship" ? "双人片段" : "聊天片段"}</h2>
          <p>{report.report_type === "relationship"
            ? "这组卡片展示两个人对话中更有代表性的句子。"
            : "这些片段来自原始聊天记录，用于辅助理解报告结论。"}</p>
        </div>
        <div className="quote-grid">
          {report.quotes.map((quote) => (
            <article className="quote-card" key={quote.id}>
              <span>{quoteIcon(quote.icon)}</span>
              <blockquote>{quote.text}</blockquote>
              <strong>{quote.speaker}</strong>
              <p>{quote.comment}</p>
            </article>
          ))}
        </div>
      </section>

      <ShareCard report={report} shareUrl={shareUrl} />
    </article>
  );
}
