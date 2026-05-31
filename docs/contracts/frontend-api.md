# 前端接口契约

这份文档记录当前前后端共享的渲染契约。字段源头以 `frontend/src/contracts/report.ts` 和 `backend/models.py` 为准。

## ReportPayload 关键字段

```ts
interface ReportPayload {
  report_id: string;
  report_type: "group_roast" | "relationship";
  created_at: string;
  title: string;
  tagline: string;
  hero: { kicker: string; quote: string; visual: string };
  tags: string[];
  sections: ReportSection[];
  quotes: QuoteItem[];
  content_highlights?: ContentHighlight[];
  stats: ReportStats;
  share: { slug?: string; hook: string; watermark: string };
}
```

`content_highlights` 用于解决“报告只讲统计、不讲内容”的问题。后端会从高信息密度对话窗口里抽取真实原话，让 LLM 输出可验证的内容亮点；LLM 不可用时，fallback 也会保留候选片段。

## ContentHighlight

```ts
interface DialogueLine {
  sender: string;
  text: string;
  ts?: string;
}

interface ContentHighlight {
  id: string;
  title: string;
  insight: string;
  tag: string;
  evidence: DialogueLine[];
}
```

约束：

- `evidence[].text` 必须来自真实聊天消息，可以截断，不能改写或编造。
- `insight` 要解释内容亮点、关系模式、梗、接话节奏或情绪变化，不要只复述消息数。
- `tag` 建议使用 `content`、`roast`、`relationship`、`meme`、`warmth`、`rhythm`。
- 前端会跳过没有 `evidence` 的 highlight。
