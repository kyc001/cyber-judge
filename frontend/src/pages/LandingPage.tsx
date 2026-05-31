import { BarChart3, Brain, HeartHandshake, MessageCircleMore, Sparkles, Upload } from "lucide-react";
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
          <p className="eyebrow">微信聊天分析</p>
          <h1>导入聊天记录，生成统计页和 AI 报告。</h1>
          <p>
            支持本机微信自动导入，也可以上传 JSON。系统会统计时间、成员、
            语言、表情、互动和代表片段，再生成中间页和最终报告。
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/upload">
              <Upload size={18} />
              <span>导入聊天记录</span>
            </Link>
            <Link className="btn btn-secondary" to="/upload?type=relationship">
              <HeartHandshake size={18} />
              <span>双人分析</span>
            </Link>
          </div>
          <div className="hero-proof-row" aria-label="核心分析能力">
            <span><Brain size={16} /> 本机微信导入</span>
            <span><MessageCircleMore size={16} /> 群聊/双人报告</span>
            <span><Sparkles size={16} /> 中间分析页</span>
          </div>
        </div>

        <div className="hero-preview" aria-label="报告预览">
          <div className="preview-phone">
            <div className="preview-screen">
              <p className="preview-chip">报告摘要</p>
              <h2>聊天记录概览</h2>
              <div className="preview-stack">
                <span>消息量、成员与时间范围</span>
                <span>互动关系与回复节奏</span>
                <span>代表性原话和上下文</span>
              </div>
              <blockquote>导入后先展示中间页，再进入最终报告。</blockquote>
            </div>
          </div>
        </div>
      </section>

      <section className="feature-band feature-band-product">
        <article>
          <Brain />
          <h2>自动导入</h2>
          <p>从本机微信读取会话，也支持手动上传 JSON。</p>
        </article>
        <article>
          <MessageCircleMore />
          <h2>群聊报告</h2>
          <p>成员活跃、互动关系、共同词汇和表情偏好。</p>
        </article>
        <article>
          <HeartHandshake />
          <h2>双人报告</h2>
          <p>消息占比、主动程度、回复节奏和共同语言。</p>
        </article>
        <article>
          <BarChart3 />
          <h2>中间分析页</h2>
          <p>时间、语言、表情、情绪和媒体结构分屏查看。</p>
        </article>
      </section>

      <section className="faq-band">
        <h2>FAQ</h2>
        <details>
          <summary>支持哪些聊天格式？</summary>
          <p>支持本机微信自动导入，也支持 WeFlow 或微信导出的 JSON。</p>
        </details>
        <details>
          <summary>聊天数据会上传到服务器吗？</summary>
          <p>会提交给本地后端完成解析、统计和 LLM 生成；开启脱敏后昵称会替换为 A同学、B同学。</p>
        </details>
        <details>
          <summary>需要手动导出微信聊天记录吗？</summary>
          <p>通常不需要。进入导入页，先准备微信数据，再读取并选择会话。</p>
        </details>
      </section>
    </main>
  );
}
