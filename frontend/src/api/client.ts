/** API client for the Cyber Judge backend. All calls go through the Vite proxy to localhost:8000. */

import type {
  AnalyzeResponse,
  ExportFormat,
  ExportPayload,
  ReportPayload,
  SharePayload,
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
