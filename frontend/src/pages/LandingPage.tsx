import { ArrowRight, LockKeyhole, Share2, Sparkles, Upload } from "lucide-react";
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
          <p className="eyebrow">微信聊天记录锐评报告</p>
          <h1>上传聊天记录，生成一份全群都想转发的赛博体检。</h1>
          <p>
            先用 mock 数据跑通全链路，等 2 / 3 / 5 号接口到位后无缝替换。
            原始消息只在浏览器内处理，不作为产品数据保存。
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/upload">
              <Upload size={18} />
              <span>上传 txt</span>
            </Link>
            <Link className="btn btn-secondary" to="/report/demo-report-001">
              <Sparkles size={18} />
              <span>看 Demo 报告</span>
            </Link>
            <Link className="btn btn-secondary" to="/upload?type=relationship">
              <Share2 size={18} />
              <span>测双人关系</span>
            </Link>
          </div>
        </div>

        <div className="hero-preview" aria-label="Demo 报告预览">
          <div className="preview-phone">
            <div className="preview-screen">
              <p>群聊人格样本</p>
              <h2>深夜放毒嘴硬互助会</h2>
              <div className="preview-bars">
                <span />
                <span />
                <span />
              </div>
              <blockquote>你们不是没有作息，只是作息长得比较抽象。</blockquote>
            </div>
          </div>
        </div>
      </section>

      <section className="feature-band">
        <article>
          <Upload />
          <h2>导入低门槛</h2>
          <p>拖拽、点击、粘贴三种入口，先支持微信 PC txt。</p>
        </article>
        <article>
          <LockKeyhole />
          <h2>隐私先行</h2>
          <p>默认脱敏，后端只接收结构化消息和统计结果。</p>
        </article>
        <article>
          <Share2 />
          <h2>出片可分享</h2>
          <p>报告页、分享页、二维码和长图导出全部预留，也支持双人关系报告。</p>
        </article>
      </section>

      <section className="demo-strip">
        <div>
          <p className="eyebrow">D1 联调目标</p>
          <h2>不等真实接口，先把群聊和双人关系两条线都跑通。</h2>
          <p>
            前端当前内置 role 2 / 3 / 5 的 mock 合同，后续只替换 API
            适配层，不推倒页面。
          </p>
        </div>
        <Link className="btn btn-ghost" to="/upload">
          <span>进入上传页</span>
          <ArrowRight size={18} />
        </Link>
      </section>

      <section className="faq-band">
        <h2>FAQ</h2>
        <details>
          <summary>现在没有后端可以看效果吗？</summary>
          <p>可以。当前默认 mock 模式，上传后会生成 demo 报告。</p>
        </details>
        <details>
          <summary>原始聊天会保存吗？</summary>
          <p>前端只在本次页面流程里读取文本，接口合同要求不上传原始文件。</p>
        </details>
        <details>
          <summary>Streamlit 能不能用？</summary>
          <p>可以作为内部调试台，但正式分享页面使用 React 前端。</p>
        </details>
      </section>
    </main>
  );
}
