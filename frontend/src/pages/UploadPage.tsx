import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle, FileText, HeartHandshake, Loader2,
  MessageCircleMore, ShieldCheck, Wand2,
} from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  getWeFlowSessions,
  getWeFlowStatus,
  importWeFlowSession,
  uploadRawChat,
  type WeFlowSession,
} from "../api/client";
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
  1: "Text",
  3: "Image",
  34: "Voice",
  43: "Video",
  47: "Emoji",
  49: "File",
  10000: "System",
};

function hasLink(item: Record<string, unknown>): boolean {
  const content = String(item.content || "");
  const source = String(item.source || "");
  const linkUrl = String(item.linkUrl || "");
  const rawType = String(item.type || "");
  return Boolean(
    linkUrl.startsWith("http://") ||
    linkUrl.startsWith("https://") ||
    /https?:\/\//.test(content) ||
    /https?:\/\//.test(source) ||
    rawType.toLowerCase().includes("link") ||
    rawType.includes("链接")
  );
}

function detectPreviewType(item: Record<string, unknown>): string {
  const localType = Number(item.localType ?? 1);
  const content = String(item.content || "");
  const rawType = String(item.type || "");
  if (rawType.includes("红包") || content.includes("红包")) return "Red Packet";
  if (rawType.includes("转账") || content.includes("转账")) return "Transfer";
  if (localType === 1 && hasLink(item)) return "Link";
  if (localType === 49 && hasLink(item)) return "Link";
  return TYPE_LABELS[localType] || "Other";
}

