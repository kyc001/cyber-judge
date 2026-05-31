import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle, Brain, CalendarDays, FileText, HeartHandshake, Loader2,
  MessageCircleMore, Quote, RefreshCw, ShieldCheck, Sparkles, Wand2,
} from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  downloadWechatImportJson,
  getWechatChats,
  getLlmConfig,
  prepareWechatData,
  saveLlmConfig,
  startWechatChatImport,
  testLlmConfig,
  uploadRawChat,
} from "../api/client";
import { Button } from "../components/ui/Button";
import type {
  LlmConfig,
  LlmConfigUpdate,
  LlmProviderOption,
  ReportType,
  WechatChatSummary,
  WechatImportProgressEvent,
} from "../contracts/report";

const MAX_FILE_SIZE_MB = 30;
const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024;
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const DEFAULT_LLM_PROVIDERS: LlmProviderOption[] = [
  {
    id: "deepseek",
    label: "DeepSeek",
    models: ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
    default_model: "deepseek-v4-pro",
  },
  {
    id: "openai",
    label: "OpenAI",
    models: [
      "gpt-5.5",
      "gpt-5.4",
      "gpt-5.4-mini",
      "gpt-5.4-nano",
      "gpt-5.2",
      "gpt-4.1",
      "gpt-4.1-mini",
      "gpt-4o",
      "gpt-4o-mini",
    ],
    default_model: "gpt-5.4-mini",
  },
  {
    id: "qwen",
    label: "通义千问",
    models: [
      "qwen3.7-max",
      "qwen3.6-plus",
      "qwen3.6-flash",
      "qwen3.5-plus",
      "qwen3.5-flash",
      "qwen-plus",
      "qwen-plus-latest",
      "qwen-max",
      "qwen-max-latest",
      "qwen-turbo",
      "qwen-turbo-latest",
    ],
    default_model: "qwen3.6-plus",
  },
];

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

type AnalysisIntent = "auto_roast" | "group_dynamics" | "relationship_lab" | "quote_mining";
type WechatKind = "all" | "group" | "single";
type ImportStep = { step: string; status: string; message?: string; error?: string };
type LlmDraft = {
  provider: string;
  model: string;
};
type JsonSavePicker = (options: {
  suggestedName?: string;
  types?: { description: string; accept: Record<string, string[]> }[];
}) => Promise<JsonFileHandle>;
type JsonFileHandle = {
  createWritable: () => Promise<{
    write: (data: Blob) => Promise<void>;
    close: () => Promise<void>;
  }>;
};
type JsonSaveTarget = {
  kind: "picker";
  handle: JsonFileHandle;
  filename: string;
} | {
  kind: "download";
  filename: string;
};
type DesktopWindow = Window & {
  pywebview?: {
    api?: {
      choose_directory?: () => Promise<string | string[] | null>;
    };
  };
  showSaveFilePicker?: JsonSavePicker;
};

const ANALYSIS_INTENTS: {
  id: AnalysisIntent;
  icon: typeof Brain;
  title: string;
  body: string;
  reportType: ReportType;
  chips: string[];
}[] = [
  {
    id: "auto_roast",
    icon: Brain,
    title: "综合分析",
    body: "自动提取摘要、异常互动、代表片段和报告主题。",
    reportType: "group_roast",
    chips: ["摘要", "异常互动", "代表片段"],
  },
  {
    id: "group_dynamics",
    icon: MessageCircleMore,
    title: "群聊分析",
    body: "统计成员活跃、接话关系、共同词汇和表情偏好。",
    reportType: "group_roast",
    chips: ["成员活跃", "互动关系", "共同词汇"],
  },
  {
    id: "relationship_lab",
    icon: HeartHandshake,
    title: "双人关系",
    body: "分析双方消息量、主动程度、回复节奏和共同语言。",
    reportType: "relationship",
    chips: ["消息占比", "回复节奏", "共同语言"],
  },
  {
    id: "quote_mining",
    icon: Quote,
    title: "片段提取",
    body: "从原始聊天中挑出可引用的代表性对话。",
    reportType: "group_roast",
    chips: ["原话", "上下文", "时间"],
  },
];

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

