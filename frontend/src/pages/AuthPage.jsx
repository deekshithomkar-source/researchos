import { useState } from "react";
import { signupUser, signinUser, apiErrorMessage } from "../services/api.js";
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  User,
} from "lucide-react";

export default function AuthPage() {
  const [submitting, setSubmitting] = useState(false);
  const [mode, setMode] = useState(() => new URLSearchParams(window.location.search).get("mode") === "signin" ? "signin" : "signup");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const isSignup = mode === "signup";
  const isReset = mode === "reset";

  function handleModeChange(nextMode) {
    setMode(nextMode);
    setError("");
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setError('');
    setSuccess('');
    if (isReset) {
      setError('Password recovery is not available yet. A verified email recovery flow is required.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = { email: email.trim().toLowerCase(), password };
      if (isSignup) await signupUser({ ...payload, name: fullName.trim() });
      else await signinUser(payload);
      setPassword('');
      window.location.assign('/dashboard');
    } catch (error) {
      setError(apiErrorMessage(error, 'Unable to reach the server. Please try again.'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-shell">
        <section className="auth-form-panel" aria-label="Authorization form">
          <a className="auth-back-link" href="/">
            <ArrowLeft size={17} />
            Back to workflow
          </a>

          <div className="auth-form-heading">
            <div className="auth-lock">
              <LockKeyhole size={24} />
            </div>
            <div>
              <span>Account authorization</span>
              <h2>{isReset ? "Reset password" : isSignup ? "Create your account" : "Welcome back"}</h2>
            </div>
          </div>

          <div className="auth-mode-tabs" aria-label="Authorization mode">
            <button
              className={isSignup ? "active" : ""}
              type="button"
              onClick={() => handleModeChange("signup")}
            >
              Sign up
            </button>
            <button
              className={!isSignup ? "active" : ""}
              type="button"
              onClick={() => handleModeChange("signin")}
            >
              Sign in
            </button>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            {isSignup && !isReset && (
              <label>
                Full name
                <span>
                  <User size={18} />
                  <input
                    type="text"
                    placeholder="Enter your name"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    required={isSignup}
                    minLength={2}
                    maxLength={120}
                  />
                </span>
              </label>
            )}

            <label>
              Email address
              <span>
                <Mail size={18} />
                <input
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </span>
            </label>

            {!isReset && <label>
              Password
              <span className="auth-password-field">
                <ShieldCheck size={18} />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder={isSignup ? "At least 12 characters" : "Enter your password"}
                  minLength={isSignup ? 12 : 1}
                  maxLength={128}
                  autoComplete={isSignup ? "new-password" : "current-password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <button
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="auth-password-toggle"
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>}

            {isReset && <p className="auth-error" role="status">Password recovery is not available yet. A verified email recovery flow is required.</p>}
            {error && <p className="auth-error" role="alert">{error}</p>}
            {success && <p className="auth-success" role="status">{success}</p>}

            {!isReset && (
              <div className="auth-options">
              <label>
                <input type="checkbox" defaultChecked disabled />
                {isSignup ? "Secure workspace access" : "Session expires automatically"}
              </label>
              {!isSignup && (
                <button className="auth-inline-action" type="button" onClick={() => handleModeChange("reset")}>
                  Forgot password?
                </button>
              )}
              </div>
            )}

            <button className="auth-submit" type="submit" disabled={submitting || isReset}>
              {submitting ? "Please wait..." : isReset ? "Recovery unavailable" : isSignup ? "Create account" : "Sign in"}
              <ArrowRight size={18} />
            </button>
          </form>

          <div className="auth-switch-note">
            {isReset ? (
              <>
                Remember your password?
                <button type="button" onClick={() => handleModeChange("signin")}>
                  Sign in
                </button>
              </>
            ) : isSignup ? (
              <>
                Already have an account?
                <button type="button" onClick={() => handleModeChange("signin")}>
                  Sign in
                </button>
              </>
            ) : (
              <>
                New to the platform?
                <button type="button" onClick={() => handleModeChange("signup")}>
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
