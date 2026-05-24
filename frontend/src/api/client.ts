import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ReportPayload,
  SharePayload,
} from "../contracts/report";
import {
  createMockSharePayload,
  getMockReportById,
  getMockShareSlugForReport,
} from "../mock/report";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const API_MODE = import.meta.env.VITE_API_MODE ?? "mock";

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function analyzeChat(
  request: AnalyzeRequest,
): Promise<AnalyzeResponse> {
  if (API_MODE !== "mock") {
    return requestJson<AnalyzeResponse>("/api/analyze", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  await wait(520);
  return {
    report_id:
      request.messages.length > 0
        ? request.report_type === "relationship"
          ? "demo-relationship-001"
          : "demo-report-001"
        : "empty-report",
    status: "processing",
    estimated_seconds: 4,
  };
}

export async function getReport(id: string): Promise<ReportPayload> {
  if (API_MODE !== "mock") {
    return requestJson<ReportPayload>(`/api/report/${id}`);
  }

  await wait(360);
  if (id === "empty-report") {
    throw new Error("No report data");
  }

  return getMockReportById(id || "demo-report-001");
}

export async function createShare(id: string): Promise<SharePayload> {
  if (API_MODE !== "mock") {
    return requestJson<SharePayload>(`/api/share/${id}`, {
      method: "POST",
    });
  }

  await wait(320);
  return createMockSharePayload(getMockShareSlugForReport(id));
}

export async function getShare(slug: string): Promise<SharePayload> {
  if (API_MODE !== "mock") {
    return requestJson<SharePayload>(`/api/share/${slug}`);
  }

  await wait(280);
  return createMockSharePayload(slug || "demo-longwang");
}
