# 前端接口契约

这份文档用于让 2 号解析器、3 号后端、5 号 LLM 和 4 号前端并行开发。当前前端已经内置 mock 实现；真实接口接入时请优先保持字段名不变。

约定原则：

- 只允许新增可选字段，不要随意改名或删除字段。
- 时间统一使用 ISO 8601 字符串。
- 原始聊天文件和原始聊天全文不落库，也不通过接口上传。
- 分享页不能暴露原始消息或昵称映射表。

## 2 号输出：解析后的消息

2 号解析器最终要把微信 txt 文本解析成 `ChatMessage[]`。当前临时实现位于 `frontend/src/utils/parser.ts`，后续可以整体替换，但返回结构要保持一致。

```ts
type MessageType =
  | "text"
  | "image"
  | "emoji"
  | "file"
  | "link"
  | "system"
  | "red_packet"
  | "transfer"
  | "unknown";

interface ChatMessage {
  msg_id: string;
  sender: string;
  ts: string; // ISO 8601
  type: MessageType;
  content: string;
  reply_to?: string;
  meta?: Record<string, string | number | boolean>;
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `msg_id` | `string` | 是 | 消息唯一 ID，本地解析可用递增 ID。 |
| `sender` | `string` | 是 | 发言人昵称或脱敏代号，例如 `A 同学`。 |
| `ts` | `string` | 是 | 发送时间，统一 ISO 8601。 |
| `type` | `MessageType` | 是 | 消息类型。无法判断时用 `unknown`。 |
| `content` | `string` | 是 | 文本内容或占位描述。 |
| `reply_to` | `string` | 否 | 被回复消息的 `msg_id`。 |
| `meta` | `object` | 否 | 额外信息，例如文件名、链接标题等。 |

## POST `/api/analyze`

前端把结构化消息发给 3 号后端，后端负责统计、调用或转交 LLM，并返回 `report_id`。

请求示例：

```json
{
  "report_type": "relationship",
  "source": "wechat_txt",
  "messages": [
    {
      "msg_id": "local-1",
      "sender": "A 同学",
      "ts": "2026-05-24T14:10:00.000Z",
      "type": "text",
      "content": "我只是随便问问"
    }
  ],
  "privacy": {
    "anonymized": true,
    "alias_map": {
      "真实昵称": "A 同学"
    }
  },
  "client_meta": {
    "schema_version": "2026-05-24",
    "locale": "zh-CN"
  }
}
```

请求字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `report_type` | `"group_roast" \| "relationship"` | 是 | 报告类型：群聊锐评或双人关系。 |
| `source` | `"wechat_txt" \| "paste" \| "mock"` | 是 | 数据来源。 |
| `messages` | `ChatMessage[]` | 是 | 解析后的消息数组。 |
| `privacy.anonymized` | `boolean` | 是 | 是否已脱敏。默认应该为 `true`。 |
| `privacy.alias_map` | `Record<string,string>` | 否 | 昵称到代号的映射，仅浏览器内需要，后端不要公开。 |
| `client_meta.schema_version` | `string` | 是 | 当前约定版本，先固定为 `2026-05-24`。 |
| `client_meta.locale` | `string` | 是 | 当前固定 `zh-CN`。 |

响应示例：

```json
{
  "report_id": "demo-relationship-001",
  "status": "processing",
  "estimated_seconds": 4
}
```

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `report_id` | `string` | 报告 ID，前端会跳转到 `/report/:id`。 |
| `status` | `"queued" \| "processing" \| "done"` | 分析状态。 |
| `estimated_seconds` | `number` | 预计等待秒数，可用于分析中页面。 |

## GET `/api/report/:id`

返回完整报告渲染数据。4 号前端只依赖这个结构渲染页面，不直接关心后端数据库结构。

```ts
interface ReportPayload {
  report_id: string;
  report_type: "group_roast" | "relationship";
  created_at: string;
  title: string;
  tagline: string;
  hero: {
    kicker: string;
    quote: string;
    visual: string;
  };
  tags: string[];
  sections: ReportSection[];
  quotes: QuoteItem[];
  stats: ReportStats;
  share: {
    slug?: string;
    hook: string;
    watermark: string;
  };
}
```

责任边界：

- 3 号负责 `stats`，也就是统计和图表数据。
- 5 号负责 LLM 文案，包括 `title`、`tagline`、`hero`、`sections`、`quotes`、`tags`。
- 4 号负责按字段渲染，不在页面里猜测后端私有结构。

### `ReportSection`

```ts
interface ReportSection {
  id: string;
  type:
    | "summary"
    | "dragon_rank"
    | "heatmap"
    | "keywords"
    | "radar"
    | "emoji"
    | "timeline"
    | "relationship";
  heading: string;
  body: string;
  chart_ref?: keyof ReportStats;
}
```

`type` 决定前端渲染哪种图表或内容区。没有数据时前端会尽量降级显示，不让整页崩。

### 双人关系报告字段

双人关系报告建议在 `stats` 中提供：

```ts
interface RelationshipMetric {
  label: string;
  value: number; // 0-100
  caption: string;
}

interface RelationshipEdge {
  from: string;
  to: string;
  weight: number; // 0-1
  label: string;
}
```

字段用途：

- `relationship_edges`：用于渲染主动方向关系图，例如谁更常开启话题。
- `relationship_metrics`：用于渲染关系分数卡，例如 CP 感、回复稳定、嘴硬关心。

`relationship_metrics` 可以暂时不传；前端会继续渲染 `relationship_edges`。

## POST `/api/share/:id`

把某个报告标记为可分享，并返回分享地址。

响应示例：

```json
{
  "slug": "demo-relationship",
  "url": "https://example.com/share/demo-relationship",
  "report": {}
}
```

说明：

- `slug` 用于 `/share/:slug`。
- `url` 是完整分享链接。
- `report` 应该是同一个 `ReportPayload` 结构。

## GET `/api/share/:slug`

返回公开分享页数据。

响应示例：

```json
{
  "slug": "demo-relationship",
  "url": "https://example.com/share/demo-relationship",
  "report": {}
}
```

分享页安全要求：

- 不返回原始聊天消息。
- 不返回真实昵称映射表。
- 只返回渲染报告所需的统计结果和 LLM 文案。

## 前端 mock 对照

当前前端 mock 数据位于 `frontend/src/mock/report.ts`：

- 群聊报告：`demo-report-001`
- 双人关系报告：`demo-relationship-001`
- 群聊分享：`demo-longwang`
- 双人关系分享：`demo-relationship`

3 号和 5 号可以先按这些 mock 字段对齐真实接口。
