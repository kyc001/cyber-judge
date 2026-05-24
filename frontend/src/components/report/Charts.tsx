import type {
  EmojiStat,
  HeatmapCell,
  KeywordStat,
  ParticipantStat,
  RadarMetric,
  RelationshipEdge,
  RelationshipMetric,
  TimelineEvent,
} from "../../contracts/report";
import { clamp, formatCount } from "../../utils/format";

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
              <div
                className="bar-fill"
                style={{ width: `${(item.message_count / max) * 100}%` }}
              />
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
    <div className="heatmap-wrap" aria-label="24 小时乘以 7 天热力图">
      <div className="heatmap-axis">
        <span>周一</span>
        <span>周三</span>
        <span>周五</span>
        <span>周日</span>
      </div>
      <div className="heatmap-grid">
        {cells.map((cell) => (
          <span
            className="heat-cell"
            key={`${cell.day}-${cell.hour}`}
            style={{ opacity: 0.15 + clamp(cell.value, 0, 1) * 0.85 }}
            title={`day ${cell.day + 1}, ${cell.hour}:00`}
          />
        ))}
      </div>
      <div className="heatmap-hours">
        <span>00:00</span>
        <span>12:00</span>
        <span>23:00</span>
      </div>
    </div>
  );
}

export function KeywordCloud({ keywords }: { keywords: KeywordStat[] }) {
  const max = Math.max(...keywords.map((item) => item.count), 1);

  return (
    <div className="keyword-cloud">
      {keywords.map((item) => (
        <span
          className={`keyword keyword-${item.tone}`}
          key={item.word}
          style={{ fontSize: `${0.92 + (item.count / max) * 1.55}rem` }}
        >
          {item.word}
        </span>
      ))}
    </div>
  );
}

export function RadarChart({ metrics }: { metrics: RadarMetric[] }) {
  const center = 120;
  const radius = 92;
  const points = metrics.map((item, index) => {
    const angle = (Math.PI * 2 * index) / metrics.length - Math.PI / 2;
    const scaled = radius * clamp(item.value / 100, 0, 1);
    return {
      x: center + Math.cos(angle) * scaled,
      y: center + Math.sin(angle) * scaled,
      labelX: center + Math.cos(angle) * (radius + 24),
      labelY: center + Math.sin(angle) * (radius + 24),
      label: item.label,
      value: item.value,
    };
  });
  const polygon = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="radar-wrap">
      <svg viewBox="0 0 240 240" role="img" aria-label="人格雷达图">
        {[0.25, 0.5, 0.75, 1].map((scale) => (
          <circle
            cx={center}
            cy={center}
            fill="none"
            key={scale}
            r={radius * scale}
            stroke="rgba(32, 32, 32, 0.12)"
          />
        ))}
        {points.map((point) => (
          <line
            key={point.label}
            stroke="rgba(32, 32, 32, 0.12)"
            x1={center}
            x2={point.labelX}
            y1={center}
            y2={point.labelY}
          />
        ))}
        <polygon fill="rgba(25, 132, 196, 0.22)" points={polygon} stroke="#1984c4" strokeWidth="3" />
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} fill="#f26b5e" r="4" />
            <text x={point.labelX} y={point.labelY} textAnchor="middle">
              {point.label}
            </text>
          </g>
        ))}
      </svg>
      <div className="radar-values">
        {metrics.map((item) => (
          <span key={item.label}>
            {item.label} {item.value}
          </span>
        ))}
      </div>
    </div>
  );
}

export function EmojiBoard({ emojis }: { emojis: EmojiStat[] }) {
  return (
    <div className="emoji-board">
      {emojis.map((item, index) => (
        <div className="emoji-tile" key={item.label}>
          <span className="emoji-rank">#{index + 1}</span>
          <strong>{item.label}</strong>
          <p>
            {formatCount(item.value)} 次
            {item.owner ? ` · ${item.owner} 偏爱` : ""}
          </p>
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
          <div>
            <strong>{event.title}</strong>
            <p>{event.body}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

export function RelationshipMap({ edges }: { edges: RelationshipEdge[] }) {
  if (edges.length === 0) {
    return <p className="muted">双人关系数据还没接入，先等 3 号统计模块投喂。</p>;
  }

  return (
    <div className="relationship-map">
      {edges.map((edge) => (
        <div className="relationship-edge" key={`${edge.from}-${edge.to}`}>
          <span>{edge.from}</span>
          <div className="edge-line" style={{ height: `${8 + edge.weight * 18}px` }} />
          <span>{edge.to}</span>
          <strong>{edge.label}</strong>
        </div>
      ))}
    </div>
  );
}

export function RelationshipScoreboard({
  metrics,
}: {
  metrics: RelationshipMetric[];
}) {
  if (metrics.length === 0) {
    return null;
  }

  return (
    <div className="relationship-scoreboard">
      {metrics.map((metric) => (
        <article className="relationship-score" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          <div className="score-track">
            <div style={{ width: `${clamp(metric.value, 0, 100)}%` }} />
          </div>
          <p>{metric.caption}</p>
        </article>
      ))}
    </div>
  );
}
