"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getUser, clearAuth, sendChatMessage, listChatrooms, createChatroom, getChatroomMessages, saveConversation } from "../../lib/api";
import {
  Activity, Send,
  MessageSquare, Plus, Sparkles, BarChart3, Clock,
  Keyboard, MousePointer2, Monitor, Bot, User,
} from "lucide-react";
import React from "react";
import Sidebar from "../../components/Sidebar";

// ── Mock AI Response Generator ──

interface ChartData {
  label: string;
  value: number;
  color: string;
}

interface AIResponse {
  text: string;
  charts?: { title: string; type: "bar" | "pie" | "metric"; data: ChartData[] }[];
  metrics?: { label: string; value: string; change?: string; icon: string }[];
  error?: string;
}

function generateMockResponse(question: string): AIResponse {
  const q = question.toLowerCase();

  if (q.includes("keystroke") || q.includes("typing") || q.includes("keyboard")) {
    return {
      text: "Here's your keystroke analysis for today. You've been most active during the morning hours, with a significant typing burst between 10-11 AM. Your typing speed has improved by 12% compared to last week.",
      metrics: [
        { label: "Total Keystrokes", value: "15,432", change: "+12%", icon: "keyboard" },
        { label: "Peak Hour", value: "10:00 AM", icon: "clock" },
        { label: "Avg Speed", value: "82 WPM", change: "+5%", icon: "sparkles" },
      ],
      charts: [{
        title: "Keystrokes by Hour",
        type: "bar",
        data: [
          { label: "8AM", value: 420, color: "#4f46e5" },
          { label: "9AM", value: 1250, color: "#4f46e5" },
          { label: "10AM", value: 2800, color: "#10b981" },
          { label: "11AM", value: 2100, color: "#4f46e5" },
          { label: "12PM", value: 890, color: "#4f46e5" },
          { label: "1PM", value: 450, color: "#f59e0b" },
          { label: "2PM", value: 1900, color: "#4f46e5" },
          { label: "3PM", value: 2200, color: "#4f46e5" },
          { label: "4PM", value: 1800, color: "#4f46e5" },
          { label: "5PM", value: 622, color: "#4f46e5" },
        ],
      }],
    };
  }

  if (q.includes("productive") || q.includes("productivity") || q.includes("score")) {
    return {
      text: "Your productivity score today is **87%**, which is above your weekly average of 79%. The biggest contributor is your focused coding sessions in VS Code. You had 3 deep work sessions lasting over 45 minutes each.\n\n**Key Insight:** Your productivity drops significantly after lunch — consider taking a short walk before resuming work.",
      metrics: [
        { label: "Productivity Score", value: "87%", change: "+8%", icon: "sparkles" },
        { label: "Deep Work Sessions", value: "3", change: "+1", icon: "monitor" },
        { label: "Focus Time", value: "4h 23m", icon: "clock" },
        { label: "Distractions", value: "12", change: "-3", icon: "mousepointer" },
      ],
      charts: [{
        title: "Productivity by App Category",
        type: "pie",
        data: [
          { label: "Coding (VS Code)", value: 45, color: "#4f46e5" },
          { label: "Communication (Slack)", value: 18, color: "#f59e0b" },
          { label: "Browsing (Chrome)", value: 22, color: "#06b6d4" },
          { label: "Documents", value: 10, color: "#10b981" },
          { label: "Other", value: 5, color: "#64748b" },
        ],
      }],
    };
  }

  if (q.includes("app") || q.includes("application") || q.includes("window") || q.includes("using")) {
    return {
      text: "Here's your application usage breakdown for today. **VS Code** dominates with 4+ hours, followed by Chrome and Slack. You switched between applications 47 times today, which is 15% less than yesterday — nice improvement in focus!",
      metrics: [
        { label: "Total Apps Used", value: "8", icon: "monitor" },
        { label: "App Switches", value: "47", change: "-15%", icon: "sparkles" },
        { label: "Top App", value: "VS Code", icon: "monitor" },
      ],
      charts: [{
        title: "Time Spent per Application",
        type: "bar",
        data: [
          { label: "VS Code", value: 265, color: "#4f46e5" },
          { label: "Chrome", value: 98, color: "#06b6d4" },
          { label: "Slack", value: 67, color: "#f59e0b" },
          { label: "Terminal", value: 45, color: "#10b981" },
          { label: "Figma", value: 32, color: "#a855f7" },
          { label: "Notion", value: 18, color: "#ec4899" },
        ],
      }],
    };
  }

  if (q.includes("click") || q.includes("mouse")) {
    return {
      text: "Your mouse activity shows **5,104 clicks** today. Right clicks make up about 8% of total clicks. Your most click-intensive app is Chrome (likely form filling and navigation), followed by Figma.",
      metrics: [
        { label: "Total Clicks", value: "5,104", icon: "mousepointer" },
        { label: "Right Clicks", value: "408", icon: "mousepointer" },
        { label: "Mouse Distance", value: "2.3 km", icon: "sparkles" },
      ],
      charts: [{
        title: "Clicks by Application",
        type: "bar",
        data: [
          { label: "Chrome", value: 1890, color: "#06b6d4" },
          { label: "Figma", value: 1240, color: "#a855f7" },
          { label: "VS Code", value: 980, color: "#4f46e5" },
          { label: "Slack", value: 560, color: "#f59e0b" },
          { label: "Other", value: 434, color: "#64748b" },
        ],
      }],
    };
  }

  if (q.includes("team") || q.includes("employee") || q.includes("compare")) {
    return {
      text: "Here's how your team performed this week. **Sarah** leads in productivity score, while **Mike** has shown the biggest improvement (+18%). The team average productivity is 76%, up from 71% last week.\n\n**Action Item:** John seems to be struggling — consider checking in with him.",
      metrics: [
        { label: "Team Avg Score", value: "76%", change: "+5%", icon: "sparkles" },
        { label: "Most Improved", value: "Mike", change: "+18%", icon: "sparkles" },
        { label: "Team Size", value: "5", icon: "monitor" },
      ],
      charts: [{
        title: "Team Productivity Scores",
        type: "bar",
        data: [
          { label: "Sarah", value: 92, color: "#10b981" },
          { label: "You", value: 87, color: "#4f46e5" },
          { label: "Mike", value: 81, color: "#06b6d4" },
          { label: "Lisa", value: 74, color: "#f59e0b" },
          { label: "John", value: 48, color: "#ef4444" },
        ],
      }],
    };
  }

  if (q.includes("summary") || q.includes("today") || q.includes("overview") || q.includes("how am i")) {
    return {
      text: "Here's your day at a glance:\n\n- **Active Time:** 7h 12m (started at 8:47 AM)\n- **Most Used App:** VS Code (4h 25m)\n- **Keystrokes:** 15,432 across 8 applications\n- **Mouse Clicks:** 5,104\n- **Window Switches:** 47\n- **Screenshots Taken:** 14\n\nYou had a strong morning with 3 deep work sessions. Afternoon was more fragmented with frequent app switching. Overall a productive day!",
      metrics: [
        { label: "Active Time", value: "7h 12m", icon: "clock" },
        { label: "Keystrokes", value: "15,432", icon: "keyboard" },
        { label: "Clicks", value: "5,104", icon: "mousepointer" },
        { label: "Productivity", value: "87%", change: "+8%", icon: "sparkles" },
      ],
    };
  }

  // Default response
  return {
    text: "I can help you analyze your productivity data! Here are some things you can ask me:\n\n- **\"How productive am I today?\"** — Get your productivity score with insights\n- **\"Show my keystroke analysis\"** — Detailed typing patterns\n- **\"What apps am I using most?\"** — Application usage breakdown\n- **\"Show my mouse activity\"** — Click patterns and mouse stats\n- **\"How is my team doing?\"** — Team comparison and insights\n- **\"Give me a summary of today\"** — Full day overview\n\nI analyze your ProMe tracking data to give you actionable insights with charts and metrics.",
  };
}

