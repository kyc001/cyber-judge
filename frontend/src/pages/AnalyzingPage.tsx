import { useEffect, useMemo, useState } from "react";
import { Brain, ChartNoAxesColumnIncreasing, MessageCircleMore } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

const copy = ["正在解析聊天记录", "正在计算统计特征", "正在整理代表片段", "正在生成报告"];
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const stepLabels: Record<string, string> = {
  stats: "统计特征提取",
  hero: "标题与封面",
  participants: "成员摘要",
  quotes: "代表片段",
  sections: "报告正文撰写",
  predictions: "趋势预测",
  insight_briefs: "中间页锐评",
  chat_dna: "聊天摘要",
  llm_single: "LLM 综合生成",
};

export function AnalyzingPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const reportId = searchParams.get("reportId") || "";
  const [progress, setProgress] = useState(8);
  const [steps, setSteps] = useState<{ step: string; status: string; error?: string }[]>([]);
  const [error, setError] = useState("");
  const phrase = useMemo(
    () => copy[Math.min(copy.length - 1, Math.floor(progress / 28))],
    [progress],
  );

  useEffect(() => {
    if (!reportId) return undefined;
    const source = new EventSource(`${API_BASE}/api/report/${reportId}/progress`);
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { type: string; step?: string; status?: string; error?: string };
        if (data.type === "progress" && data.step && data.status) {
          const step = data.step;
          const status = data.status;
          setSteps((prev) => {
            const next = prev.filter((item) => item.step !== step);
            return [...next, { step, status, error: data.error }];
          });
          if (status === "done") setProgress((prev) => Math.min(96, prev + 12));
        }
        if (data.type === "done") {
          setProgress(100);
          window.setTimeout(() => navigate(`/insights/${reportId}/summary`), 420);
        }
        if (data.type === "error") {
          setError(data.error || "报告生成失败");
        }
      } catch {
        // Ignore malformed progress events and continue polling.
      }
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, [navigate, reportId]);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      while (!cancelled) {
        if (cancelled) return;
        try {
          const res = await fetch(`${API_BASE}/api/report/${reportId}`);
          if (res.status === 200) {
            setProgress(100);
            setTimeout(() => navigate(`/insights/${reportId}/summary`), 420);
            return;
          }
          if (res.status === 202) setProgress((prev) => Math.min(95, prev + 5));
          if (res.status >= 400 && res.status !== 202) {
            const body = await res.text();
            setError(body || `报告生成失败 (${res.status})`);
            return;
          }
        } catch {
          // retry
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    poll();
    return () => { cancelled = true; };
  }, [navigate, reportId]);

  return (
    <main className="page analyzing-page">
      <section className="analyzing-card">
        <div className="analysis-icons">
          <MessageCircleMore />
          <ChartNoAxesColumnIncreasing />
          <Brain />
        </div>
        <p className="eyebrow">分析中</p>
        <h1>{phrase}...</h1>
        <p>正在分析聊天记录，请稍候。</p>
        {error ? <p className="muted">{error}</p> : null}
        <div className="progress-shell">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
        <span className="progress-label">{progress}%</span>
        {steps.length > 0 && (
          <div style={{ display: "grid", gap: 8, margin: "0 auto 20px", maxWidth: 420, textAlign: "left" }}>
            {steps.map((item) => (
              <div key={item.step} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <span>{stepLabels[item.step] || item.step}</span>
                <span className="muted">
                  {item.status === "done" ? "完成" : item.status === "error" ? "重试/降级" : "进行中"}
                </span>
              </div>
            ))}
          </div>
        )}
        <Link className="inline-link" to="/upload">重新上传</Link>
      </section>
    </main>
  );
}
