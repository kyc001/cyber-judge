import {
  BarChart3,
  Brain,
  Clock3,
  FileJson,
  HeartHandshake,
  MessageCircleMore,
  MessageSquareQuote,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { Link } from "react-router-dom";

export function LandingPage() {
  return (
    <main className="page landing-page">
      <nav className="top-nav app-top-nav" aria-label="主导航">
        <Link className="brand" to="/">
          <span>判</span>
          赛博判官
        </Link>
        <div className="top-nav-actions">
          <Link className="nav-link" to="/upload?type=relationship">双人关系</Link>
          <Link className="nav-cta" to="/upload">
            <Upload size={16} />
            <span>新建分析</span>
          </Link>
        </div>
      </nav>

      <section className="landing-hero app-workbench">
        <div className="hero-content">
          <p className="eyebrow">聊天关系审判台</p>
          <h1>把聊天记录送上被告席。</h1>
          <p>
            从本机微信或 JSON 导入，先看数据证据，再生成几页可翻阅的锐评报告。
            群聊看权力结构，双人看关系节奏，不再只给两句“挺活跃”的废话。
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/upload">
              <Upload size={18} />
              <span>开始导入</span>
            </Link>
            <Link className="btn btn-secondary" to="/upload?type=relationship">
              <HeartHandshake size={18} />
              <span>双人分析</span>
            </Link>
          </div>
          <dl className="hero-metric-grid" aria-label="分析链路">
            <div>
              <dt>01</dt>
              <dd>读取会话</dd>
            </div>
            <div>
              <dt>02</dt>
              <dd>证据拆解</dd>
            </div>
            <div>
              <dt>03</dt>
              <dd>生成锐评</dd>
            </div>
          </dl>
        </div>

        <div className="hero-preview app-preview" aria-label="产品界面预览">
          <div className="preview-window">
            <div className="preview-window-bar">
              <span />
              <span />
              <span />
              <strong>report.console</strong>
            </div>
            <div className="preview-console-grid">
              <section className="preview-verdict">
                <p className="preview-chip">关系模式</p>
                <h2>龙王供氧型群聊</h2>
                <p>有人负责点火，有人负责接梗，还有人只在关键时刻冒泡证明自己没退群。</p>
              </section>
              <section className="preview-evidence">
                <div>
                  <span>高峰时段</span>
                  <strong>23:00</strong>
                </div>
                <div>
                  <span>主导成员</span>
                  <strong>A同学</strong>
                </div>
                <div>
                  <span>代表片段</span>
                  <strong>12条</strong>
                </div>
              </section>
              <section className="preview-flow">
                <span><Clock3 size={15} /> 作息病历</span>
                <span><MessageSquareQuote size={15} /> 原话证据</span>
                <span><Sparkles size={15} /> 后续走势</span>
              </section>
            </div>
          </div>
        </div>
      </section>

      <section className="feature-band feature-band-product product-console-band">
        <article>
          <Brain />
          <h2>本机导入</h2>
          <p>从本机微信读取会话，也支持手动上传 JSON。</p>
        </article>
        <article>
          <MessageCircleMore />
          <h2>群聊锐评</h2>
          <p>成员活跃、互动关系、共同词汇和表情偏好一起看。</p>
        </article>
        <article>
          <HeartHandshake />
          <h2>双人关系</h2>
          <p>消息占比、主动程度、回复节奏和共同语言。</p>
        </article>
        <article>
          <FileJson />
          <h2>模型可配</h2>
          <p>内置默认模型，也可以换 Base URL、Key 和模型名。</p>
        </article>
      </section>

      <section className="faq-band workflow-band">
        <div>
          <p className="eyebrow">报告结构</p>
          <h2>先给证据，再下判词。</h2>
        </div>
        <div className="workflow-grid">
          <article>
            <ShieldCheck />
            <strong>脱敏预处理</strong>
            <p>默认替换昵称，报告里保留行为证据，不把隐私摆上台面。</p>
          </article>
          <article>
            <BarChart3 />
            <strong>中间页分屏</strong>
            <p>时间、语言、表情、互动、情绪、媒体结构逐页拆开。</p>
          </article>
          <article>
            <MessageSquareQuote />
            <strong>原话支撑</strong>
            <p>结论旁边保留代表性片段，锐评不是凭空嘴硬。</p>
          </article>
        </div>
      </section>
    </main>
  );
}
