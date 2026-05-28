import { ChangeEvent, DragEvent, FormEvent, useMemo, useRef, useState } from "react";
import {
  AlertCircle, CalendarDays, FileText, HeartHandshake, Loader2,
  MessageCircleMore, RefreshCw, Search, ShieldCheck, Wand2,
} from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { exportWechatChatForAnalysis, getWechatChats, prepareWechatData, uploadRawChat } from "../api/client";
import { Button } from "../components/ui/Button";
import type { ReportType, WechatChatSummary } from "../contracts/report";

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

const WEFLOW_TYPE_LABELS: Record<number, string> = {
  1: "文字",
  3: "图片",
  34: "语音",
  43: "视频",
  47: "表情",
  49: "文件/链接",
  10000: "系统",
};

const WECHAT_TYPE_LABELS: Record<string, string> = {
  text: "文字",
  image: "图片",
  voice: "语音",
  sticker: "表情",
  video: "视频",
  link_or_file: "文件/链接",
  transfer: "转账",
  system: "系统",
  recall: "撤回",
};

function formatUnixTime(value: unknown) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds) || seconds <= 0) return "";
  return new Date(seconds * 1000).toISOString().slice(0, 16).replace("T", " ");
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
        dateRange: "-",
        typeRows: [],
        participants: [],
        samples: [],
        recommendedType: "group_roast",
      };
    }

    const isWechatDecrypt = "timestamp" in messages[0];
    const participants = Array.from(new Set(messages.map((item) => {
      if (isWechatDecrypt) return String(item.sender || "未知");
      return String(item.senderDisplayName || item.senderUsername || "未知");
    })));
    const typeCount = new Map<string, number>();
    const times = messages
      .map((item) => isWechatDecrypt ? formatUnixTime(item.timestamp) : String(item.formattedTime || ""))
      .filter(Boolean)
      .sort();

    for (const item of messages) {
      const label = isWechatDecrypt
        ? WECHAT_TYPE_LABELS[String(item.type || "text")] || "其他"
        : WEFLOW_TYPE_LABELS[Number(item.localType ?? 1)] || "其他";
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
        sender: isWechatDecrypt
          ? String(item.sender || "未知")
          : String(item.senderDisplayName || item.senderUsername || "未知"),
        time: isWechatDecrypt
          ? formatUnixTime(item.timestamp)
          : String(item.formattedTime || "").slice(0, 16),
        content: String(item.content || item.transcription || "[非文本消息]").slice(0, 52),
      })),
      recommendedType: participants.length === 2 ? "relationship" : "group_roast",
    };
  } catch {
    return {
      error: "JSON 尚未解析成功，请检查括号、逗号或文件内容。",
      messageCount: 0,
      participantCount: 0,
      dateRange: "-",
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
  const [wechatQuery, setWechatQuery] = useState("");
  const [wechatStart, setWechatStart] = useState("");
  const [wechatEnd, setWechatEnd] = useState("");
  const [wechatChats, setWechatChats] = useState<WechatChatSummary[]>([]);
  const [selectedWechat, setSelectedWechat] = useState("");
  const [wechatError, setWechatError] = useState("");
  const [wechatTotal, setWechatTotal] = useState(0);
  const [isLoadingWechat, setIsLoadingWechat] = useState(false);
  const [isPreparingWechat, setIsPreparingWechat] = useState(false);
  const [wechatPrepareMessage, setWechatPrepareMessage] = useState("");
  const [isWechatSubmitting, setIsWechatSubmitting] = useState(false);
  const preview = useMemo(() => buildUploadPreview(text), [text]);

  async function readFile(file: File) {
    setError("");
    if (!file.name.endsWith(".json")) {
      setError("仅支持 .json 格式。");
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

  async function handleLoadWechatChats() {
    setWechatError("");
    setIsLoadingWechat(true);
    try {
      const response = await getWechatChats({
        query: wechatQuery,
        limit: 80,
        startTime: wechatStart,
        endTime: wechatEnd,
      });
      setWechatChats(response.chats);
      setWechatTotal(response.total);
      if (response.chats[0] && !selectedWechat) {
        setSelectedWechat(response.chats[0].username);
        setReportType(response.chats[0].kind === "single" ? "relationship" : "group_roast");
      }
    } catch (caught) {
      setWechatError(caught instanceof Error ? caught.message : "读取微信会话失败。");
    } finally {
      setIsLoadingWechat(false);
    }
  }

  async function handlePrepareWechatData() {
    setWechatError("");
    setWechatPrepareMessage("");
    setIsPreparingWechat(true);
    try {
      const status = await prepareWechatData(false);
      setWechatPrepareMessage(status.message || (status.decrypted ? "微信数据已准备好" : "准备流程已完成"));
      await handleLoadWechatChats();
    } catch (caught) {
      setWechatError(
        caught instanceof Error
          ? caught.message
          : "准备微信数据失败。请确认微信已登录，并用管理员身份启动 Cyber Judge。"
      );
    } finally {
      setIsPreparingWechat(false);
    }
  }

  async function handleWechatSubmit() {
    setWechatError("");
    if (!selectedWechat) {
      setWechatError("请选择一个微信会话。");
      return;
    }
    setIsWechatSubmitting(true);
    try {
      const response = await exportWechatChatForAnalysis({
        username: selectedWechat,
        reportType,
        anonymized,
        startTime: wechatStart,
        endTime: wechatEnd,
      });
      navigate(`/analyzing?reportId=${response.report_id}`);
    } catch (caught) {
      setWechatError(caught instanceof Error ? caught.message : "导出或分析失败。");
    } finally {
      setIsWechatSubmitting(false);
    }
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
            <p className="eyebrow">Import</p>
            <h1>选择微信聊天或上传 JSON 记录</h1>
            <p>支持本机微信解密导出，也保留手动导入 JSON 的流程。</p>
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

          <div className="wechat-import-panel">
            <div className="wechat-import-head">
              <div>
                <p className="eyebrow">Local WeChat</p>
                <h2>从本机微信选择聊天</h2>
              </div>
              <button
                className="icon-action"
                disabled={isLoadingWechat || isPreparingWechat}
                onClick={handleLoadWechatChats}
                title="刷新会话"
                type="button"
              >
                {isLoadingWechat ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
              </button>
            </div>
            <div className="wechat-filters">
              <label>
                <Search size={16} />
                <input
                  onChange={(event) => setWechatQuery(event.target.value)}
                  placeholder="联系人、群名或 wxid"
                  value={wechatQuery}
                />
              </label>
              <label>
                <CalendarDays size={16} />
                <input
                  onChange={(event) => setWechatStart(event.target.value)}
                  placeholder="开始时间 2025-01-01"
                  value={wechatStart}
                />
              </label>
              <label>
                <CalendarDays size={16} />
                <input
                  onChange={(event) => setWechatEnd(event.target.value)}
                  placeholder="结束时间，可留空"
                  value={wechatEnd}
                />
              </label>
            </div>
            <div className="wechat-actions">
              <button
                className="inline-link"
                disabled={isPreparingWechat}
                onClick={handlePrepareWechatData}
                type="button"
              >
                {isPreparingWechat ? "准备中" : "准备微信数据"}
              </button>
              <button className="inline-link" disabled={isLoadingWechat || isPreparingWechat} onClick={handleLoadWechatChats} type="button">
                {isLoadingWechat ? "读取中" : "读取会话"}
              </button>
              {wechatTotal ? <span className="muted">匹配 {wechatTotal} 个会话</span> : null}
            </div>

            {wechatPrepareMessage ? (
              <p className="muted" style={{ margin: 0 }}>{wechatPrepareMessage}</p>
            ) : null}

            {wechatChats.length ? (
              <div className="wechat-chat-list">
                {wechatChats.map((chat) => (
                  <button
                    className={`wechat-chat-row ${selectedWechat === chat.username ? "wechat-chat-row-active" : ""}`}
                    key={chat.username}
                    onClick={() => {
                      setSelectedWechat(chat.username);
                      setReportType(chat.kind === "single" ? "relationship" : "group_roast");
                    }}
                    type="button"
                  >
                    <span>
                      <strong>{chat.display_name}</strong>
                      <small>{chat.kind === "group" ? "群聊" : "单聊"} · {chat.username}</small>
                    </span>
                    <span>
                      <strong>{chat.message_count.toLocaleString("zh-CN")}</strong>
                      <small>{chat.first_time ? `${chat.first_time.slice(0, 10)} ~ ${chat.last_time.slice(0, 10)}` : "无匹配消息"}</small>
                    </span>
                  </button>
                ))}
              </div>
            ) : null}

            {wechatError ? (
              <p className="error-text"><AlertCircle size={18} />{wechatError}</p>
            ) : null}

            <Button
              disabled={isWechatSubmitting || isPreparingWechat || !selectedWechat}
              icon={isWechatSubmitting ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
              onClick={handleWechatSubmit}
              type="button"
            >
              {isWechatSubmitting ? "导出中" : "导出并分析"}
            </Button>
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
              placeholder="在此粘贴 WeFlow 或微信解密导出的 JSON 内容..."
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
            {isSubmitting ? "提交中" : "分析手动 JSON"}
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
                    {preview.recommendedType !== reportType ? "，可在左侧切换" : ""}
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
              <p className="eyebrow">Setup</p>
              <h2>本机微信导入</h2>
              <ol>
                <li>先在 wechat-decrypt 项目完成数据库解密</li>
                <li>点击读取会话，按联系人、群名和时间范围筛选</li>
                <li>选择会话后直接导出 JSON 并进入分析</li>
              </ol>
            </>
          )}
        </aside>
      </section>
    </main>
  );
}
