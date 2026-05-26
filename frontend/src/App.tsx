import { Route, Routes } from "react-router-dom";
import { ThemeProvider } from "./theme/ThemeSystem";
import { AnalyzingPage } from "./pages/AnalyzingPage";
import { InsightsPage } from "./pages/InsightsPage";
import { LandingPage } from "./pages/LandingPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ReportPage } from "./pages/ReportPage";
import { SharePage } from "./pages/SharePage";
import { UploadPage } from "./pages/UploadPage";

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/report/:id" element={<ReportPage />} />
        <Route path="/insights/:id" element={<InsightsPage />} />
        <Route path="/insights/:id/:view" element={<InsightsPage />} />
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/analyzing" element={<AnalyzingPage />} />
        <Route path="/share/:slug" element={<SharePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ThemeProvider>
  );
}
