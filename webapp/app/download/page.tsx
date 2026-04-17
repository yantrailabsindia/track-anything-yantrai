"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, downloadWindowsAgent, downloadCCTVAgent, checkDownloadAvailable } from "../../lib/api";
import {
  Activity, Download, ArrowLeft, Monitor, Camera, Zap, CheckCircle2, Copy
} from "lucide-react";
import Link from "next/link";

export default function DownloadPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [available, setAvailable] = useState({ windows_agent: false, cctv_agent: false });
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [serverUrl, setServerUrl] = useState("http://localhost:8765");

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    setUser(u);

    // Set server URL to current origin
    if (typeof window !== "undefined") {
      setServerUrl(window.location.origin);
    }

    checkDownloadAvailable()
      .then(avail => setAvailable(avail))
      .catch(() => setAvailable({ windows_agent: false, cctv_agent: false }))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleDownload(agentType: "windows" | "cctv") {
    setDownloading(agentType);
    try {
      if (agentType === "windows") {
        await downloadWindowsAgent();
      } else {
        await downloadCCTVAgent();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setDownloading(null);
    }
  }

  function copyServerUrl() {
    navigator.clipboard.writeText(serverUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <Activity size={48} color="var(--primary)" />
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", padding: 32, maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 48 }}>
        <Link href={user?.role === "admin" ? "/dashboard" : "/my-dashboard"}>
          <div className="glass" style={{ padding: 12, borderRadius: 12, cursor: "pointer", display: "flex" }}>
            <ArrowLeft size={20} color="#94a3b8" />
          </div>
        </Link>
        <div>
          <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.04em" }}>
            <span className="text-gradient">App Store</span>
          </h1>
          <p style={{ color: "#64748b", fontSize: 13 }}>Download and manage ProMe agents for your team</p>
        </div>
      </header>

      {/* Apps Grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
        gap: 24,
        marginBottom: 40,
      }}>
        {/* Windows Agent Card */}
        <div className="card" style={{
          padding: 32,
          display: "flex",
          flexDirection: "column",
          gap: 20,
          borderLeft: "4px solid var(--primary)",
        }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
            <div>
              <Monitor size={40} color="var(--primary)" style={{ marginBottom: 12 }} />
              <h2 style={{ fontSize: 22, fontWeight: 900, marginBottom: 4 }}>Windows Agent</h2>
              <p style={{ color: "#64748b", fontSize: 13 }}>Productivity & Activity Tracking</p>
            </div>
          </div>

          <p style={{ color: "#cbd5e1", fontSize: 14, lineHeight: 1.6 }}>
            Silent desktop agent that captures productivity metrics, screenshots, and activity data in real-time.
            Runs from boot in the system tray without disrupting workflow.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13, color: "#94a3b8" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle2 size={16} color="#10b981" />
              <span>Real-time activity monitoring</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle2 size={16} color="#10b981" />
              <span>Automatic startup on boot</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle2 size={16} color="#10b981" />
              <span>System tray integration</span>
            </div>
          </div>

          <button
            className="btn-primary"
            onClick={() => handleDownload("windows")}
            disabled={!available.windows_agent || downloading === "windows"}
            style={{
              padding: "12px 24px",
              fontSize: 14,
              fontWeight: 700,
              background: "var(--primary)",
              color: "white",
              borderRadius: 10,
              border: "none",
              cursor: available.windows_agent ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              opacity: available.windows_agent ? 1 : 0.5,
            }}
          >
            <Download size={16} />
            {downloading === "windows" ? "Downloading..." : available.windows_agent ? "Download ProMe.exe" : "Not Available"}
          </button>
        </div>

        {/* CCTV Agent Card */}
        <div className="card" style={{
          padding: 32,
          display: "flex",
          flexDirection: "column",
          gap: 20,
          borderLeft: "4px solid #f59e0b",
        }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
            <div>
              <Camera size={40} color="#f59e0b" style={{ marginBottom: 12 }} />
              <h2 style={{ fontSize: 22, fontWeight: 900, marginBottom: 4 }}>CCTV Agent</h2>
              <p style={{ color: "#64748b", fontSize: 13 }}>Security Camera Snapshot Capture</p>
            </div>
          </div>

          <p style={{ color: "#cbd5e1", fontSize: 14, lineHeight: 1.6 }}>
            Captures periodic snapshots from CCTV cameras via ONVIF, stores them organized by location/camera/hour,
            and uploads to cloud storage. Includes offline queue resilience and manual upload controls.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13, color: "#94a3b8" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle2 size={16} color="#10b981" />
              <span>ONVIF camera discovery & config</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle2 size={16} color="#10b981" />
              <span>Hourly batch uploads to cloud</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle2 size={16} color="#10b981" />
              <span>Offline queue persistence</span>
            </div>
          </div>

          <button
            className="btn-primary"
            onClick={() => handleDownload("cctv")}
            disabled={!available.cctv_agent || downloading === "cctv"}
            style={{
              padding: "12px 24px",
              fontSize: 14,
              fontWeight: 700,
              background: "#f59e0b",
              color: "white",
              borderRadius: 10,
              border: "none",
              cursor: available.cctv_agent ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              opacity: available.cctv_agent ? 1 : 0.5,
            }}
          >
            <Download size={16} />
            {downloading === "cctv" ? "Downloading..." : available.cctv_agent ? "Download CCTVAgent.exe" : "Not Available"}
          </button>
        </div>
      </div>

      {/* Server Configuration */}
      <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
            <Zap size={18} color="#fbbf24" /> Server URL Configuration
          </h3>
          <p style={{ color: "#64748b", fontSize: 13 }}>Configure this URL in agents when prompted during first run.</p>
          <code style={{
            display: "inline-block", marginTop: 8, padding: "8px 16px",
            background: "rgba(255,255,255,0.04)", borderRadius: 8,
            fontSize: 14, fontFamily: "monospace", color: "#fbbf24",
          }}>
            {serverUrl}
          </code>
        </div>
        <button
          onClick={copyServerUrl}
          className="glass"
          style={{ padding: "10px 16px", borderRadius: 10, cursor: "pointer", border: "none", color: copied ? "#10b981" : "#94a3b8", display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600 }}
        >
          {copied ? <><CheckCircle2 size={16} /> Copied!</> : <><Copy size={16} /> Copy</>}
        </button>
      </div>

      {/* Quick Setup Instructions */}
      <div className="card">
        <h3 style={{ fontSize: 20, fontWeight: 800, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
          <Zap size={20} color="var(--primary)" /> Getting Started
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 20 }}>
          {[
            { title: "Windows Agent", icon: Monitor, steps: ["Download ProMe.exe", "Run on employee laptop", "Agent auto-starts on boot", "Data flows to dashboard"] },
            { title: "CCTV Agent", icon: Camera, steps: ["Download CCTVAgent.exe", "Run on monitoring PC", "Scan and configure cameras", "Snapshots upload to cloud"] },
          ].map(({ title, icon: Icon, steps }) => (
            <div key={title}>
              <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <Icon size={16} />
                {title}
              </h4>
              <ol style={{ display: "flex", flexDirection: "column", gap: 8, paddingLeft: 20 }}>
                {steps.map((step, idx) => (
                  <li key={idx} style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.5 }}>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
