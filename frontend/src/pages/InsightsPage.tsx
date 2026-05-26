import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft, ArrowRight, CalendarDays, Clock3, FileText, HeartHandshake,
  Image, Languages, Loader2, MessageSquare, Network, Sparkles,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { getReport } from "../api/client";
import {
  AnnualSummaryCard,
  ChatDNACard,
  ChronotypeList,
  ClockFingerprintGrid,
  DualReportExtrasCard,
  EmojiBoard,
  EmojiCommonalityPanel,
  EmojiInlineList,
  EmojiSpecificityChart,
  EnhancedDNACard,
  FamousQuotesPanel,
  FirstChatCard,
  InteractionMatrixPanel,
  InitiativeRanking,
  KeywordCloud,
  LinkStatsList,
  MessageTypeChart,
  MessageTypeEvolutionPanel,
  MilestonesTimeline,
  MonthlySentimentTrend,
  PersonalityBadgeGrid,
  PredictionsCard,
  RelationshipMap,
  RelationshipScoreboard,
  SentimentGauge,
  StreakCard,
  TimeProfilePanel,
  WordCommonalityChart,
  WordSpecificityChart,
} from "../components/report/Charts";
import type { ReportPayload } from "../contracts/report";

type InsightView =
  | "summary" | "time" | "language" | "emoji" | "interaction"
  | "emotion" | "media" | "relationship" | "quotes" | "predictions";

const VIEW_META: { id: InsightView; title: string; body: string }[] = [
  { id: "summary", title: "聊天总览", body: "把总量、时间跨度、峰值、连续聊天和聊天 DNA 做成总览。" },
  { id: "time", title: "时间与作息", body: "拆解 24 小时活跃曲线、星期偏好、个人作息指纹和深夜占比。" },
  { id: "language", title: "语言与梗", body: "展示词云、个人口头禅、共同词汇、n-gram 热词和名场面候选。" },
  { id: "emoji", title: "表情包档案", body: "合并中英文微信表情别名，展示表情偏好、共性、专属性和出现时间。" },
  { id: "interaction", title: "互动网络", body: "把发言占比、快速接话、@ 提及、主动破冰和链接分享集中看。" },
  { id: "emotion", title: "情绪温度", body: "查看整体情绪、月度情绪趋势和每个人的情绪标签。" },
  { id: "media", title: "消息结构", body: "聚合文本、图片、表情、文件、链接、撤回、红包和类型演变。" },
  { id: "relationship", title: "关系走势", body: "用月度互动量、双方发言差异、里程碑和最初对话展示关系变化。" },
  { id: "quotes", title: "名场面回放", body: "把真实聊天里的高分句子、代表语录和最初对话做成回放页。" },
  { id: "predictions", title: "赛博占卜", body: "AI 基于趋势给出未来预测、人格勋章和下一阶段看点。" },
];

const cardStyle = {
  background: "var(--bg-secondary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
  padding: "1rem",
} as const;

const gridStyle = {
  display: "grid",
  gap: 12,
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
} as const;

function ViewIcon({ id }: { id: InsightView }) {
  const props = { size: 22 };
  if (id === "summary") return <CalendarDays {...props} />;
  if (id === "time") return <Clock3 {...props} />;
  if (id === "language") return <Languages {...props} />;
  if (id === "emoji") return <Image {...props} />;
  if (id === "interaction") return <Network {...props} />;
  if (id === "emotion") return <Sparkles {...props} />;
  if (id === "media") return <MessageSquare {...props} />;
  if (id === "relationship") return <HeartHandshake {...props} />;
  if (id === "quotes") return <MessageSquare {...props} />;
  return <Sparkles {...props} />;
}

function MetricGrid({ items }: { items: [string, ReactNode, string?][] }) {
  return (
    <div style={gridStyle}>
      {items.map(([label, value, hint]) => (
        <div key={label} style={cardStyle}>
          <span className="muted">{label}</span>
          <strong style={{ display: "block", fontSize: "1.35rem", marginTop: 6 }}>{value}</strong>
          {hint ? <p className="muted" style={{ margin: "0.45rem 0 0" }}>{hint}</p> : null}
        </div>
      ))}
    </div>
  );
}

