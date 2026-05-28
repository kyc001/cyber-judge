/** API client for the Cyber Judge backend. All calls go through the Vite proxy to localhost:8000. */

import type {
  AnalyzeResponse,
  ExportedChatPayload,
  ExportedChatsResponse,
  ExportFormat,
  ExportPayload,
  ReportPayload,
  SharePayload,
  WechatChatsResponse,
  WechatPrepareStatus,
} from "../contracts/report";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

/** Fetch JSON from the API. Throws with Chinese-localized message on network errors. */
async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch (err) {
    throw new Error(
      "无法连接后端服务。请确保后端已启动：cd backend && python main.py\n" +
      `详细错误: ${err instanceof Error ? err.message : String(err)}`
    );
  }
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Request failed: ${response.status} - ${body}`);
  }
  return (await response.json()) as T;
}

/** Poll an endpoint until it returns 200, with 2s intervals. Times out after maxRetries. */
async function requestJsonWithPolling<T>(path: string, maxRetries = 15): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        headers: { "Content-Type": "application/json" },
      });
    } catch (err) {
      throw new Error(
        "无法连接后端服务。请确保后端已启动：cd backend && python main.py\n" +
        `详细错误: ${err instanceof Error ? err.message : String(err)}`
      );
    }
    if (response.status === 200) return (await response.json()) as T;
    if (response.status === 202) {
      await new Promise((r) => setTimeout(r, 2000));
      continue;
    }
    throw new Error(`Request failed: ${response.status}`);
  }
  throw new Error("Report generation timed out. Please try again.");
}

/** Upload raw WeFlow JSON text to the backend for parsing and analysis. */
export async function uploadRawChat(text: string, reportType: string, anonymized: boolean): Promise<AnalyzeResponse> {
  return requestJson<AnalyzeResponse>("/api/upload", {
    method: "POST",
    body: JSON.stringify({ text, report_type: reportType, anonymized }),
  });
}

/** Load local WeChat sessions through the wechat-decrypt adapter. */
export async function getWechatChats(params: {
  query?: string;
  limit?: number;
  startTime?: string;
  endTime?: string;
} = {}): Promise<WechatChatsResponse> {
  const search = new URLSearchParams();
  if (params.query) search.set("query", params.query);
  if (params.limit) search.set("limit", String(params.limit));
  if (params.startTime) search.set("start_time", params.startTime);
  if (params.endTime) search.set("end_time", params.endTime);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return requestJson<WechatChatsResponse>(`/api/wechat/chats${suffix}`);
}

/** List medium-sized local JSON exports for quick demo and QA runs. */
export async function getExportedChatSamples(params: {
  query?: string;
  kind?: "all" | "group" | "single";
  limit?: number;
  minSize?: number;
  maxSize?: number;
} = {}): Promise<ExportedChatsResponse> {
  const search = new URLSearchParams();
  if (params.query) search.set("query", params.query);
  if (params.kind) search.set("kind", params.kind);
  if (params.limit) search.set("limit", String(params.limit));
  if (params.minSize) search.set("min_size", String(params.minSize));
  if (params.maxSize) search.set("max_size", String(params.maxSize));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return requestJson<ExportedChatsResponse>(`/api/wechat/exported-chats${suffix}`);
}

/** Load one local exported JSON file into the manual upload preview flow. */
export async function getExportedChatSample(fileName: string): Promise<ExportedChatPayload> {
  return requestJson<ExportedChatPayload>(`/api/wechat/exported-chats/${encodeURIComponent(fileName)}`);
}

/** Prepare local WeChat databases by running the bundled decrypt flow. */
export async function prepareWechatData(force = false): Promise<WechatPrepareStatus> {
  return requestJson<WechatPrepareStatus>("/api/wechat/prepare", {
    method: "POST",
    body: JSON.stringify({ force }),
  });
}

/** Export a selected local WeChat chat to JSON and run the existing analysis flow. */
export async function exportWechatChatForAnalysis(payload: {
  username: string;
  reportType: string;
  anonymized: boolean;
  startTime?: string;
  endTime?: string;
}): Promise<AnalyzeResponse> {
  return requestJson<AnalyzeResponse>("/api/wechat/export", {
    method: "POST",
    body: JSON.stringify({
      username: payload.username,
      report_type: payload.reportType,
      anonymized: payload.anonymized,
      start_time: payload.startTime || "",
      end_time: payload.endTime || "",
    }),
  });
}

/** Fetch a report by ID, polling while it's being generated. */
export async function getReport(id: string): Promise<ReportPayload> {
  return requestJsonWithPolling<ReportPayload>(`/api/report/${id}`);
}

/** Create a share link for a report. */
export async function createShare(id: string): Promise<SharePayload> {
  return requestJson<SharePayload>(`/api/share/${id}`, { method: "POST" });
}

/** Load a shared report by its slug. */
export async function getShare(slug: string): Promise<SharePayload> {
  return requestJson<SharePayload>(`/api/share/${slug}`);
}

/** Export a generated report in a backend-supported format. */
export async function exportReport(id: string, format: ExportFormat): Promise<ExportPayload> {
  return requestJson<ExportPayload>("/api/export", {
    method: "POST",
    body: JSON.stringify({ report_id: id, format }),
  });
}
