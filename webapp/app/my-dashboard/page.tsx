"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { fetchStats, fetchActivity, getUser, clearAuth, fetchMyInvites, acceptInvite, declineInvite } from "../../lib/api";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Activity, Clock, MousePointer2, Keyboard, Monitor,
  BarChart3, TrendingUp, Shield
} from "lucide-react";
import Sidebar from "../../components/Sidebar";
import { CCTVDashboard } from "../../components/CCTVDashboard";

export default function MyDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSharing, setIsSharing] = useState(true);
  const [pendingInvites, setPendingInvites] = useState<any[]>([]);
  const [showInviteHub, setShowInviteHub] = useState(false);
  const [timeRange, setTimeRange] = useState<"1h" | "24h" | "7d" | "custom">("24h");
  const [chartMetric, setChartMetric] = useState<"activeTime" | "keystrokes" | "clicks" | "sessions">("activeTime");
  const [weekActivity, setWeekActivity] = useState<any[] | null>(null);
  const [loadingWeek, setLoadingWeek] = useState(false);
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [showCustomRange, setShowCustomRange] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    setUser(u);

    async function loadData() {
      try {
        const [s, aResp, invites] = await Promise.all([
          fetchStats(), fetchActivity({ limit: 500 }),
          fetchMyInvites().catch(() => [])
        ]);
        setStats(s);
        setActivity(aResp.logs || []);
        setPendingInvites(invites);
        if (invites.length > 0) setShowInviteHub(true);
      } catch (error) {
        console.error("Error loading data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [router]);

  // Load 7-day data when that range is selected
  useEffect(() => {
    if (timeRange !== "7d" || weekActivity !== null) return;
    setLoadingWeek(true);
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 6);
    fetchActivity({
      startDate: start.toISOString().slice(0, 10),
      endDate: end.toISOString().slice(0, 10),
      limit: 5000,
    })
      .then((resp: any) => setWeekActivity(resp.logs || []))
      .catch(() => setWeekActivity([]))
      .finally(() => setLoadingWeek(false));
  }, [timeRange, weekActivity]);

  async function handleAcceptInvite(id: string) {
    try {
      await acceptInvite(id);
      window.location.reload();
    } catch (e: any) { alert(e.message); }
  }

  async function handleDeclineInvite(id: string) {
    try {
      await declineInvite(id);
      setPendingInvites(prev => prev.filter(i => i.id !== id));
      if (pendingInvites.length <= 1) setShowInviteHub(false);
    } catch (e: any) { alert(e.message); }
  }

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  // Build activity data based on time range
  const chartData = useMemo(() => {
    const now = new Date();
    let startTime = new Date();
    let endTime = new Date(now); // always default to now
    let interval = 60; // minutes
    let labels: string[] = [];

    // Pick the data source: 7d uses weekActivity, everything else uses today's activity
    const dataSource = timeRange === "7d" ? (weekActivity || []) : activity;

    if (timeRange === "1h") {
      // Rolling last 60 minutes
      startTime = new Date(now.getTime() - 60 * 60 * 1000);
      interval = 5;
      labels = Array.from({ length: 12 }, (_, i) => {
        const d = new Date(startTime.getTime() + i * 5 * 60 * 1000);
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      });
    } else if (timeRange === "24h") {
      startTime = new Date(now);
      startTime.setHours(0, 0, 0, 0);
      interval = 60;
      labels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
    } else if (timeRange === "7d") {
      startTime = new Date(now);
      startTime.setDate(now.getDate() - 6);
      startTime.setHours(0, 0, 0, 0);
      endTime = new Date(now);
      endTime.setHours(23, 59, 59, 999);
      interval = 1440;
      labels = Array.from({ length: 7 }, (_, i) => {
        const d = new Date(startTime);
        d.setDate(d.getDate() + i);
        return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
      });
    } else if (timeRange === "custom" && customStartDate && customEndDate) {
      startTime = new Date(customStartDate);
      endTime = new Date(customEndDate);
      if (startTime >= endTime) return [];

      const diffMs = endTime.getTime() - startTime.getTime();
      const diffDays = diffMs / (1000 * 60 * 60 * 24);

      if (diffDays <= 1) {
        interval = 5;
      } else if (diffDays <= 30) {
        interval = 60;
      } else {
        interval = 1440;
      }
      const bucketCount = Math.ceil(diffMs / (interval * 60 * 1000));
      labels = Array.from({ length: bucketCount }, (_, i) => {
        const d = new Date(startTime.getTime() + i * interval * 60 * 1000);
        return interval <= 5
          ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          : interval <= 60
          ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          : d.toLocaleDateString([], { month: "short", day: "numeric" });
      });
    } else if (timeRange === "custom") {
      return [];
    }

    const buckets = labels.map(() => ({
      activeTime: 0, keystrokes: 0, clicks: 0, sessions: 0,
    }));

    for (const entry of dataSource) {
      if (!entry.timestamp) continue;
      try {
        const entryTime = new Date(entry.timestamp);
        if (entryTime < startTime || entryTime > endTime) continue;

        const minutesSinceStart = (entryTime.getTime() - startTime.getTime()) / 60000;
        const bucketIndex = Math.floor(minutesSinceStart / interval);

        if (bucketIndex >= 0 && bucketIndex < buckets.length) {
          if (entry.event_type === "window_change") {
            buckets[bucketIndex].activeTime += Math.round((entry.data?.duration_seconds || 0) / 60);
            buckets[bucketIndex].sessions += 1;
          }
          if (entry.event_type === "input_summary") {
            buckets[bucketIndex].keystrokes += entry.data?.keystrokes || 0;
            buckets[bucketIndex].clicks += entry.data?.mouse_clicks || 0;
          }
        }
      } catch { /* skip */ }
    }

    return labels.map((label, i) => ({
      time: label,
      activeTime: buckets[i].activeTime,
      keystrokes: buckets[i].keystrokes,
      clicks: buckets[i].clicks,
      sessions: buckets[i].sessions,
    }));
  }, [activity, weekActivity, timeRange, customStartDate, customEndDate]);

  // Count window sessions
  const windowSessions = useMemo(() => {
    return activity.filter(a => a.event_type === "window_change").length;
  }, [activity]);

  // Hydration safety
  if (!mounted) return <div style={{ minHeight: "100vh", background: "var(--background)" }} />;

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <Activity size={48} color="var(--primary)" style={{ animation: "pulse 1.5s infinite" }} />
        <p style={{ marginTop: 16, fontSize: 18, fontWeight: 600 }}>Loading your dashboard...</p>
      </div>
    </div>
  );

  const score = stats?.productivity_score || 0;

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* Shared Sidebar */}
      {user && (
        <Sidebar user={user} onLogout={handleLogout} activePage="/my-dashboard" />
      )}

      {/* Main Content */}
      <main style={{ flex: 1, padding: 32, overflowY: "auto" }}>
        {/* Header */}
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 40 }}>
          <div>
            <h1 style={{ fontSize: 36, fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 4 }}>
              <span className="text-gradient">Hey, {user?.name} 👋</span>
            </h1>
            <p style={{ color: "#64748b" }}>
              {user?.org_id ? `Active Member of ${user.org_name}` : "Your personal productivity universe"}
            </p>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            {user?.org_id && (
              <div onClick={() => setIsSharing(!isSharing)} className="glass" style={{
                padding: "12px 20px", display: "flex", alignItems: "center", gap: 10,
                borderRadius: 14, cursor: "pointer",
                border: isSharing ? "1px solid rgba(16,185,129,0.3)" : "1px solid rgba(239,68,68,0.3)"
              }}>
                <Shield size={18} color={isSharing ? "#10b981" : "#f87171"} />
                <span style={{ fontWeight: 600, fontSize: 14, color: isSharing ? "#10b981" : "#f87171" }}>
                  {isSharing ? "Sharing Enabled" : "Sharing Paused"}
                </span>
              </div>
            )}
          </div>
        </header>

        {/* Invitation Hub */}
        {showInviteHub && pendingInvites.length > 0 && (
          <div className="glass" style={{ padding: 24, borderRadius: 20, marginBottom: 32, border: "1px solid rgba(79,70,229,0.3)", background: "linear-gradient(135deg, rgba(79,70,229,0.1), transparent)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800, display: "flex", alignItems: "center", gap: 8 }}>
                <Monitor size={20} color="var(--primary)" /> Organization Invitation
              </h2>
              <span onClick={() => setShowInviteHub(false)} style={{ fontSize: 12, color: "#64748b", cursor: "pointer" }}>Dismiss</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {pendingInvites.map((inv) => (
                <div key={inv.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.02)" }}>
                  <div>
                    <span style={{ fontWeight: 700, fontSize: 15, display: "block" }}>{inv.org_name}</span>
                    <span style={{ fontSize: 12, color: "#64748b" }}>Admin {inv.inviter_name} invited you</span>
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    <button className="btn-primary" onClick={() => handleAcceptInvite(inv.id)} style={{ padding: "8px 20px", fontSize: 12 }}>Join Org</button>
                    <button onClick={() => handleDeclineInvite(inv.id)} style={{ padding: "8px 12px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, color: "#94a3b8", fontSize: 12, cursor: "pointer" }}>Decline</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Productivity Score */}
        <div className="primary-gradient" style={{
          padding: 32, borderRadius: 24, marginBottom: 32,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          boxShadow: "0 10px 40px rgba(79,70,229,0.3)"
        }}>
          <div>
            <p style={{ fontSize: 14, opacity: 0.8, marginBottom: 8 }}>Daily Productivity Score</p>
            <h2 style={{ fontSize: 56, fontWeight: 900 }}>{score}%</h2>
            <div style={{ height: 6, width: 200, background: "rgba(255,255,255,0.2)", borderRadius: 3, marginTop: 12, overflow: "hidden" }}>
              <div style={{ width: `${score}%`, height: "100%", background: "white", borderRadius: 3, transition: "width 0.5s ease" }} />
            </div>
          </div>
          <TrendingUp size={64} style={{ opacity: 0.3 }} />
        </div>

        {/* Stats Row — click to change chart metric */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 32 }}>
          <MiniStat icon={<Monitor size={20} color="#a855f7" />} label="Active Time" value={formatTime(stats?.total_time_seconds || 0)} active={chartMetric === "activeTime"} color="#a855f7" onClick={() => setChartMetric("activeTime")} />
          <MiniStat icon={<Keyboard size={20} color="#10b981" />} label="Keystrokes" value={stats?.activity_summary?.keystrokes?.toLocaleString() || "0"} active={chartMetric === "keystrokes"} color="#10b981" onClick={() => setChartMetric("keystrokes")} />
          <MiniStat icon={<MousePointer2 size={20} color="#f59e0b" />} label="Mouse Clicks" value={stats?.activity_summary?.clicks?.toLocaleString() || "0"} active={chartMetric === "clicks"} color="#f59e0b" onClick={() => setChartMetric("clicks")} />
          <MiniStat icon={<Clock size={20} color="#06b6d4" />} label="Sessions" value={String(windowSessions)} active={chartMetric === "sessions"} color="#06b6d4" onClick={() => setChartMetric("sessions")} />
        </div>

        {/* Activity Chart */}
        <div className="card" style={{ marginBottom: 32, display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
              <BarChart3 size={20} color="var(--primary)" /> Activity Timeline
            </h3>
            <div style={{ display: "flex", gap: 8 }}>
              {(["1h", "24h", "7d"] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => {
                    setTimeRange(range);
                    setShowCustomRange(false);
                    if (range !== "7d") setWeekActivity(null); // reset so it refetches next time
                  }}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 8,
                    fontSize: 12,
                    fontWeight: 600,
                    border: "1px solid rgba(255,255,255,0.1)",
                    background: timeRange === range ? "var(--primary)" : "rgba(255,255,255,0.04)",
                    color: timeRange === range ? "white" : "#94a3b8",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  {range === "1h" ? "Last Hour" : range === "24h" ? "Last 24h" : "Last 7 Days"}
                </button>
              ))}
              <button
                onClick={() => setShowCustomRange(!showCustomRange)}
                style={{
                  padding: "6px 14px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 600,
                  border: "1px solid rgba(255,255,255,0.1)",
                  background: timeRange === "custom" ? "var(--primary)" : "rgba(255,255,255,0.04)",
                  color: timeRange === "custom" ? "white" : "#94a3b8",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                Custom Range
              </button>
            </div>
          </div>

          {/* Custom Date Range Picker */}
          {showCustomRange && (
            <div style={{ marginBottom: 16, padding: 16, background: "rgba(79,70,229,0.08)", borderRadius: 12, border: "1px solid rgba(79,70,229,0.2)" }}>
              <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 6, color: "#94a3b8" }}>Start Date & Time</label>
                  <input
                    type="datetime-local"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    style={{
                      width: "100%", padding: "8px 12px", borderRadius: 8,
                      border: "1px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.3)",
                      color: "#fff", fontSize: 12,
                    }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 6, color: "#94a3b8" }}>End Date & Time</label>
                  <input
                    type="datetime-local"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    style={{
                      width: "100%", padding: "8px 12px", borderRadius: 8,
                      border: "1px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.3)",
                      color: "#fff", fontSize: 12,
                    }}
                  />
                </div>
                <button
                  onClick={() => { if (customStartDate && customEndDate) setTimeRange("custom"); }}
                  disabled={!customStartDate || !customEndDate}
                  style={{
                    padding: "8px 16px", borderRadius: 8,
                    background: customStartDate && customEndDate ? "var(--primary)" : "rgba(255,255,255,0.1)",
                    color: "white", border: "none", fontSize: 12, fontWeight: 600,
                    cursor: customStartDate && customEndDate ? "pointer" : "not-allowed",
                    opacity: customStartDate && customEndDate ? 1 : 0.5, whiteSpace: "nowrap",
                  }}
                >
                  Apply
                </button>
              </div>
            </div>
          )}

          {(() => {
            const metricConfig = {
              activeTime: { label: "Active Time (min)", color: "#a855f7" },
              keystrokes: { label: "Keystrokes", color: "#10b981" },
              clicks: { label: "Mouse Clicks", color: "#f59e0b" },
              sessions: { label: "Window Sessions", color: "#06b6d4" },
            };
            const cfg = metricConfig[chartMetric];
            return (
              <>
                <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
                  <div style={{ padding: "8px 12px", background: `${cfg.color}1a`, borderRadius: 8, fontSize: 12, color: cfg.color }}>
                    {cfg.label}
                  </div>
                  {timeRange === "custom" && (
                    <div style={{ padding: "8px 12px", background: "rgba(168,85,247,0.1)", borderRadius: 8, fontSize: 12, color: "#d8b4fe" }}>
                      Custom Range
                    </div>
                  )}
                </div>
                <div style={{ flex: 1, width: "100%", minHeight: 300 }}>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="metricGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={cfg.color} stopOpacity={0.3} />
                            <stop offset="100%" stopColor={cfg.color} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="time" stroke="#475569" fontSize={11} tickLine={false} angle={(timeRange === "1h" || (timeRange === "custom" && chartData.length > 20)) ? -45 : 0} height={(timeRange === "1h" || (timeRange === "custom" && chartData.length > 20)) ? 60 : 30} />
                        <YAxis stroke="#475569" fontSize={11} />
                        <Tooltip contentStyle={{ background: "#16161a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, color: "#fff" }} formatter={(value) => [Math.round(value as number), cfg.label]} />
                        <Area type="monotone" dataKey={chartMetric} stroke={cfg.color} fill="url(#metricGrad)" strokeWidth={2} isAnimationActive={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#64748b" }}>
                      Select valid start and end dates to view activity
                    </div>
                  )}
                </div>
              </>
            );
          })()}
        </div>

        {/* CCTV Live Monitoring */}
        <div style={{ marginBottom: 32 }}>
          <CCTVDashboard />
        </div>
      </main>
    </div>
  );
}

function MiniStat({ icon, label, value, active = false, color, onClick }: {
  icon: any; label: string; value: string; active?: boolean; color?: string; onClick?: () => void;
}) {
  return (
    <div className="card" onClick={onClick} style={{
      padding: 20, cursor: onClick ? "pointer" : "default",
      border: active ? `1px solid ${color || "var(--primary)"}` : "1px solid transparent",
      transition: "all 0.2s",
    }}>
      <div style={{ marginBottom: 10, padding: 8, background: "rgba(255,255,255,0.03)", borderRadius: 10, width: "fit-content" }}>{icon}</div>
      <p style={{ color: "#64748b", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>{label}</p>
      <h4 style={{ fontSize: 22, fontWeight: 800 }}>{value}</h4>
    </div>
  );
}

function formatTime(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m ${seconds % 60}s`;
}