function SectionBlock({ children, kicker, title }: { children: ReactNode; kicker: string; title: string }) {
  return (
    <section className="report-section">
      <div className="section-copy">
        <p className="eyebrow">{kicker}</p>
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function sectionBody(report: ReportPayload, ids: string[]) {
  return report.sections.find((section) => ids.includes(section.id))?.body || "";
}

function getAiBrief(report: ReportPayload, view: InsightView) {
  const stats = report.stats;
  const briefs: Record<InsightView, string> = {
    summary: sectionBody(report, ["chat-dna", "summary"]) ||
      `AI 先看总账：${stats.chat_dna?.total_messages ?? 0} 条消息、${stats.chat_dna?.active_days ?? 0} 个活跃日，最值得关注的是聊天节奏和高频成员。`,
    time: sectionBody(report, ["heatmap", "chronotype", "monthly"]) ||
      `AI 判断黄金时段在 ${stats.chat_dna?.top_hour ?? "未知"} 点，作息页会重点看谁在深夜撑起聊天量。`,
    language: sectionBody(report, ["keywords", "specificity", "commonality"]) ||
      "AI 会把高频词、个人口头禅和共同词汇放在一起看，判断这个聊天关系里真正反复出现的暗号。",
    emoji: sectionBody(report, ["emoji"]) ||
      "AI 会把中英文微信表情名先合并，再看谁的表情最有个人识别度，避免 Facepalm 和捂脸被拆成两个表情。",
    interaction: sectionBody(report, ["initiative", "relationship-map", "links"]) ||
      "AI 不只看谁发得多，也看谁接话、谁打破冷场、谁在对话网络里承担连接作用。",
    emotion: sectionBody(report, ["sentiment"]) ||
      `AI 给出的情绪底色是：${stats.sentiment_overview?.label || "数据不足，待观察"}。`,
    media: sectionBody(report, ["msg-types", "links"]) ||
      "AI 会根据文字、图片、表情、链接、红包、撤回等结构判断聊天的表达方式，而不是只看消息数量。",
    relationship: sectionBody(report, ["relationship-summary", "relationship-radar", "relationship-timeline"]) ||
      "AI 会把关系走势当作时间序列看：互动总量、双方发言差异、里程碑和断联重连共同决定观察重点。",
    quotes: report.quotes[0]?.comment ||
      "AI 会优先挑真实出现过、有记忆点、能代表聊天氛围的原话，而不是重新编造金句。",
    predictions: sectionBody(report, ["predictions"]) ||
      "AI 的预测会基于活跃趋势、作息、互动网络和共同语言，只做娱乐化判断，不替用户定义现实关系。",
  };
  return briefs[view];
}

function PageShell({
  children,
  index,
  meta,
  report,
}: {
  children: ReactNode;
  index: number;
  meta: (typeof VIEW_META)[number];
  report: ReportPayload;
}) {
  const previous = VIEW_META[index - 1];
  const next = VIEW_META[index + 1];
  const previousUrl = previous ? `/insights/${report.report_id}/${previous.id}` : `/report/${report.report_id}`;
  const nextUrl = next ? `/insights/${report.report_id}/${next.id}` : `/report/${report.report_id}`;

  return (
    <main className="page report-page">
      <nav className="report-toolbar">
        <Link className="icon-link" to={previousUrl} title={previous ? "上一页" : "最终报告"}>
          <ArrowLeft size={18} />
        </Link>
        <strong>{meta.title}</strong>
        <span className="muted" style={{ marginLeft: "auto" }}>
          {index + 1} / {VIEW_META.length}
        </span>
        {!next ? <Link className="btn btn-primary" to={`/report/${report.report_id}`}>
          <FileText size={18} />
          <span>最终报告</span>
        </Link> : null}
      </nav>
      <article className="report-renderer">
        <section className="report-hero" style={{ minHeight: "34vh" }}>
          <div className="report-mark"><ViewIcon id={meta.id} /></div>
          <p className="eyebrow">主题分镜</p>
          <h1>{meta.title}</h1>
          <p className="report-tagline">{meta.body}</p>
        </section>
        <SectionBlock kicker="AI" title="AI 先判一句">
          <p style={{ fontSize: "1.05rem", lineHeight: 1.8, margin: 0 }}>{getAiBrief(report, meta.id)}</p>
        </SectionBlock>
        {children}
        <section className="report-section">
          <div style={{ display: "grid", gap: 14 }}>
            <div
              aria-label={`第 ${index + 1} 页，共 ${VIEW_META.length} 页`}
              style={{ display: "grid", gap: 4, gridTemplateColumns: `repeat(${VIEW_META.length}, 1fr)` }}
            >
              {VIEW_META.map((item, itemIndex) => (
                <span
                  key={item.id}
                  style={{
                    background: itemIndex <= index ? "var(--accent)" : "var(--border-default)",
                    borderRadius: 999,
                    display: "block",
                    height: 6,
                  }}
                />
              ))}
            </div>
            <div style={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "space-between" }}>
              <p className="muted" style={{ margin: 0 }}>
                {next ? `下一页：${next.title}` : "主题分镜已完成，进入最终报告。"}
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {previous ? (
                  <Link className="btn btn-secondary" to={previousUrl}>
                    <ArrowLeft size={18} />
                    <span>上一页</span>
                  </Link>
                ) : null}
                <Link className="btn btn-primary" to={nextUrl}>
                  {next ? <ArrowRight size={18} /> : <FileText size={18} />}
                  <span>{next ? "下一页" : "进入最终报告"}</span>
                </Link>
              </div>
            </div>
          </div>
        </section>
      </article>
    </main>
  );
}

function SummaryView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="总览" title="聊天总账">
        <AnnualSummaryCard annual={stats.annual_summary} />
      </SectionBlock>
      <SectionBlock kicker="基因" title="聊天基因">
        <div className="v2-stack">
          {stats.chat_dna ? <ChatDNACard dna={stats.chat_dna} /> : <p className="muted">暂无聊天 DNA。</p>}
          {stats.enhanced_chat_dna ? <EnhancedDNACard dna={stats.enhanced_chat_dna} /> : null}
          {stats.streak && stats.streak.length > 1 ? <StreakCard streak={stats.streak} /> : null}
        </div>
      </SectionBlock>
    </>
  );
}

