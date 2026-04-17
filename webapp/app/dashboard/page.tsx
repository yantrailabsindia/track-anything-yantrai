"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  fetchStats, fetchActivity, fetchScreenshots, fetchUsers, createUser,
  getUser, clearAuth, downloadWindowsAgent, checkDownloadAvailable, fetchOrganizationDetails,
  fetchMyInvites, acceptInvite, declineInvite, sendInvite
} from "../../lib/api";
import { CCTVDashboard } from "../../components/CCTVDashboard";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Activity, Clock, MousePointer2, Keyboard, Monitor, Globe,
  BarChart3, Image as ImageIcon, LayoutDashboard, Settings, LogOut,
  Users, UserPlus, Download, Shield, FolderOpen, ArrowLeft
} from "lucide-react";

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const viewOrgId = searchParams.get("org"); // super_admin viewing a specific org
  const [user, setUser] = useState<any>(null);
  const [viewOrg, setViewOrg] = useState<any>(null);
  const [dashboardData, setDashboardData] = useState({
    stats: null as any,
    activity: [] as any[],
    screenshots: [] as any[],
    users: [] as any[],
    downloadAvailable: false,
    pendingInvites: [] as any[]
  });
  const [loading, setLoading] = useState(true);
  const [showAddUser, setShowAddUser] = useState(false);
  const [showInviteHub, setShowInviteHub] = useState(false);
  const [isSharing, setIsSharing] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [selectedScreenshot, setSelectedScreenshot] = useState<any>(null);

  useEffect(() => {
    setMounted(true);
  }, []);


  // Add user form
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("employee");
  const [newTeamId, setNewTeamId] = useState("");
  const [addUserMsg, setAddUserMsg] = useState("");

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    if (u.role === "employee") { router.push("/my-dashboard"); return; }
    setUser(u);

    async function loadData() {
      try {
        if (viewOrgId && u.role === "super_admin") {
          try {
            const orgDetails = await fetchOrganizationDetails(viewOrgId);
            setViewOrg(orgDetails);
          } catch (e) { console.error("Failed to fetch org details", e); }
        }

        // Use individual catch to prevent one hanging API from blocking the whole dashboard
        const [s, a, ss, ul, dl, invites] = await Promise.all([
          fetchStats().catch(err => { console.error("Stats fail", err); return null; }),
          fetchActivity({ limit: 500 }).then(r => r.logs || []).catch(err => { console.error("Activity fail", err); return []; }),
          fetchScreenshots().catch(err => { console.error("Screenshots fail", err); return []; }),
          fetchUsers(viewOrgId || undefined).catch(() => []),
          checkDownloadAvailable().catch(() => false),
          fetchMyInvites().catch(() => [])
        ]);

        setDashboardData({
          stats: s,
          activity: a,
          screenshots: ss,
          users: ul,
          downloadAvailable: dl,
          pendingInvites: invites
        });

        if (invites && invites.length > 0) setShowInviteHub(true);
      } catch (error) {
        console.error("Dashboard primary load error:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [router, viewOrgId]);

  async function handleAcceptInvite(id: string) {
    try {
      await acceptInvite(id);
      window.location.reload(); // Refresh to update org context
    } catch (e: any) {
      alert(e.message);
    }
  }

  async function handleDeclineInvite(id: string) {
    try {
      await declineInvite(id);
      setDashboardData(prev => ({ ...prev, pendingInvites: prev.pendingInvites.filter(i => i.id !== id) }));
      if (dashboardData.pendingInvites.length <= 1) setShowInviteHub(false);
    } catch (e: any) {
      alert(e.message);
    }
  }


  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  async function handleAddUser(e: React.FormEvent) {
    e.preventDefault();
    try {
      // When super_admin is viewing a specific org, create user for that org
      const targetOrgId = viewOrgId || user?.org_id;
      await createUser(newUsername, newPassword, newName, newRole, newTeamId || undefined, targetOrgId);
      setAddUserMsg(`✅ User "${newUsername}" created successfully!`);
      setNewUsername(""); setNewPassword(""); setNewName(""); setNewRole("employee"); setNewTeamId("");
      const ul = await fetchUsers(viewOrgId || undefined);
      setDashboardData(prev => ({ ...prev, users: ul }));
      setTimeout(() => setAddUserMsg(""), 4000);
    } catch (err: any) {
      setAddUserMsg(`❌ ${err.message}`);
    }
  }

  // Hydration safety: Return null or same-structure skeleton during SSR
  if (!mounted) return <div style={{ minHeight: "100vh", background: "var(--background)" }} />;

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <Activity size={48} color="var(--primary)" style={{ animation: "pulse 1.5s infinite" }} />
        <p style={{ marginTop: 16, fontSize: 18, fontWeight: 600 }}>Loading ProMe...</p>
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* Sidebar */}
      <aside className="glass" style={{ width: 240, margin: 16, marginRight: 0, padding: 24, display: "flex", flexDirection: "column", gap: 32, borderRadius: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div className="primary-gradient" style={{ width: 40, height: 40, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Activity color="white" />
          </div>
          <div>
            <span style={{ fontSize: 20, fontWeight: 800, display: "block", letterSpacing: "-0.03em" }}>ProMe</span>
            <span style={{ fontSize: 11, color: "#64748b" }}>{viewOrg?.name || user?.org_name || (user?.role === "super_admin" ? "Platform Control" : "Personal Mode")}</span>
          </div>

        </div>

        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {user?.role === "super_admin" && (
            <SidebarItem icon={<ArrowLeft size={20} />} label="← Back to Orgs" onClick={() => router.push("/organizations")} />
          )}
          <SidebarItem icon={<LayoutDashboard size={20} />} label="Dashboard" active />
          <SidebarItem icon={<Activity size={20} />} label="Activity Logs" onClick={() => router.push("/logs")} />
          <SidebarItem icon={<Activity size={20} />} label="AI Assistant" onClick={() => router.push("/chat")} />
          <SidebarItem icon={<Users size={20} />} label="Employees" onClick={() => setShowAddUser(!showAddUser)} />
          <SidebarItem icon={<FolderOpen size={20} />} label="Teams" onClick={() => router.push("/teams")} />
          <SidebarItem icon={<Download size={20} />} label="Downloads" onClick={() => router.push("/download")} />
          <SidebarItem icon={<Settings size={20} />} label="Settings" onClick={() => router.push("/settings")} />
        </nav>

        <div style={{ marginTop: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontSize: 13, color: "#94a3b8" }}>
            <Shield size={16} />
            <span>{user?.name}</span>
          </div>
          <SidebarItem icon={<LogOut size={20} />} label="Sign Out" onClick={handleLogout} />
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: 32, overflowY: "auto" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 40 }}>
          <div>
            <h1 style={{ fontSize: 36, fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 4 }}>
              <span className="text-gradient">
                {viewOrg ? viewOrg.name : (user?.role === "super_admin" ? "Global Control" : (user?.org_id ? "Admin Dashboard" : "Personal Space"))}
              </span>
            </h1>
            <p style={{ color: "#64748b" }}>
              {viewOrg ? `Managing ${viewOrg.name}` : (user?.org_id ? `${user.org_name} productivity overview` : "Master your focus and productivity")}
            </p>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            {user?.org_id && user?.role === "employee" && (
              <div onClick={() => setIsSharing(!isSharing)} className="glass" style={{ padding: "12px 20px", display: "flex", alignItems: "center", gap: 10, borderRadius: 14, cursor: "pointer", border: isSharing ? "1px solid rgba(16,185,129,0.3)" : "1px solid rgba(239,68,68,0.3)" }}>
                <Shield size={18} color={isSharing ? "#10b981" : "#f87171"} />
                <span style={{ fontWeight: 600, fontSize: 14, color: isSharing ? "#10b981" : "#f87171" }}>
                  {isSharing ? "Sharing Enabled" : "Sharing Paused"}
                </span>
              </div>
            )}
            <div className="glass" style={{ padding: "12px 20px", display: "flex", alignItems: "center", gap: 10, borderRadius: 14 }}>
              <Clock size={18} color="var(--primary)" />
              <span style={{ fontWeight: 600, fontSize: 14 }}>{new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</span>
            </div>
          </div>
        </header>

        {/* Invitation Hub */}
        {showInviteHub && dashboardData.pendingInvites.length > 0 && (
          <div className="glass" style={{ padding: 24, borderRadius: 20, marginBottom: 32, border: "1px solid rgba(79,70,229,0.3)", background: "linear-gradient(135deg, rgba(79,70,229,0.1), transparent)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
                  <UserPlus size={24} color="var(--primary)" /> Organization Invitation
                </h2>
                <p style={{ color: "#94a3b8" }}>You have been invited to join a professional organization.</p>
              </div>
              <button onClick={() => setShowInviteHub(false)} style={{ color: "#64748b", background: "none", border: "none", cursor: "pointer" }}>Dismiss</button>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {dashboardData.pendingInvites.map((inv) => (
                <div key={inv.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255,255,255,0.02)" }}>
                  <div>
                    <span style={{ fontWeight: 700, fontSize: 16, display: "block" }}>{inv.org_name}</span>
                    <span style={{ fontSize: 13, color: "#64748b" }}>Invited by {inv.inviter_name}</span>
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    <button className="btn-primary" onClick={() => handleAcceptInvite(inv.id)} style={{ padding: "8px 24px", fontSize: 13 }}>Join Business</button>
                    <button onClick={() => handleDeclineInvite(inv.id)} style={{ padding: "8px 16px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, color: "#94a3b8", fontSize: 13, cursor: "pointer" }}>Decline</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}


        {/* Stats Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 16, marginBottom: 32 }}>
          <StatsCard title="Productivity" value={`${dashboardData.stats?.productivity_score || 0}%`} icon={<Activity size={22} color="var(--primary)" />} />
          <StatsCard title="Active Time" value={formatTime(dashboardData.stats?.total_time_seconds || 0)} icon={<Monitor size={22} color="#a855f7" />} />
          <StatsCard title="Keystrokes" value={dashboardData.stats?.activity_summary?.keystrokes?.toLocaleString() || "0"} icon={<Keyboard size={22} color="#10b981" />} />
          <StatsCard title="Mouse Clicks" value={dashboardData.stats?.activity_summary?.clicks?.toLocaleString() || "0"} icon={<MousePointer2 size={22} color="#f59e0b" />} />
          <StatsCard title="Employees" value={String(dashboardData.users.length)} icon={<Users size={22} color="#06b6d4" />} />
        </div>

        {/* Charts + Screenshots */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
          {/* Top Apps Chart */}
          <div className="card" style={{ height: 400, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: 18, marginBottom: 20, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
              <BarChart3 size={20} color="var(--primary)" /> Top Applications
            </h3>
            <div style={{ flex: 1, width: "100%", minHeight: 0 }}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={(dashboardData.stats?.top_apps || []).slice(0, 5)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2e" horizontal={false} />
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" stroke="#94a3b8" width={150} fontSize={12} tickFormatter={(v: string) => v.length > 25 ? v.slice(0, 22) + '...' : v} />
                  <Tooltip contentStyle={{ backgroundColor: '#16161a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12 }} itemStyle={{ color: '#fff' }} formatter={(value: any) => [`${Math.round(Number(value))}s`, 'Duration']} />
                  <Bar dataKey="duration" fill="url(#barGrad)" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                    <defs>
                      <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#4f46e5" />
                        <stop offset="100%" stopColor="#8b5cf6" />
                      </linearGradient>
                    </defs>
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Screenshots */}
          <div className="card" style={{ height: 400, display: "flex", flexDirection: "column" }}>
            <h3 style={{ fontSize: 18, marginBottom: 20, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
              <ImageIcon size={20} color="#a855f7" /> Recent Snapshots
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, flex: 1, overflow: "hidden" }}>
              {dashboardData.screenshots.slice(0, 4).map((shot) => (
                <div key={shot.filename} onClick={() => setSelectedScreenshot(shot)} style={{ position: "relative", overflow: "hidden", borderRadius: 12, border: "1px solid rgba(255,255,255,0.05)", aspectRatio: "16/10", background: "rgba(255,255,255,0.02)", cursor: "pointer", transition: "all 0.2s", transform: "scale(1)" }} onMouseEnter={e => (e.currentTarget.style.transform = "scale(1.02)")} onMouseLeave={e => (e.currentTarget.style.transform = "scale(1)")}>
                  <img src={`${shot.url}`} alt="Capture" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
              ))}
              {dashboardData.screenshots.length === 0 && <div style={{ gridColumn: "1/3", display: "flex", alignItems: "center", justifyContent: "center", color: "#475569" }}>No snapshots yet.</div>}
            </div>
          </div>
        </div>

        {/* CCTV Live Feeds */}
        <div style={{ marginBottom: 32 }}>
          <CCTVDashboard />
        </div>

        {/* Employee Management */}
        <div className="card" style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
              <Users size={20} color="var(--primary)" /> Employee Management
            </h3>
            <button className="btn-primary" onClick={() => setShowAddUser(!showAddUser)} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, padding: "8px 16px" }}>
              <UserPlus size={16} /> Add Employee
            </button>
          </div>

          {/* Add User Form */}
          {showAddUser && (
            <form onSubmit={handleAddUser} style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "flex-end" }}>
              <FormField label="Name" value={newName} onChange={setNewName} placeholder="John Doe" />
              <FormField label="Username" value={newUsername} onChange={setNewUsername} placeholder="john.doe" />
              <FormField label="Password" value={newPassword} onChange={setNewPassword} placeholder="••••••" type="password" />
              <FormField label="Team ID" value={newTeamId} onChange={setNewTeamId} placeholder="engineering" />
              <div>
                <label style={{ display: "block", fontSize: 11, color: "#64748b", marginBottom: 6, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>Role</label>
                <select value={newRole} onChange={e => setNewRole(e.target.value)} style={{ padding: "10px 12px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#f0f0f3", fontSize: 14 }}>
                  <option value="employee">Employee</option>
                  <option value="team_lead">Team Lead</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <button type="submit" className="btn-primary" style={{ padding: "10px 20px" }}>Create</button>
              {addUserMsg && <span style={{ fontSize: 13, padding: "10px 0", width: "100%" }}>{addUserMsg}</span>}
            </form>
          )}

          {/* Users Table */}
          <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", color: "#64748b", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                <th style={{ padding: "10px 0" }}>Name</th>
                <th style={{ padding: "10px 0" }}>Username</th>
                <th style={{ padding: "10px 0" }}>Role</th>
                <th style={{ padding: "10px 0" }}>Team</th>
                <th style={{ padding: "10px 0" }}>Created</th>
              </tr>
            </thead>
            <tbody>
              {dashboardData.users.map((u) => (
                <tr key={u.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                  <td style={{ padding: "12px 0", fontWeight: 500 }}>{u.name}</td>
                  <td style={{ padding: "12px 0", color: "#94a3b8", fontSize: 13 }}>{u.username}</td>
                  <td style={{ padding: "12px 0" }}>
                    <span style={{
                      padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                      background: u.role === "admin" ? "rgba(79,70,229,0.15)" : u.role === "team_lead" ? "rgba(245,158,11,0.15)" : "rgba(16,185,129,0.15)",
                      color: u.role === "admin" ? "#818cf8" : u.role === "team_lead" ? "#fbbf24" : "#34d399"
                    }}>{u.role}</span>
                  </td>
                  <td style={{ padding: "12px 0", color: "#94a3b8", fontSize: 13 }}>{u.team_id || "—"}</td>
                  <td style={{ padding: "12px 0", color: "#64748b", fontSize: 12 }}>{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {dashboardData.users.length === 0 && <tr><td colSpan={5} style={{ padding: 20, textAlign: "center", color: "#475569" }}>No employees yet.</td></tr>}
            </tbody>
          </table>
        </div>

        {/* Download Section */}
        <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "linear-gradient(135deg, rgba(79,70,229,0.08), rgba(139,92,246,0.04))" }}>
          <div>
            <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
              <Download size={20} color="var(--primary)" /> ProMe Agent Download
            </h3>
            <p style={{ color: "#64748b", fontSize: 13 }}>
              {dashboardData.downloadAvailable ? "Distribute this installer to employees." : "Build not available. Run PyInstaller to generate the .exe."}
            </p>
          </div>
          <button className="btn-primary" onClick={downloadWindowsAgent} disabled={!dashboardData.downloadAvailable} style={{ display: "flex", alignItems: "center", gap: 8, opacity: dashboardData.downloadAvailable ? 1 : 0.4 }}>
            <Download size={18} /> {dashboardData.downloadAvailable ? "Download .exe" : "Not Available"}
          </button>
        </div>

        {/* Real-Time Activity Logs */}
        <div className="card" style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
            <Activity size={20} color="var(--primary)" /> Real-Time Activity Logs
          </h3>
          <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: 12, padding: 16, fontFamily: "'Courier New', monospace", fontSize: 12, color: "#cbd5e1", maxHeight: 300, overflowY: "auto", lineHeight: 1.6 }}>
            {dashboardData.activity.length > 0 ? (
              <div>
                {dashboardData.activity.slice().reverse().slice(0, 20).map((item, idx) => {
                  const timestamp = new Date(item.timestamp).toLocaleTimeString('en-US', { hour12: false });
                  const eventType = item.event_type || "unknown";
                  let eventDetail = "";

                  if (eventType === "input_summary") {
                    const keys = item.data?.keystrokes || 0;
                    const clicks = item.data?.mouse_clicks || 0;
                    const dist = item.data?.mouse_distance_px || 0;
                    eventDetail = `Keyboard: ${keys} keys | Mouse: ${clicks} clicks | ${Math.round(dist)}px`;
                  } else if (eventType === "window_change") {
                    const win = item.data?.window_title || "Unknown";
                    const dur = item.data?.duration_seconds || 0;
                    eventDetail = `Window: ${win.substring(0, 45)} (${dur}s)`;
                  } else if (eventType === "screenshot") {
                    eventDetail = "Screenshot captured";
                  } else if (eventType === "telemetry") {
                    const cpu = item.data?.cpu_percent || 0;
                    const ram = item.data?.ram_percent || 0;
                    eventDetail = `System: CPU ${cpu}% RAM ${ram}%`;
                  } else {
                    eventDetail = `${eventType}: ${JSON.stringify(item.data || {}).substring(0, 40)}`;
                  }

                  return (
                    <div key={item.id || idx} style={{ marginBottom: 8, color: "#cbd5e1", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                      [{timestamp}] {eventDetail}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ color: "#475569", textAlign: "center", padding: 32 }}>
                No activity logs yet. Start the ProMe desktop agent to capture logs.
              </div>
            )}
          </div>
        </div>

        {/* Activity Timeline (Window Changes Only) */}
        <div className="card" style={{ marginTop: 24 }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>Window Activity Timeline</h3>
          <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", color: "#64748b", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                <th style={{ padding: "10px 0" }}>Time</th>
                <th style={{ padding: "10px 0" }}>Activity</th>
                <th style={{ padding: "10px 0", textAlign: "right" }}>Duration</th>
              </tr>
            </thead>
            <tbody>
              {dashboardData.activity.filter(a => a.event_type === "window_change").slice(-10).reverse().map((item) => (
                <tr key={item.id || item.timestamp} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                  <td style={{ padding: "12px 0", fontSize: 12, color: "#94a3b8" }}>{new Date(item.timestamp).toLocaleTimeString()}</td>
                  <td style={{ padding: "12px 0", fontWeight: 500, fontSize: 13 }}>{item.data?.window_title || "Unknown"}</td>
                  <td style={{ padding: "12px 0", textAlign: "right" }}>
                    <span style={{ background: "rgba(79,70,229,0.12)", color: "var(--primary)", padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600 }}>
                      {item.data?.duration_seconds || 0}s
                    </span>
                  </td>
                </tr>
              ))}
              {dashboardData.activity.filter(a => a.event_type === "window_change").length === 0 && (
                <tr><td colSpan={3} style={{ padding: 20, textAlign: "center", color: "#475569" }}>
                  No window activity logs yet. Start the ProMe desktop agent.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Screenshot Modal */}
        {selectedScreenshot && (
          <div onClick={() => setSelectedScreenshot(null)} style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.8)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, cursor: "pointer" }}>
            <div onClick={e => e.stopPropagation()} style={{ position: "relative", maxWidth: "90vw", maxHeight: "90vh", cursor: "default" }}>
              <button onClick={() => setSelectedScreenshot(null)} style={{ position: "absolute", top: -40, right: 0, background: "none", border: "none", color: "#fff", fontSize: 24, cursor: "pointer" }}>✕</button>
              <img src={`${selectedScreenshot.url}`} alt="Full screenshot" style={{ maxWidth: "100%", maxHeight: "100%", borderRadius: 16, border: "1px solid rgba(255,255,255,0.1)" }} />
              <div style={{ marginTop: 12, color: "#94a3b8", fontSize: 12, textAlign: "center" }}>
                {new Date(selectedScreenshot.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

import React from "react";

const SidebarItem = React.memo(({ icon, label, active = false, onClick }: { icon: any, label: string, active?: boolean, onClick?: () => void }) => {
  return (
    <div onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", borderRadius: 12, cursor: "pointer",
      transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
      background: active ? "var(--primary)" : "transparent",
      color: active ? "white" : "#94a3b8",
      boxShadow: active ? "0 4px 12px rgba(79,70,229,0.3)" : "none",
      fontWeight: 600, fontSize: 14
    }}>
      {icon}
      <span>{label}</span>
    </div>
  );
});

const StatsCard = React.memo(({ title, value, icon }: { title: string, value: string, icon: any }) => {
  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ marginBottom: 12, padding: 10, background: "rgba(255,255,255,0.03)", borderRadius: 12, width: "fit-content" }}>{icon}</div>
      <p style={{ color: "#64748b", fontSize: 11, marginBottom: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>{title}</p>
      <h4 style={{ fontSize: 24, fontWeight: 800 }}>{value}</h4>
    </div>
  );
});

function SidebarItem_DEPRECATED() { return null; } // Kept for anchor if needed, but replaced with memoized versions

function FormField({ label, value, onChange, placeholder, type = "text" }: any) {
  return (
    <div>
      <label style={{ display: "block", fontSize: 11, color: "#64748b", marginBottom: 6, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} required
        style={{ padding: "10px 12px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#f0f0f3", fontSize: 14, width: 160, outline: "none" }}
      />
    </div>
  );
}

function formatTime(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m ${seconds % 60}s`;
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", background: "var(--background)" }} />}>
      <DashboardContent />
    </Suspense>
  );
}
