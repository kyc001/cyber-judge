# Cyber Judge / 赛博判官

Cyber Judge 是一个本地优先的微信聊天记录与 JSON 聊天数据分析工具。它可以导入本机微信会话或手动上传聊天 JSON，生成统计中间页和最终 AI 报告。

当前推荐的分发方式是 Windows 桌面版：把构建出的 `CyberJudgeDesktop.exe` 作为 GitHub Release 附件发布，源码仓库只保存代码、文档、锁文件和示例数据。

## 功能

- 本机微信导入：准备微信数据、读取会话列表，按群聊、单聊、全部、起止日期筛选。
- 手动 JSON 导入：支持上传或粘贴 WeFlow、wechat-decrypt 等工具导出的 JSON。
- 报告模型配置：在导入页选择 DeepSeek、OpenAI 或通义千问，并填写 API Key。
- 支持群聊报告和双人报告，可选择匿名化称呼。
- 分析页展示解析、统计和 LLM 生成进度。
- 中间主题页包含聊天总览、时间与作息、语言与梗、表情包档案、互动网络、情绪温度、消息结构、关系走势、名场面回放、趋势预测。
- 最终报告支持分享链接、JSON 导出和 HTML 导出。

## 快速开始

首次安装依赖：

```powershell
npm run setup
```

`npm run setup` 会安装前端依赖，创建 `backend/venv`，并准备桌面打包用的 Pixi 环境。Python 版本建议使用 3.11、3.12 或 3.13。

启动开发环境：

```powershell
npm run dev
```

访问：

```text
http://127.0.0.1:5173/
```

`npm run dev` 会由 Vite 启动前端，并通过代理访问后端 `http://127.0.0.1:8000`。

## 桌面版构建

Windows 一键构建：

```powershell
desktop\build-windows.bat
```

构建脚本会先执行前端构建，再用 PyInstaller 打包桌面应用。脚本默认输出：

```text
dist\CyberJudgeDesktop.exe
```

如果你手上已经有重建后的产物，例如：

```text
D:\Study\26sp\cyber-judge\dist-rebuild\CyberJudgeDesktop.exe
```

也可以直接把这个文件作为 GitHub Release 附件上传。

## 发布到 GitHub Release

先确认 exe 存在：

```powershell
Get-Item dist-rebuild\CyberJudgeDesktop.exe
```

发布前建议只提交源码和文档，不要把 exe 提交进 Git。`dist-rebuild/` 已经在 `.gitignore` 中，适合放本地发布产物。

如果这个 exe 之前已经被提交过，先把它从 Git 索引中移除，但保留本地文件：

```powershell
git rm --cached dist-rebuild\CyberJudgeDesktop.exe
```

### 网页方式

1. 把源码改动提交并推送到 GitHub：

```powershell
git status
git add README.md .gitignore
git commit -m "docs: update release instructions"
git push
```

2. 打开 GitHub 仓库主页，进入右侧或顶部的 `Releases`。
3. 点击 `Draft a new release`。
4. 在 `Choose a tag` 中创建版本号，例如 `v0.1.0`，目标分支选 `main` 或你的发布分支。
5. Release title 填 `Cyber Judge Desktop v0.1.0`。
6. 在附件区域拖入或选择 `dist-rebuild\CyberJudgeDesktop.exe`。
7. 填写 release notes，例如本次修复、已知问题、Windows 未签名提示。
8. 点击 `Publish release`。如果还想检查附件，可以先点 `Save draft`。

### GitHub CLI 方式

安装并登录 GitHub CLI 后，可以在仓库根目录执行：

```powershell
gh auth login
gh release create v0.1.0 "dist-rebuild\CyberJudgeDesktop.exe#Cyber Judge Desktop for Windows" --title "Cyber Judge Desktop v0.1.0" --notes "Windows desktop build." --target main
```

如果 release 已经创建，只是补传或覆盖 exe：

```powershell
gh release upload v0.1.0 dist-rebuild\CyberJudgeDesktop.exe --clobber
```

发布成功后，下载地址通常是：

```text
https://github.com/<owner>/<repo>/releases/download/v0.1.0/CyberJudgeDesktop.exe
```

## LLM 配置

桌面 exe 不打包 `.env`，也不会自动读取 exe 旁边的 `.env`。用户在导入页的模型设置里选择服务商、模型并填写 API Key；配置会保存到本机应用数据目录。

开发环境仍可以用环境变量作为兜底配置：

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

- `backend/`：FastAPI、微信导入、解析、统计、LLM、导出。
- `frontend/`：React 页面、图表组件和 API client。
- `desktop/`：桌面启动壳、PyInstaller spec 和 Windows 构建脚本。
- `docs/`：架构、功能清单、桌面版说明和交接文档。
- `example/`：示例聊天数据。
- `dist-rebuild/`：本地发布产物目录，已忽略，不提交到 Git。

## 检查

重新安装依赖后运行：

```powershell
npm run build
```

注意：未签名的 Windows exe 可能触发系统或杀毒软件提示；正式公开发布前建议做代码签名或提供校验信息。
