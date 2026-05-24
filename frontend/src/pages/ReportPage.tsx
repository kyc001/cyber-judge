import { useEffect, useMemo, useRef, useState } from "react";
import { Copy, Download, Home, ImageDown, Loader2, Share2 } from "lucide-react";
import html2canvas from "html2canvas";
import { Link, useParams } from "react-router-dom";
import { createShare, getReport } from "../api/client";
import { ReportRenderer } from "../components/report/ReportRenderer";
import { Button } from "../components/ui/Button";
import type { ReportPayload } from "../contracts/report";
import { getPublicUrl } from "../utils/format";

export function ReportPage() {
  const { id = "demo-report-001" } = useParams();
  const reportRef = useRef<HTMLElement | null>(null);
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [shareUrl, setShareUrl] = useState(
    getPublicUrl(`/share/${id.includes("relationship") ? "demo-relationship" : "demo-longwang"}`),
  );
  const [notice, setNotice] = useState("");
  const [scrollPercent, setScrollPercent] = useState(0);

  const publicShareUrl = useMemo(() => shareUrl || getPublicUrl(`/share/${id}`), [id, shareUrl]);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    getReport(id)
      .then((payload) => {
        if (active) {
          setReport(payload);
          setShareUrl(
            getPublicUrl(
              `/share/${payload.share.slug || (payload.report_type === "relationship" ? "demo-relationship" : "demo-longwang")}`,
            ),
          );
        }
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "报告加载失败");
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    function updateScroll() {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setScrollPercent(max <= 0 ? 0 : Math.round((window.scrollY / max) * 100));
    }

    updateScroll();
    window.addEventListener("scroll", updateScroll, { passive: true });
    return () => window.removeEventListener("scroll", updateScroll);
  }, []);

  async function ensureShare() {
    const payload = await createShare(id);
    setShareUrl(payload.url);
    return payload.url;
  }

  async function copyLink() {
    try {
      const url = await ensureShare();
      await navigator.clipboard.writeText(url);
      setNotice("分享链接已复制");
    } catch {
      setNotice("复制失败，请手动复制地址栏链接");
    }
  }

  async function exportImage() {
    if (!reportRef.current) {
      return;
    }

    setIsExporting(true);
    setNotice("");
    try {
      const canvas = await html2canvas(reportRef.current, {
        backgroundColor: "#f7f0e8",
        scale: 2,
        useCORS: true,
      });
      const url = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.href = url;
      link.download = `${id}-report.png`;
      link.click();
      setNotice("长图已生成");
    } catch {
      setNotice("生成长图失败，稍后可以换浏览器再试");
    } finally {
      setIsExporting(false);
    }
  }

  async function systemShare() {
    try {
      const url = await ensureShare();
      if (!navigator.share) {
        setNotice("当前浏览器不支持系统分享，已为你生成链接");
        await navigator.clipboard.writeText(url);
        return;
      }

      await navigator.share({
        title: report?.title ?? "赛博判官聊天报告",
        text: report?.share.hook ?? "来测测你在群里是几号龙王",
        url,
      });
    } catch {
      setNotice("分享被取消或失败");
    }
  }

  if (isLoading) {
    return (
      <main className="page state-page">
        <Loader2 className="spin" />
        <p>报告加载中...</p>
      </main>
    );
  }

  if (error || !report) {
    return (
      <main className="page state-page">
        <h1>报告暂时走丢了</h1>
        <p>{error || "没有拿到可渲染的数据。"}</p>
        <Link className="btn btn-primary" to="/upload">
          重新上传
        </Link>
      </main>
    );
  }

  return (
    <main className="page report-page">
      <div className="scroll-progress" style={{ width: `${scrollPercent}%` }} />
      <nav className="report-toolbar">
        <Link className="icon-link" to="/" title="回到首页">
          <Home size={18} />
        </Link>
        <div className="toolbar-actions">
          <Button icon={<Copy size={18} />} onClick={copyLink} variant="secondary">
            复制链接
          </Button>
          <Button
            disabled={isExporting}
            icon={isExporting ? <Loader2 className="spin" size={18} /> : <ImageDown size={18} />}
            onClick={exportImage}
            variant="secondary"
          >
            保存长图
          </Button>
          <Button icon={<Share2 size={18} />} onClick={systemShare}>
            系统分享
          </Button>
        </div>
      </nav>

      {notice ? <div className="toast">{notice}</div> : null}
      <section ref={reportRef}>
        <ReportRenderer report={report} shareUrl={publicShareUrl} />
      </section>
      <div className="next-hint">
        <Download size={16} />
        滚到最后可保存分享卡片
      </div>
    </main>
  );
}
