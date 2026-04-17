"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { register, setToken } from "../../lib/api";
import { Activity, Eye, EyeOff, Lock, User, UserPlus } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await register(username, password, name);
      setToken(data.token, data.user);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Registration failed");
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
          <UserPlus color="white" size={32} />
        </div>

        <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8, letterSpacing: "-0.02em" }}>Get Started</h2>
        <p style={{ color: "#94a3b8", fontSize: 14, marginBottom: 32 }}>Create your personal productivity account</p>

        <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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

          {/* Full Name */}
          <div style={{ position: "relative" }}>
            <User size={18} color="#475569" style={{ position: "absolute", left: 16, top: 16 }} />
            <input
              type="text"
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
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

          {/* Username */}
          <div style={{ position: "relative" }}>
            <Activity size={18} color="#475569" style={{ position: "absolute", left: 16, top: 16 }} />
            <input
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
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
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
            {loading ? "Creating Account..." : "Sign Up"}
          </button>
        </form>

        <p style={{ marginTop: 24, fontSize: 13, color: "#94a3b8" }}>
          Already have an account?{" "}
          <span 
            onClick={() => router.push("/login")}
            style={{ color: "#818cf8", cursor: "pointer", fontWeight: 600 }}
          >
            Sign In
          </span>
        </p>

        <p style={{ marginTop: 32, color: "#475569", fontSize: 12 }}>
          Secured by YantrAI Enterprise
        </p>
      </div>
    </div>
  );
}
