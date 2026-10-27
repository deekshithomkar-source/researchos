import { useEffect } from "react";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import MinimalLanding from "./components/MinimalLanding";

function App() {
  useEffect(() => {
    // Purge plaintext credentials left by the previous browser-only prototype.
    try {
      localStorage.removeItem('researchos_accounts');
      localStorage.removeItem('researchos_active_user');
    } catch { /* Storage may be disabled; authentication does not depend on it. */ }
  }, []);
  const path = window.location.pathname.replace(/\/+$/, "") || "/";

  useEffect(() => {
    const titles = {"/auth": "Sign in or join", "/dashboard": "Your research workspace"};
    const descriptions = {"/auth": "Sign in to ResearchOS or create your research workspace.", "/dashboard": "Explore your research, evidence, reports, and saved history in ResearchOS."};
    const description = descriptions[path] || "Explore ideas, analyze academic knowledge, and discover evidence-supported research opportunities in one focused workspace.";
    document.querySelector('meta[name="description"]')?.setAttribute('content', description);
    document.querySelector('meta[property="og:description"]')?.setAttribute('content', description);
    document.title = `${titles[path] || "Great research starts with curiosity"} | ResearchOS`;
    document.querySelector('meta[property="og:title"]')?.setAttribute('content', document.title);
    document.querySelector('meta[name="robots"]')?.setAttribute("content", path === "/" ? "index, follow" : "noindex, nofollow");
  }, [path]);

  if (path === "/auth") {
    return <AuthPage />;
  }

  if (path === "/dashboard") {
    return <Dashboard />;
  }

  return (
    <div>
      <MinimalLanding />
    </div>
  );
}

export default App;
