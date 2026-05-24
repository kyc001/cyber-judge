import { useEffect, useState } from "react";
import QRCode from "qrcode";
import type { ReportPayload } from "../../contracts/report";

interface ShareCardProps {
  report: ReportPayload;
  shareUrl: string;
}

export function ShareCard({ report, shareUrl }: ShareCardProps) {
  const [qrCode, setQrCode] = useState("");

  useEffect(() => {
    let active = true;
    QRCode.toDataURL(shareUrl, {
      margin: 1,
      width: 168,
      color: {
        dark: "#202124",
        light: "#ffffff",
      },
    }).then((url) => {
      if (active) {
        setQrCode(url);
      }
    });

    return () => {
      active = false;
    };
  }, [shareUrl]);

  return (
    <section className="share-card" id="share-card">
      <div className="share-card-mark">{report.hero.visual}</div>
      <p className="eyebrow">{report.share.watermark}</p>
      <h2>{report.share.hook}</h2>
      <p>{report.hero.quote}</p>
      <div className="share-card-bottom">
        {qrCode ? <img alt="分享二维码" src={qrCode} /> : <div className="qr-placeholder" />}
        <span>扫码查看完整报告</span>
      </div>
    </section>
  );
}
