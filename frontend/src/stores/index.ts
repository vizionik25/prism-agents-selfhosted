import { create } from "zustand"
import { persist } from "zustand/middleware"
import { api, type User, type ChatMessage, type Generation, type Board, type Agent, type Team, type BillingStatus, type TeamPlan, type NodeState, type NodeStatus } from "@/lib/api"

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
const SELF_HOSTED = process.env.NEXT_PUBLIC_SELF_HOSTED === "true"

const DEMO_USER: User = {
  id: "00000000-0000-0000-0000-000000000000",
  username: "Demo User",
  email: "demo@prismagents.com",
  avatar_url: null,
  role: "SUPER_ADMIN",
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  setAuth: (token: string, user: User) => void
  logout: () => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isLoading: true,
      setAuth: (token, user) => {
        localStorage.setItem("token", token)
        set({ token, user })
      },
      logout: () => {
        if (DEMO_MODE) return  // prevent demo users from logging out
        localStorage.removeItem("token")
        set({ token: null, user: null })
      },
      checkAuth: async () => {
        if (DEMO_MODE) {
          localStorage.setItem("token", "demo-token")
          set({ user: DEMO_USER, token: "demo-token", isLoading: false })
          return
        }
        const token = localStorage.getItem("token")
        if (!token) {
          set({ isLoading: false })
          return
        }
        try {
          const user = await api.auth.me()
          set({ user, token, isLoading: false })
        } catch {
          localStorage.removeItem("token")
          set({ user: null, token: null, isLoading: false })
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ token: state.token }),
    }
  )
)

interface BoardState {
  boards: Board[]
  currentBoard: Board | null
  setBoards: (boards: Board[]) => void
  setCurrentBoard: (board: Board | null) => void
  addBoard: (board: Board) => void
  updateBoard: (id: string, data: Partial<Board>) => void
  removeBoard: (id: string) => void
}

export const useBoardStore = create<BoardState>((set) => ({
  boards: [],
  currentBoard: null,
  setBoards: (boards) => set({ boards }),
  setCurrentBoard: (board) => set({ currentBoard: board }),
  addBoard: (board) => set((state) => ({ boards: [board, ...state.boards] })),
  updateBoard: (id, data) =>
    set((state) => ({
      boards: state.boards.map((b) => (b.id === id ? { ...b, ...data } : b)),
      currentBoard:
        state.currentBoard?.id === id ? { ...state.currentBoard, ...data } : state.currentBoard,
    })),
  removeBoard: (id) =>
    set((state) => ({
      boards: state.boards.filter((b) => b.id !== id),
      currentBoard: state.currentBoard?.id === id ? null : state.currentBoard,
    })),
}))

interface ChatState {
  messages: ChatMessage[]
  isGenerating: boolean
  currentGenerationId: string | null
  addMessage: (message: ChatMessage) => void
  updateLastMessage: (content: string) => void
  addUrlToLastMessage: (url: string) => void
  setLastMessagePlan: (plan: TeamPlan) => void
  updateLastMessageNode: (nodeId: string, patch: Partial<NodeState>) => void
  setGenerating: (isGenerating: boolean, generationId?: string | null) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isGenerating: false,
  currentGenerationId: null,
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, { ...message, timestamp: Date.now() }],
    })),
  updateLastMessage: (content) =>
    set((state) => ({
      messages: state.messages.map((m, i) =>
        i === state.messages.length - 1 ? { ...m, content } : m
      ),
    })),
  addUrlToLastMessage: (url) =>
    set((state) => ({
      messages: state.messages.map((m, i) =>
        i === state.messages.length - 1
          ? { ...m, urls: [...(m.urls ?? []), url] }
          : m
      ),
    })),
  setLastMessagePlan: (plan) =>
    set((state) => ({
      messages: state.messages.map((m, i) => {
        if (i !== state.messages.length - 1) return m
        const nodes: Record<string, NodeState> = {}
        for (const n of plan.nodes) {
          nodes[n.id] = { status: "pending", text: "", urls: [], error: null, spent: null }
        }
        return { ...m, plan, nodes }
      }),
    })),
  updateLastMessageNode: (nodeId, patch) =>
    set((state) => ({
      messages: state.messages.map((m, i) => {
        if (i !== state.messages.length - 1) return m
        const existing = m.nodes?.[nodeId] ?? {
          status: "pending" as NodeStatus, text: "", urls: [], error: null, spent: null,
        }
        return {
          ...m,
          nodes: { ...(m.nodes ?? {}), [nodeId]: { ...existing, ...patch } },
        }
      }),
    })),
  setGenerating: (isGenerating, generationId = null) =>
    set({ isGenerating, currentGenerationId: generationId }),
  clearMessages: () => set({ messages: [], isGenerating: false, currentGenerationId: null }),
}))

