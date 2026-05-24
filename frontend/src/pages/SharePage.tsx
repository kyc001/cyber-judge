import { useEffect, useState } from "react";
import { Loader2, RotateCcw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { getShare } from "../api/client";
import { ShareCard } from "../components/report/ShareCard";
import type { SharePayload } from "../contracts/report";

export function SharePage() {
  const { slug = "demo-longwang" } = useParams();
  const [payload, setPayload] = useState<SharePayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getShare(slug)
      .then((result) => {
        if (active) {
          setPayload(result);
        }
      })
      .catch((caught) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "分享页加载失败");
        }
      });

    return () => {
      active = false;
    };
  }, [slug]);

  if (error) {
    return (
      <main className="page state-page">
        <h1>分享链接不可用</h1>
        <p>{error}</p>
        <Link className="btn btn-primary" to="/upload">
          我也要测
        </Link>
      </main>
    );
  }

  if (!payload) {
    return (
      <main className="page state-page">
        <Loader2 className="spin" />
        <p>分享页加载中...</p>
      </main>
    );
  }

  return (
    <main className="page share-page">
      <section className="share-shell">
        <ShareCard report={payload.report} shareUrl={payload.url} />
        <Link className="btn btn-primary" to="/upload">
          <RotateCcw size={18} />
          <span>我也要测</span>
        </Link>
      </section>
    </main>
  );
}
