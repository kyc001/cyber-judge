import { ChangeEvent, DragEvent, FormEvent, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  FileText,
  HeartHandshake,
  Loader2,
  MessageCircleMore,
  ShieldCheck,
  Upload,
  Wand2,
} from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { analyzeChat } from "../api/client";
import { Button } from "../components/ui/Button";
import type { ReportType } from "../contracts/report";
import { buildAnalyzeRequest } from "../utils/parser";

const MAX_FILE_SIZE = 8 * 1024 * 1024;
const groupSampleText = `2026-05-24 22:10 A同学: 我只是随便问问，这个项目怎么突然就开始了？
2026-05-24 22:11 B同学: 因为你问得太像需求评审了。
2026-05-24 22:12 C同学: 我睡了，真的睡了，最后看一眼手机。
2026-05-24 22:14 D同学: 别吵，我正在严肃地摸鱼。`;

const relationshipSampleText = `2026-05-24 09:18 A同学: 我到了，你今天别忘了带伞。
2026-05-24 09:21 B同学: 你怎么比天气预报还准。
2026-05-24 22:46 B同学: 你随便，但别太晚睡。
2026-05-24 22:48 A同学: 嘴硬关心是吧，我懂。`;

export function UploadPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const initialReportType: ReportType =
    searchParams.get("type") === "relationship" ? "relationship" : "group_roast";
  const [reportType, setReportType] = useState<ReportType>(initialReportType);
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("");
  const [anonymized, setAnonymized] = useState(true);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const messageCount = useMemo(
    () => text.split(/\r?\n/).filter((line) => line.trim()).length,
    [text],
  );
  const activeSampleText =
    reportType === "relationship" ? relationshipSampleText : groupSampleText;

  async function readFile(file: File) {
    setError("");

    if (!file.name.endsWith(".txt")) {
      setError("MVP 当前只支持 .txt 文件。html / zip 等格式先交给后续版本。");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError("文件超过 8MB。请先裁剪聊天记录，或等 2 号的大文件分片解析接入。");
      return;
    }

    setFileName(file.name);
    setText(await file.text());
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      void readFile(file);
    }
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      void readFile(file);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (text.trim().length < 20) {
      setError("聊天文本太短，至少贴几行对话，判官才有发挥空间。");
      return;
    }

    setIsSubmitting(true);
    try {
      const request = buildAnalyzeRequest(
        text,
        fileName ? "wechat_txt" : "paste",
        anonymized,
        reportType,
      );
      const response = await analyzeChat(request);
      navigate(`/analyzing?reportId=${response.report_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "分析请求失败，请稍后再试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page upload-page">
      <nav className="simple-nav">
        <Link className="brand" to="/">
          <span>判</span>
          赛博判官
        </Link>
        <div className="nav-links">
          <Link to="/report/demo-report-001">群聊 Demo</Link>
          <Link to="/report/demo-relationship-001">双人 Demo</Link>
        </div>
      </nav>

      <section className="upload-layout">
        <form className="upload-panel" onSubmit={handleSubmit}>
          <div className="section-copy">
            <p className="eyebrow">Upload</p>
            <h1>拖一个 txt，或者直接粘贴聊天文本。</h1>
            <p>先选择报告类型，再由前端 mock 解析器转成统一消息 schema。</p>
          </div>

          <div className="report-type-grid" role="radiogroup" aria-label="选择报告类型">
            <button
              aria-checked={reportType === "group_roast"}
              className={`type-option ${reportType === "group_roast" ? "type-option-active" : ""}`}
              onClick={() => setReportType("group_roast")}
              role="radio"
              type="button"
            >
              <MessageCircleMore size={20} />
              <strong>群聊锐评</strong>
              <span>龙王榜、群人设、元宝语录</span>
            </button>
            <button
              aria-checked={reportType === "relationship"}
              className={`type-option ${reportType === "relationship" ? "type-option-active" : ""}`}
              onClick={() => setReportType("relationship")}
              role="radio"
              type="button"
            >
              <HeartHandshake size={20} />
              <strong>双人关系</strong>
              <span>主动程度、默契雷达、关系金句</span>
            </button>
          </div>

          <input
            accept=".txt,text/plain"
            hidden
            onChange={handleFileChange}
            ref={inputRef}
            type="file"
          />

          <label
            className="drop-zone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
          >
            <FileText size={30} />
            <strong>{fileName || "拖拽 txt 到这里"}</strong>
            <span>或点击选择文件，最大 8MB</span>
            <button
              className="inline-link"
              onClick={() => inputRef.current?.click()}
              type="button"
            >
              选择文件
            </button>
          </label>

          <label className="textarea-label">
            <span>粘贴文本</span>
            <textarea
              onChange={(event) => setText(event.target.value)}
              placeholder={activeSampleText}
              value={text}
            />
          </label>

          <div className="upload-options">
            <label className="toggle-row">
              <input
                checked={anonymized}
                onChange={(event) => setAnonymized(event.target.checked)}
                type="checkbox"
              />
              <span>
                <ShieldCheck size={18} />
                默认脱敏昵称
              </span>
            </label>
            <button className="inline-link" onClick={() => setText(activeSampleText)} type="button">
              填入样例文本
            </button>
          </div>

          <div className="upload-meta">
            <span>{messageCount} 行候选消息</span>
            <span>{reportType === "relationship" ? "双人关系报告" : "群聊锐评报告"}</span>
            <span>{anonymized ? "会发送代号昵称" : "保留原昵称给后端"}</span>
          </div>

          {error ? (
            <p className="error-text">
              <AlertCircle size={18} />
              {error}
            </p>
          ) : null}

          <Button
            disabled={isSubmitting}
            icon={isSubmitting ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
            type="submit"
          >
            {isSubmitting ? "提交中" : "开始分析"}
          </Button>
        </form>

        <aside className="tutorial-panel">
          <p className="eyebrow">Tutorial Slot</p>
          <h2>给 1 号素材预留的位置</h2>
          <ol>
            <li>微信 PC 端打开目标聊天</li>
            <li>导出或复制 txt 文本</li>
            <li>回到这里上传，开启默认脱敏</li>
          </ol>
          <div className="tutorial-video">
            <Upload />
            <span>30s GIF / 视频占位</span>
          </div>
        </aside>
      </section>
    </main>
  );
}
