// src/LoginScreen.jsx
import React, { useState } from "react";
import { supabase } from "./supabaseClient";
import loginHero from "./assets/login-hero.svg";

export default function LoginScreen({ onLogin }) {
  const [mode, setMode] = useState("signin"); // "signin" | "signup" | "forgot"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleGoogleLogin = async () => {
    setError("");
    setLoading(true);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: window.location.origin },
      });
      if (error) throw error;
    } catch (err) {
      setError(err.message || "Google sign-in failed");
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        if (!data.session) {
          setSuccess(
            "Account created. Check your email to confirm, then sign in."
          );
          setMode("signin");
          setLoading(false);
          return;
        }
        onLogin(data.session);
      } else if (mode === "forgot") {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        });
        if (error) throw error;
        setSuccess("Reset link sent! Check your email.");
        setLoading(false);
        return;
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        onLogin(data.session);
      }
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-split-page">
      {/* LEFT: Illustration panel */}
      <div className="login-hero">
        <div className="hero-brand">
          <div className="brand-mark">O</div>
          <span>Orbit</span>
        </div>

        <div className="hero-illustration">
          <img src={loginHero} alt="Orbit" className="hero-svg" />
        </div>

        <div className="hero-text">
          <h2>Work together, faster</h2>
        </div>
      </div>

      {/* RIGHT: Form panel */}
      <div className="login-form-panel">
        <div className="login-form-box">
          <h1 className="login-title">
            {mode === "signup"
              ? "Create your account"
              : mode === "forgot"
              ? "Reset your password"
              : "Sign in to Orbit"}
          </h1>
          <p className="login-subtitle">
            {mode === "signup"
              ? "Start getting real work done."
              : mode === "forgot"
              ? "We'll send you a reset link."
              : "Welcome back. Let's get to work."}
          </p>

          {/* Google + divider (only on signin/signup) */}
          {mode !== "forgot" && (
            <>
              <button
                type="button"
                className="google-button"
                onClick={handleGoogleLogin}
                disabled={loading}
              >
                <svg width="18" height="18" viewBox="0 0 18 18">
                  <path fill="#4285F4" d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
                  <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
                  <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
                  <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
                </svg>
                <span>Continue with Google</span>
              </button>

              <div className="login-divider">
                <span>or</span>
              </div>
            </>
          )}

          <form onSubmit={handleSubmit} className="login-form">
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              className="login-input"
            />

            {mode !== "forgot" && (
              <div className="password-wrapper">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Password (min 6 chars)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="login-input password-input"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "🙈" : "👁"}
                </button>
              </div>
            )}

            {error && <div className="login-error">{error}</div>}
            {success && <div className="login-success">{success}</div>}

            <button type="submit" disabled={loading} className="login-button">
              {loading
                ? "Please wait…"
                : mode === "signup"
                ? "Create account"
                : mode === "forgot"
                ? "Send reset link"
                : "Sign in"}
            </button>
          </form>

          {mode === "signin" && (
            <button
              type="button"
              className="login-link"
              onClick={() => {
                setMode("forgot");
                setError("");
                setSuccess("");
              }}
            >
              Forgot password?
            </button>
          )}

          <div className="login-switch">
            {mode === "signin" && (
              <>
                Don't have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    setError("");
                    setSuccess("");
                  }}
                  className="login-switch-btn"
                >
                  Sign up
                </button>
              </>
            )}
            {mode === "signup" && (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setError("");
                    setSuccess("");
                  }}
                  className="login-switch-btn"
                >
                  Sign in
                </button>
              </>
            )}
            {mode === "forgot" && (
              <button
                type="button"
                onClick={() => {
                  setMode("signin");
                  setError("");
                  setSuccess("");
                }}
                className="login-switch-btn"
              >
                ← Back to sign in
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}