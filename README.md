# Cyber Judge / 赛博判官

Cyber Judge 是一个本地优先的微信聊天记录与聊天 JSON 分析工具。它可以导入本机微信会话，或读取 WeFlow、wechat-decrypt 等工具导出的 JSON，生成统计证据、中间主题页和最终 AI 报告。

一句话版：把聊天记录送上被告席，先看证据，再下判词。

## 项目链接

- 项目展示页：<https://kyc001.github.io/cyber-judge/>
- GitHub Release：<https://github.com/kyc001/cyber-judge/releases/tag/v0.1.0>
- Windows 桌面版下载：<https://github.com/kyc001/cyber-judge/releases/download/v0.1.0/CyberJudgeDesktop.exe>
- 源码仓库：<https://github.com/kyc001/cyber-judge>

## 当前版本

- 版本：`Cyber Judge Desktop v0.1.0`
- 平台：Windows
- 发布附件：`CyberJudgeDesktop.exe`
- 文件大小：48,722,900 bytes，约 46.5 MB
- SHA256：`D362CFA75B08DAC54689B52B00E030955199AEC7C68FF0160428A8469386A547`

当前 exe 尚未做代码签名，首次运行时 Windows 或杀毒软件可能提示风险。

## 核心功能

- 本机微信导入：读取本机微信会话列表，支持群聊、单聊、全部会话筛选。
- 日期范围筛选：可限制起止时间，避免整段历史聊天过大或主题过杂。
- 手动 JSON 导入：支持上传或粘贴 WeFlow、wechat-decrypt 等工具导出的聊天 JSON。
- 数据预览：导入前查看成员、消息类型、时间范围和样例消息。
- 群聊报告：分析成员活跃度、互动结构、共同语言、表情偏好、时间节奏和关系走势。
- 双人关系报告：分析消息占比、主动程度、回复节奏、共同词汇、情绪温度和关系模式。
- 中间主题页：包含聊天总览、时间与作息、语言与梗、表情包档案、互动网络、情绪温度、消息结构、关系走势、名场面回放和趋势预测。
- AI 报告生成：可配置 DeepSeek、OpenAI、通义千问等服务商和模型。
- 导出与分享：最终报告支持分享链接、JSON 导出和 HTML 导出。
- 桌面运行：将 FastAPI 后端、React 前端和微信导入适配器打包为一个可双击启动的 Windows exe。

## 普通用户使用

1. 打开 Release 页面：<https://github.com/kyc001/cyber-judge/releases/tag/v0.1.0>
2. 下载附件 `CyberJudgeDesktop.exe`。
3. 双击运行桌面版。
4. 在导入页选择本机微信导入，或手动上传聊天 JSON。
5. 选择群聊报告或双人关系报告。
6. 按需要设置日期范围、匿名化选项和模型配置。
7. 等待解析、统计和 LLM 生成完成。
8. 查看中间主题页与最终报告，按需要导出或分享。

## 隐私与数据

Cyber Judge 的设计目标是本地优先，而不是把聊天记录托管到云端。

- 桌面版不会打包 `.env`，也不会自动读取 exe 旁边的 `.env`。
- LLM API Key 由用户在应用内模型设置中填写，并保存到本机应用数据目录。
- 微信导入、消息解析、统计计算和本地数据库默认运行在用户自己的电脑上。
- 只有生成 AI 报告时，应用才会按照用户配置调用对应 LLM 服务商。
- 如果处理敏感聊天记录，建议开启匿名化，并确认所选 LLM 服务商的数据处理政策。

## 开发环境

### 前置要求

- Node.js 与 npm
- Python 3.11、3.12 或 3.13
- Windows 桌面打包环境使用 Pixi；`npm run setup` 会检查并准备 Pixi 环境

### 首次安装

```powershell
npm run setup
```

这个命令会完成：

- 安装前端依赖
- 创建 `backend/venv`
- 安装后端 Python 依赖
- 准备 `backend/pixi.toml` 对应的 Pixi 桌面打包环境

### 启动开发环境

```powershell
npm run dev
```

访问：

```text
http://127.0.0.1:5173/
```

前端由 Vite 启动，Vite 插件会自动尝试启动 `backend/main.py`。开发时前端 API 通过代理访问后端 `http://127.0.0.1:8000`。

### 构建前端

```powershell
npm run build
```

构建产物位于 `frontend/dist/`，这是桌面版打包时会被嵌入的前端静态资源。

## 桌面版

### Windows 一键打包

```powershell
desktop\build-windows.bat
```

构建脚本会先执行前端构建，再用 PyInstaller 打包桌面应用。默认输出：

```text
dist\CyberJudgeDesktop.exe
```

如果需要单独运行桌面启动壳，可以先构建前端，再执行：

```powershell
pixi run --manifest-path backend\pixi.toml python desktop\cyber_judge_desktop.py --no-webview
```

嵌入式 WebView 模式：

