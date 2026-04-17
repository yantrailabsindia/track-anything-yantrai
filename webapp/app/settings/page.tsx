"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, clearAuth } from "../../lib/api";
import {
  Activity, ArrowLeft, Settings as SettingsIcon, Clock, Wifi, Shield, Save
} from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  // Settings state
  const [screenshotInterval, setScreenshotInterval] = useState("300");
  const [inputInterval, setInputInterval] = useState("60");
  const [serverUrl, setServerUrl] = useState("");
  const [autoStart, setAutoStart] = useState(true);

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    // Remove strict admin redirect to allow employees access to personal settings
    // if (u.role !== "admin" && u.role !== "super_admin") { router.push("/dashboard"); return; }
    setUser(u);
    setLoading(false);
  }, [router]);

  function handleSave() {
    // Settings are stored locally — in production these would be stored on the server
    localStorage.setItem("prome_settings", JSON.stringify({
      screenshotInterval, inputInterval, serverUrl, autoStart
    }));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <Activity size={48} color="var(--primary)" />
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", padding: 32, maxWidth: 700, margin: "0 auto" }}>
      {/* Header */}
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 48 }}>
        <Link href="/dashboard">
          <div className="glass" style={{ padding: 12, borderRadius: 12, cursor: "pointer", display: "flex" }}>
            <ArrowLeft size={20} color="#94a3b8" />
          </div>
        </Link>
        <div>
          <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.04em" }}>
            <span className="text-gradient">Settings</span>
          </h1>
          <p style={{ color: "#64748b", fontSize: 13 }}>Configure {user?.org_name || "your organization"}&apos;s ProMe settings</p>
        </div>
      </header>

      {saved && (
        <div style={{
          padding: "12px 20px", background: "rgba(16,185,129,0.1)",
          border: "1px solid rgba(16,185,129,0.2)", borderRadius: 12,
          color: "#10b981", fontSize: 14, fontWeight: 600, marginBottom: 24,
        }}>
          ✅ Settings saved successfully
        </div>
      )}

      {/* Capture Settings (Admin Only) */}
      {(user?.role === "admin" || user?.role === "super_admin") && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
            <Camera size={20} color="var(--primary)" /> Capture Settings
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div>
              <label style={labelStyle}>Screenshot Interval (seconds)</label>
              <p style={descStyle}>How often the desktop agent captures a screenshot of the screen.</p>
              <input type="number" value={screenshotInterval} onChange={e => setScreenshotInterval(e.target.value)} style={inputStyle} min="30" step="30" />
            </div>
            <div>
              <label style={labelStyle}>Input Summary Interval (seconds)</label>
              <p style={descStyle}>How often keystroke and click counts are logged.</p>
              <input type="number" value={inputInterval} onChange={e => setInputInterval(e.target.value)} style={inputStyle} min="10" step="10" />
            </div>
          </div>
        </div>
      )}

      {/* Server Settings (Admin Only) */}
      {(user?.role === "admin" || user?.role === "super_admin") && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
            <Wifi size={20} color="#10b981" /> Server Settings
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div>
              <label style={labelStyle}>API Server URL</label>
              <p style={descStyle}>The URL that the desktop agents connect to.</p>
              <input type="url" value={serverUrl} onChange={e => setServerUrl(e.target.value)} style={inputStyle} />
            </div>
          </div>
        </div>
      )}

      {/* Agent Settings */}
      <div className="card" style={{ marginBottom: 32 }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={20} color="#f59e0b" /> Agent Behavior
        </h3>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <label style={labelStyle}>Auto-Start on Login</label>
            <p style={descStyle}>Automatically start the agent when the user logs in to Windows.</p>
          </div>
          <div
            onClick={() => setAutoStart(!autoStart)}
            style={{
              width: 52, height: 28, borderRadius: 14, cursor: "pointer", position: "relative",
              background: autoStart ? "var(--primary)" : "rgba(255,255,255,0.1)",
              transition: "background 0.2s",
            }}
          >
            <div style={{
              width: 22, height: 22, borderRadius: 11, background: "white",
              position: "absolute", top: 3,
              left: autoStart ? 27 : 3,
              transition: "left 0.2s",
              boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
            }} />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button className="btn-primary" onClick={handleSave} style={{
        width: "100%", padding: "16px", fontSize: 16, fontWeight: 700, borderRadius: 14,
        display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
        boxShadow: "0 10px 30px rgba(79,70,229,0.3)",
      }}>
        <Save size={20} /> Save Settings
      </button>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block", fontSize: 14, fontWeight: 700, marginBottom: 4,
};

const descStyle: React.CSSProperties = {
  color: "#64748b", fontSize: 12, marginBottom: 10,
};

const inputStyle: React.CSSProperties = {
  padding: "12px 16px", background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12,
  color: "#f0f0f3", fontSize: 15, outline: "none", width: "100%",
  boxSizing: "border-box",
};
