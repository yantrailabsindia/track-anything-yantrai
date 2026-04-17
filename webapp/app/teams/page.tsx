"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, clearAuth, fetchTeams, createTeam, fetchUsers, assignTeamMember } from "../../lib/api";
import {
  Activity, Users, UserPlus, Plus, ArrowLeft, Shield, LogOut, FolderOpen
} from "lucide-react";
import Link from "next/link";

export default function TeamsPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [teams, setTeams] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [msg, setMsg] = useState("");

  // Assign member
  const [showAssign, setShowAssign] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState("");

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    if (u.role !== "admin" && u.role !== "super_admin") { router.push("/dashboard"); return; }
    setUser(u);

    async function load() {
      try {
        const [t, ul] = await Promise.all([
          fetchTeams().catch(() => []),
          fetchUsers().catch(() => []),
        ]);
        setTeams(t);
        setUsers(ul);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createTeam(newName, newDesc);
      setMsg("✅ Team created!");
      setNewName(""); setNewDesc(""); setShowCreate(false);
      const t = await fetchTeams();
      setTeams(t);
      setTimeout(() => setMsg(""), 3000);
    } catch (err: any) {
      setMsg(`❌ ${err.message}`);
    }
  }

  async function handleAssign(teamId: string) {
    if (!selectedUser) return;
    try {
      await assignTeamMember(teamId, selectedUser);
      setMsg("✅ Member assigned!");
      setShowAssign(null); setSelectedUser("");
      const t = await fetchTeams();
      setTeams(t);
      setTimeout(() => setMsg(""), 3000);
    } catch (err: any) {
      setMsg(`❌ ${err.message}`);
    }
  }

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <Activity size={48} color="var(--primary)" />
    </div>
  );

  const unassignedUsers = users.filter(u => !u.team_id);

  return (
    <div style={{ minHeight: "100vh", padding: 32, maxWidth: 900, margin: "0 auto" }}>
      {/* Header */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 40 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Link href="/dashboard">
            <div className="glass" style={{ padding: 12, borderRadius: 12, cursor: "pointer", display: "flex" }}>
              <ArrowLeft size={20} color="#94a3b8" />
            </div>
          </Link>
          <div>
            <h1 style={{ fontSize: 32, fontWeight: 900, letterSpacing: "-0.04em" }}>
              <span className="text-gradient">Team Management</span>
            </h1>
            <p style={{ color: "#64748b", fontSize: 13 }}>Manage teams for {user?.org_name || "your organization"}</p>
          </div>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(!showCreate)} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
          <Plus size={18} /> New Team
        </button>
      </header>

      {msg && (
        <div className="glass" style={{ padding: "12px 20px", borderRadius: 12, marginBottom: 24, fontSize: 14, fontWeight: 600 }}>
          {msg}
        </div>
      )}

      {/* Create Team Form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="card" style={{ marginBottom: 32 }}>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <FolderOpen size={20} color="var(--primary)" /> Create New Team
          </h3>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div>
              <label style={labelStyle}>Team Name</label>
              <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Engineering" required style={inputStyle} />
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label style={labelStyle}>Description</label>
              <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Optional description" style={inputStyle} />
            </div>
            <button type="submit" className="btn-primary" style={{ padding: "12px 24px" }}>Create</button>
          </div>
        </form>
      )}

      {/* Teams Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 20 }}>
        {teams.map((team) => (
          <div key={team.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>{team.name}</h3>
                {team.description && <p style={{ color: "#64748b", fontSize: 12 }}>{team.description}</p>}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, background: "rgba(79,70,229,0.1)", padding: "6px 12px", borderRadius: 8 }}>
                <Users size={16} color="var(--primary)" />
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--primary)" }}>{team.member_count || 0}</span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => setShowAssign(showAssign === team.id ? null : team.id)}
                className="glass"
                style={{ padding: "8px 14px", borderRadius: 10, fontSize: 12, fontWeight: 600, cursor: "pointer", border: "none", color: "#94a3b8", display: "flex", alignItems: "center", gap: 6 }}
              >
                <UserPlus size={14} /> Add Member
              </button>
            </div>

            {showAssign === team.id && (
              <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
                <select
                  value={selectedUser}
                  onChange={e => setSelectedUser(e.target.value)}
                  style={{ ...inputStyle, flex: 1 }}
                >
                  <option value="">Select user...</option>
                  {unassignedUsers.map(u => (
                    <option key={u.id} value={u.id}>{u.name} ({u.username})</option>
                  ))}
                </select>
                <button className="btn-primary" onClick={() => handleAssign(team.id)} style={{ padding: "10px 16px", fontSize: 12 }}>Assign</button>
              </div>
            )}
          </div>
        ))}
        {teams.length === 0 && (
          <div className="card" style={{ gridColumn: "1/-1", textAlign: "center", padding: 48 }}>
            <FolderOpen size={48} color="#475569" style={{ marginBottom: 16 }} />
            <p style={{ color: "#475569", fontSize: 16 }}>No teams yet. Create your first team above.</p>
          </div>
        )}
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block", fontSize: 11, color: "#64748b", marginBottom: 6,
  fontWeight: 600, textTransform: "uppercase", letterSpacing: 1,
};

const inputStyle: React.CSSProperties = {
  padding: "10px 14px", background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
  color: "#f0f0f3", fontSize: 14, outline: "none", width: "100%",
  boxSizing: "border-box",
};