const WECHAT_IMPORT_STEP_LABELS: Record<string, string> = {
  queued: "创建任务",
  export: "导出聊天",
  parse: "解析 JSON",
  privacy: "昵称脱敏",
  analysis: "创建分析",
  error: "导入失败",
};

function formatUnixTime(value: unknown) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds) || seconds <= 0) return "";
  return new Date(seconds * 1000).toISOString().slice(0, 16).replace("T", " ");
}

function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isAbortError(caught: unknown) {
  return caught instanceof Error && caught.name === "AbortError";
}

async function chooseDesktopDirectory() {
  const chooseDirectory = (window as DesktopWindow).pywebview?.api?.choose_directory;
  if (!chooseDirectory) return "";
  const selected = await chooseDirectory();
  if (Array.isArray(selected)) return String(selected[0] || "");
  return String(selected || "");
}

async function prepareJsonSaveTarget(filename: string): Promise<JsonSaveTarget> {
  const safeName = filename || "wechat-chat.json";
  const savePicker = (window as DesktopWindow).showSaveFilePicker;
  if (!savePicker) return { kind: "download", filename: safeName };
  try {
    const handle = await savePicker({
      suggestedName: safeName,
      types: [{ description: "JSON 文件", accept: { "application/json": [".json"] } }],
    });
    return { kind: "picker", handle, filename: safeName };
  } catch (caught) {
    if (isAbortError(caught)) throw caught;
    return { kind: "download", filename: safeName };
  }
}

