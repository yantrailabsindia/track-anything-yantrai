"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchOrganizations, createOrganization, updateOrganization, getUser, clearAuth } from "../../lib/api";
import {
    Activity, Globe, Plus, LogOut, Shield, Settings,
    BarChart3, Users, CheckCircle2, XCircle, ExternalLink
} from "lucide-react";
import Link from "next/link";

export default function OrganizationsPage() {
    const router = useRouter();
    const [user, setUser] = useState<any>(null);
    const [organizations, setOrganizations] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    
    // Create Org State
    const [newName, setNewName] = useState("");
    const [newSlug, setNewSlug] = useState("");
    const [newPlan, setNewPlan] = useState("free");
    const [newMaxUsers, setNewMaxUsers] = useState(50);
    const [msg, setMsg] = useState("");

    useEffect(() => {
        const u = getUser();
        if (!u) { router.push("/login"); return; }
        if (u.role !== "super_admin") { router.push("/dashboard"); return; }
        setUser(u);

        async function load() {
            try {
                const orgs = await fetchOrganizations();
                setOrganizations(orgs);
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
            await createOrganization(newName, newSlug, newPlan, newMaxUsers);
            setMsg("✅ Organization created successfully!");
            setNewName(""); setNewSlug(""); setNewPlan("free"); setNewMaxUsers(50);
            setShowCreate(false);
            const orgs = await fetchOrganizations();
            setOrganizations(orgs);
            setTimeout(() => setMsg(""), 3000);
        } catch (err: any) {
            setMsg(`❌ ${err.message}`);
        }
    }

    async function toggleOrgActive(orgId: string, currentStatus: boolean) {
        try {
            await updateOrganization(orgId, { is_active: !currentStatus });
            const orgs = await fetchOrganizations();
            setOrganizations(orgs);
        } catch (e) {
            console.error(e);
        }
    }

    function handleLogout() {
        clearAuth();
        router.push("/login");
    }

    if (loading) return (
        <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
            <Activity size={48} color="var(--primary)" className="animate-pulse" />
        </div>
    );

    return (
        <div style={{ display: "flex", minHeight: "100vh" }}>
            {/* Sidebar */}
            <aside className="glass" style={{ width: 260, margin: 16, marginRight: 0, padding: 24, display: "flex", flexDirection: "column", gap: 32, borderRadius: 24 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div className="primary-gradient" style={{ width: 40, height: 40, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Activity color="white" />
                    </div>
                    <div>
                        <span style={{ fontSize: 20, fontWeight: 800, display: "block", letterSpacing: "-0.03em" }}>ProMe</span>
                        <span style={{ fontSize: 11, color: "#64748b" }}>Control Plane</span>
                    </div>
                </div>

                <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <SidebarItem icon={<Globe size={20} />} label="Organizations" active />
                    <SidebarItem icon={<Users size={20} />} label="Global Users" onClick={() => router.push("/dashboard")} />
                    <SidebarItem icon={<Settings size={20} />} label="Platform Settings" />
                </nav>

                <div style={{ marginTop: "auto" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontSize: 13, color: "#94a3b8" }}>
                        <Shield size={16} />
                        <span>Super Admin</span>
                    </div>
                    <SidebarItem icon={<LogOut size={20} />} label="Sign Out" onClick={handleLogout} />
                </div>
            </aside>

            {/* Main Content */}
            <main style={{ flex: 1, padding: 40, overflowY: "auto" }}>
                <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 40 }}>
                    <div>
                        <h1 style={{ fontSize: 36, fontWeight: 900, letterSpacing: "-0.04em", marginBottom: 4 }}>
                            <span className="text-gradient">Organization Management</span>
                        </h1>
                        <p style={{ color: "#64748b" }}>Manage multi-tenant isolation and seat limits</p>
                    </div>
                    <button className="btn-primary" onClick={() => setShowCreate(!showCreate)} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Plus size={20} /> New Organization
                    </button>
                </header>

                {msg && (
                    <div className="glass" style={{ padding: "12px 20px", borderRadius: 12, marginBottom: 24, fontSize: 14, fontWeight: 600 }}>
                        {msg}
                    </div>
                )}

                {/* Create Org Form */}
                {showCreate && (
                    <div className="card" style={{ marginBottom: 32, animation: "slideDown 0.3s ease-out" }}>
                        <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
                            <Plus size={20} color="var(--primary)" /> Onboard New Client
                        </h3>
                        <form onSubmit={handleCreate} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 20 }}>
                            <FormField label="Organization Name" value={newName} onChange={setNewName} placeholder="e.g. Acme Corporation" />
                            <FormField label="URL Slug" value={newSlug} onChange={setNewSlug} placeholder="acme-corp" />
                            <div>
                                <label style={labelStyle}>Plan Type</label>
                                <select value={newPlan} onChange={e => setNewPlan(e.target.value)} style={inputStyle}>
                                    <option value="free">Free</option>
                                    <option value="pro">Pro</option>
                                    <option value="enterprise">Enterprise</option>
                                </select>
                            </div>
                            <FormField label="Max Users (Seats)" value={String(newMaxUsers)} onChange={(v: string) => setNewMaxUsers(parseInt(v, 10) || 50)} type="number" />
                            <div style={{ gridColumn: "1/-1", display: "flex", gap: 12, marginTop: 10 }}>
                                <button type="submit" className="btn-primary" style={{ padding: "12px 32px" }}>Create Organization</button>
                                <button type="button" onClick={() => setShowCreate(false)} className="glass" style={{ padding: "12px 24px" }}>Cancel</button>
                            </div>
                        </form>
                    </div>
                )}

                {/* Orgs Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 24 }}>
                    {organizations.map((org) => (
                        <div key={org.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                <div>
                                    <h3 style={{ fontSize: 20, fontWeight: 800, letterSpacing: "-0.02em" }}>{org.name}</h3>
                                    <p style={{ color: "#64748b", fontSize: 12, fontFamily: "monospace" }}>/{org.slug}</p>
                                </div>
                                <div style={{ 
                                    padding: "4px 10px", borderRadius: 8, fontSize: 11, fontWeight: 700, textTransform: "uppercase",
                                    background: org.plan === "enterprise" ? "rgba(168, 85, 247, 0.15)" : "rgba(79, 70, 229, 0.1)",
                                    color: org.plan === "enterprise" ? "#a855f7" : "var(--primary)"
                                }}>
                                    {org.plan}
                                </div>
                            </div>
                            
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                <div className="glass" style={{ padding: 12, borderRadius: 12, textAlign: "center" }}>
                                    <span style={{ fontSize: 10, color: "#64748b", display: "block", textTransform: "uppercase" }}>Users</span>
                                    <span style={{ fontSize: 18, fontWeight: 800 }}>{org.user_count} / {org.max_users}</span>
                                </div>
                                <div className="glass" style={{ padding: 12, borderRadius: 12, textAlign: "center" }}>
                                    <span style={{ fontSize: 10, color: "#64748b", display: "block", textTransform: "uppercase" }}>Teams</span>
                                    <span style={{ fontSize: 18, fontWeight: 800 }}>{org.team_count}</span>
                                </div>
                            </div>

                            <div style={{ marginTop: "auto", display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 16, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                    {org.is_active ? 
                                        <><CheckCircle2 size={16} color="#10b981" /><span style={{ fontSize: 12, color: "#10b981", fontWeight: 600 }}>Active</span></> : 
                                        <><XCircle size={16} color="#ef4444" /><span style={{ fontSize: 12, color: "#ef4444", fontWeight: 600 }}>Suspended</span></>
                                    }
                                </div>
                                <div style={{ display: "flex", gap: 8 }}>
                                    <button onClick={() => toggleOrgActive(org.id, org.is_active)} className="glass" style={{ padding: "8px 12px", borderRadius: 8, fontSize: 11, fontWeight: 600 }}>
                                        {org.is_active ? "Suspend" : "Activate"}
                                    </button>
                                    <button onClick={() => router.push(`/dashboard?org=${org.id}`)} className="btn-primary" style={{ padding: "8px 12px", borderRadius: 8, fontSize: 11, fontWeight: 600 }}>
                                        Manage
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                    {organizations.length === 0 && (
                        <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 80, color: "#475569" }}>
                            <Globe size={48} style={{ margin: "0 auto 20px", opacity: 0.2 }} />
                            <p>No organizations found. Onboard your first client above.</p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}

function SidebarItem({ icon, label, active = false, onClick }: any) {
    return (
        <div onClick={onClick} style={{
            display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", borderRadius: 12, cursor: "pointer",
            transition: "all 0.2s",
            background: active ? "var(--primary)" : "transparent",
            color: active ? "white" : "#94a3b8",
            boxShadow: active ? "0 4px 12px rgba(79,70,229,0.3)" : "none",
            fontWeight: 600, fontSize: 14
        }}>
            {icon}
            <span>{label}</span>
        </div>
    );
}

function FormField({ label, value, onChange, placeholder, type = "text" }: any) {
    return (
        <div>
            <label style={labelStyle}>{label}</label>
            <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} required style={inputStyle} />
        </div>
    );
}

const labelStyle = { display: "block", fontSize: 11, color: "#64748b", marginBottom: 6, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 };
const inputStyle = { padding: "12px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, color: "#f0f0f3", fontSize: 14, width: "100%", outline: "none" };
