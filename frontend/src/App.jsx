import { useEffect } from "react";
import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import ResearchWorkflow from "./components/ResearchWorkflow";

function App() {
  useEffect(() => {
    // Purge plaintext credentials left by the previous browser-only prototype.
    try {
      localStorage.removeItem('researchos_accounts');
      localStorage.removeItem('researchos_active_user');
    } catch { /* Storage may be disabled; authentication does not depend on it. */ }
  }, []);
  const path = window.location.pathname.replace(/\/+$/, "") || "/";

  if (path === "/auth") {
    return <AuthPage />;
  }

  if (path === "/dashboard") {
    return <Dashboard />;
  }

  return (
    <div>
      <ResearchWorkflow />
    </div>
  );
}

export default App;
