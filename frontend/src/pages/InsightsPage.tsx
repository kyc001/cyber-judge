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
import { ContentHighlightsPanel } from "../components/report/ContentHighlights";
import type { ReportPayload } from "../contracts/report";

type InsightView =
  | "summary" | "time" | "language" | "emoji" | "interaction"
  | "emotion" | "media" | "relationship" | "quotes" | "predictions";

const VIEW_META: { id: InsightView; title: string; body: string }[] = [
  { id: "summary", title: "总判词", body: "先给这份聊天定性：它到底是稳定陪聊、抽象水群，还是嘴硬互助局。" },
  { id: "time", title: "作息病历", body: "看高峰、深夜占比和连续聊天，判断这群人是在生活，还是在守夜。" },
  { id: "language", title: "语言指纹", body: "从高频词、共同暗号和口头禅里抓人设，少一点废话，多一点证据。" },
  { id: "emoji", title: "表情包人格", body: "表情包不是装饰，是懒得打字时暴露真实态度的精神外设。" },
  { id: "interaction", title: "权力结构", body: "谁供氧、谁接话、谁只在关键时刻冒泡，互动网络会自己招供。" },
  { id: "emotion", title: "嘴硬温度", body: "把情绪比例和月度趋势拆开，看吐槽下面是热乎，还是纯粹犯欠。" },
  { id: "media", title: "消息成分", body: "文本、图片、链接、撤回和红包的比例，能看出聊天到底靠什么续命。" },
  { id: "relationship", title: "关系判型", body: "双人看默契，群聊看秩序：谁更主动、谁更会接、谁负责装死。" },
  { id: "quotes", title: "证据展台", body: "别只看结论，真实原话才是这份锐评能不能站住脚的证据链。" },
  { id: "predictions", title: "后续走势", body: "用已有趋势推下一阶段，不做人生导师，只做赛博围观群众。" },
];