function TimeView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="时间" title="时间分布">
        <TimeProfilePanel hourly={stats.hourly_distribution} peakDay={stats.peak_day} weekday={stats.weekday_distribution} yearly={stats.yearly_monthly} />
      </SectionBlock>
      <SectionBlock kicker="作息" title="作息指纹">
        <div className="v2-stack">
          <ChronotypeList chronotypes={stats.chronotypes} />
          <ClockFingerprintGrid fingerprints={stats.clock_fingerprints} />
        </div>
      </SectionBlock>
    </>
  );
}

function LanguageView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="语言" title="词云与口头禅">
        <div className="v2-stack">
          <KeywordCloud keywords={stats.keywords} />
          <WordSpecificityChart items={stats.word_specificity} />
          <WordCommonalityChart items={stats.word_commonality} />
        </div>
      </SectionBlock>
      <SectionBlock kicker="短语" title="高频短语">
        <div style={gridStyle}>
          {stats.ngrams.slice(0, 12).map((item) => (
            <div key={item.phrase} style={cardStyle}>
              <strong>{item.phrase}</strong>
              <p className="muted" style={{ margin: "0.45rem 0 0" }}>{item.count} 次</p>
            </div>
          ))}
        </div>
      </SectionBlock>
    </>
  );
}

function EmojiView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="表情" title="表情偏好">
        <div className="v2-stack">
          <EmojiBoard emojis={stats.emojis} />
          <EmojiSpecificityChart catalog={stats.emojis} items={stats.emoji_specificity} />
          <EmojiCommonalityPanel byHour={stats.emoji_time_distribution} items={stats.emoji_commonality} />
        </div>
      </SectionBlock>
      {stats.dual_report_extras ? (
        <SectionBlock kicker="专属" title="双人专属表情">
          <MetricGrid items={[
            ["A 专属", <EmojiInlineList items={stats.dual_report_extras.p1_exclusive_emojis} />],
            ["B 专属", <EmojiInlineList items={stats.dual_report_extras.p2_exclusive_emojis} />],
          ]} />
        </SectionBlock>
      ) : null}
    </>
  );
}

