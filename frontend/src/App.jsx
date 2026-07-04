import AuthPage from "./pages/AuthPage";
import Dashboard from "./pages/Dashboard";
import ResearchWorkflow from "./components/ResearchWorkflow";

function App() {
  const path = window.location.pathname;

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
