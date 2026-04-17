"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, setToken } from "../../lib/api";
import { Activity, Eye, EyeOff, Lock, User } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await login(username, password);
      if (data.user.role === "super_admin") {
        router.push("/organizations");
      } else if (data.user.role === "admin" || data.user.role === "team_lead") {
        router.push("/dashboard");
      } else {
        router.push("/my-dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "radial-gradient(ellipse at top, rgba(79,70,229,0.12), #0a0a0c 60%)",
      padding: 20
    }}>
      <div className="glass" style={{
        width: "100%",
        maxWidth: 420,
        padding: "48px 36px",
        borderRadius: 24,
        textAlign: "center"
      }}>
        {/* Logo */}
        <div className="primary-gradient" style={{
          width: 64, height: 64, borderRadius: 20,
          margin: "0 auto 24px",
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 10px 40px rgba(79,70,229,0.4)"
        }}>
          <Activity color="white" size={32} />
        </div>

        <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8, letterSpacing: "-0.02em" }}>Welcome to ProMe</h2>
        <p style={{ color: "#94a3b8", fontSize: 14, marginBottom: 32 }}>Enterprise Productivity Portal</p>

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {error && (
            <div style={{
              padding: "12px 16px",
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.2)",
              borderRadius: 12,
              color: "#f87171",
              fontSize: 13
            }}>
              {error}
            </div>
          )}

          {/* Username */}
          <div style={{ position: "relative" }}>
            <User size={18} color="#475569" style={{ position: "absolute", left: 16, top: 16 }} />
            <input
              id="username"
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              style={{
                width: "100%",
                padding: "16px 16px 16px 48px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 14,
                color: "white",
                outline: "none",
                fontSize: 15,
                boxSizing: "border-box"
              }}
            />
          </div>

          {/* Password */}
          <div style={{ position: "relative" }}>
            <Lock size={18} color="#475569" style={{ position: "absolute", left: 16, top: 16 }} />
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={{
                width: "100%",
                padding: "16px 48px 16px 48px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 14,
                color: "white",
                outline: "none",
                fontSize: 15,
                boxSizing: "border-box"
              }}
            />
            <div onClick={() => setShowPassword(!showPassword)} style={{
              position: "absolute", right: 16, top: 16, cursor: "pointer", color: "#475569"
            }}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{
              padding: "16px",
              fontSize: 16,
              fontWeight: 700,
              borderRadius: 14,
              marginTop: 8,
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>

        <p style={{ marginTop: 24, fontSize: 13, color: "#94a3b8" }}>
          Don't have an account?{" "}
          <span 
            onClick={() => router.push("/register")}
            style={{ color: "#818cf8", cursor: "pointer", fontWeight: 600 }}
          >
            Register Now
          </span>
        </p>

        <p style={{ marginTop: 32, color: "#475569", fontSize: 12 }}>
          Secured by YantrAI Enterprise
        </p>
      </div>
    </div>
  );
}
