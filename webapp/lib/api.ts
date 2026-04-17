const API_BASE_URL = "/api";

// ─── Auth ───────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("prome_token");
}

export function getUser(): any | null {
  if (typeof window === "undefined") return null;
  const u = localStorage.getItem("prome_user");
  return u ? JSON.parse(u) : null;
}

export function saveAuth(token: string, user: any) {
  localStorage.setItem("prome_token", token);
  localStorage.setItem("prome_user", JSON.stringify(user));
}

// Alias for login page compatibility
export const setToken = saveAuth;

export function clearAuth() {
  localStorage.removeItem("prome_token");
  localStorage.removeItem("prome_user");
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(username: string, password: string) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  saveAuth(data.token, data.user);
  return data;
}

export async function register(username: string, password: string, name: string) {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, name }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Registration failed");
  }
  const data = await res.json();
  saveAuth(data.token, data.user);
  return data;
}

// ─── Handshake / Invites ────────────────────────────────

export async function fetchMyInvites() {
  const res = await fetch(`${API_BASE_URL}/invites/my`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch invites");
  return res.json();
}

export async function acceptInvite(inviteId: string) {
  const res = await fetch(`${API_BASE_URL}/invites/${inviteId}/accept`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to accept invite");
  return res.json();
}

export async function declineInvite(inviteId: string) {
  const res = await fetch(`${API_BASE_URL}/invites/${inviteId}/decline`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to decline invite");
  return res.json();
}

export async function sendInvite(username: string) {
  const res = await fetch(`${API_BASE_URL}/invites/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ username }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to send invite");
  }
  return res.json();
}

export async function fetchMe() {
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

// ─── Data ───────────────────────────────────────────────

export async function fetchStats(date?: string) {
  const url = date ? `${API_BASE_URL}/stats/?date=${date}` : `${API_BASE_URL}/stats/`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function fetchActivity(opts: { date?: string; startDate?: string; endDate?: string; limit?: number; offset?: number } = {}) {
  const params = new URLSearchParams();
  if (opts.startDate && opts.endDate) {
    params.set("start_date", opts.startDate);
    params.set("end_date", opts.endDate);
  } else if (opts.date) {
    params.set("date", opts.date);
  }
  params.set("limit", String(opts.limit ?? 200));
  params.set("offset", String(opts.offset ?? 0));
  const res = await fetch(`${API_BASE_URL}/activity/?${params}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch activity");
  return res.json();
}

export async function fetchScreenshots() {
  const res = await fetch(`${API_BASE_URL}/screenshots/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch screenshots");
  return res.json();
}

// ─── Admin ──────────────────────────────────────────────

export async function fetchUsers(orgId?: string) {
  const url = orgId ? `${API_BASE_URL}/auth/users?org=${orgId}` : `${API_BASE_URL}/auth/users`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch users");
  return res.json();
}

export async function createUser(username: string, password: string, name: string, role: string, team_id?: string, org_id?: string) {
  const res = await fetch(`${API_BASE_URL}/auth/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ username, password, name, role, team_id: team_id || null, org_id: org_id || null }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create user");
  }
  return res.json();
}

// ─── Organizations (Super Admin Only) ───────────────────

export async function fetchOrganizations() {
  const res = await fetch(`${API_BASE_URL}/orgs/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch organizations");
  return res.json();
}

export async function fetchOrganizationDetails(orgId: string) {
  const res = await fetch(`${API_BASE_URL}/orgs/${orgId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch organization details");
  return res.json();
}

export async function createOrganization(name: string, slug: string, plan: string = "free", maxUsers: number = 50) {
  const res = await fetch(`${API_BASE_URL}/orgs/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, slug, plan, max_users: maxUsers }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create organization");
  }
  return res.json();
}

export async function updateOrganization(orgId: string, updates: any) {
  const res = await fetch(`${API_BASE_URL}/orgs/${orgId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update organization");
  return res.json();
}

// ─── Downloads ──────────────────────────────────────────

export function getDownloadUrl(type: 'windows' | 'cctv'): string {
  const token = getToken();
  return `${API_BASE_URL}/download/${type === 'windows' ? 'windows-agent' : 'cctv-agent'}?token=${token}`;
}

export async function downloadWindowsAgent(): Promise<void> {
  const url = getDownloadUrl('windows');
  window.location.assign(url);
}

export async function downloadCCTVAgent(): Promise<void> {
  const url = getDownloadUrl('cctv');
  window.location.assign(url);
}

export async function checkDownloadAvailable(): Promise<{ windows_agent: boolean; cctv_agent: boolean }> {
  const res = await fetch(`${API_BASE_URL}/download/check`);
  const data = await res.json();
  return {
    windows_agent: data.windows_agent || false,
    cctv_agent: data.cctv_agent || false,
  };
}

// ─── Teams ──────────────────────────────────────────────

export async function fetchTeams() {
  const res = await fetch(`${API_BASE_URL}/teams/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch teams");
  return res.json();
}

export async function createTeam(name: string, description?: string) {
  const res = await fetch(`${API_BASE_URL}/teams/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, description: description || "" }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create team");
  }
  return res.json();
}

export async function fetchTeamMembers(teamId: string) {
  const res = await fetch(`${API_BASE_URL}/teams/${teamId}/members`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch team members");
  return res.json();
}

export async function assignTeamMember(teamId: string, userId: string) {
  const res = await fetch(`${API_BASE_URL}/teams/${teamId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ user_id: userId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to assign member");
  }
  return res.json();
}

// ─── AI Chat ───────────────────────────────────────────────

export async function sendChatMessage(message: string, date?: string) {
  const res = await fetch(`${API_BASE_URL}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, date: date || undefined }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Chat request failed" }));
    throw new Error(err.detail || "Chat request failed");
  }
  return res.json();
}

// ─── Chatrooms ──────────────────────────────────────────────

export async function listChatrooms() {
  const res = await fetch(`${API_BASE_URL}/chatrooms/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch chatrooms");
  return res.json();
}

export async function createChatroom(name: string, description?: string) {
  const res = await fetch(`${API_BASE_URL}/chatrooms/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, description: description || "" }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create chatroom");
  }
  return res.json();
}

export async function getChatroom(chatroomId: string) {
  const res = await fetch(`${API_BASE_URL}/chatrooms/${chatroomId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch chatroom");
  return res.json();
}

export async function getChatroomMessages(chatroomId: string, limit: number = 100, offset: number = 0) {
  const url = new URL(`${API_BASE_URL}/chatrooms/${chatroomId}/messages`);
  url.searchParams.set("limit", String(limit));
  url.searchParams.set("offset", String(offset));
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

export async function updateChatroom(chatroomId: string, updates: any) {
  const res = await fetch(`${API_BASE_URL}/chatrooms/${chatroomId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update chatroom");
  return res.json();
}

export async function deleteChatroom(chatroomId: string) {
  const res = await fetch(`${API_BASE_URL}/chatrooms/${chatroomId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete chatroom");
  return res.json();
}

export async function saveConversation(chatroomId: string, messages: any[]) {
  const res = await fetch(`${API_BASE_URL}/chatrooms/${chatroomId}/save-conversation`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ chatroom_id: chatroomId, messages }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to save conversation");
  }
  return res.json();
}
