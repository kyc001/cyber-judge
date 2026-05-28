import { MessageSquareQuote, Sparkles } from "lucide-react";
import type { ContentHighlight } from "../../contracts/report";

interface ContentHighlightsPanelProps {
  highlights?: ContentHighlight[];
  title?: string;
  intro?: string;
  compact?: boolean;
}

const TAG_LABELS: Record<string, string> = {
  content: "内容",
  meme: "梗点",
  relationship: "关系",
  rhythm: "节奏",
  roast: "锐评",
  warmth: "温度",
};

function formatTime(ts?: string) {
  if (!ts) return "";
  return ts.replace("T", " ").slice(0, 16);
}

export function ContentHighlightsPanel({
  highlights,
  title = "AI 从真实对话里抓到的亮点",
  intro = "不只看谁发得多，而是把高信息密度的对话片段拿出来，看看梗、关系和情绪是怎么在原话里出现的。",
  compact = false,
}: ContentHighlightsPanelProps) {
  const visibleHighlights = (highlights ?? []).filter((item) => item.evidence?.length).slice(0, 5);
  if (!visibleHighlights.length) return null;

  return (
    <section className={`report-section content-highlight-section${compact ? " content-highlight-compact" : ""}`}>
      <div className="section-copy">
        <p className="eyebrow">Dialogue Evidence</p>
        <h2>{title}</h2>
        <p>{intro}</p>
      </div>
      <div className="content-highlight-grid">
        {visibleHighlights.map((highlight, index) => (
          <article className="content-highlight-card" key={highlight.id || `${highlight.title}-${index}`}>
            <div className="content-highlight-head">
              <span className="content-highlight-icon">
                {index === 0 ? <Sparkles size={18} /> : <MessageSquareQuote size={18} />}
              </span>
              <div>
                <strong>{highlight.title}</strong>
                <em>{TAG_LABELS[highlight.tag] ?? highlight.tag ?? "内容"}</em>
              </div>
            </div>
            <p className="content-highlight-insight">{highlight.insight}</p>
            <div className="dialogue-evidence" aria-label={`${highlight.title} 的真实对话证据`}>
              {highlight.evidence.slice(0, compact ? 3 : 4).map((line, lineIndex) => (
                <blockquote className="dialogue-line" key={`${line.sender}-${line.ts ?? ""}-${lineIndex}`}>
                  <span>
                    <strong>{line.sender || "匿名用户"}</strong>
                    {line.ts ? <time>{formatTime(line.ts)}</time> : null}
                  </span>
                  <p>{line.text}</p>
                </blockquote>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
