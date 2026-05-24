import { useEffect, useMemo, useState } from "react";
import { Brain, ChartNoAxesColumnIncreasing, MessageCircleMore } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

const copy = ["正在统计哈哈哈数量", "正在挖元宝语录", "正在让 AI 想锐评", "正在生成分享卡片"];

export function AnalyzingPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const reportId = searchParams.get("reportId") || "demo-report-001";
  const [progress, setProgress] = useState(8);
  const phrase = useMemo(
    () => copy[Math.min(copy.length - 1, Math.floor(progress / 28))],
    [progress],
  );

  useEffect(() => {
    const interval = window.setInterval(() => {
      setProgress((current) => Math.min(100, current + 7));
    }, 260);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (progress >= 100) {
      const timeout = window.setTimeout(() => navigate(`/report/${reportId}`), 420);
      return () => window.clearTimeout(timeout);
    }

    return undefined;
  }, [navigate, progress, reportId]);

  return (
    <main className="page analyzing-page">
      <section className="analyzing-card">
        <div className="analysis-icons">
          <MessageCircleMore />
          <ChartNoAxesColumnIncreasing />
          <Brain />
        </div>
        <p className="eyebrow">Analyzing</p>
        <h1>{phrase}...</h1>
        <p>mock 模式会在几秒内进入报告页，后端接入后这里改成真实轮询。</p>
        <div className="progress-shell">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
        <span className="progress-label">{progress}%</span>
        <Link className="inline-link" to="/upload">
          重新上传
        </Link>
      </section>
    </main>
  );
}
