# 4 号前端交接文档

这份文档给团队同学快速接手前端使用。当前前端已经能在 mock 模式下跑通群聊锐评和双人关系锐评两条主链路。

前端工程位置：`frontend/`。请在这个目录下运行 npm 命令。

## 当前状态

已完成：

- Vite + React + TypeScript 前端工程。
- 落地页、上传页、分析中页、报告页、分享页。
- 群聊报告 mock 数据和渲染。
- 双人关系报告 mock 数据和渲染。
- 上传页支持报告类型选择、拖拽文件、点击上传、粘贴文本、默认脱敏。
- 报告页支持图表、金句卡片、分享卡片、复制链接、保存长图、系统分享。
- 接口契约文档：[docs/contracts/frontend-api.md](../contracts/frontend-api.md)

还没接真实数据：

- 2 号真实微信 txt 解析器。
- 3 号真实后端 API。
- 5 号真实 LLM 输出。
- 1 号正式视觉稿、教程 GIF / 视频、Demo 截图素材。

## 如何运行

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173/
```

构建检查：

```bash
cd frontend
npm run build
```

当前构建可能出现 chunk 体积警告，不影响 MVP 使用。

## 推荐验收路线

群聊路线：

1. 打开 `/upload`
2. 选择“群聊锐评”
3. 点击“填入样例文本”
4. 点击“开始分析”
5. 等待跳转到 `/report/demo-report-001`
6. 测试复制链接、保存长图、系统分享

双人关系路线：

1. 打开 `/upload?type=relationship`
2. 确认“双人关系”已选中
3. 点击“填入样例文本”
4. 点击“开始分析”
5. 等待跳转到 `/report/demo-relationship-001`
6. 打开 `/share/demo-relationship` 检查分享页

## 目录说明

```text
frontend/src/
├── api/client.ts              # API 适配层，mock / 真实后端切换点
├── contracts/report.ts        # 全队共用的报告和消息类型
├── mock/report.ts             # 群聊、双人关系 mock 数据
├── utils/parser.ts            # 临时文本解析器，等 2 号替换
├── pages/                     # 页面路由
└── components/report/         # 报告图表、分享卡片、渲染器
```

## 交给 2 号：解析器接入点

当前临时解析函数在：

```text
frontend/src/utils/parser.ts
```

2 号只要保证最终能产出 `ChatMessage[]` 即可。字段要求见：

```text
frontend/src/contracts/report.ts
docs/contracts/frontend-api.md
```

注意：

- 前端默认脱敏，昵称会变成 `A 同学`、`B 同学` 这类代号。
- 原始聊天文本不要持久化。
- 大文件分片和 Web Worker 还没接，可以后续单独做。

## 交给 3 号：后端接入点

前端所有接口调用都集中在：

```text
frontend/src/api/client.ts
```

真实后端准备好后，建议做这几件事：

1. 设置 `VITE_API_MODE=real`
2. 设置 `VITE_API_BASE_URL=http://你的后端地址`
3. 保持以下接口路径：
   - `POST /api/analyze`
   - `GET /api/report/:id`
   - `POST /api/share/:id`
   - `GET /api/share/:slug`
4. 返回结构按 `docs/contracts/frontend-api.md` 对齐。

后端如果暂时只做 mock，也没问题，只要字段名稳定，前端就能继续联调。

## 交给 5 号：LLM 输出接入点

5 号的输出最终应该进入 `ReportPayload`：

- `title`：报告标题
- `tagline`：副标题
- `hero`：第一屏金句和视觉符号
- `tags`：标签
- `sections`：报告段落
- `quotes`：金句卡片

群聊和双人关系都走同一个结构，只是 `report_type` 不同：

- `group_roast`：群聊锐评
- `relationship`：双人关系

前端已经根据 `report_type` 对金句区和关系图做了差异化展示。

## 交给 1 号：视觉和素材替换点

当前页面里有这些占位：

- 首页 Demo 报告预览是 CSS 做的假图。
- 上传页右侧教程区是 GIF / 视频占位。
- 报告视觉风格已经可用，但还不是最终品牌稿。

后续 1 号给素材后，优先替换：

- `frontend/src/pages/LandingPage.tsx` 首页预览和文案。
- `frontend/src/pages/UploadPage.tsx` 教程区素材。
- `frontend/src/styles.css` 里的颜色、字体、间距变量。

## 已知注意事项

- `html2canvas` 会让构建产物稍大，当前 MVP 可接受。
- 现在没有配置 ESLint，质量检查先用 `npm run build`。
- `relationship_metrics` 是可选字段，后端早期没给也不会阻塞关系报告渲染。
- 不要在页面组件里直接 `fetch`，统一走 `frontend/src/api/client.ts`。
- 不要把原始聊天文本写入 localStorage、数据库或分享接口。
- Trellis / agent 目录只是 4 号本地 AI 工作流文件，已在 `.gitignore` 里忽略，队友不用提交或维护。

## 最小联调清单

- [ ] `/upload` 可以提交群聊样例。
- [ ] `/upload?type=relationship` 可以提交双人样例。
- [ ] `/report/demo-report-001` 正常显示群聊报告。
- [ ] `/report/demo-relationship-001` 正常显示双人关系报告。
- [ ] `/share/demo-longwang` 正常显示群聊分享页。
- [ ] `/share/demo-relationship` 正常显示双人关系分享页。
- [ ] `npm run build` 通过。
