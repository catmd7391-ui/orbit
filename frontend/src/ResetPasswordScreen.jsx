import React, { useState, useEffect } from "react";
import { supabase } from "./supabaseClient";

export default function ResetPasswordScreen({ onDone }) {
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [validSession, setValidSession] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setValidSession(!!data.session));
  }, []);

  const handleReset = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      setSuccess(true);
      setTimeout(() => onDone(), 2000);
    } catch (err) {
      setError(err.message || "Could not reset password");
    } finally {
      setLoading(false);
    }
  };

  if (!validSession) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-logo">O</div>
          <h1 className="login-title">Invalid or expired link</h1>
          <p className="login-subtitle">Please request a new password reset.</p>
          <button className="login-button" onClick={onDone}>Back to sign in</button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">O</div>
        <h1 className="login-title">Set a new password</h1>
        <p className="login-subtitle">Enter your new password below.</p>
        {success ? (
          <div className="login-success">Password updated! Redirecting…</div>
        ) : (
          <form onSubmit={handleReset} className="login-form">
            <div className="password-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="New password (min 6 chars)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="login-input password-input"
              />
              <button type="button" className="password-toggle" onClick={() => setShowPassword((v) => !v)}>
                {showPassword ? "🙈" : "👁"}
              </button>
            </div>
            {error && <div className="login-error">{error}</div>}
            <button type="submit" disabled={loading} className="login-button">
              {loading ? "Please wait…" : "Update password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}