function previewTime(item: Record<string, unknown>): string {
  const formatted = String(item.formattedTime || "");
  if (formatted) return formatted;
  const raw = Number(item.createTime || item.timestamp || 0);
  if (!Number.isFinite(raw) || raw <= 0) return "";
  const seconds = raw > 10_000_000_000 ? raw / 1000 : raw;
  const date = new Date(seconds * 1000);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().replace("T", " ").slice(0, 19);
}

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
      .map((item) => previewTime(item))
      .filter(Boolean)
      .sort();
    for (const item of messages) {
      const label = detectPreviewType(item);
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
        time: previewTime(item).slice(0, 16),
        content: String(item.content || `[${detectPreviewType(item)}]`).slice(0, 52),
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
  const [weflowBaseUrl, setWeflowBaseUrl] = useState("http://127.0.0.1:5031");
  const [weflowToken, setWeflowToken] = useState("");
  const [weflowSessions, setWeflowSessions] = useState<WeFlowSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [weflowSearch, setWeflowSearch] = useState("");
  const [weflowStartDate, setWeflowStartDate] = useState("");
  const [weflowEndDate, setWeflowEndDate] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [weflowMessage, setWeflowMessage] = useState("");
  const preview = useMemo(() => buildUploadPreview(text), [text]);
  const sortedWeFlowSessions = useMemo(() => {
    const keyword = weflowSearch.trim().toLowerCase();
    return [...weflowSessions]
      .filter((session) => {
        if (!keyword) return true;
        return `${session.name} ${session.id}`.toLowerCase().includes(keyword);
      })
      .sort((a, b) => Number(b.last_message_at || 0) - Number(a.last_message_at || 0));
  }, [weflowSessions, weflowSearch]);

  useEffect(() => {
    if (sortedWeFlowSessions.length === 0) {
      setSelectedSessionId("");
      return;
    }
    if (!sortedWeFlowSessions.some((session) => session.id === selectedSessionId)) {
      setSelectedSessionId(sortedWeFlowSessions[0].id);
    }
  }, [selectedSessionId, sortedWeFlowSessions]);

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

  async function handleLoadWeFlowSessions() {
    setError("");
    setWeflowMessage("正在连接本地 WeFlow API...");
    setIsLoadingSessions(true);
    try {
      const status = await getWeFlowStatus(weflowBaseUrl);
      if (!status.running) {
        setWeflowMessage(`未连接到 WeFlow API。状态码：${status.status_code}；详情：${status.detail || "无返回"}`);
        return;
      }
      setWeflowMessage("WeFlow API 已连接，正在读取会话...");
      const sessions = await getWeFlowSessions(weflowBaseUrl, weflowToken, weflowSearch);
      const sorted = [...sessions].sort((a, b) => Number(b.last_message_at || 0) - Number(a.last_message_at || 0));
      setWeflowSessions(sorted);
      setSelectedSessionId(sorted[0]?.id ?? "");
      if (sessions.length === 0) {
        setWeflowMessage("已连接 WeFlow，但没有读取到会话。请确认 WeFlow 已完成数据加载。");
      } else {
        setWeflowMessage(`已读取 ${sessions.length} 个 WeFlow 会话，请选择后导入。`);
      }
    } catch (caught) {
      setWeflowMessage(caught instanceof Error ? caught.message : "读取 WeFlow 会话失败。");
    } finally {
      setIsLoadingSessions(false);
    }
  }

  async function handleImportWeFlowSession() {
    setError("");
    setWeflowMessage("");
    if (!selectedSessionId) {
      setWeflowMessage("请先选择一个 WeFlow 会话。");
      return;
    }
    setIsSubmitting(true);
    try {
      setWeflowMessage("正在从 WeFlow 导入该会话...");
      const response = await importWeFlowSession(
        weflowBaseUrl,
        weflowToken,
        selectedSessionId,
        reportType,
        anonymized,
        weflowStartDate,
        weflowEndDate,
      );
      navigate(`/analyzing?reportId=${response.report_id}`);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "从 WeFlow 导入失败。";
      if (message.includes("No messages were imported") || message.includes("selected time range")) {
        setWeflowMessage("该时间段没有聊天记录，请调整开始日期或结束日期。");
      } else {
        setWeflowMessage(message);
      }
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
              <span>主动程度、共同语言、关系金句</span>
            </button>
          </div>

          <div style={{ display: "grid", gap: 12, padding: 16, border: "1px solid var(--border)", borderRadius: 8 }}>
            <div className="section-copy" style={{ gap: 4 }}>
              <p className="eyebrow">WeFlow API</p>
              <h2 style={{ margin: 0, fontSize: "1.05rem" }}>从本地 WeFlow 一键导入</h2>
              <p style={{ margin: 0 }}>在 WeFlow 中打开“设置 → API 服务 → 启动服务”，再读取会话。</p>
            </div>
            <label className="textarea-label">
              <span>API 地址</span>
              <input
                onChange={(event) => setWeflowBaseUrl(event.target.value)}
                placeholder="http://127.0.0.1:5031"
                type="text"
                value={weflowBaseUrl}
              />
            </label>
            <label className="textarea-label">
              <span>Access Token（如 WeFlow 开启鉴权则填写）</span>
              <input
                onChange={(event) => setWeflowToken(event.target.value)}
                placeholder="可留空"
                type="password"
                value={weflowToken}
              />
            </label>
            <label className="textarea-label">
              <span>搜索最近聊天的人或群聊</span>
              <input
                onChange={(event) => setWeflowSearch(event.target.value)}
                placeholder="输入昵称、群名或会话 ID"
                type="search"
                value={weflowSearch}
              />
            </label>
            <Button
              disabled={isLoadingSessions}
              icon={isLoadingSessions ? <Loader2 className="spin" size={18} /> : <MessageCircleMore size={18} />}
              onClick={handleLoadWeFlowSessions}
              type="button"
            >
              {isLoadingSessions ? "读取中" : "读取 WeFlow 会话"}
            </Button>
            {weflowMessage ? (
              <p className={weflowMessage.includes("失败") || weflowMessage.includes("未连接") || weflowMessage.includes("Request failed") ? "error-text" : "muted"} style={{ margin: 0 }}>
                {weflowMessage}
              </p>
            ) : null}
            {weflowSessions.length > 0 ? (
              <>
                <label className="textarea-label">
                  <span>选择会话</span>
                  <select
                    onChange={(event) => setSelectedSessionId(event.target.value)}
                    value={selectedSessionId}
                  >
                    {sortedWeFlowSessions.map((session) => (
                      <option key={session.id} value={session.id}>
                        {session.name} · {session.id}
                      </option>
                    ))}
                  </select>
                </label>
                <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
                  <label className="textarea-label">
                    <span>开始日期</span>
                    <input
                      onChange={(event) => setWeflowStartDate(event.target.value)}
                      type="date"
                      value={weflowStartDate}
                    />
                  </label>
                  <label className="textarea-label">
                    <span>结束日期</span>
                    <input
                      onChange={(event) => setWeflowEndDate(event.target.value)}
                      type="date"
                      value={weflowEndDate}
                    />
                  </label>
                </div>
                <Button
                  disabled={isSubmitting}
                  icon={isSubmitting ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
                  onClick={handleImportWeFlowSession}
                  type="button"
                >
                  {isSubmitting ? "导入中" : "导入该会话并分析"}
                </Button>
              </>
            ) : null}
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


