import type { ReportPayload, ReportSection } from "../../contracts/report";
import {
  DragonRanking,
  EmojiBoard,
  Heatmap,
  KeywordCloud,
  RadarChart,
  RelationshipMap,
  RelationshipScoreboard,
  Timeline,
} from "./Charts";
import { ShareCard } from "./ShareCard";

interface ReportRendererProps {
  report: ReportPayload;
  shareUrl: string;
}

function renderChart(report: ReportPayload, section: ReportSection) {
  switch (section.type) {
    case "dragon_rank":
      return <DragonRanking participants={report.stats.participants} />;
    case "heatmap":
      return <Heatmap cells={report.stats.heatmap} />;
    case "keywords":
      return <KeywordCloud keywords={report.stats.keywords} />;
    case "radar":
      return <RadarChart metrics={report.stats.radar} />;
    case "emoji":
      return <EmojiBoard emojis={report.stats.emojis} />;
    case "timeline":
      return <Timeline events={report.stats.timeline} />;
    case "relationship":
      return (
        <div className="relationship-stack">
          <RelationshipMap edges={report.stats.relationship_edges} />
          <RelationshipScoreboard metrics={report.stats.relationship_metrics ?? []} />
        </div>
      );
    default:
      return null;
  }
}

export function ReportRenderer({ report, shareUrl }: ReportRendererProps) {
  return (
    <article className="report-renderer">
      <section className="report-hero">
        <div className="report-mark">{report.hero.visual}</div>
        <p className="eyebrow">{report.hero.kicker}</p>
        <h1>{report.title}</h1>
        <p className="report-tagline">{report.tagline}</p>
        <blockquote>{report.hero.quote}</blockquote>
        <div className="tag-row">
          {report.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      </section>

      {report.sections.map((section) => (
        <section className={`report-section report-section-${section.type}`} key={section.id}>
          <div className="section-copy">
            <p className="eyebrow">{section.type.replace("_", " ")}</p>
            <h2>{section.heading}</h2>
            <p>{section.body}</p>
          </div>
          {renderChart(report, section)}
        </section>
      ))}

      <section className="quote-gallery">
        <div className="section-copy">
          <p className="eyebrow">Quote Cards</p>
          <h2>{report.report_type === "relationship" ? "关系金句" : "元宝语录"}</h2>
          <p>
            {report.report_type === "relationship"
              ? "这组卡片更偏向两个人之间那些说不清但截图后很上头的句子。"
              : "5 号给真实 LLM 输出后，这里可以直接吃 `quotes[]` 渲染。"}
          </p>
        </div>
        <div className="quote-grid">
          {report.quotes.map((quote) => (
            <article className="quote-card" key={quote.id}>
              <span>{quote.icon}</span>
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
