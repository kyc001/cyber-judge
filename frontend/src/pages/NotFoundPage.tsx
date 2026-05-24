import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="page state-page">
      <h1>页面不存在</h1>
      <p>这个链接没有匹配到当前前端路由。</p>
      <Link className="btn btn-primary" to="/">
        回到首页
      </Link>
    </main>
  );
}
