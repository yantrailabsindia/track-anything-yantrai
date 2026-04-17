"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchActivity, fetchScreenshots, getUser, clearAuth } from "../../lib/api";
import {
  Activity, Keyboard, MousePointer2, Monitor, Camera, Cpu, Filter
} from "lucide-react";
import React from "react";
import Sidebar from "../../components/Sidebar";

type FilterType = "all" | "input_summary" | "window_change" | "screenshot" | "telemetry";

export default function LogsPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [typeCounts, setTypeCounts] = useState<Record<string, number>>({});
  const [screenshots, setScreenshots] = useState<any[]>([]);
  const [selectedScreenshot, setSelectedScreenshot] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("all");
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    setUser(u);

    async function loadLogs() {
      try {
        const [resp, ss] = await Promise.all([
          fetchActivity({ limit: 200 }).catch(() => ({ logs: [], total: 0, counts: {} })),
          fetchScreenshots().catch(() => []),
        ]);
        setActivity(resp.logs || []);
        setTotalCount(resp.total || 0);
        setTypeCounts(resp.counts || {});
        setScreenshots(ss);
      } catch (e) {
        console.error("Failed to load activity logs:", e);
      } finally {
        setLoading(false);
      }
    }

    loadLogs();
    const interval = setInterval(loadLogs, 30000); // Refresh every 30s (was 5s)
    return () => clearInterval(interval);
  }, [router]);

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  // Build screenshot entries from the screenshots table so they appear
  // even when no matching activity_log "screenshot" event exists.
  const screenshotEntries = screenshots.map((s: any, idx: number) => ({
    id: `ss-${idx}`,
    timestamp: s.timestamp,
    event_type: "screenshot" as const,
    data: { filename: s.filename, url: s.url },
  }));

  const filtered = filter === "screenshot"
    ? screenshotEntries
    : filter === "all"
      ? activity
      : activity.filter(a => a.event_type === filter);

  const filterCounts = {
    all: totalCount,
    input_summary: typeCounts["input_summary"] || 0,
    window_change: typeCounts["window_change"] || 0,
    screenshot: screenshots.length,
    telemetry: typeCounts["telemetry"] || 0,
  };

  if (!mounted) return <div style={{ minHeight: "100vh", background: "var(--background)" }} />;

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <Activity size={48} color="var(--primary)" style={{ animation: "pulse 1.5s infinite" }} />
    </div>
  );

  // Helper to add cache-busting to screenshot URLs (uses filename hash as cache key)
  const getCachebustedUrl = (url: string) => {
    // Extract filename from URL (e.g., "/screenshots/device_2024-04-13_14-30-45.png")
    const filename = url.split('/').pop() || 'unknown';
    // Use filename hash as cache key (stable, changes only when screenshot changes)
    const cacheKey = filename.replace(/[^a-zA-Z0-9]/g, '');
    return `http://localhost:8765${url}?t=${cacheKey}`;
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* Shared Sidebar */}
      {user && (
        <Sidebar user={user} onLogout={handleLogout} activePage="/logs" />
      )}

      {/* Main Content */}
      <main style={{ flex: 1, padding: 32, overflowY: "auto", display: "flex", flexDirection: "column" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 4 }}>
              <span className="text-gradient">Activity Logs</span>
            </h1>
            <p style={{ color: "#64748b" }}>
              Real-time view of all captured events — {totalCount} events today
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#94a3b8", fontSize: 13 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981", animation: "pulse 2s infinite" }} />
            Auto-refreshing every 30s
          </div>
        </header>

        {/* Filter Bar */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
          <FilterButton label="All" count={filterCounts.all} icon={<Filter size={14} />}
            active={filter === "all"} onClick={() => setFilter("all")} />
          <FilterButton label="Input" count={filterCounts.input_summary} icon={<Keyboard size={14} />}
            active={filter === "input_summary"} onClick={() => setFilter("input_summary")} />
          <FilterButton label="Windows" count={filterCounts.window_change} icon={<Monitor size={14} />}
            active={filter === "window_change"} onClick={() => setFilter("window_change")} />
          <FilterButton label="Screenshots" count={filterCounts.screenshot} icon={<Camera size={14} />}
            active={filter === "screenshot"} onClick={() => setFilter("screenshot")} />
          <FilterButton label="System" count={filterCounts.telemetry} icon={<Cpu size={14} />}
            active={filter === "telemetry"} onClick={() => setFilter("telemetry")} />
        </div>

        {/* Log Stream */}
        <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{
            flex: 1, overflowY: "auto", background: "rgba(0,0,0,0.4)", borderRadius: 12,
            padding: 0, fontFamily: "'Consolas', 'Courier New', monospace", fontSize: 12,
          }}>
            {filtered.length > 0 ? (
              <div style={{ padding: 16 }}>
                {filtered.slice(0, 100).map((item, idx) => (
                  <LogEntry key={item.id || idx} item={item} screenshots={screenshots} onScreenshotClick={setSelectedScreenshot} getCachebustedUrl={getCachebustedUrl} />
                ))}
              </div>
            ) : (
              <div style={{ padding: 48, textAlign: "center", color: "#475569" }}>
                <Activity size={32} color="#334155" style={{ marginBottom: 12 }} />
                <p>No {filter === "all" ? "" : filter.replace("_", " ")} events logged yet.</p>
                <p style={{ fontSize: 11, marginTop: 4 }}>Start the ProMe desktop agent to begin capturing.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Screenshot Modal */}
      {selectedScreenshot && (
        <div onClick={() => setSelectedScreenshot(null)} style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center",
          justifyContent: "center", zIndex: 1000, cursor: "pointer",
        }}>
          <div onClick={e => e.stopPropagation()} style={{ position: "relative", maxWidth: "90vw", maxHeight: "90vh", cursor: "default" }}>
            <button onClick={() => setSelectedScreenshot(null)} style={{
              position: "absolute", top: -40, right: 0, background: "none",
              border: "none", color: "#fff", fontSize: 24, cursor: "pointer",
            }}>✕</button>
            <img
              src={getCachebustedUrl(selectedScreenshot)}
              alt="Screenshot"
              style={{ maxWidth: "100%", maxHeight: "85vh", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)" }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Components ──

const LogEntry = React.memo(({ item, screenshots, onScreenshotClick, getCachebustedUrl }: { item: any; screenshots: any[]; onScreenshotClick: (url: string) => void; getCachebustedUrl: (url: string) => string }) => {
  const timestamp = new Date(item.timestamp).toLocaleTimeString("en-US", { hour12: false });
  const eventType = item.event_type || "unknown";
  const data = item.data || {};

  let icon: React.ReactNode;
  let color: string;
  let detail: string;
  let thumbnailUrl: string | null = null;

  if (eventType === "input_summary") {
    icon = <Keyboard size={14} />;
    color = "#10b981";
    const keys = data.keystrokes || 0;
    const clicks = data.mouse_clicks || 0;
    const dist = Math.round(data.mouse_distance_px || 0);
    detail = `Keyboard: ${keys} keys  |  Mouse: ${clicks} clicks  |  ${dist}px moved`;
  } else if (eventType === "window_change") {
    icon = <Monitor size={14} />;
    color = "#a855f7";
    const win = (data.window_title || "Unknown").substring(0, 60);
    const dur = data.duration_seconds || 0;
    detail = `Window: ${win}  (${dur}s)`;
  } else if (eventType === "screenshot") {
    icon = <Camera size={14} />;
    color = "#f59e0b";
    detail = "Screenshot captured";
    // Use URL directly if available (from screenshots table entries)
    if (data.url) {
      thumbnailUrl = data.url;
    }
    // Match this event to a screenshot record by filename
    const filename = data.filename;
    if (!thumbnailUrl && filename) {
      const match = screenshots.find((s: any) => s.filename === filename);
      if (match) thumbnailUrl = match.url;
    }
    if (!thumbnailUrl && screenshots.length > 0) {
      // Fallback: find closest screenshot by timestamp
      const eventTime = new Date(item.timestamp).getTime();
      let closest = screenshots[0];
      let closestDiff = Math.abs(new Date(closest.timestamp).getTime() - eventTime);
      for (const s of screenshots) {
        const diff = Math.abs(new Date(s.timestamp).getTime() - eventTime);
        if (diff < closestDiff) { closest = s; closestDiff = diff; }
      }
      if (closestDiff < 30000) thumbnailUrl = closest.url; // within 30s
    }
  } else if (eventType === "telemetry") {
    icon = <Cpu size={14} />;
    color = "#06b6d4";
    detail = `System: CPU ${data.cpu_percent || 0}%  |  RAM ${data.ram_percent || 0}%  |  Battery ${data.battery_percent || "?"}%`;
  } else {
    icon = <Activity size={14} />;
    color = "#64748b";
    detail = `${eventType}: ${JSON.stringify(data).substring(0, 50)}`;
  }

  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10, padding: "6px 0",
      borderBottom: "1px solid rgba(255,255,255,0.03)", lineHeight: 1.5,
    }}>
      <span style={{ color: "#475569", flexShrink: 0, fontVariantNumeric: "tabular-nums" }}>
        [{timestamp}]
      </span>
      <span style={{ color, flexShrink: 0, marginTop: 2 }}>{icon}</span>
      <span style={{ color: "#cbd5e1", wordBreak: "break-word" }}>{detail}</span>
      {thumbnailUrl && (
        <img
          src={getCachebustedUrl(thumbnailUrl)}
          alt="Screenshot"
          onClick={() => onScreenshotClick(thumbnailUrl!)}
          style={{
            width: 80, height: 45, objectFit: "cover", borderRadius: 6,
            border: "1px solid rgba(255,255,255,0.1)", cursor: "pointer",
            flexShrink: 0, marginLeft: 8, transition: "transform 0.15s",
          }}
          onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.1)")}
          onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}
        />
      )}
    </div>
  );
});

const FilterButton = React.memo(({ label, count, icon, active, onClick }: {
  label: string; count: number; icon: React.ReactNode; active: boolean; onClick: () => void;
}) => (
  <button onClick={onClick} style={{
    display: "flex", alignItems: "center", gap: 6, padding: "8px 14px",
    borderRadius: 10, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600,
    background: active ? "var(--primary)" : "rgba(255,255,255,0.04)",
    color: active ? "white" : "#94a3b8",
    transition: "all 0.2s",
  }}>
    {icon}
    {label}
    <span style={{
      background: active ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.06)",
      padding: "2px 6px", borderRadius: 6, fontSize: 10, marginLeft: 2,
    }}>{count}</span>
  </button>
));