function InteractionView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="互动" title="互动网络">
        <InteractionMatrixPanel items={stats.interaction_matrix} mentions={stats.at_mention_stats} sendRatio={stats.send_ratio} />
      </SectionBlock>
      <SectionBlock kicker="主动性" title="主动与分享">
        <div className="v2-stack">
          <InitiativeRanking scores={stats.initiative_scores} />
          <LinkStatsList links={stats.link_stats} />
        </div>
      </SectionBlock>
    </>
  );
}

function EmotionView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="情绪" title="总体温度">
        <div className="v2-stack">
          {stats.sentiment_overview ? <SentimentGauge sentiment={stats.sentiment_overview} /> : <p className="muted">暂无情绪数据。</p>}
          <MonthlySentimentTrend data={stats.monthly_sentiment} />
        </div>
      </SectionBlock>
      <SectionBlock kicker="成员" title="成员情绪标签">
        <div style={gridStyle}>
          {stats.per_contact_sentiment.map((item) => (
            <div key={item.name} style={cardStyle}>
              <strong>{item.name}</strong>
              <p className="muted">{item.label}</p>
              <div style={{ background: "var(--bg-tertiary)", borderRadius: 999, display: "flex", height: 10, overflow: "hidden" }}>
                <div style={{ background: "var(--green)", width: `${item.positive_ratio}%` }} />
                <div style={{ background: "var(--coral)", width: `${item.negative_ratio}%` }} />
              </div>
            </div>
          ))}
        </div>
      </SectionBlock>
    </>
  );
}

function MediaView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="类型" title="消息结构">
        <div className="v2-stack">
          <MessageTypeChart types={stats.message_type_breakdown} />
          <MessageTypeEvolutionPanel evolution={stats.message_type_evolution} recall={stats.recall_stats} redPacket={stats.red_packet_overview} />
        </div>
      </SectionBlock>
      <SectionBlock kicker="链接" title="链接趋势">
        <div className="v2-stack">
          <LinkStatsList links={stats.link_stats} />
          <div style={gridStyle}>
            {stats.link_time_trends.slice(-8).map((item) => (
              <div key={item.month} style={cardStyle}>
                <span className="muted">{item.label}</span>
                <strong style={{ display: "block", fontSize: "1.25rem", marginTop: 6 }}>{item.count}</strong>
              </div>
            ))}
          </div>
        </div>
      </SectionBlock>
    </>
  );
}

function RelationshipCandles({ report }: { report: ReportPayload }) {
  const monthly = report.stats.dual_report_extras?.monthly ?? report.stats.monthly_activity.map((m) => ({
    month: m.month,
    label: m.label,
    p1_count: m.count,
    p2_count: Math.round(m.count * 0.72),
  }));
  const rows = monthly.slice(-8).map((m) => ({
    ...m,
    total: m.p1_count + m.p2_count,
  }));
  const maxTotal = Math.max(1, ...rows.map((m) => m.total));

  return (
    <div style={{ ...cardStyle, display: "grid", gap: 12 }}>
      <strong>月度互动走势</strong>
      <div style={{ display: "grid", gap: 10 }}>
        {rows.map((row) => (
          <div key={row.month} style={{ display: "grid", gap: 5 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <span>{row.label}</span>
              <span className="muted">{row.total} 条</span>
            </div>
            <div style={{ background: "var(--bg-tertiary)", borderRadius: 999, display: "flex", height: 10, overflow: "hidden" }}>
              <div title="A" style={{ background: "var(--coral)", width: `${(row.p1_count / maxTotal) * 100}%` }} />
              <div title="B" style={{ background: "var(--blue)", width: `${(row.p2_count / maxTotal) * 100}%` }} />
            </div>
            <div className="muted" style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <span>A {row.p1_count}</span>
              <span>B {row.p2_count}</span>
            </div>
          </div>
        ))}
      </div>
      <p className="muted" style={{ margin: 0 }}>这里只展示可数的月度互动量和双方发言差异，用来观察聊天变化。</p>
    </div>
  );
}

function RelationshipView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="关系" title="关系结构">
        <div className="v2-stack">
          <RelationshipMap edges={stats.relationship_edges} />
          <RelationshipScoreboard metrics={stats.relationship_metrics ?? []} />
          {stats.dual_report_extras ? <DualReportExtrasCard extras={stats.dual_report_extras} /> : null}
        </div>
      </SectionBlock>
      <SectionBlock kicker="走势" title="走势与里程碑">
        <div className="v2-stack">
          <RelationshipCandles report={report} />
          {stats.first_chat ? <FirstChatCard data={stats.first_chat} /> : null}
          <MilestonesTimeline milestones={stats.relationship_milestones} />
        </div>
      </SectionBlock>
    </>
  );
}

