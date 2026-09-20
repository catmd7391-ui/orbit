// src/LoginScreen.jsx
import React, { useState } from "react";
import { supabase } from "./supabaseClient";

export default function LoginScreen({ onLogin }) {
  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;

        // If email confirmation is required, `data.user` exists but session is null
        if (!data.session) {
          setError(
            "Account created. Check your email to confirm, then sign in."
          );
          setMode("signin");
          setLoading(false);
          return;
        }
        onLogin(data.session);
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
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">O</div>
        <h1 className="login-title">
          {mode === "signup" ? "Create your account" : "Sign in to Orbit"}
        </h1>
        <p className="login-subtitle">
          {mode === "signup"
            ? "Start getting real work done."
            : "Your AI workspace for daily work."}
        </p>

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

          <input
            type="password"
            placeholder="Password (min 6 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="login-input"
          />

          {error && <div className="login-error">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="login-button"
          >
            {loading
              ? "Please wait…"
              : mode === "signup"
              ? "Create account"
              : "Sign in"}
          </button>
        </form>

        <div className="login-switch">
          {mode === "signin" ? (
            <>
              Don't have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("signup");
                  setError("");
                }}
                className="login-switch-btn"
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("signin");
                  setError("");
                }}
                className="login-switch-btn"
              >
                Sign in
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}