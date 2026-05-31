# Cyber Judge / 赛博判官

赛博判官用于读取本机微信聊天或聊天 JSON，生成统计中间页和最终 AI 报告。当前主流程是本机微信自动导入；也支持手动上传或粘贴 WeFlow、wechat-decrypt 导出的 JSON。

## 功能

- 本机微信导入：准备微信数据、读取会话、按群聊/单聊/全部筛选、按起止日期筛选
- 导入微信会话后直接进入分析，可选择保存一份 JSON 副本；桌面模式使用目录选择器，浏览器模式使用保存对话框
- 手动 JSON 导入：上传或粘贴 JSON，并预览成员、消息类型、时间范围和样例消息
- 导入页可配置报告生成模型：选择 DeepSeek、OpenAI 或通义千问及对应模型，只需填写 API Key
- 支持群聊报告和双人报告两种分析类型
- 可选择匿名化昵称
- 分析页展示解析、统计和 LLM 生成进度
- 中间主题页按固定顺序展示：聊天总览、时间与作息、语言与梗、表情包档案、互动网络、情绪温度、消息结构、关系走势、名场面回放、趋势预测
- 表情包档案会读取 WeFlow 的 `emojiCdnUrl` 和 `emojiMd5`，支持 GIF、PNG、WebP、JPG 等真实表情包资源，并合并微信中英文别名避免重复展示
- 最终报告支持分享链接、JSON 导出和 HTML 导出

## 运行

首次安装：

```powershell
npm run setup
```

`npm run setup` 会安装前端依赖、创建后端 `venv`，并检查/安装 Pixi 桌面打包环境。

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

桌面 exe 不打包 `.env`，也不会自动读取 exe 旁边的 `.env`。用户在导入页的“模型设置”里选择服务商、模型并填写 API Key；配置会保存到本机应用数据目录，后续报告生成直接使用这份本机配置。

开发环境仍可使用环境变量作为兜底配置：

```powershell
copy backend\.env.example backend\.env
```

常用配置：

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_FALLBACK_PROVIDER`、`LLM_FALLBACK_API_KEY`、`LLM_FALLBACK_API_BASE`、`LLM_FALLBACK_MODEL`（可选）
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `DATABASE_PATH`

## 页面

- `/`：首页
- `/upload`：导入、筛选、预览
- `/analyzing?reportId=...`：分析进度
- `/insights/:id/summary`：中间主题页起点
- `/insights/:id/:view`：指定主题页
- `/report/:id`：最终报告
- `/share/:slug`：分享页

## API

- `POST /api/upload`
- `POST /api/wechat/prepare`
- `GET /api/wechat/chats`
- `POST /api/wechat/import`
- `GET /api/wechat/import/:id/progress`
- `GET /api/wechat/import/:id/json`
- `POST /api/wechat/export`
- `GET /api/llm/config`
- `POST /api/llm/config`
- `POST /api/llm/test`
- `GET /api/report/:id`
- `GET /api/report/:id/progress`
- `POST /api/share/:id`
- `GET /api/share/:slug`
- `POST /api/export`
- `GET /api/health`

## 目录

- `backend/`：FastAPI、微信导入、解析、统计、LLM、导出
- `frontend/`：React 页面、图表组件和 API client
- `desktop/`：桌面启动壳和目录选择桥接
- `docs/`：架构、功能清单和交接文档
- `references/`：参考项目
- `example/`、`texts/`：测试数据

## 检查

```powershell
npm run build
```
