import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";

const authBenefits = [
  "Save research history securely",
  "Export reports across sessions",
  "Access quality-scored source trails",
];

export default function AuthPage() {
  const [mode, setMode] = useState("signup");
  const isSignup = mode === "signup";

  return (
    <main className="auth-page">
      <section className="auth-shell">
        <aside className="auth-brand-panel">
          <a className="auth-back-link" href="/">
            <ArrowLeft size={17} />
            Back to workflow
          </a>

          <div className="auth-brand-content">
            <span className="auth-kicker">
              <Sparkles size={16} />
              Secure access
            </span>
            <h1>Authorize your research workspace</h1>
            <p>
              Sign in to start research runs, preserve your findings, and manage
              generated reports from one organized workspace.
            </p>
          </div>

          <div className="auth-benefits">
            {authBenefits.map((benefit) => (
              <div key={benefit}>
                <CheckCircle2 size={18} />
                {benefit}
              </div>
            ))}
          </div>
        </aside>

        <section className="auth-form-panel" aria-label="Authorization form">
          <div className="auth-form-heading">
            <div className="auth-lock">
              <LockKeyhole size={24} />
            </div>
            <div>
              <span>Account authorization</span>
              <h2>{isSignup ? "Create your account" : "Welcome back"}</h2>
            </div>
          </div>

          <div className="auth-mode-tabs" aria-label="Authorization mode">
            <button
              className={isSignup ? "active" : ""}
              type="button"
              onClick={() => setMode("signup")}
            >
              Sign up
            </button>
            <button
              className={!isSignup ? "active" : ""}
              type="button"
              onClick={() => setMode("signin")}
            >
              Sign in
            </button>
          </div>

          <form className="auth-form">
            {isSignup && (
              <label>
                Full name
                <span>
                  <User size={18} />
                  <input type="text" placeholder="Enter your name" />
                </span>
              </label>
            )}

            <label>
              Email address
              <span>
                <Mail size={18} />
                <input type="email" placeholder="name@example.com" />
              </span>
            </label>

            <label>
              Password
              <span>
                <ShieldCheck size={18} />
                <input type="password" placeholder="Enter your password" />
              </span>
            </label>

            <div className="auth-options">
              <label>
                <input type="checkbox" defaultChecked />
                {isSignup ? "Agree to secure workspace access" : "Remember this device"}
              </label>
              {!isSignup && <a href="/auth">Forgot password?</a>}
            </div>

            <a className="auth-submit" href="/dashboard">
              {isSignup ? "Create account" : "Sign in"}
              <ArrowRight size={18} />
            </a>
          </form>

          <div className="auth-switch-note">
            {isSignup ? (
              <>
                Already have an account?
                <button type="button" onClick={() => setMode("signin")}>
                  Sign in
                </button>
              </>
            ) : (
              <>
                New to the platform?
                <button type="button" onClick={() => setMode("signup")}>
                  Create an account
                </button>
              </>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
