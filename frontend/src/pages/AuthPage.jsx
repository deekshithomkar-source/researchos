import { useState } from "react";
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
  const [mode, setMode] = useState("signup");
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

  function handleSubmit(event) {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();
    const storedAccounts = JSON.parse(localStorage.getItem("researchos_accounts") || "{}");
    const existingAccount = storedAccounts[normalizedEmail];

    if (!normalizedEmail || !password) {
      setError(isReset ? "Please enter your email and new password." : "Please enter your email and password.");
      setSuccess("");
      return;
    }

    if (isSignup) {
      if (!fullName.trim()) {
        setError("Please enter your full name.");
        setSuccess("");
        return;
      }

      if (existingAccount) {
        setError("User already exists. Please sign in.");
        setSuccess("");
        return;
      }

      if (password.length < 6) {
        setError("Password must be at least 6 characters.");
        setSuccess("");
        return;
      }

      storedAccounts[normalizedEmail] = {
        name: fullName.trim(),
        email: normalizedEmail,
        password,
      };

      localStorage.setItem("researchos_accounts", JSON.stringify(storedAccounts));
      localStorage.setItem("researchos_active_user", normalizedEmail);
      window.location.href = "/dashboard";
      return;
    }

    if (isReset) {
      if (!existingAccount) {
        setError("No account found with this email. Please create an account first.");
        setSuccess("");
        return;
      }

      if (password.length < 6) {
        setError("New password must be at least 6 characters.");
        setSuccess("");
        return;
      }

      storedAccounts[normalizedEmail] = {
        ...existingAccount,
        password,
      };

      localStorage.setItem("researchos_accounts", JSON.stringify(storedAccounts));
      setPassword("");
      setShowPassword(false);
      setMode("signin");
      setError("");
      setSuccess("Password changed successfully. Please sign in with your new password.");
      return;
    }

    if (!existingAccount || existingAccount.password !== password) {
      setError("Invalid email or password. Please check your details and try again.");
      setSuccess("");
      return;
    }

    localStorage.setItem("researchos_active_user", normalizedEmail);
    window.location.href = "/dashboard";
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

            <label>
              {isReset ? "New password" : "Password"}
              <span className="auth-password-field">
                <ShieldCheck size={18} />
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder={isReset ? "Enter new password" : "Enter your password"}
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
            </label>

            {error && <p className="auth-error" role="alert">{error}</p>}
            {success && <p className="auth-success" role="status">{success}</p>}

            {!isReset && (
              <div className="auth-options">
              <label>
                <input type="checkbox" defaultChecked />
                {isSignup ? "Agree to secure workspace access" : "Remember this device"}
              </label>
              {!isSignup && (
                <button className="auth-inline-action" type="button" onClick={() => handleModeChange("reset")}>
                  Forgot password?
                </button>
              )}
              </div>
            )}

            <button className="auth-submit" type="submit">
              {isReset ? "Change password" : isSignup ? "Create account" : "Sign in"}
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