```powershell
pixi run --manifest-path backend\pixi.toml python desktop\cyber_judge_desktop.py
```

### 桌面版运行流程

1. 启动 `CyberJudgeDesktop.exe`。
2. 启动壳在本机启动 FastAPI 服务。
3. FastAPI 从同一本地 origin 提供 `frontend/dist` 和 `/api/*`。
4. 启动壳优先打开内嵌 WebView；不可用时回退到默认浏览器。
5. 用户在本地页面中完成导入、分析和导出。

## LLM 配置

桌面版推荐在应用内配置模型。开发环境可以用 `backend/.env` 作为兜底配置：

```powershell
copy backend\.env.example backend\.env
```

常用配置项：

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_FALLBACK_PROVIDER`
- `LLM_FALLBACK_API_KEY`
- `LLM_FALLBACK_API_BASE`
- `LLM_FALLBACK_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `DATABASE_PATH`

## GitHub Pages

项目展示页位于 `docs/`，并通过 GitHub Actions 自动部署到 GitHub Pages。

- 静态页面：`docs/index.html`
- 页面样式：`docs/styles.css`
- 展示图：`docs/assets/hero.png`
- 部署 workflow：`.github/workflows/pages.yml`

推送 `master` 后，如果修改范围包含 `docs/**` 或 Pages workflow，会自动部署：

```text
https://kyc001.github.io/cyber-judge/
```

这里没有直接部署完整 `frontend` 应用，因为线上 GitHub Pages 没有本地 FastAPI 后端；展示页只承担项目介绍和下载入口。

## 发布流程

源码仓库不再提交桌面 exe。构建产物应作为 GitHub Release 附件发布。

本地发布产物目录：

```text
dist-rebuild/
```

如果某个 exe 曾经被提交进 Git，可以先从索引移除，但保留本地文件：

```powershell
git rm --cached dist-rebuild\CyberJudgeDesktop.exe
```

创建 release：

先把 release 说明写到一个临时文件，例如 `RELEASE_NOTES.md`；这个文件可以只在本地使用，不一定要提交进仓库。

```powershell
gh release create v0.1.0 "dist-rebuild\CyberJudgeDesktop.exe#Cyber Judge Desktop for Windows" --target master --title "Cyber Judge Desktop v0.1.0" --notes-file RELEASE_NOTES.md
```

如果 release 已存在，只补传或覆盖附件：

```powershell
gh release upload v0.1.0 dist-rebuild\CyberJudgeDesktop.exe --clobber
```

更新 release 文案：

```powershell
gh release edit v0.1.0 --title "Cyber Judge Desktop v0.1.0" --notes-file RELEASE_NOTES.md
```

## 页面路由

- `/`：首页
- `/upload`：导入、筛选、预览和模型配置
- `/analyzing?reportId=...`：分析进度
- `/insights/:id/summary`：中间主题页起点
- `/insights/:id/:view`：指定中间主题页
- `/report/:id`：最终报告
- `/share/:slug`：分享页

## API 概览

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

## 目录结构

- `backend/`：FastAPI 后端、微信导入、解析、统计、LLM、报告导出。
- `backend/wechat_decrypt/`：微信数据读取、解密、导出和相关工具。
- `frontend/`：React 前端页面、图表组件、主题系统和 API client。
- `desktop/`：桌面启动壳、PyInstaller spec 和 Windows 构建脚本。
- `docs/`：GitHub Pages 展示页、架构文档、功能清单和桌面版说明。
- `example/`：示例聊天数据。
- `dist-rebuild/`：本地发布产物目录，已忽略，不提交到 Git。

## 常见问题

### 为什么 README 里有 GitHub Pages，而不是直接把前端部署上去？

完整前端应用依赖本地 FastAPI 后端和本地文件导入能力。GitHub Pages 是静态托管，适合做项目介绍、下载入口和文档展示，不适合直接运行完整分析应用。

### 为什么 exe 不提交进 Git？

exe 是构建产物，体积大、变化频繁，也不方便代码审查。更合适的方式是把它放到 GitHub Release，源码仓库只保留代码、文档、锁文件和必要示例。

### 为什么 Windows 会提示风险？

当前 exe 未做代码签名。未签名的 Windows 桌面应用，尤其是会读取本地数据或启动本地服务的应用，可能被系统或杀毒软件提示风险。正式公开分发前建议加入代码签名和校验说明。

### 聊天数据会上传到服务器吗？

默认解析、统计和数据库都在本机运行。生成 AI 报告时，会根据你在应用内配置的模型服务商调用外部 API；这一步会涉及发送用于生成报告的内容或摘要。处理敏感数据时请开启匿名化，并谨慎选择模型服务商。

## 开发备注

当前主分支为 `master`。如果要修改展示页，编辑 `docs/` 后推送即可触发 Pages 部署；如果要修改完整应用，请优先修改 `frontend/`、`backend/` 或 `desktop/` 对应模块。