const cardStyle = {
  background: "var(--report-panel, var(--bg-secondary))",
  border: "1px solid var(--report-line, var(--border-default))",
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

function SectionBlock({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="report-section">
      <div className="section-copy">
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function sectionBody(report: ReportPayload, ids: string[]) {
  return report.sections.find((section) => ids.includes(section.id))?.body || "";
}

function compactNumber(value: number | undefined) {
  if (!Number.isFinite(value)) return "暂无";
  const safeValue = value ?? 0;
  if (safeValue >= 10000) return `${(safeValue / 10000).toFixed(1)}万`;
  return safeValue.toLocaleString("zh-CN");
}

function pct(value: number | undefined) {
  if (!Number.isFinite(value)) return "暂无";
  return `${(value ?? 0).toFixed(1)}%`;
}

function joinTop(items: string[], fallback = "暂无") {
  const visible = items.filter(Boolean).slice(0, 3);
  return visible.length ? visible.join("、") : fallback;
}

function getAiBrief(report: ReportPayload, view: InsightView) {
  const llmBrief = report.insight_briefs?.[view]?.trim();
  if (llmBrief) return llmBrief;

  const briefs: Record<InsightView, string> = {
    summary: sectionBody(report, ["chat-dna", "summary"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    time: sectionBody(report, ["heatmap", "chronotype", "monthly"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    language: sectionBody(report, ["keywords", "specificity", "commonality"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    emoji: sectionBody(report, ["emoji"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    interaction: sectionBody(report, ["initiative", "relationship-map", "links"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    emotion: sectionBody(report, ["sentiment"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    media: sectionBody(report, ["msg-types", "links"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    relationship: sectionBody(report, ["relationship-summary", "relationship-radar", "relationship-timeline"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    quotes: report.quotes[0]?.comment ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
    predictions: sectionBody(report, ["predictions"]) ||
      "本页锐评暂未生成。重新生成报告可以补齐这段内容。",
  };
  return briefs[view];
}

interface ModeDiagnosis {
  mode: string;
  subtitle: string;
  evidence: { label: string; value: ReactNode; note: string }[];
  verdict: string;
}

function buildModeDiagnosis(report: ReportPayload, view: InsightView): ModeDiagnosis {
  const stats = report.stats;
  const relationship = report.report_type === "relationship";
  const dna = stats.chat_dna;
  const topSender = dna?.top_sender_name || stats.participants[0]?.name || "暂无";
  const topWord = dna?.top_word || stats.keywords[0]?.word || "暂无";
  const topEmoji = dna?.top_emoji || stats.emojis[0]?.label || "暂无";
  const topKeywordLine = joinTop(stats.keywords.map((item) => item.word));
  const topNgrams = joinTop(stats.ngrams.map((item) => item.phrase));
  const topCommonWords = joinTop(stats.word_commonality.map((item) => item.word));
  const topInitiator = stats.initiative_scores[0]?.name || topSender;
  const topMessageType = stats.message_type_breakdown[0]?.label || "暂无";
  const firstParticipant = stats.participants[0]?.name || "A";
  const secondParticipant = stats.participants[1]?.name || "B";

  const sharedEvidence = [
    { label: "消息量", value: compactNumber(dna?.total_messages), note: "聊天体量决定这份判词不是看两眼就开喷" },
    { label: "活跃天数", value: compactNumber(dna?.active_days), note: "能坚持这么多天，说明不是一阵风" },
    { label: "高频词", value: topWord, note: "脑回路最容易从重复词里漏出来" },
  ];

  if (view === "summary") {
    return {
      mode: relationship ? "嘴硬搭子型" : "龙王供氧型",
      subtitle: relationship ? "表面像正常聊天，底层已经有固定接话协议。" : "看似一群人随便水，实际有人供氧、有人歪楼、有人装死。",
      evidence: sharedEvidence,
      verdict: relationship
        ? `这不是简单的数据多，而是 ${firstParticipant} 和 ${secondParticipant} 的聊天已经形成默认线路：一个抛、一个接，嘴上都挺淡定，记录里全是破绽。`
        : `这群的核心问题不是话多，是每个人都在自己的岗位上稳定发电。${topSender} 负责把局续上，其他人负责把话题加工成更抽象的形状。`,
    };
  }

  if (view === "time") {
    return {
      mode: (dna?.late_night_ratio ?? 0) >= 20 ? "阴间作息型" : "规律续航型",
      subtitle: "作息不是道德问题，但聊天记录会诚实暴露谁在深夜还不肯下线。",
      evidence: [
        { label: "高峰时段", value: dna ? `${dna.top_hour}:00` : "暂无", note: "最容易开聊的时间窗口" },
        { label: "深夜占比", value: pct(dna?.late_night_ratio), note: "越高越像集体守夜" },
        { label: "最长空窗", value: dna ? `${dna.longest_gap_days}天` : "暂无", note: "关系或群聊续航的掉线证据" },
      ],
      verdict: (dna?.late_night_ratio ?? 0) >= 20
        ? "深夜消息占比已经有点像值班表了，嘴上说随便聊聊，身体倒是很诚实地在凌晨继续营业。"
        : "节奏相对稳定，没到集体阴间作息的程度，但高峰时段一到，该冒泡的人还是会准时上班。",
    };
  }

  if (view === "language") {
    return {
      mode: relationship ? "暗号复用型" : "梗词循环型",
      subtitle: "语言习惯是最难演的，谁爱说什么、谁跟谁共享暗号，数据全记着。",
      evidence: [
        { label: "高频词", value: topKeywordLine, note: "群体脑回路的露馅现场" },
        { label: "共同词", value: topCommonWords, note: "两个人或多人共享的暗号库存" },
        { label: "短语", value: topNgrams, note: "复读越多，人设越稳" },
      ],
      verdict: relationship
        ? "共同词不是普通词库，是两个人偷懒沟通的压缩包。别人看着像废话，你们自己知道每个词后面接哪段戏。"
        : "高频词一排开，群体精神状态基本不用审了：不是没话找话，是把同一套梗盘到包浆还舍不得停。",
    };
  }

  if (view === "emoji") {
    return {
      mode: "表情代偿型",
      subtitle: "表情包是聊天里的替身攻击，越懒得解释，越爱甩图解决。",
      evidence: [
        { label: "头号表情", value: topEmoji, note: "最常用的情绪快捷键" },
        { label: "表情种类", value: compactNumber(stats.emojis.length), note: "图库越厚，嘴越懒" },
        { label: "专属表情", value: compactNumber(stats.emoji_specificity.length), note: "谁的表情包已经长出个人产权" },
      ],
      verdict: "这里的表情包不是辅助表达，是直接接管表达。能用一张图解决的，绝不浪费三行字，突出一个精神外包。",
    };
  }

  if (view === "interaction") {
    return {
      mode: relationship ? "一抛一接型" : "供氧分层型",
      subtitle: "互动结构比消息数更狠：谁开局、谁续命、谁只负责围观，一眼就能分层。",
      evidence: [
        { label: "主动破冰", value: topInitiator, note: "最常把沉默撕开的人" },
        { label: "@ 提及", value: compactNumber(stats.at_mention_stats.length), note: "被点名的社交债" },
        { label: "互动边", value: compactNumber(stats.relationship_edges.length), note: "关系网不是靠感觉画的" },
      ],
      verdict: relationship
        ? "这类互动最典型：一个人负责把球抛出去，另一个人嘴上嫌弃但手上接得很稳，装不熟装得像流程管理。"
        : "群聊不是人人平等，至少聊天记录不这么认为。有人负责供氧，有人负责加工，有人负责在关键时刻冒泡刷存在感。",
    };
  }

  if (view === "emotion") {
    return {
      mode: (stats.sentiment_overview?.negative_ratio ?? 0) > 25 ? "互怼升温型" : "嘴硬温热型",
      subtitle: "情绪不是看一句话甜不甜，而是看长期底色到底在往哪里偏。",
      evidence: [
        { label: "情绪标签", value: stats.sentiment_overview?.label || "暂无", note: "整体聊天底色" },
        { label: "正向比例", value: pct(stats.sentiment_overview?.positive_ratio), note: "热乎气还剩多少" },
        { label: "负向比例", value: pct(stats.sentiment_overview?.negative_ratio), note: "互怼浓度的量化证据" },
      ],
      verdict: (stats.sentiment_overview?.negative_ratio ?? 0) > 25
        ? "吐槽和互怼含量不低，但这不等于关系差，更像一群人把关心包装成犯欠，嘴硬得很有职业素养。"
        : "整体温度还算稳，没那么多大开大合，属于表面淡定、底层持续供暖的聊天生态。",
    };
  }

  if (view === "media") {
    return {
      mode: "成分复杂型",
      subtitle: "消息类型能看出聊天靠什么续命：靠文字、靠图、靠链接，还是靠撤回制造悬念。",
      evidence: [
        { label: "主类型", value: topMessageType, note: "最常用的表达方式" },
        { label: "撤回", value: compactNumber(stats.recall_stats?.total_recalls), note: "说出口又后悔的现场" },
        { label: "链接域名", value: compactNumber(stats.link_stats.length), note: "资讯搬运和外部话题来源" },
      ],
      verdict: "如果文本是主食，图片表情就是调味，链接和撤回是加戏。消息结构越杂，越说明这段聊天不是单线叙事，是多人即兴拼盘。",
    };
  }

  if (view === "relationship") {
    return {
      mode: relationship ? "装不熟互烦型" : "熟人局分工型",
      subtitle: relationship ? "不替你们定义现实关系，只判聊天里的互动模式。" : "群聊里的关系不是谁话多谁赢，而是谁能影响节奏。",
      evidence: [
        { label: "A 发言", value: compactNumber(stats.dual_report_extras?.p1_message_count), note: firstParticipant },
        { label: "B 发言", value: compactNumber(stats.dual_report_extras?.p2_message_count), note: secondParticipant },
        { label: "里程碑", value: compactNumber(stats.relationship_milestones.length), note: "聊天关系变化的节点" },
      ],
      verdict: relationship
        ? "这类聊天最有意思的地方是双方都不一定直说，但节奏会替人说话。谁主动、谁接住、谁把废话变成暗号，记录里藏不住。"
        : "群聊关系像一张小型生态网：龙王负责供氧，熟人负责接梗，潜水员负责让大家误以为群还很正常。",
    };
  }

  if (view === "quotes") {
    return {
      mode: "原话破防型",
      subtitle: "真实片段比统计更有杀伤力，因为它能证明这份锐评不是凭空嘴贱。",
      evidence: [
        { label: "精选片段", value: compactNumber(report.quotes.length), note: "可直接回放的代表语句" },
        { label: "证据卡", value: compactNumber(report.content_highlights?.length), note: "带上下文的判断依据" },
        { label: "高分原话", value: compactNumber(stats.famous_quotes.length), note: "系统筛出的名场面候选" },
      ],
      verdict: "看完原话再看结论，味就对了。很多关系和群聊不是被分析出来的，是自己在聊天记录里当场招供的。",
    };
  }

  return {
    mode: relationship ? "稳定续费型" : "循环开播型",
    subtitle: "预测不装大师，只看已有聊天信号会把大家带到哪里。",
    evidence: [
      { label: "预测条目", value: compactNumber(stats.predictions.length), note: "下一阶段看点" },
      { label: "人格勋章", value: compactNumber(stats.personality_badges.length), note: "谁的人设已经被数据钉住" },
      { label: "主动者", value: topInitiator, note: "最可能开启下一轮聊天" },
    ],
    verdict: relationship
      ? "只要主动和接话这套循环还在，聊天大概率会继续续费。区别只是下一次谁先装作随手问一句。"
      : "这个群不会突然变正经，顶多换一批梗继续开播。只要龙王还在，冷场就只是临时加载中。",
  };
}

function InsightNav({ active, report }: { active: InsightView; report: ReportPayload }) {
  return (
    <div className="insight-nav-grid" aria-label="分析页导航">
      {VIEW_META.map((item) => (
        <Link
          className={`insight-nav-item ${item.id === active ? "insight-nav-active" : ""}`}
          key={item.id}
          to={`/insights/${report.report_id}/${item.id}`}
        >
          <ViewIcon id={item.id} />
          <span>{item.title}</span>
        </Link>
      ))}
    </div>
  );
}

function InsightBriefBlock({ text }: { text: string }) {
  const paragraphs = text.split(/\n+/).map((item) => item.trim()).filter(Boolean);
  return (
    <div className="insight-brief-text">
      {(paragraphs.length ? paragraphs : [text]).map((paragraph, index) => (
        <p key={`${paragraph.slice(0, 16)}-${index}`}>{paragraph}</p>
      ))}
    </div>
  );
}

function ModeDiagnosisPanel({ diagnosis }: { diagnosis: ModeDiagnosis }) {
  return (
    <section className="report-section insight-diagnosis-section">
      <div className="section-copy">
        <p className="eyebrow">模式判定</p>
        <h2>{diagnosis.mode}</h2>
        <p>{diagnosis.subtitle}</p>
      </div>
      <div className="insight-evidence-grid">
        {diagnosis.evidence.map((item) => (
          <article className="insight-evidence-card" key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.note}</p>
          </article>
        ))}
      </div>
      <p className="insight-verdict">{diagnosis.verdict}</p>
    </section>
  );
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
  const diagnosis = buildModeDiagnosis(report, meta.id);

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
          <h1>{meta.title}</h1>
          <p className="report-tagline">{meta.body}</p>
        </section>
        <InsightNav active={meta.id} report={report} />
        <SectionBlock title="贴吧判词">
          <InsightBriefBlock text={getAiBrief(report, meta.id)} />
        </SectionBlock>
        <ModeDiagnosisPanel diagnosis={diagnosis} />
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
                {next ? `下一页：${next.title}` : "中间分析页已完成，进入最终报告。"}
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
      <ContentHighlightsPanel
        compact
        highlights={report.content_highlights}
        title="这份聊天最有内容的几处"
        intro="优先读这些真实对话片段，再结合统计结果判断群聊氛围、关系模式和名场面。"
      />
      <SectionBlock title="聊天总账">
        <AnnualSummaryCard annual={stats.annual_summary} />
      </SectionBlock>
      <SectionBlock title="聊天基因">
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
      <SectionBlock title="时间分布">
        <TimeProfilePanel hourly={stats.hourly_distribution} peakDay={stats.peak_day} weekday={stats.weekday_distribution} yearly={stats.yearly_monthly} />
      </SectionBlock>
      <SectionBlock title="作息指纹">
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
      <SectionBlock title="词云与口头禅">
        <div className="v2-stack">
          <KeywordCloud keywords={stats.keywords} />
          <WordSpecificityChart items={stats.word_specificity} />
          <WordCommonalityChart items={stats.word_commonality} />
        </div>
      </SectionBlock>
      <SectionBlock title="高频短语">
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
      <SectionBlock title="表情偏好">
        <div className="v2-stack">
          <EmojiBoard emojis={stats.emojis} />
          <EmojiSpecificityChart catalog={stats.emojis} items={stats.emoji_specificity} />
          <EmojiCommonalityPanel byHour={stats.emoji_time_distribution} items={stats.emoji_commonality} />
        </div>
      </SectionBlock>
      {stats.dual_report_extras ? (
        <SectionBlock title="双人专属表情">
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
      <SectionBlock title="互动网络">
        <InteractionMatrixPanel items={stats.interaction_matrix} mentions={stats.at_mention_stats} sendRatio={stats.send_ratio} />
      </SectionBlock>
      <SectionBlock title="主动与分享">
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
      <SectionBlock title="总体温度">
        <div className="v2-stack">
          {stats.sentiment_overview ? <SentimentGauge sentiment={stats.sentiment_overview} /> : <p className="muted">暂无情绪数据。</p>}
          <MonthlySentimentTrend data={stats.monthly_sentiment} />
        </div>
      </SectionBlock>
      <SectionBlock title="成员情绪标签">
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
      <SectionBlock title="消息结构">
        <div className="v2-stack">
          <MessageTypeChart types={stats.message_type_breakdown} />
          <MessageTypeEvolutionPanel evolution={stats.message_type_evolution} recall={stats.recall_stats} redPacket={stats.red_packet_overview} />
        </div>
      </SectionBlock>
      <SectionBlock title="链接趋势">
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
      <SectionBlock title="关系结构">
        <div className="v2-stack">
          <RelationshipMap edges={stats.relationship_edges} />
          <RelationshipScoreboard metrics={stats.relationship_metrics ?? []} />
          {stats.dual_report_extras ? <DualReportExtrasCard extras={stats.dual_report_extras} /> : null}
        </div>
      </SectionBlock>
      <SectionBlock title="走势与里程碑">
        <div className="v2-stack">
          <RelationshipCandles report={report} />
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
      <ContentHighlightsPanel
        compact
        highlights={report.content_highlights}
        title="带证据的名场面"
        intro="这里展示的是实际参考的上下文，不只是孤立的一句金句。"
      />
      <SectionBlock title="带标注的名场面">
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
      <SectionBlock title="关系开场">
        <div className="v2-stack">
          {stats.first_chat ? <FirstChatCard data={stats.first_chat} /> : <p className="muted">暂无最初对话记录。</p>}
        </div>
      </SectionBlock>
    </>
  );
}

function PredictionsView({ report }: { report: ReportPayload }) {
  const stats = report.stats;
  return (
    <>
      <SectionBlock title="下一阶段预测">
        <div className="v2-stack">
          <PredictionsCard predictions={stats.predictions} />
          <PersonalityBadgeGrid badges={stats.personality_badges} />
        </div>
      </SectionBlock>
      <SectionBlock title="参考的聊天信号">
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
        <p>中间分析页加载中...</p>
      </main>
    );
  }

  return (
    <PageShell index={activeIndex} meta={activeMeta} report={report}>
      {renderView(activeMeta.id, report)}
    </PageShell>
  );
}
