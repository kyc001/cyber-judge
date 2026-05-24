import { Route, Routes } from "react-router-dom";
import { AnalyzingPage } from "./pages/AnalyzingPage";
import { LandingPage } from "./pages/LandingPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ReportPage } from "./pages/ReportPage";
import { SharePage } from "./pages/SharePage";
import { UploadPage } from "./pages/UploadPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/analyzing" element={<AnalyzingPage />} />
      <Route path="/report/:id" element={<ReportPage />} />
      <Route path="/share/:slug" element={<SharePage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
