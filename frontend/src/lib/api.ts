const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  } else if (DEMO_MODE) {
    headers["Authorization"] = "Bearer demo-token"
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }))
    throw new Error(error.detail || "Request failed")
  }

  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}

export const api = {
  auth: {
    githubLogin: () => request<{ url: string; state: string }>("/auth/github"),
    githubCallback: (code: string, state: string) =>
      request<{ access_token: string; user: User }>(
        `/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
      ),
    login: (body: Record<string, string>) =>
      request<{ access_token: string; user: User }>("/auth/login", {
        method: "POST",
        body,
      }),
    register: (body: Record<string, string>) =>
      request<{ access_token: string; user: User }>("/auth/register", {
        method: "POST",
        body,
      }),
    me: () => request<User>("/auth/me"),
    logout: () => request("/auth/logout", { method: "POST" }),
  },

  boards: {
    list: () => request<{ boards: Board[] }>("/boards"),
    create: (data: { name: string; description?: string }) =>
      request<Board>("/boards", { method: "POST", body: data }),
    get: (id: string) => request<Board>(`/boards/${id}`),
    update: (id: string, data: { name?: string; description?: string }) =>
      request<Board>(`/boards/${id}`, { method: "PUT", body: data }),
    delete: (id: string) => request<void>(`/boards/${id}`, { method: "DELETE" }),
  },

  agents: {
    list: (boardId?: string) =>
      request<{ agents: Agent[] }>(`/agents${boardId ? `?board_id=${boardId}` : ""}`),
    create: (data: {
      name: string
      system_prompt: string
      description?: string
      board_id?: string
      config?: Record<string, unknown>
    }) => request<Agent>("/agents", { method: "POST", body: data }),
    get: (id: string) => request<Agent>(`/agents/${id}`),
    update: (id: string, data: Partial<Agent>) =>
      request<Agent>(`/agents/${id}`, { method: "PUT", body: data }),
    delete: (id: string) => request<void>(`/agents/${id}`, { method: "DELETE" }),
  },

  teams: {
    list: (boardId?: string) =>
      request<{ teams: Team[] }>(`/teams${boardId ? `?board_id=${boardId}` : ""}`),
    create: (data: {
      name: string
      description?: string
      board_id?: string
      members?: TeamMembers
      orchestrator?: TeamOrchestrator
    }) => request<Team>("/teams", { method: "POST", body: data }),
    get: (id: string) => request<Team>(`/teams/${id}`),
    update: (id: string, data: Partial<{
      name: string
      description: string
      members: TeamMembers
      orchestrator: TeamOrchestrator
    }>) => request<Team>(`/teams/${id}`, { method: "PUT", body: data }),
    delete: (id: string) => request<void>(`/teams/${id}`, { method: "DELETE" }),
  },

  generations: {
    list: (boardId: string) =>
      request<{ generations: Generation[] }>(`/generations?board_id=${boardId}`),
    get: (id: string) => request<Generation>(`/generations/${id}`),
    delete: (id: string) => request<void>(`/generations/${id}`, { method: "DELETE" }),
  },

  billing: {
    status: () => request<BillingStatus>("/billing/status"),
    createSubscriptionCheckout: (
      tier: "starter" | "plus" | "pro",
      billing_period: "monthly" | "yearly"
    ) =>
      request<{ client_secret: string }>("/billing/checkout", {
        method: "POST",
        body: { type: "subscription", tier, billing_period },
      }),
    createPackCheckout: (pack_size: "small" | "medium" | "large") =>
      request<{ client_secret: string }>("/billing/checkout", {
        method: "POST",
        body: { type: "pack", pack_size },
      }),
    portal: () => request<{ url: string }>("/billing/portal"),
  },

  admin: {
    listUsers: (params?: { search?: string; tier?: string; page?: number; per_page?: number }) => {
      const query = new URLSearchParams()
      if (params?.search) query.set("search", params.search)
      if (params?.tier) query.set("tier", params.tier)
      if (params?.page) query.set("page", String(params.page))
      if (params?.per_page) query.set("per_page", String(params.per_page))
      const qs = query.toString()
      return request<AdminUserListResponse>(`/admin/users${qs ? `?${qs}` : ""}`)
    },
    getUser: (id: string) => request<AdminUserDetail>(`/admin/users/${id}`),
    changeTier: (id: string, tier: string) =>
      request<AdminUserSummary>(`/admin/users/${id}/tier`, { method: "PATCH", body: { tier } }),
    grantCredits: (id: string, data: { subscription_credits?: number; pack_credits?: number }) =>
      request<AdminUserSummary>(`/admin/users/${id}/credits`, { method: "PATCH", body: data }),
    changeRole: (id: string, role: string) =>
      request<AdminUserSummary>(`/admin/users/${id}/role`, { method: "PATCH", body: { role } }),
    revokeApiKey: (id: string, keyId: string) =>
      request<void>(`/admin/users/${id}/api-keys/${keyId}`, { method: "DELETE" }),
  },
}

export interface User {
  id: string
  username: string
  email: string
  avatar_url: string | null
  role: "USER" | "ADMIN" | "SUPER_ADMIN"
}

export interface Board {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface Agent {
  id: string
  name: string
  description: string | null
  system_prompt: string
  board_id: string | null
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TeamMembers {
  capabilities: string[]
  agent_ids: string[]
}

export interface TeamOrchestrator {
  system_prompt?: string
  model?: string
  temperature?: number
  routing_strategy?: string
  max_credits?: number | null
}

export interface Team {
  id: string
  name: string
  description: string | null
  board_id: string | null
  members: TeamMembers
  orchestrator: TeamOrchestrator
  created_at: string
  updated_at: string
}

export interface Generation {
  id: string
  board_id: string
  agent_id: string | null
  prompt: string
  status: "pending" | "processing" | "completed" | "failed"
  result_url: string | null
  result_type: string | null
  metadata: Record<string, unknown>
  variants: Variant[]
  created_at: string
}

export interface Variant {
  id: string
  variant_index: number
  result_url: string | null
  result_type: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface PlanNode {
  id: string
  member: string
  request: string
  depends_on: string[]
  rationale: string | null
}

export interface TeamPlan {
  summary: string
  nodes: PlanNode[]
  estimated_credits: number
}

export type NodeStatus = "pending" | "running" | "done" | "failed" | "skipped"

export interface NodeState {
  status: NodeStatus
  text: string
  urls: string[]
  error: string | null
  spent: number | null
}

export interface Attachment {
  filename: string
  mime_type: string   // e.g. "image/png", "video/mp4", "application/pdf"
  data_url: string    // "data:<mime>;base64,<content>"
  size: number        // bytes, for display only
}

export type ChatMessage = {
  role: "user" | "assistant"
  content: string
  urls?: string[]
  plan?: TeamPlan
  nodes?: Record<string, NodeState>
  timestamp?: number
  attachments?: Attachment[]
}

export interface BillingStatus {
  tier: "FREE_TRIAL" | "STARTER" | "PLUS" | "PRO" | "ENTERPRISE"
  subscription_credits: number
  pack_credits: number
  credits_reset_at: string | null
}

export interface AdminUserSummary {
  id: string
  username: string
  email: string
  role: string
  subscription_tier: string
  subscription_credits: number
  pack_credits: number
  created_at: string | null
}

export interface AdminApiKey {
  id: string
  name: string
  key_prefix: string
  created_at: string | null
  last_used_at: string | null
  revoked_at: string | null
}

export interface AdminUserDetail extends AdminUserSummary {
  avatar_url: string | null
  credits_reset_at: string | null
  stripe_customer_id: string | null
  api_keys: AdminApiKey[]
}

export interface AdminUserListResponse {
  users: AdminUserSummary[]
  total: number
  page: number
  per_page: number
}