function QuotesView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="金句" title="AI 标注的名场面">
        <div className="v2-stack">
          {report.quotes.length ? (
            <div style={gridStyle}>
              {report.quotes.map((quote) => (
                <article key={quote.id} style={cardStyle}>
                  <div style={{ alignItems: "center", display: "flex", gap: 10 }}>
                    <strong>{quote.icon}</strong>
                    <strong>{quote.speaker}</strong>
                  </div>
                  <p style={{ fontSize: "1.05rem", lineHeight: 1.7 }}>{quote.text}</p>
                  <p className="muted" style={{ margin: 0 }}>{quote.comment}</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="muted">暂无可展示的名场面。</p>
          )}
          <FamousQuotesPanel quotes={stats.famous_quotes} />
        </div>
      </SectionBlock>
      <SectionBlock kicker="回放" title="关系开场">
        <div className="v2-stack">
          {stats.first_chat ? <FirstChatCard data={stats.first_chat} /> : <p className="muted">暂无最初对话记录。</p>}
          <MilestonesTimeline milestones={stats.relationship_milestones} />
        </div>
      </SectionBlock>
    </>
  );
}

function PredictionsView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock kicker="预测" title="下一阶段预测">
        <div className="v2-stack">
          <PredictionsCard predictions={stats.predictions} />
          <PersonalityBadgeGrid badges={stats.personality_badges} />
        </div>
      </SectionBlock>
      <SectionBlock kicker="信号" title="AI 参考的聊天信号">
        <MetricGrid items={[
          ["活跃天数", stats.chat_dna?.active_days ?? "—", "判断趋势是否稳定"],
          ["峰值时段", stats.chat_dna ? `${stats.chat_dna.top_hour}:00` : "—", "观察热聊更常出现的时间"],
          ["共同暗号", stats.word_commonality.slice(0, 3).map((item) => item.word).join("、") || "暂无", "判断还能继续复用的梗"],
          ["主动破冰", stats.initiative_scores[0]?.name || "暂无", "判断谁更可能开启下一轮聊天"],
          ["情绪底色", stats.sentiment_overview?.label || "暂无", "判断预测的语气和温度"],
          ["表情代表", stats.emojis[0]?.label || "暂无", "判断下一阶段最可能延续的表情符号"],
        ]} />
      </SectionBlock>
    </>
  );
}

function renderView(view: InsightView, report: ReportPayload) {
  if (view === "summary") return <SummaryView report={report} />;
  if (view === "time") return <TimeView report={report} />;
  if (view === "language") return <LanguageView report={report} />;
  if (view === "emoji") return <EmojiView report={report} />;
  if (view === "interaction") return <InteractionView report={report} />;
  if (view === "emotion") return <EmotionView report={report} />;
  if (view === "media") return <MediaView report={report} />;
  if (view === "relationship") return <RelationshipView report={report} />;
  if (view === "quotes") return <QuotesView report={report} />;
  if (view === "predictions") return <PredictionsView report={report} />;
  return <SummaryView report={report} />;
}

export function InsightsPage() {
  const { id = "", view } = useParams();
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getReport(id)
      .then((payload) => {
        if (active) setReport(payload);
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "中间分析台加载失败");
      });
    return () => {
      active = false;
    };
  }, [id]);

  const activeIndex = useMemo(
    () => Math.max(0, VIEW_META.findIndex((item) => item.id === view)),
    [view],
  );
  const activeMeta = VIEW_META[activeIndex];

  if (error) {
    return (
      <main className="page state-page">
        <h1>数据加载失败</h1>
        <p>{error}</p>
        <Link className="btn btn-primary" to={`/report/${id}`}>
          <ArrowLeft size={18} />
          <span>返回报告</span>
        </Link>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="page state-page">
        <Loader2 className="spin" />
        <p>聊天分镜加载中...</p>
      </main>
    );
  }

  return (
    <PageShell index={activeIndex} meta={activeMeta} report={report}>
      {renderView(activeMeta.id, report)}
    </PageShell>
  );
}