interface HistoryState {
  generations: Generation[]
  selectedGeneration: Generation | null
  setGenerations: (generations: Generation[]) => void
  addGeneration: (generation: Generation) => void
  updateGeneration: (id: string, data: Partial<Generation>) => void
  setSelectedGeneration: (generation: Generation | null) => void
}

export const useHistoryStore = create<HistoryState>((set) => ({
  generations: [],
  selectedGeneration: null,
  setGenerations: (generations) => set({ generations }),
  addGeneration: (generation) =>
    set((state) => ({ generations: [generation, ...state.generations] })),
  updateGeneration: (id, data) =>
    set((state) => ({
      generations: state.generations.map((g) => (g.id === id ? { ...g, ...data } : g)),
      selectedGeneration:
        state.selectedGeneration?.id === id
          ? { ...state.selectedGeneration, ...data }
          : state.selectedGeneration,
    })),
  setSelectedGeneration: (generation) => set({ selectedGeneration: generation }),
}))

interface AgentState {
  agents: Agent[]
  currentAgent: Agent | null
  setAgents: (agents: Agent[]) => void
  setCurrentAgent: (agent: Agent | null) => void
  addAgent: (agent: Agent) => void
  updateAgent: (id: string, data: Partial<Agent>) => void
  removeAgent: (id: string) => void
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  currentAgent: null,
  setAgents: (agents) => set({ agents }),
  setCurrentAgent: (agent) => set({ currentAgent: agent }),
  addAgent: (agent) => set((state) => ({ agents: [agent, ...state.agents] })),
  updateAgent: (id, data) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, ...data } : a)),
      currentAgent:
        state.currentAgent?.id === id ? { ...state.currentAgent, ...data } : state.currentAgent,
    })),
  removeAgent: (id) =>
    set((state) => ({
      agents: state.agents.filter((a) => a.id !== id),
      currentAgent: state.currentAgent?.id === id ? null : state.currentAgent,
    })),
}))

interface TeamState {
  teams: Team[]
  currentTeam: Team | null
  setTeams: (teams: Team[]) => void
  setCurrentTeam: (team: Team | null) => void
  addTeam: (team: Team) => void
  updateTeam: (id: string, data: Partial<Team>) => void
  removeTeam: (id: string) => void
}

export const useTeamStore = create<TeamState>((set) => ({
  teams: [],
  currentTeam: null,
  setTeams: (teams) => set({ teams }),
  setCurrentTeam: (team) => set({ currentTeam: team }),
  addTeam: (team) => set((state) => ({ teams: [team, ...state.teams] })),
  updateTeam: (id, data) =>
    set((state) => ({
      teams: state.teams.map((t) => (t.id === id ? { ...t, ...data } : t)),
      currentTeam:
        state.currentTeam?.id === id ? { ...state.currentTeam, ...data } : state.currentTeam,
    })),
  removeTeam: (id) =>
    set((state) => ({
      teams: state.teams.filter((t) => t.id !== id),
      currentTeam: state.currentTeam?.id === id ? null : state.currentTeam,
    })),
}))

interface BillingState {
  tier: BillingStatus["tier"]
  subscriptionCredits: number
  packCredits: number
  creditsResetAt: string | null
  isLoaded: boolean
  setStatus: (status: BillingStatus) => void
  fetchStatus: () => Promise<void>
  totalCredits: () => number
}

export const useBillingStore = create<BillingState>((set, get) => ({
  tier: "FREE_TRIAL",
  subscriptionCredits: 0,
  packCredits: 0,
  creditsResetAt: null,
  isLoaded: false,
  setStatus: (status) =>
    set({
      tier: status.tier,
      subscriptionCredits: status.subscription_credits,
      packCredits: status.pack_credits,
      creditsResetAt: status.credits_reset_at,
      isLoaded: true,
    }),
  fetchStatus: async () => {
    if (DEMO_MODE || SELF_HOSTED) {
      set({
        tier: "ENTERPRISE",
        subscriptionCredits: 999999,
        packCredits: 999999,
        creditsResetAt: null,
        isLoaded: true,
      })
      return
    }
    try {
      const status = await api.billing.status()
      get().setStatus(status)
    } catch {
      // not authenticated yet
    }
  },
  totalCredits: () => get().subscriptionCredits + get().packCredits,
}))
