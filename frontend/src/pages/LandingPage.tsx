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
          <p className="eyebrow">AI 聊天体检 / 关系锐评</p>
          <h1>把聊天记录交给 AI，让它自己找人设、关系和名场面。</h1>
          <p>
            不只做词云和排行榜。赛博判官会先读聊天结构，再让 AI 自主总结
            谁在控场、谁在接话、哪些句子值得截图、好友关系到底是什么温度。
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/upload">
              <Upload size={18} />
              <span>上传聊天记录</span>
            </Link>
            <Link className="btn btn-secondary" to="/upload?type=relationship">
              <HeartHandshake size={18} />
              <span>测好友关系</span>
            </Link>
          </div>
          <div className="hero-proof-row" aria-label="核心分析能力">
            <span><Brain size={16} /> AI 先讲重点</span>
            <span><MessageCircleMore size={16} /> 群聊锐评</span>
            <span><Sparkles size={16} /> 名场面挖掘</span>
          </div>
        </div>

        <div className="hero-preview" aria-label="报告预览">
          <div className="preview-phone">
            <div className="preview-screen">
              <p className="preview-chip">AI 先说重点</p>
              <h2>这段聊天最值得看的 4 件事</h2>
              <div className="preview-stack">
                <span>夜猫子联盟：23 点后仍在稳定上分</span>
                <span>关系温度：高频接话比单向输出更明显</span>
                <span>名场面：真实金句优先，不硬编段子</span>
              </div>
              <blockquote>数据不会说谎，只会锐评。</blockquote>
            </div>
          </div>
        </div>
      </section>

      <section className="feature-band feature-band-product">
        <article>
          <Brain />
          <h2>AI 自主分析</h2>
          <p>先归纳异常信号，再写出像人读过聊天一样的锐评。</p>
        </article>
        <article>
          <MessageCircleMore />
          <h2>群聊体检</h2>
          <p>龙王榜、人设勋章、控场角色、共同暗号和互动图谱。</p>
        </article>
        <article>
          <HeartHandshake />
          <h2>好友关系</h2>
          <p>主动程度、回复节奏、共同语言、关系里程碑和温度变化。</p>
        </article>
        <article>
          <BarChart3 />
          <h2>聊天分镜</h2>
          <p>时间、语言、表情、情绪、媒体结构和预测分屏查看。</p>
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
