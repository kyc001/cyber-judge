import { Upload } from "lucide-react";
import { Link } from "react-router-dom";

export function LandingPage() {
  return (
    <main className="page landing-page">
      <section className="landing-hero">
        <nav className="top-nav" aria-label="主导航">
          <Link className="brand" to="/">
            <span>判</span>
            赛博判官
          </Link>
          <Link className="nav-cta" to="/upload">
            开始生成
          </Link>
        </nav>

        <div className="hero-content">
          <p className="eyebrow">微信聊天记录 AI 锐评报告</p>
          <h1>上传聊天记录，生成全群都想转发的赛博体检报告。</h1>
          <p>
            支持 WeFlow JSON 格式。45+ 个统计维度，
            多段 LLM 分析、AI 锐评、个性勋章、赛博占卜和聊天分镜。
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/upload">
              <Upload size={18} />
              <span>上传聊天记录</span>
            </Link>
          </div>
        </div>

        <div className="hero-preview" aria-label="报告预览">
          <div className="preview-phone">
            <div className="preview-screen">
              <p>群聊人格样本</p>
              <h2>你们群的 AI 体检报告</h2>
              <div className="preview-bars">
                <span /><span /><span />
              </div>
              <blockquote>数据不会说谎，只会锐评。</blockquote>
            </div>
          </div>
        </div>
      </section>

      <section className="feature-band">
        <article>
          <Upload />
          <h2>拖拽上传</h2>
          <p>支持 WeFlow JSON，拖拽或粘贴即可。</p>
        </article>
        <article>
          <span className="feature-icon">📊</span>
          <h2>45 维分析</h2>
          <p>热力图、词云、互动图谱、情绪检测、作息鉴定、人格勋章。</p>
        </article>
        <article>
          <span className="feature-icon">🤖</span>
          <h2>AI 锐评</h2>
          <p>LLM 生成群聊人设、龙王锐评、金句点评、赛博占卜。</p>
        </article>
      </section>

      <section className="faq-band">
        <h2>FAQ</h2>
        <details>
          <summary>支持哪些聊天格式？</summary>
          <p>当前稳定接入 WeFlow 导出的 .json 格式。</p>
        </details>
        <details>
          <summary>聊天数据会上传到服务器吗？</summary>
          <p>会提交给本地后端完成解析、统计和 LLM 生成；开启脱敏后昵称会替换为 A同学、B同学。</p>
        </details>
        <details>
          <summary>如何导出微信聊天记录？</summary>
          <p>使用 WeFlow 打开目标聊天，导出 JSON 后上传到这里。</p>
        </details>
      </section>
    </main>
  );
}
