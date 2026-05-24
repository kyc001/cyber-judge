# cyber-judge

赛博判官项目的 4 号前端 MVP。当前实现支持两条 mock 流程：

- 群聊锐评报告：龙王榜、群人设、词云、热力图、元宝语录。
- 双人关系锐评报告：关系定性、主动程度、关系分数、关系金句、时间轴。

默认使用 mock 数据运行，不依赖后端、解析器或 LLM 服务，方便 2/3/5 号接口还没完成时先联调页面。

前端工程已集中放在 `frontend/` 目录，根目录只保留项目说明、计划文档、团队文档和 Trellis/agent 配置。

## 技术栈

- Vite
- React
- TypeScript
- CSS 设计变量
- mock 优先的 API 适配层

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

启动后访问：

```text
http://localhost:5173/
```

## 常用页面

- `/`：落地页
- `/upload`：上传 / 粘贴聊天记录
- `/upload?type=relationship`：直接进入双人关系模式
- `/analyzing`：分析中页面
- `/report/demo-report-001`：群聊 Demo 报告
- `/report/demo-relationship-001`：双人关系 Demo 报告
- `/share/demo-longwang`：群聊分享页
- `/share/demo-relationship`：双人关系分享页

## 关键文件

- `frontend/src/api/client.ts`：前端唯一 API 入口，后续从 mock 切真实后端主要改这里。
- `frontend/src/contracts/report.ts`：前端、解析器、后端、LLM 共用的数据类型。
- `frontend/src/mock/report.ts`：群聊和双人关系的 mock 报告数据。
- `frontend/src/utils/parser.ts`：临时文本解析器，后续可由 2 号替换。
- `frontend/src/components/report/`：报告图表、金句卡片、分享卡片。
- `docs/contracts/frontend-api.md`：接口契约文档。
- `docs/handover/frontend-handover.md`：前端交接说明。

## 验证命令

```bash
cd frontend
npm run build
```

当前构建会出现一个 chunk 体积警告，这是 `html2canvas` 等前端库导致的，不影响 MVP 运行。后续上线前可以再做按路由拆包。

## 接口与交接

- 接口契约见：[docs/contracts/frontend-api.md](docs/contracts/frontend-api.md)
- 前端交接见：[docs/handover/frontend-handover.md](docs/handover/frontend-handover.md)

## 提交建议

仓库已通过 `.gitignore` 忽略本地依赖、构建产物、日志、环境变量，以及 Trellis / agent 相关本地工作流文件。团队提交时主要关注：

- `frontend/`
- `docs/`
- `README.md`
- `plan.md`
