"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Activity, LayoutDashboard, Settings, LogOut, Users,
  FolderOpen, Download, Shield, ArrowLeft, MessageSquare, MessagesSquare
} from "lucide-react";

interface SidebarProps {
  user: {
    name: string;
    role: string;
    org_name?: string;
    org_id?: string;
  };
  onLogout: () => void;
  activePage?: string;
}

const SidebarItem = React.memo(({ icon, label, active = false, onClick }: {
  icon: any; label: string; active?: boolean; onClick?: () => void;
}) => (
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
));
SidebarItem.displayName = "SidebarItem";

export default function Sidebar({ user, onLogout, activePage }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();

  const role = user.role;
  const isAdmin = role === "admin" || role === "super_admin";
  const isTeamLead = role === "team_lead";
  const isEmployee = role === "employee";

  // Determine active page from prop or pathname
  const active = activePage || pathname;

  // Dashboard route depends on role
  const dashboardRoute = isEmployee ? "/my-dashboard" : "/dashboard";

  // Subtitle under logo
  const subtitle = role === "super_admin"
    ? "Platform Control"
    : user.org_name || "Personal Mode";

  return (
    <aside className="glass" style={{
      width: 240, margin: 16, marginRight: 0, padding: 24,
      display: "flex", flexDirection: "column", gap: 32, borderRadius: 20
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div className="primary-gradient" style={{
          width: 40, height: 40, borderRadius: 12,
          display: "flex", alignItems: "center", justifyContent: "center"
        }}>
          <Activity color="white" />
        </div>
        <div>
          <span style={{ fontSize: 20, fontWeight: 800, display: "block", letterSpacing: "-0.03em" }}>ProMe</span>
          <span style={{ fontSize: 11, color: "#64748b" }}>{subtitle}</span>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {/* Super admin: back to orgs */}
        {role === "super_admin" && (
          <SidebarItem
            icon={<ArrowLeft size={20} />}
            label="← Back to Orgs"
            onClick={() => router.push("/organizations")}
          />
        )}

        {/* Dashboard — all roles */}
        <SidebarItem
          icon={<LayoutDashboard size={20} />}
          label="Dashboard"
          active={active === "/dashboard" || active === "/my-dashboard"}
          onClick={() => router.push(dashboardRoute)}
        />

        {/* AI Assistant — all roles */}
        <SidebarItem
          icon={<MessageSquare size={20} />}
          label="AI Assistant"
          active={active === "/chat"}
          onClick={() => router.push("/chat")}
        />

        {/* Chatrooms — all roles */}
        <SidebarItem
          icon={<MessagesSquare size={20} />}
          label="Chatrooms"
          active={active === "/chatrooms"}
          onClick={() => router.push("/chatrooms")}
        />

        {/* Activity Logs — all roles */}
        <SidebarItem
          icon={<Activity size={20} />}
          label="Activity Logs"
          active={active === "/logs"}
          onClick={() => router.push("/logs")}
        />

        {/* Employees — team_lead, admin, super_admin only */}
        {(isAdmin || isTeamLead) && (
          <SidebarItem
            icon={<Users size={20} />}
            label="Employees"
            active={active === "/employees"}
            onClick={() => router.push("/dashboard")}
          />
        )}

        {/* Teams — admin, super_admin only */}
        {isAdmin && (
          <SidebarItem
            icon={<FolderOpen size={20} />}
            label="Teams"
            active={active === "/teams"}
            onClick={() => router.push("/teams")}
          />
        )}

        {/* Downloads — all roles */}
        <SidebarItem
          icon={<Download size={20} />}
          label="Downloads"
          active={active === "/download"}
          onClick={() => router.push("/download")}
        />

        {/* Settings — all roles */}
        <SidebarItem
          icon={<Settings size={20} />}
          label="Settings"
          active={active === "/settings"}
          onClick={() => router.push("/settings")}
        />
      </nav>

      {/* User section — bottom */}
      <div style={{ marginTop: "auto" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          marginBottom: 16, fontSize: 13, color: "#94a3b8"
        }}>
          <Shield size={16} />
          <span>{user.name}</span>
        </div>
        <SidebarItem icon={<LogOut size={20} />} label="Sign Out" onClick={onLogout} />
      </div>
    </aside>
  );
}