async function saveJsonToTarget(filename: string, jsonText: string, target: JsonSaveTarget | null) {
  const safeName = filename || target?.filename || "wechat-chat.json";
  const blob = new Blob([jsonText], { type: "application/json;charset=utf-8" });
  if (target?.kind === "picker") {
    const writable = await target.handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = safeName;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function providerOptions(config: LlmConfig | null) {
  return config?.providers?.length ? config.providers : DEFAULT_LLM_PROVIDERS;
}

function providerById(providers: LlmProviderOption[], provider: string) {
  return providers.find((item) => item.id === provider) ?? providers[0] ?? DEFAULT_LLM_PROVIDERS[0];
}

function defaultModelForProvider(providers: LlmProviderOption[], provider: string) {
  const option = providerById(providers, provider);
  return option.default_model || option.models[0] || "";
}

function modelOptionsForProvider(providers: LlmProviderOption[], provider: string) {
  return providerById(providers, provider).models;
}

function keyTailForProvider(config: LlmConfig | null, provider: string) {
  const state = config?.provider_keys?.[provider];
  if (state?.has_api_key) return state.api_key_tail;
  if (config?.provider === provider && config.has_api_key) return config.api_key_tail;
  return "";
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
  const importSourceRef = useRef<EventSource | null>(null);
  const initialReportType: ReportType =
    searchParams.get("type") === "relationship" ? "relationship" : "group_roast";
  const [reportType, setReportType] = useState<ReportType>(initialReportType);
  const [analysisIntent, setAnalysisIntent] = useState<AnalysisIntent>(
    initialReportType === "relationship" ? "relationship_lab" : "auto_roast",
  );
  const [text, setText] = useState("");
  const [fileName, setFileName] = useState("");
  const [anonymized, setAnonymized] = useState(true);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [wechatQuery, setWechatQuery] = useState("");
  const [wechatKind, setWechatKind] = useState<WechatKind>(
    initialReportType === "relationship" ? "single" : "group",
  );
  const [wechatStart, setWechatStart] = useState("");
  const [wechatEnd, setWechatEnd] = useState("");
  const [saveWechatJson, setSaveWechatJson] = useState(false);
  const [wechatChats, setWechatChats] = useState<WechatChatSummary[]>([]);
  const [selectedWechat, setSelectedWechat] = useState("");
  const [wechatError, setWechatError] = useState("");
  const [wechatTotal, setWechatTotal] = useState(0);
  const [isLoadingWechat, setIsLoadingWechat] = useState(false);
  const [isPreparingWechat, setIsPreparingWechat] = useState(false);
  const [wechatPrepareMessage, setWechatPrepareMessage] = useState("");
  const [isWechatSubmitting, setIsWechatSubmitting] = useState(false);
  const [wechatImportProgress, setWechatImportProgress] = useState(0);
  const [wechatImportCap, setWechatImportCap] = useState(46);
  const [wechatImportMessage, setWechatImportMessage] = useState("");
  const [wechatImportSteps, setWechatImportSteps] = useState<ImportStep[]>([]);
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(null);
  const [llmDraft, setLlmDraft] = useState<LlmDraft>({
    provider: DEFAULT_LLM_PROVIDERS[0].id,
    model: DEFAULT_LLM_PROVIDERS[0].default_model,
  });
  const [llmApiKey, setLlmApiKey] = useState("");
  const [llmStatus, setLlmStatus] = useState("");
  const [isSavingLlm, setIsSavingLlm] = useState(false);
  const [isTestingLlm, setIsTestingLlm] = useState(false);
  const preview = useMemo(() => buildUploadPreview(text), [text]);
  const activeIntent = ANALYSIS_INTENTS.find((intent) => intent.id === analysisIntent) ?? ANALYSIS_INTENTS[0];
  const llmProviders = useMemo(() => providerOptions(llmConfig), [llmConfig]);
  const llmModels = useMemo(
    () => modelOptionsForProvider(llmProviders, llmDraft.provider),
    [llmDraft.provider, llmProviders],
  );
  const llmSavedTail = keyTailForProvider(llmConfig, llmDraft.provider);

  useEffect(() => () => importSourceRef.current?.close(), []);

  useEffect(() => {
    let cancelled = false;
    getLlmConfig()
      .then((config) => {
        if (cancelled) return;
        setLlmConfig(config);
        setLlmDraft({ provider: config.provider, model: config.model });
      })
      .catch((caught) => {
        if (!cancelled) {
          setLlmStatus(caught instanceof Error ? caught.message : "读取模型配置失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isWechatSubmitting) return undefined;
    const timer = window.setInterval(() => {
      setWechatImportProgress((current) => Math.min(wechatImportCap, current + 1));
    }, 900);
    return () => window.clearInterval(timer);
  }, [isWechatSubmitting, wechatImportCap]);

  function updateWechatImportStep(step: ImportStep) {
    setWechatImportSteps((previous) => {
      const next = previous.filter((item) => item.step !== step.step);
      return [...next, step];
    });
  }

  function selectAnalysisIntent(intent: (typeof ANALYSIS_INTENTS)[number]) {
    setAnalysisIntent(intent.id);
    setReportType(intent.reportType);
    setWechatKind(intent.reportType === "relationship" ? "single" : "group");
    setSelectedWechat("");
  }

  function selectReportType(nextType: ReportType) {
    setReportType(nextType);
    setAnalysisIntent(nextType === "relationship" ? "relationship_lab" : "group_dynamics");
  }

  function selectLlmProvider(provider: string) {
    const model = defaultModelForProvider(llmProviders, provider);
    setLlmDraft({ provider, model });
    setLlmApiKey("");
    setLlmStatus("");
  }

  function buildLlmPayload(): LlmConfigUpdate {
    const payload: LlmConfigUpdate = {
      provider: llmDraft.provider,
      model: llmDraft.model,
    };
    const apiKey = llmApiKey.trim();
    if (apiKey) payload.api_key = apiKey;
    return payload;
  }

  async function handleSaveLlmConfig() {
    setLlmStatus("");
    setIsSavingLlm(true);
    try {
      const config = await saveLlmConfig(buildLlmPayload());
      setLlmConfig(config);
      setLlmDraft({ provider: config.provider, model: config.model });
      setLlmApiKey("");
      setLlmStatus(config.has_api_key ? "模型配置已保存" : "已保存模型选择，API Key 仍未填写");
    } catch (caught) {
      setLlmStatus(caught instanceof Error ? caught.message : "保存模型配置失败");
    } finally {
      setIsSavingLlm(false);
    }
  }

  async function handleTestLlmConfig() {
    setLlmStatus("");
    setIsTestingLlm(true);
    try {
      const result = await testLlmConfig(buildLlmPayload());
      setLlmStatus(result.ok ? `连通性正常：${result.model}` : "模型返回异常");
    } catch (caught) {
      setLlmStatus(caught instanceof Error ? caught.message : "模型连通性检查失败");
    } finally {
      setIsTestingLlm(false);
    }
  }

  async function readFile(file: File) {
    setError("");
    if (!file.name.endsWith(".json")) {
      setError("仅支持 .json 格式。");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError(`文件超过 ${MAX_FILE_SIZE_MB}MB。`);
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

  async function handleLoadWechatChats(overrides: Partial<{
    query: string;
    kind: WechatKind;
    startTime: string;
    endTime: string;
  }> = {}) {
    setWechatError("");
    setIsLoadingWechat(true);
    const nextQuery = overrides.query ?? wechatQuery;
    const nextKind = overrides.kind ?? wechatKind;
    const nextStart = overrides.startTime ?? wechatStart;
    const nextEnd = overrides.endTime ?? wechatEnd;
    try {
      const response = await getWechatChats({
        query: nextQuery,
        kind: nextKind,
        limit: 80,
        startTime: nextStart,
        endTime: nextEnd,
      });
      setWechatChats(response.chats);
      setWechatTotal(response.total);
      const selectedStillVisible = response.chats.some((chat) => chat.username === selectedWechat);
      if (response.chats[0] && (!selectedWechat || !selectedStillVisible)) {
        setSelectedWechat(response.chats[0].username);
        selectReportType(response.chats[0].kind === "single" ? "relationship" : "group_roast");
      } else if (!response.chats.length) {
        setSelectedWechat("");
      }
    } catch (caught) {
      setWechatError(caught instanceof Error ? caught.message : "读取微信失败。");
    } finally {
      setIsLoadingWechat(false);
    }
  }

  function applyWechatKind(nextKind: WechatKind) {
    setWechatKind(nextKind);
    setSelectedWechat("");
    if (nextKind === "group") selectReportType("group_roast");
    if (nextKind === "single") selectReportType("relationship");
    void handleLoadWechatChats({ kind: nextKind });
  }

  function applyWechatRange(days: number | null) {
    if (days === null) {
      setWechatStart("");
      setWechatEnd("");
      setSelectedWechat("");
      void handleLoadWechatChats({ startTime: "", endTime: "" });
      return;
    }
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days + 1);
    const nextStart = formatDateInput(start);
    const nextEnd = formatDateInput(end);
    setWechatStart(nextStart);
    setWechatEnd(nextEnd);
    setSelectedWechat("");
    void handleLoadWechatChats({ startTime: nextStart, endTime: nextEnd });
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
    setWechatImportProgress(2);
    setWechatImportCap(46);
    setWechatImportMessage("正在创建导入任务");
    setWechatImportSteps([]);
    importSourceRef.current?.close();
    try {
      const hasDesktopDirectoryPicker = Boolean((window as DesktopWindow).pywebview?.api?.choose_directory);
      const outputDir = saveWechatJson && hasDesktopDirectoryPicker ? await chooseDesktopDirectory() : "";
      const jsonSaveTarget = saveWechatJson && !outputDir
        ? await prepareJsonSaveTarget("wechat-chat.json")
        : null;
      const started = await startWechatChatImport({
        username: selectedWechat,
        reportType,
        anonymized,
        startTime: wechatStart,
        endTime: wechatEnd,
        outputDir,
      });
      setWechatImportProgress(6);
      setWechatImportMessage("导入任务已提交");
      const source = new EventSource(`${API_BASE}/api/wechat/import/${started.import_id}/progress`);
      importSourceRef.current = source;
      source.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data) as WechatImportProgressEvent;
          if (data.type === "progress" && data.step) {
            const percent = Number(data.percent || 0);
            if (Number.isFinite(percent) && percent > 0) {
              setWechatImportProgress((current) => Math.max(current, Math.min(99, percent)));
              setWechatImportCap((current) => Math.min(99, Math.max(percent + 8, current)));
            }
            setWechatImportMessage(data.message || WECHAT_IMPORT_STEP_LABELS[data.step] || "正在导入");
            updateWechatImportStep({
              step: data.step,
              status: data.status || "started",
              message: data.message,
              error: data.error,
            });
          }
          if (data.type === "done" && data.report_id) {
            source.close();
            importSourceRef.current = null;
            setWechatImportProgress(100);
            setWechatImportMessage("导入完成，正在进入分析页");
            if (saveWechatJson && !outputDir) {
              try {
                setWechatImportMessage("正在保存 JSON 副本");
                const exportedJson = await downloadWechatImportJson(started.import_id);
                await saveJsonToTarget(exportedJson.filename, exportedJson.text, jsonSaveTarget);
              } catch (saveError) {
                if (!isAbortError(saveError)) throw saveError;
              }
            }
            navigate(`/analyzing?reportId=${data.report_id}`);
          }
          if (data.type === "error") {
            source.close();
            importSourceRef.current = null;
            setIsWechatSubmitting(false);
            setWechatError(data.error || "导入或分析失败。");
          }
        } catch (caught) {
          source.close();
          importSourceRef.current = null;
          setIsWechatSubmitting(false);
          setWechatError(caught instanceof Error ? caught.message : "导入进度解析失败。");
        }
      };
      source.onerror = () => {
        source.close();
        importSourceRef.current = null;
        setIsWechatSubmitting(false);
        setWechatError("导入进度连接中断，请重试。");
      };
    } catch (caught) {
      if (isAbortError(caught)) {
        setIsWechatSubmitting(false);
        setWechatImportMessage("");
        setWechatImportSteps([]);
        setWechatImportProgress(0);
        return;
      }
      setWechatError(caught instanceof Error ? caught.message : "导入或分析失败。");
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
            <p className="eyebrow">导入与分析</p>
            <h1>选择聊天记录和分析类型</h1>
            <p>优先从本机微信导入，也可以手动上传 JSON。</p>
          </div>

          <div className="analysis-intent-grid" role="radiogroup" aria-label="选择分析类型">
            {ANALYSIS_INTENTS.map((intent) => {
              const Icon = intent.icon;
              const active = analysisIntent === intent.id;
              return (
                <button
                  aria-checked={active}
                  className={`analysis-intent-card ${active ? "analysis-intent-active" : ""}`}
                  key={intent.id}
                  onClick={() => selectAnalysisIntent(intent)}
                  role="radio"
                  type="button"
                >
                  <span className="analysis-intent-icon"><Icon size={18} /></span>
                  <strong>{intent.title}</strong>
                  <span>{intent.body}</span>
                  <span className="intent-chip-row">
                    {intent.chips.map((chip) => <em key={chip}>{chip}</em>)}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="report-type-grid" role="radiogroup" aria-label="选择报告类型">
            <button
              aria-checked={reportType === "group_roast"}
              className={`type-option ${reportType === "group_roast" ? "type-option-active" : ""}`}
              onClick={() => {
                setSelectedWechat("");
                setWechatKind("group");
                selectReportType("group_roast");
              }}
              role="radio" type="button"
            >
              <MessageCircleMore size={20} />
              <strong>群聊报告</strong>
              <span>成员、互动、语言、表情</span>
            </button>
            <button
              aria-checked={reportType === "relationship"}
              className={`type-option ${reportType === "relationship" ? "type-option-active" : ""}`}
              onClick={() => {
                setSelectedWechat("");
                setWechatKind("single");
                selectReportType("relationship");
              }}
              role="radio" type="button"
            >
              <HeartHandshake size={20} />
              <strong>双人报告</strong>
              <span>主动、节奏、共同语言</span>
            </button>
          </div>

          <div className="wechat-import-panel">
            <div className="wechat-import-head">
              <div>
                <p className="eyebrow">本机微信</p>
                <h2>自动读取微信聊天</h2>
              </div>
              <button
                className="icon-action"
                disabled={isLoadingWechat || isPreparingWechat}
                onClick={() => handleLoadWechatChats()}
                title="刷新列表"
                type="button"
              >
                {isLoadingWechat ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
              </button>
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
              <button className="inline-link" disabled={isLoadingWechat || isPreparingWechat} onClick={() => handleLoadWechatChats()} type="button">
                {isLoadingWechat ? "读取中" : "读取会话"}
              </button>
              {wechatTotal ? <span className="muted">共 {wechatTotal} 个会话</span> : null}
            </div>
            <div className="wechat-actions">
              {([
                ["group", "群聊"],
                ["single", "单聊"],
                ["all", "全部"],
              ] as const).map(([kind, label]) => (
                <button
                  aria-pressed={wechatKind === kind}
                  className="inline-link"
                  key={kind}
                  onClick={() => applyWechatKind(kind)}
                  type="button"
                >
                  {wechatKind === kind ? `✓ ${label}` : label}
                </button>
              ))}
              <button className="inline-link" onClick={() => applyWechatRange(30)} type="button">近30天</button>
              <button className="inline-link" onClick={() => applyWechatRange(90)} type="button">近90天</button>
              <button className="inline-link" onClick={() => applyWechatRange(null)} type="button">全部时间</button>
            </div>
            <div className="wechat-filters">
              <label>
                <MessageCircleMore size={16} />
                <span className="muted">会话</span>
                <input
                  onChange={(event) => setWechatQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void handleLoadWechatChats({ query: event.currentTarget.value });
                    }
                  }}
                  placeholder={wechatKind === "single" ? "联系人或 wxid" : "群名或 chatroom id"}
                  value={wechatQuery}
                />
              </label>
              <label>
                <CalendarDays size={16} />
                <span className="muted">开始</span>
                <input
                  onChange={(event) => setWechatStart(event.target.value)}
                  type="date"
                  placeholder="开始日期 2025-01-01"
                  value={wechatStart}
                />
              </label>
              <label>
                <CalendarDays size={16} />
                <span className="muted">结束</span>
                <input
                  onChange={(event) => setWechatEnd(event.target.value)}
                  type="date"
                  placeholder="结束日期，可留空"
                  value={wechatEnd}
                />
              </label>
            </div>
            <div className="upload-options">
              <label className="toggle-row">
                <input
                  checked={anonymized}
                  onChange={(event) => setAnonymized(event.target.checked)}
                  type="checkbox"
                />
                <span><ShieldCheck size={18} />默认脱敏昵称</span>
              </label>
              <label className="toggle-row">
                <input
                  checked={saveWechatJson}
                  onChange={(event) => setSaveWechatJson(event.target.checked)}
                  type="checkbox"
                />
                <span><FileText size={18} />导入时选择位置保存 JSON 副本</span>
              </label>
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
                      selectReportType(chat.kind === "single" ? "relationship" : "group_roast");
                    }}
                    type="button"
                  >
                    <span>
                      <strong>{chat.display_name}</strong>
                      <small>{chat.kind === "group" ? "群聊" : "单聊"} · {chat.username}</small>
                    </span>
                    <span>
                      <strong>{chat.message_count.toLocaleString("zh-CN")}</strong>
                      <small>{chat.first_time ? `${chat.first_time.slice(0, 10)} ~ ${chat.last_time.slice(0, 10)}` : "该时间段无消息"}</small>
                    </span>
                  </button>
                ))}
              </div>
            ) : null}

            {wechatError ? (
              <p className="error-text"><AlertCircle size={18} />{wechatError}</p>
            ) : null}

            {isWechatSubmitting ? (
              <div style={{ display: "grid", gap: 10 }}>
                <div className="progress-shell" style={{ margin: 0 }}>
                  <div className="progress-bar" style={{ width: `${wechatImportProgress}%` }} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <span className="muted">{wechatImportMessage || "正在导入聊天记录"}</span>
                  <span className="progress-label">{wechatImportProgress}%</span>
                </div>
                {wechatImportSteps.length ? (
                  <div style={{ display: "grid", gap: 6 }}>
                    {wechatImportSteps.map((item) => (
                      <div key={item.step} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                        <span>{WECHAT_IMPORT_STEP_LABELS[item.step] || item.step}</span>
                        <span className="muted">
                          {item.status === "done" ? "完成" : item.status === "error" ? "失败" : "进行中"}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            <Button
              disabled={isWechatSubmitting || isPreparingWechat || !selectedWechat}
              icon={isWechatSubmitting ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
              onClick={handleWechatSubmit}
              type="button"
            >
              {isWechatSubmitting ? "导入中" : saveWechatJson ? "导入、保存并分析" : "导入并分析"}
            </Button>
          </div>

          <div className="wechat-import-panel">
            <div className="wechat-import-head">
              <div>
                <p className="eyebrow">手动 JSON</p>
                <h2>上传或粘贴聊天 JSON</h2>
              </div>
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
              <strong>{fileName || "拖拽 JSON 文件到这里"}</strong>
              <span>也可以选择文件，最大 {MAX_FILE_SIZE_MB}MB</span>
              <button
                className="inline-link"
                onClick={() => inputRef.current?.click()}
                type="button"
              >
                选择文件
              </button>
            </label>

            <label className="textarea-label">
              <span>粘贴 JSON 文本</span>
              <textarea
                onChange={(event) => setText(event.target.value)}
                placeholder="粘贴 WeFlow 或微信导出的 JSON 内容..."
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
              {isSubmitting ? "提交中" : "分析 JSON"}
            </Button>
          </div>
        </form>

        <aside className="tutorial-panel">
          <div className="ai-brief-panel">
            <p className="eyebrow">当前选择</p>
            <h2>{activeIntent.title}</h2>
            <p>{activeIntent.body}</p>
            <div className="ai-brief-list">
              <span><Sparkles size={16} /> 读取聊天记录</span>
              <span><MessageCircleMore size={16} /> 统计消息、时间、成员与互动</span>
              <span><Quote size={16} /> 生成中间页和最终报告</span>
            </div>
          </div>
          <div className="llm-settings-panel">
            <div className="llm-settings-head">
              <div>
                <p className="eyebrow">模型设置</p>
                <h2>选择报告生成模型</h2>
              </div>
              <span className={`llm-key-state ${llmSavedTail ? "llm-key-ready" : ""}`}>
                {llmSavedTail ? `已保存 · ${llmSavedTail}` : "未填写 Key"}
              </span>
            </div>
            <div className="llm-provider-grid" role="radiogroup" aria-label="选择模型服务商">
              {llmProviders.map((provider) => (
                <button
                  aria-checked={llmDraft.provider === provider.id}
                  className={`llm-provider-option ${llmDraft.provider === provider.id ? "llm-provider-active" : ""}`}
                  key={provider.id}
                  onClick={() => selectLlmProvider(provider.id)}
                  role="radio"
                  type="button"
                >
                  <span>{provider.label}</span>
                  {keyTailForProvider(llmConfig, provider.id) ? <small>Key 已保存</small> : <small>待填写</small>}
                </button>
              ))}
            </div>
            <label className="llm-field">
              <span>模型</span>
              <select
                onChange={(event) => setLlmDraft((current) => ({ ...current, model: event.target.value }))}
                value={llmDraft.model}
              >
                {llmModels.map((model) => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </label>
            <label className="llm-field">
              <span>API Key</span>
              <input
                autoComplete="off"
                onChange={(event) => setLlmApiKey(event.target.value)}
                placeholder={llmSavedTail ? "不填则继续使用已保存 Key" : "粘贴当前服务商的 API Key"}
                type="password"
                value={llmApiKey}
              />
            </label>
            <div className="llm-actions">
              <Button
                disabled={isSavingLlm}
                icon={isSavingLlm ? <Loader2 className="spin" size={16} /> : <ShieldCheck size={16} />}
                onClick={handleSaveLlmConfig}
                type="button"
                variant="secondary"
              >
                保存
              </Button>
              <Button
                disabled={isTestingLlm}
                icon={isTestingLlm ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
                onClick={handleTestLlmConfig}
                type="button"
                variant="ghost"
              >
                测试
              </Button>
            </div>
            {llmStatus ? <p className="llm-status">{llmStatus}</p> : null}
          </div>
          {preview ? (
            <>
              <p className="eyebrow">数据预览</p>
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
                    建议模式：{preview.recommendedType === "relationship" ? "双人报告" : "群聊报告"}
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
              <p className="eyebrow">本机微信导入</p>
              <h2>使用步骤</h2>
              <ol>
                <li>准备微信数据后读取会话</li>
                <li>按会话、类型和时间筛选</li>
                <li>选择会话后导入并分析</li>
              </ol>
            </>
          )}
        </aside>
      </section>
    </main>
  );
}