// ── Components ──

function BarChartInline({ data, title }: { data: ChartData[]; title: string }) {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div style={{ marginTop: 16 }}>
      <h4 style={{ fontSize: 13, fontWeight: 700, color: "#94a3b8", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>{title}</h4>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {data.map((d, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ width: 80, fontSize: 12, color: "#94a3b8", textAlign: "right", flexShrink: 0 }}>{d.label}</span>
            <div style={{ flex: 1, height: 24, background: "rgba(255,255,255,0.04)", borderRadius: 6, overflow: "hidden" }}>
              <div style={{
                width: `${(d.value / max) * 100}%`, height: "100%",
                background: `linear-gradient(90deg, ${d.color}, ${d.color}aa)`,
                borderRadius: 6, transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
                display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 8,
              }}>
                <span style={{ fontSize: 10, color: "white", fontWeight: 700 }}>{d.value.toLocaleString()}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PieChartInline({ data, title }: { data: ChartData[]; title: string }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  let cumPercent = 0;

  return (
    <div style={{ marginTop: 16 }}>
      <h4 style={{ fontSize: 13, fontWeight: 700, color: "#94a3b8", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>{title}</h4>
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        {/* Simple ring chart using conic-gradient */}
        <div style={{
          width: 120, height: 120, borderRadius: "50%", flexShrink: 0,
          background: `conic-gradient(${data.map(d => {
            const start = cumPercent;
            cumPercent += (d.value / total) * 100;
            return `${d.color} ${start}% ${cumPercent}%`;
          }).join(", ")})`,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{ width: 70, height: 70, borderRadius: "50%", background: "#16161a", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 16, fontWeight: 800, color: "#e2e8f0" }}>{total}%</span>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {data.map((d, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
              <div style={{ width: 10, height: 10, borderRadius: 3, background: d.color, flexShrink: 0 }} />
              <span style={{ color: "#cbd5e1" }}>{d.label}</span>
              <span style={{ color: "#64748b", marginLeft: "auto" }}>{d.value}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricCards({ metrics }: { metrics: AIResponse["metrics"] }) {
  if (!metrics) return null;

  const iconMap: Record<string, React.ReactNode> = {
    keyboard: <Keyboard size={18} color="#4f46e5" />,
    clock: <Clock size={18} color="#a855f7" />,
    sparkles: <Sparkles size={18} color="#10b981" />,
    monitor: <Monitor size={18} color="#06b6d4" />,
    mousepointer: <MousePointer2 size={18} color="#f59e0b" />,
  };

  return (
    <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
      {metrics.map((m, i) => (
        <div key={i} style={{
          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 12, padding: "12px 16px", flex: "1 1 140px", minWidth: 140,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            {iconMap[m.icon] || <Activity size={18} color="#64748b" />}
            <span style={{ fontSize: 11, color: "#64748b", fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>{m.label}</span>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontSize: 22, fontWeight: 800, color: "#e2e8f0" }}>{m.value}</span>
            {m.change && (
              <span style={{ fontSize: 12, fontWeight: 600, color: m.change.startsWith("+") ? "#10b981" : "#ef4444" }}>{m.change}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function MessageBubble({ role, content, response }: { role: "user" | "ai"; content: string; response?: AIResponse }) {
  if (role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
        <div style={{
          maxWidth: "70%", padding: "12px 18px",
          background: "var(--primary)", borderRadius: "18px 18px 4px 18px",
          color: "white", fontSize: 14, lineHeight: 1.6,
        }}>
          {content}
        </div>
        <div style={{
          width: 32, height: 32, borderRadius: "50%", background: "rgba(79,70,229,0.2)",
          display: "flex", alignItems: "center", justifyContent: "center", marginLeft: 8, flexShrink: 0,
        }}>
          <User size={16} color="#818cf8" />
        </div>
      </div>
    );
  }

  // Check if response contains an error (parsing or formatting issue)
  const hasError = response?.error && response.text?.startsWith("{");
  const displayText = hasError ? "I encountered an issue formatting my response properly. The AI service returned data I couldn't parse. Please try rephrasing your question." : response?.text;

  // AI message with rich content
  return (
    <div style={{ display: "flex", marginBottom: 24 }}>
      <div style={{
        width: 32, height: 32, borderRadius: "50%",
        background: hasError
          ? "linear-gradient(135deg, #ef4444, #f97316)"
          : "linear-gradient(135deg, #4f46e5, #a855f7)",
        display: "flex", alignItems: "center", justifyContent: "center", marginRight: 12, flexShrink: 0,
      }}>
        <Bot size={16} color="white" />
      </div>
      <div style={{ flex: 1, maxWidth: "85%" }}>
        {/* Text with basic markdown-like rendering */}
        <div style={{
          padding: "16px 20px", background: hasError ? "rgba(239,68,68,0.1)" : "rgba(255,255,255,0.03)",
          border: hasError ? "1px solid rgba(239,68,68,0.3)" : "1px solid rgba(255,255,255,0.06)",
          borderRadius: "4px 18px 18px 18px",
          fontSize: 14, lineHeight: 1.7, color: hasError ? "#fca5a5" : "#cbd5e1",
        }}>
          {displayText?.split("\n").map((line, i) => {
            // Bold text
            const parts = line.split(/(\*\*.*?\*\*)/g);
            return (
              <p key={i} style={{ marginBottom: line === "" ? 8 : 4, minHeight: line === "" ? 8 : undefined }}>
                {parts.map((part, j) => {
                  if (part.startsWith("**") && part.endsWith("**")) {
                    return <strong key={j} style={{ color: hasError ? "#fca5a5" : "#e2e8f0", fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
                  }
                  if (part.startsWith("- ")) {
                    return <span key={j}>• {part.slice(2)}</span>;
                  }
                  return <span key={j}>{part}</span>;
                })}
              </p>
            );
          })}
          {hasError && (
            <p style={{ marginTop: 12, fontSize: 12, color: "#f87171" }}>
              Error: {response?.error}
            </p>
          )}
        </div>

        {/* Metric cards - only show if no error */}
        {!hasError && response?.metrics && <MetricCards metrics={response.metrics} />}

        {/* Charts - only show if no error */}
        {!hasError && response?.charts?.map((chart, i) => (
          <div key={i} style={{
            marginTop: 16, padding: 20, background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14,
          }}>
            {chart.type === "bar" && <BarChartInline data={chart.data} title={chart.title} />}
            {chart.type === "pie" && <PieChartInline data={chart.data} title={chart.title} />}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  response?: AIResponse;
}

const SUGGESTIONS = [
  "How productive am I today?",
  "Show my keystroke analysis",
  "What apps am I using most?",
  "Give me a summary of today",
  "How is my team doing?",
  "Show my mouse activity",
];

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [user, setUser] = useState<any>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [mounted, setMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Chatroom state
  const [chatrooms, setChatrooms] = useState<any[]>([]);
  const [selectedChatroom, setSelectedChatroom] = useState<string | null>(null);
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [newRoomName, setNewRoomName] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/login"); return; }
    setUser(u);

    // Load chatrooms
    async function loadChatrooms() {
      try {
        const rooms = await listChatrooms();
        setChatrooms(rooms);

        // Check if room_id from URL params
        const roomFromUrl = searchParams.get("room");
        if (roomFromUrl) {
          setSelectedChatroom(roomFromUrl);
          // Load messages from that chatroom
          const msgData = await getChatroomMessages(roomFromUrl);
          if (msgData.messages && msgData.messages.length > 0) {
            setMessages(msgData.messages.map((m: any) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              response: m.response_data
            })));
          }
        }
      } catch (err) {
        console.error("Failed to load chatrooms:", err);
      }
    }
    loadChatrooms();
  }, [router, searchParams]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Load messages when chatroom is selected
  useEffect(() => {
    if (selectedChatroom) {
      (async () => {
        try {
          const msgData = await getChatroomMessages(selectedChatroom);
          if (msgData.messages && msgData.messages.length > 0) {
            setMessages(msgData.messages.map((m: any) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              response: m.response_data
            })));
          } else {
            // Clear messages if chatroom is empty
            setMessages([]);
          }
        } catch (err) {
          console.error("Failed to load chatroom messages:", err);
        }
      })();
    }
  }, [selectedChatroom]);

  const [isLive, setIsLive] = useState(false);

  async function handleSend(text?: string) {
    const msg = text || input.trim();
    if (!msg || isTyping) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: msg };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      // Auto-create chatroom if none selected
      let chatroomId = selectedChatroom;
      if (!chatroomId) {
        const now = new Date();
        const roomName = `Chat - ${now.toLocaleDateString()} ${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
        const newRoom = await createChatroom(roomName, "Auto-created chat");
        chatroomId = newRoom.id;
        setSelectedChatroom(chatroomId);
        setChatrooms(prev => [newRoom, ...prev]);
      }

      // Try real API first
      const response = await sendChatMessage(msg);
      setIsLive(true);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(), role: "ai",
        content: response.text, response,
      };
      setMessages(prev => [...prev, aiMsg]);

      // Auto-save messages to chatroom
      if (chatroomId) {
        await saveConversation(chatroomId, [
          { role: "user", content: msg },
          { role: "ai", content: response.text, response_data: response }
        ]);
      }
    } catch (err: any) {
      console.warn("Live chat failed, falling back to mock:", err.message);
      // Fallback to mock if API is down
      await new Promise(r => setTimeout(r, 600));
      const response = generateMockResponse(msg);
      setIsLive(false);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(), role: "ai",
        content: response.text, response,
      };
      setMessages(prev => [...prev, aiMsg]);

      // Auto-save with mock response too
      if (selectedChatroom) {
        try {
          await saveConversation(selectedChatroom, [
            { role: "user", content: msg },
            { role: "ai", content: response.text, response_data: response }
          ]);
        } catch (saveErr) {
          console.error("Failed to auto-save:", saveErr);
        }
      }
    } finally {
      setIsTyping(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleLogout() { clearAuth(); router.push("/login"); }

  async function handleCreateRoom() {
    if (!newRoomName.trim()) return;
    try {
      const newRoom = await createChatroom(newRoomName);
      setChatrooms([...chatrooms, newRoom]);
      setSelectedChatroom(newRoom.id);
      setNewRoomName("");
      setShowCreateRoom(false);
    } catch (err) {
      console.error("Failed to create chatroom:", err);
    }
  }

  async function handleSaveConversation() {
    if (!selectedChatroom) {
      alert("Please select or create a chatroom first");
      return;
    }
    setIsSaving(true);
    try {
      const msgsToSave = messages.map(m => ({
        role: m.role,
        content: m.content,
        response_data: m.response
      }));
      await saveConversation(selectedChatroom, msgsToSave);
      alert("✅ Conversation saved!");
    } catch (err) {
      alert(`❌ Failed to save: ${err}`);
    } finally {
      setIsSaving(false);
    }
  }

  if (!mounted) return <div style={{ minHeight: "100vh", background: "var(--background)" }} />;

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* Shared Sidebar */}
      {user && <Sidebar user={user} onLogout={handleLogout} activePage="/chat" />}

      {/* Main Chat Area */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh" }}>

        {/* Chat Header */}
        <div style={{
          padding: "16px 32px", borderBottom: "1px solid rgba(255,255,255,0.06)",
          display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap"
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg, #4f46e5, #a855f7)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Sparkles size={18} color="white" />
          </div>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#e2e8f0" }}>ProMe AI Assistant</h2>
            <p style={{ fontSize: 11, color: "#64748b" }}>
              {selectedChatroom ? `📁 ${chatrooms.find(r => r.id === selectedChatroom)?.name || "Chatroom"}` : "No chatroom selected"}
            </p>
          </div>

          {/* Chatroom Selector */}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <select
              value={selectedChatroom || ""} onChange={(e) => setSelectedChatroom(e.target.value || null)}
              style={{
                padding: "6px 10px", background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6,
                color: "#cbd5e1", fontSize: 12, cursor: "pointer"
              }}
            >
              <option value="">Select chatroom...</option>
              {chatrooms.map(room => (
                <option key={room.id} value={room.id}>{room.name}</option>
              ))}
            </select>

            <button
              onClick={() => setShowCreateRoom(!showCreateRoom)}
              style={{
                padding: "6px 12px", background: "rgba(79,70,229,0.2)",
                border: "1px solid var(--primary)", borderRadius: 6,
                color: "#818cf8", fontSize: 11, cursor: "pointer", fontWeight: 600
              }}
            >
              + New
            </button>

            {selectedChatroom && (
              <div style={{
                padding: "6px 12px", background: "rgba(16,185,129,0.15)",
                border: "1px solid #10b981", borderRadius: 6,
                color: "#10b981", fontSize: 11, fontWeight: 600
              }}>
                ✓ Auto-saving
              </div>
            )}

            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: isLive ? "#10b981" : "#f59e0b" }} />
              <span style={{ fontSize: 12, color: "#64748b" }}>{isLive ? "Live" : "Mock"}</span>
            </div>
          </div>
        </div>

        {/* Create Room Form */}
        {showCreateRoom && (
          <div style={{
            padding: "12px 32px", background: "rgba(255,255,255,0.02)",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            display: "flex", gap: 8, alignItems: "center"
          }}>
            <input
              type="text" placeholder="New chatroom name"
              value={newRoomName} onChange={(e) => setNewRoomName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreateRoom()}
              style={{
                flex: 1, padding: "8px 12px", background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6,
                color: "#e2e8f0", fontSize: 12
              }}
            />
            <button
              onClick={handleCreateRoom}
              style={{
                padding: "8px 16px", background: "var(--primary)",
                color: "white", border: "none", borderRadius: 6,
                fontSize: 12, cursor: "pointer", fontWeight: 600
              }}
            >
              Create
            </button>
            <button
              onClick={() => setShowCreateRoom(false)}
              style={{
                padding: "8px 16px", background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6,
                color: "#cbd5e1", fontSize: 12, cursor: "pointer"
              }}
            >
              Cancel
            </button>
          </div>
        )}

        {/* Messages Area */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
          {messages.length === 0 ? (
            /* Empty State */
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 24 }}>
              <div style={{
                width: 72, height: 72, borderRadius: 20,
                background: "linear-gradient(135deg, #4f46e5, #a855f7)",
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: "0 8px 32px rgba(79,70,229,0.3)",
              }}>
                <Sparkles size={32} color="white" />
              </div>
              <div style={{ textAlign: "center" }}>
                <h2 style={{ fontSize: 24, fontWeight: 800, color: "#e2e8f0", marginBottom: 8 }}>
                  What would you like to know?
                </h2>
                <p style={{ color: "#64748b", fontSize: 14, maxWidth: 400 }}>
                  I can analyze your productivity data, show insights with charts, and help you understand your work patterns.
                </p>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 600, marginTop: 8 }}>
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} onClick={() => handleSend(s)} style={{
                    padding: "10px 18px", background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12,
                    color: "#cbd5e1", fontSize: 13, cursor: "pointer",
                    transition: "all 0.2s", fontWeight: 500,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--primary)"; e.currentTarget.style.color = "white"; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)"; e.currentTarget.style.color = "#cbd5e1"; }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Message List */
            <>
              {messages.map(msg => (
                <MessageBubble key={msg.id} role={msg.role} content={msg.content} response={msg.response} />
              ))}
              {isTyping && (
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: "50%",
                    background: "linear-gradient(135deg, #4f46e5, #a855f7)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Bot size={16} color="white" />
                  </div>
                  <div style={{
                    padding: "12px 20px", background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)", borderRadius: "4px 18px 18px 18px",
                    display: "flex", gap: 6,
                  }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4f46e5", animation: "pulse 1s infinite" }} />
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4f46e5", animation: "pulse 1s infinite 0.2s" }} />
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4f46e5", animation: "pulse 1s infinite 0.4s" }} />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Bar */}
        <div style={{ padding: "16px 32px 24px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 12,
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 16, padding: "4px 4px 4px 20px",
            transition: "border-color 0.2s",
          }}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your productivity..."
              style={{
                flex: 1, background: "none", border: "none", outline: "none",
                color: "#e2e8f0", fontSize: 14, padding: "12px 0",
              }}
            />
            <button onClick={() => handleSend()} disabled={!input.trim() || isTyping} style={{
              width: 40, height: 40, borderRadius: 12, border: "none",
              background: input.trim() ? "var(--primary)" : "rgba(255,255,255,0.04)",
              color: input.trim() ? "white" : "#475569",
              cursor: input.trim() ? "pointer" : "default",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s",
            }}>
              <Send size={18} />
            </button>
          </div>
          <p style={{ textAlign: "center", fontSize: 11, color: "#475569", marginTop: 8 }}>
            ProMe AI uses your tracked data to provide personalized insights. {isLive ? "Powered by Gemini." : "API offline — using mock mode."}
          </p>
        </div>
      </main>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", background: "var(--background)" }} />}>
      <ChatPageContent />
    </Suspense>
  );
}
