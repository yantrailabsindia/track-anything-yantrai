"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getUser, clearAuth, listChatrooms, createChatroom, deleteChatroom, getChatroomMessages } from "../../lib/api";
import {
  Activity, MessageSquare, Plus, ArrowLeft, LogOut, Trash2, Eye, ChevronDown
} from "lucide-react";
import Link from "next/link";

interface ChatroomItem {
  id: string;
  name: string;
  description: string;
  created_at: string;
  message_count: number;
}

export default function ChatroomsPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [chatrooms, setChatrooms] = useState<ChatroomItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [msg, setMsg] = useState("");
  const [expandedRoom, setExpandedRoom] = useState<string | null>(null);
  const [roomMessages, setRoomMessages] = useState<any>(null);
  const [loadingMessages, setLoadingMessages] = useState(false);

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    setUser(u);

    async function load() {
      try {
        const rooms = await listChatrooms();
        setChatrooms(rooms);
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
    if (!newName.trim()) {
      setMsg("❌ Chatroom name is required");
      return;
    }
    try {
      await createChatroom(newName, newDesc);
      setMsg("✅ Chatroom created!");
      setNewName(""); setNewDesc(""); setShowCreate(false);
      const rooms = await listChatrooms();
      setChatrooms(rooms);
      setTimeout(() => setMsg(""), 3000);
    } catch (err: any) {
      setMsg(`❌ ${err.message}`);
    }
  }

  async function handleDelete(roomId: string) {
    if (!window.confirm("Are you sure you want to delete this chatroom? This cannot be undone.")) return;
    try {
      await deleteChatroom(roomId);
      setMsg("✅ Chatroom deleted!");
      const rooms = await listChatrooms();
      setChatrooms(rooms);
      setExpandedRoom(null);
      setTimeout(() => setMsg(""), 3000);
    } catch (err: any) {
      setMsg(`❌ ${err.message}`);
    }
  }

  async function handleToggleMessages(roomId: string) {
    if (expandedRoom === roomId) {
      setExpandedRoom(null);
      setRoomMessages(null);
      return;
    }

    setExpandedRoom(roomId);
    setLoadingMessages(true);
    try {
      const msgs = await getChatroomMessages(roomId);
      setRoomMessages(msgs);
    } catch (err: any) {
      setMsg(`❌ Failed to load messages: ${err.message}`);
    } finally {
      setLoadingMessages(false);
    }
  }

  if (loading) return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <Activity size={48} color="var(--primary)" />
    </div>
  );

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
              <span className="text-gradient">My Chatrooms</span>
            </h1>
            <p style={{ color: "#64748b", fontSize: 13 }}>Organize and manage your AI conversations</p>
          </div>
        </div>
        <button
          onClick={() => { clearAuth(); router.push("/login"); }}
          style={{
            padding: "8px 16px", background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8,
            color: "#cbd5e1", cursor: "pointer", fontSize: 13, display: "flex", alignItems: "center", gap: 8
          }}
        >
          <LogOut size={16} /> Logout
        </button>
      </header>

      {/* Message */}
      {msg && (
        <div style={{
          padding: 12, marginBottom: 20, borderRadius: 8,
          background: msg.includes("✅") ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
          color: msg.includes("✅") ? "#10b981" : "#ef4444",
          fontSize: 13
        }}>
          {msg}
        </div>
      )}

      {/* Create Button */}
      <div style={{ marginBottom: 32 }}>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            padding: "12px 20px", background: "var(--primary)",
            color: "white", border: "none", borderRadius: 12,
            fontSize: 14, fontWeight: 600, cursor: "pointer",
            display: "flex", alignItems: "center", gap: 8
          }}
        >
          <Plus size={18} /> New Chatroom
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="glass" style={{ padding: 24, marginBottom: 32, borderRadius: 12 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: "#e2e8f0" }}>Create New Chatroom</h3>
          <form onSubmit={handleCreate}>
            <input
              type="text" placeholder="Chatroom name"
              value={newName} onChange={e => setNewName(e.target.value)}
              style={{
                width: "100%", padding: "10px 12px", marginBottom: 12,
                background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 8, color: "#e2e8f0", fontSize: 14
              }}
            />
            <textarea
              placeholder="Description (optional)"
              value={newDesc} onChange={e => setNewDesc(e.target.value)}
              style={{
                width: "100%", padding: "10px 12px", marginBottom: 16,
                background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 8, color: "#e2e8f0", fontSize: 14, minHeight: 80, fontFamily: "inherit"
              }}
            />
            <div style={{ display: "flex", gap: 12 }}>
              <button
                type="submit"
                style={{
                  padding: "10px 20px", background: "var(--primary)",
                  color: "white", border: "none", borderRadius: 8,
                  fontSize: 13, fontWeight: 600, cursor: "pointer"
                }}
              >
                Create
              </button>
              <button
                type="button" onClick={() => setShowCreate(false)}
                style={{
                  padding: "10px 20px", background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8,
                  color: "#cbd5e1", fontSize: 13, cursor: "pointer"
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Chatrooms List */}
      {chatrooms.length === 0 ? (
        <div style={{
          textAlign: "center", padding: 60, background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12
        }}>
          <MessageSquare size={48} color="#64748b" style={{ marginBottom: 16 }} />
          <p style={{ color: "#64748b", fontSize: 14 }}>No chatrooms yet. Create one to get started!</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {chatrooms.map(room => (
            <div key={room.id} style={{
              background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 12, overflow: "hidden"
            }}>
              {/* Room Header */}
              <div style={{
                padding: 16, display: "flex", alignItems: "center", justifyContent: "space-between",
                cursor: "pointer", background: expandedRoom === room.id ? "rgba(255,255,255,0.04)" : "transparent"
              }}
              onClick={() => handleToggleMessages(room.id)}
              >
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 700, color: "#e2e8f0", marginBottom: 4 }}>
                    {room.name}
                  </h3>
                  {room.description && (
                    <p style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>{room.description}</p>
                  )}
                  <p style={{ fontSize: 11, color: "#64748b" }}>
                    {room.message_count} messages • {new Date(room.created_at).toLocaleDateString()}
                  </p>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <button
                    onClick={(e) => { e.stopPropagation(); router.push(`/chat?room=${room.id}`); }}
                    style={{
                      padding: "8px 12px", background: "var(--primary)",
                      color: "white", border: "none", borderRadius: 6,
                      fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 4
                    }}
                  >
                    <Eye size={14} /> Open
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(room.id); }}
                    style={{
                      padding: "8px 12px", background: "rgba(239,68,68,0.1)",
                      color: "#ef4444", border: "none", borderRadius: 6,
                      fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 4
                    }}
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                  <ChevronDown
                    size={16} color="#64748b"
                    style={{ transform: expandedRoom === room.id ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
                  />
                </div>
              </div>

              {/* Messages Preview */}
              {expandedRoom === room.id && (
                <div style={{
                  padding: 16, borderTop: "1px solid rgba(255,255,255,0.06)",
                  background: "rgba(255,255,255,0.01)", maxHeight: 400, overflowY: "auto"
                }}>
                  {loadingMessages ? (
                    <p style={{ color: "#64748b", fontSize: 12 }}>Loading messages...</p>
                  ) : roomMessages?.messages?.length === 0 ? (
                    <p style={{ color: "#64748b", fontSize: 12 }}>No messages in this chatroom yet.</p>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      {roomMessages?.messages?.map((msg: any, i: number) => (
                        <div key={i} style={{
                          padding: 12, background: msg.role === "user" ? "rgba(79,70,229,0.1)" : "rgba(255,255,255,0.03)",
                          borderRadius: 8, borderLeft: `3px solid ${msg.role === "user" ? "var(--primary)" : "#64748b"}`
                        }}>
                          <p style={{ fontSize: 10, color: "#94a3b8", marginBottom: 4, textTransform: "uppercase", fontWeight: 600 }}>
                            {msg.role === "user" ? "You" : "AI"}
                          </p>
                          <p style={{ fontSize: 12, color: "#cbd5e1", lineHeight: 1.5 }}>
                            {msg.content.length > 100 ? msg.content.substring(0, 100) + "..." : msg.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
