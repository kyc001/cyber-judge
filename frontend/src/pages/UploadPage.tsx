import { ChangeEvent, DragEvent, FormEvent, useMemo, useRef, useState } from "react";
import {
  AlertCircle, FileText, HeartHandshake, Loader2,
  MessageCircleMore, ShieldCheck, Wand2,
} from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { uploadRawChat } from "../api/client";
import { Button } from "../components/ui/Button";
import type { ReportType } from "../contracts/report";

const MAX_FILE_SIZE = 8 * 1024 * 1024;

interface UploadPreview {
  error?: string;
  messageCount: number;
  participantCount: number;
  dateRange: string;
  typeRows: { label: string; count: number }[];
  participants: string[];
  samples: { sender: string; time: string; content: string }[];
  recommendedType: ReportType;
}

const TYPE_LABELS: Record<number, string> = {
  1: "文字",
  3: "图片",
  34: "语音",
  43: "视频",
  47: "表情",
  49: "文件/链接",
  10000: "系统",
};

function buildUploadPreview(raw: string): UploadPreview | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    const data = JSON.parse(trimmed) as { messages?: Record<string, unknown>[] };
    const messages = Array.isArray(data.messages) ? data.messages : [];
    if (messages.length === 0) {
      return {
        error: "JSON 中没有识别到 messages 数组。",
        messageCount: 0,
        participantCount: 0,
        dateRange: "—",
        typeRows: [],
        participants: [],
        samples: [],
        recommendedType: "group_roast",
      };
    }

    const participants = Array.from(new Set(messages.map((item) => (
      String(item.senderDisplayName || item.senderUsername || "未知")
    ))));
    const typeCount = new Map<string, number>();
    const times = messages
      .map((item) => String(item.formattedTime || ""))
      .filter(Boolean)
      .sort();
    for (const item of messages) {
      const localType = Number(item.localType ?? 1);
      const label = TYPE_LABELS[localType] || "其他";
      typeCount.set(label, (typeCount.get(label) || 0) + 1);
    }

    return {
      messageCount: messages.length,
      participantCount: participants.length,
      dateRange: times.length > 0 ? `${times[0].slice(0, 10)} ~ ${times[times.length - 1].slice(0, 10)}` : "时间未知",
      typeRows: Array.from(typeCount.entries())
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => b.count - a.count),
      participants: participants.slice(0, 8),
      samples: messages.slice(0, 4).map((item) => ({
        sender: String(item.senderDisplayName || item.senderUsername || "未知"),
        time: String(item.formattedTime || "").slice(0, 16),
        content: String(item.content || `[${TYPE_LABELS[Number(item.localType ?? 0)] || "非文本消息"}]`).slice(0, 52),
      })),
      recommendedType: participants.length === 2 ? "relationship" : "group_roast",
    };
  } catch {
    return {
      error: "JSON 尚未解析成功，请检查括号、逗号或文件内容。",
      messageCount: 0,
      participantCount: 0,
      dateRange: "—",
      typeRows: [],
      participants: [],
      samples: [],
      recommendedType: "group_roast",
    };
  }
}

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
  const preview = useMemo(() => buildUploadPreview(text), [text]);

  async function readFile(file: File) {
    setError("");
    if (!file.name.endsWith(".json")) {
      setError("仅支持 WeFlow 导出的 .json 格式。");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("文件超过 8MB。");
      return;
    }
    setFileName(file.name);
    setText(await file.text());
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void readFile(file);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) void readFile(file);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (text.trim().length < 20) {
      setError("JSON 内容太短，请检查文件。");
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await uploadRawChat(text, reportType, anonymized);
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
          <span>判</span>赛博判官
        </Link>
        <div className="nav-links" />
      </nav>

      <section className="upload-layout">
        <form className="upload-panel" onSubmit={handleSubmit}>
          <div className="section-copy">
            <p className="eyebrow">Upload</p>
            <h1>上传 WeFlow 导出的 JSON 聊天记录。</h1>
            <p>仅支持 .json 格式。</p>
          </div>

          <div className="report-type-grid" role="radiogroup" aria-label="选择报告类型">
            <button
              aria-checked={reportType === "group_roast"}
              className={`type-option ${reportType === "group_roast" ? "type-option-active" : ""}`}
              onClick={() => setReportType("group_roast")}
              role="radio" type="button"
            >
              <MessageCircleMore size={20} />
              <strong>群聊锐评</strong>
              <span>龙王榜、群人设、名场面</span>
            </button>
            <button
              aria-checked={reportType === "relationship"}
              className={`type-option ${reportType === "relationship" ? "type-option-active" : ""}`}
              onClick={() => setReportType("relationship")}
              role="radio" type="button"
            >
              <HeartHandshake size={20} />
              <strong>双人关系</strong>
              <span>主动程度、默契雷达、关系金句</span>
            </button>
          </div>

          <input
            accept=".json,application/json"
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
            <strong>{fileName || "拖拽 .json 文件到这里"}</strong>
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
            <span>或直接粘贴 JSON 文本</span>
            <textarea
              onChange={(event) => setText(event.target.value)}
              placeholder="在此粘贴 WeFlow JSON 内容..."
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
              <span><ShieldCheck size={18} />默认脱敏昵称</span>
            </label>
          </div>

          {error ? (
            <p className="error-text">
              <AlertCircle size={18} />{error}
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
          {preview ? (
            <>
              <p className="eyebrow">Data Preview</p>
              <h2>上传前预检</h2>
              {preview.error ? (
                <p className="error-text"><AlertCircle size={18} />{preview.error}</p>
              ) : (
                <div style={{ display: "grid", gap: 14 }}>
                  <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
                    <div>
                      <span className="muted">消息数</span>
                      <strong style={{ display: "block", fontSize: "1.35rem" }}>{preview.messageCount.toLocaleString("zh-CN")}</strong>
                    </div>
                    <div>
                      <span className="muted">成员数</span>
                      <strong style={{ display: "block", fontSize: "1.35rem" }}>{preview.participantCount}</strong>
                    </div>
                  </div>
                  <p className="muted" style={{ margin: 0 }}>时间范围：{preview.dateRange}</p>
                  <p className="muted" style={{ margin: 0 }}>
                    建议模式：{preview.recommendedType === "relationship" ? "双人关系" : "群聊锐评"}
                    {preview.recommendedType !== reportType ? "，可以在左侧切换" : ""}
                  </p>
                  <div>
                    <strong>消息结构</strong>
                    <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
                      {preview.typeRows.slice(0, 5).map((row) => (
                        <div key={row.label} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                          <span>{row.label}</span>
                          <span className="muted">{row.count.toLocaleString("zh-CN")} 条</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <strong>成员预览</strong>
                    <p className="muted" style={{ margin: "8px 0 0" }}>{preview.participants.join("、")}</p>
                  </div>
                  <div>
                    <strong>开头样本</strong>
                    <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
                      {preview.samples.map((sample, index) => (
                        <p className="muted" key={`${sample.sender}-${index}`} style={{ margin: 0 }}>
                          {sample.time} · {sample.sender}: {sample.content}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              <p className="eyebrow">Tutorial</p>
              <h2>如何导出 JSON</h2>
              <ol>
                <li>使用 WeFlow 打开目标聊天</li>
                <li>导出聊天记录为 JSON</li>
                <li>回到这里上传，开启默认脱敏</li>
              </ol>
            </>
          )}
        </aside>
      </section>
    </main>
  );
}
