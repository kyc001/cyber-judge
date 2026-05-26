# Cyber Judge / 赛博判官

赛博判官读取 WeFlow 导出的微信聊天 JSON，先生成按顺序播放的聊天分镜，再进入最终 AI 报告页。当前输入只支持 WeFlow JSON。

## 功能

- 上传聊天 JSON，预览成员、消息类型、时间范围和样例消息
- 支持群聊锐评和双人关系两种报告类型
- 可选择匿名化昵称
- 分析页展示解析、统计和 LLM 生成进度
- 聊天分镜按固定顺序展示：聊天总览、时间与作息、语言与梗、表情包档案、互动网络、情绪温度、消息结构、关系走势、名场面回放、赛博占卜
- 表情包档案会读取 WeFlow 的 `emojiCdnUrl` 和 `emojiMd5`，支持 GIF、PNG、WebP、JPG 等真实表情包资源，并合并微信中英文别名避免重复展示
- 最终报告支持分享链接、JSON 导出和 HTML 导出

## 运行

首次安装：

```powershell
npm run setup
```

启动开发环境：

```powershell
npm run dev
```

访问：

```text
http://127.0.0.1:5173/
```

`npm run dev` 会由 Vite 自动启动 `backend/main.py`，前端 API 通过代理访问 `http://127.0.0.1:8000`。

## LLM 配置

复制环境变量模板：

```powershell
copy backend\.env.example backend\.env
```

需要配置：

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_API_BASE`
- `LLM_MODEL`
- `LLM_FALLBACK_PROVIDER`、`LLM_FALLBACK_API_KEY`、`LLM_FALLBACK_API_BASE`、`LLM_FALLBACK_MODEL`（可选）
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `DATABASE_PATH`

## 页面

- `/`：首页
- `/upload`：上传与预览
- `/analyzing?reportId=...`：分析进度
- `/insights/:id/summary`：聊天分镜起点
- `/insights/:id/:view`：指定分镜页
- `/report/:id`：最终报告
- `/share/:slug`：分享页

## API

- `POST /api/upload`
- `GET /api/report/:id`
- `GET /api/report/:id/progress`
- `POST /api/share/:id`
- `GET /api/share/:slug`
- `POST /api/export`
- `GET /api/health`

## 目录

- `backend/`：FastAPI、解析、统计、LLM、导出
- `frontend/`：React 页面、图表组件和 API client
- `docs/`：架构、功能清单和交接文档
- `references/`：参考项目
- `example/`、`texts/`：测试数据

## 检查

```powershell
npm run build
```
