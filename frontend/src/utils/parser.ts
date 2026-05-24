import type { AnalyzeRequest, ChatMessage, ReportType } from "../contracts/report";

const ALIASES = ["A 同学", "B 同学", "C 同学", "D 同学", "E 同学", "F 同学"];

export interface ParsedInput {
  messages: ChatMessage[];
  aliasMap: Record<string, string>;
}

function normalizeSender(raw: string, aliasMap: Record<string, string>) {
  if (!aliasMap[raw]) {
    aliasMap[raw] = ALIASES[Object.keys(aliasMap).length % ALIASES.length];
  }

  return aliasMap[raw];
}

export function parseTextToMessages(text: string, anonymized: boolean): ParsedInput {
  const aliasMap: Record<string, string> = {};
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const messages = lines.map<ChatMessage>((line, index) => {
    const namedLine = line.match(
      /^(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\s+)?([^:：]{1,24})[:：]\s*(.+)$/,
    );
    const rawSender = namedLine?.[1]?.trim() || `成员${(index % 4) + 1}`;
    const content = namedLine?.[2]?.trim() || line;
    const sender = anonymized ? normalizeSender(rawSender, aliasMap) : rawSender;

    return {
      msg_id: `local-${index + 1}`,
      sender,
      ts: new Date(Date.now() - (lines.length - index) * 60_000).toISOString(),
      type: content.includes("[图片]") ? "image" : content.includes("[表情]") ? "emoji" : "text",
      content,
    };
  });

  return {
    messages,
    aliasMap,
  };
}

export function buildAnalyzeRequest(
  text: string,
  source: "wechat_txt" | "paste",
  anonymized: boolean,
  reportType: ReportType,
): AnalyzeRequest {
  const parsed = parseTextToMessages(text, anonymized);

  return {
    report_type: reportType,
    source,
    messages: parsed.messages,
    privacy: {
      anonymized,
      alias_map: anonymized ? parsed.aliasMap : undefined,
    },
    client_meta: {
      schema_version: "2026-05-24",
      locale: "zh-CN",
    },
  };
}
