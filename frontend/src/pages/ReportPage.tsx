import { useEffect, useMemo, useState } from "react";
import { BarChart3, Copy, Download, Home, Loader2, Share2, Upload } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { createShare, exportReport, getReport } from "../api/client";
import { ReportRenderer } from "../components/report/ReportRenderer";
import { Button } from "../components/ui/Button";
import { ThemeToggle } from "../theme/ThemeSystem";
import type { ExportFormat, ReportPayload } from "../contracts/report";
import { getPublicUrl } from "../utils/format";

export function ReportPage() {
  const { id } = useParams();
  const reportId = id || "";
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | "">("");
  const [shareUrl, setShareUrl] = useState(
    getPublicUrl(`/share/${reportId}`),
  );
  const [notice, setNotice] = useState("");
  const [scrollPercent, setScrollPercent] = useState(0);

  const publicShareUrl = useMemo(() => shareUrl || getPublicUrl(`/share/${reportId}`), [reportId, shareUrl]);

  // Load report
  useEffect(() => {
    let active = true;
    setIsLoading(true);
    getReport(reportId)
      .then((payload) => {
        if (active) {
          setReport(payload);
          setShareUrl(getPublicUrl(`/share/${payload.share.slug || reportId}`));
        }
      })
      .catch((caught) => {
        if (active) setError(caught instanceof Error ? caught.message : "报告加载失败");
      })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [reportId]);

  // Scroll progress
  useEffect(() => {
    function updateScroll() {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setScrollPercent(max <= 0 ? 0 : Math.round((window.scrollY / max) * 100));
    }
    window.addEventListener("scroll", updateScroll, { passive: true });
    return () => window.removeEventListener("scroll", updateScroll);
  }, []);

  // Copy link
  const ensureShareUrl = async () => {
    if (report?.share.slug) return publicShareUrl;
    const payload = await createShare(reportId);
    setReport(payload.report);
    setShareUrl(payload.url);
    return payload.url;
  };

  const copyLink = async () => {
    try {
      const url = await ensureShareUrl();
      await navigator.clipboard.writeText(url);
      setNotice("链接已复制");
    } catch { setNotice("分享链接生成失败"); }
    setTimeout(() => setNotice(""), 2000);
  };

  const exportFile = async (format: ExportFormat) => {
    if (exportingFormat) return;
    setExportingFormat(format);
    try {
      const data = await exportReport(reportId, format);
      const blob = new Blob([data.content], { type: data.content_type });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = data.filename;
      a.click(); URL.revokeObjectURL(url);
      setNotice(`${format.toUpperCase()}已下载`);
    } catch { setNotice("导出失败"); }
    setExportingFormat("");
    setTimeout(() => setNotice(""), 2000);
  };

  const systemShare = async () => {
    let url = publicShareUrl;
    try {
      url = await ensureShareUrl();
    } catch {
      setNotice("分享链接生成失败");
      setTimeout(() => setNotice(""), 2000);
      return;
    }
    if (navigator.share) {
      try { await navigator.share({ title: report?.title, url }); }
      catch {}
    } else { copyLink(); }
  };

  // Use counter for hero stats
  if (isLoading) {
    return (
      <main className="page report-page">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: "1rem" }}>
          <Loader2 className="spin" size={48} />
          <p style={{ color: "var(--text-secondary)" }}>加载报告中...</p>
        </div>
      </main>
    );
  }

  if (error || !report) {
    return (
      <main className="page report-page">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", flexDirection: "column", gap: "1rem" }}>
          <p>{error || "报告暂时走丢了"}</p>
          <Link to="/upload">重新上传</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="page report-page">
      <div className="scroll-progress" style={{ width: `${scrollPercent}%` }} />
      <nav className="report-toolbar">
        <Link className="icon-link" to="/" title="首页">
          <Home size={18} />
        </Link>
        <Link className="icon-link" to="/upload" title="上传新文件" style={{ marginLeft: 8 }}>
          <Upload size={18} />
        </Link>
        <Link className="icon-link" to={`/insights/${reportId}/annual`} title="年度分镜" style={{ marginLeft: 8 }}>
          <BarChart3 size={18} />
        </Link>
        <ThemeToggle />
        <div className="toolbar-actions">
          <Button icon={<Copy size={18} />} onClick={copyLink} variant="secondary">
            复制链接
          </Button>
          <Button
            disabled={Boolean(exportingFormat)}
            icon={exportingFormat === "json" ? <Loader2 className="spin" size={18} /> : <Download size={18} />}
            onClick={() => exportFile("json")}
            variant="secondary"
          >
            导出JSON
          </Button>
          <Button
            disabled={Boolean(exportingFormat)}
            icon={exportingFormat === "html" ? <Loader2 className="spin" size={18} /> : <Download size={18} />}
            onClick={() => exportFile("html")}
            variant="secondary"
          >
            导出HTML
          </Button>
          <Button icon={<Share2 size={18} />} onClick={systemShare}>
            系统分享
          </Button>
        </div>
      </nav>

      {notice ? <div className="toast">{notice}</div> : null}
      <section>
        <ReportRenderer report={report} shareUrl={publicShareUrl} />
      </section>
      <div className="next-hint">
        <Download size={16} />
        滚到最后可保存分享卡片
      </div>
    </main>
  );
}
