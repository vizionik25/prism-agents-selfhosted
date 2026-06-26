"use client"

import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { Send, Loader2, Zap, Sparkles, Download, ExternalLink, FileBox, Users, Radar, Cpu, X, Plus, Image, Video, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useChatStore } from "@/stores"
import type { Team, TeamPlan, NodeStatus, NodeState } from "@/lib/api"
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const ONE_HOUR_MS = 60 * 60 * 1000

const MAX_ATTACHMENTS = 5

const SIZE_LIMITS = {
  image: 20 * 1024 * 1024,     // 20 MB
  video: 50 * 1024 * 1024,     // 50 MB
  document: 10 * 1024 * 1024,  // 10 MB
}

const FILE_ACCEPT = {
  image: "image/jpeg,image/png,image/gif,image/webp,image/svg+xml",
  video: "video/mp4,video/webm,video/quicktime,video/x-msvideo",
  document: "application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

interface PendingAttachment {
  id: string
  filename: string
  mimeType: string
  size: number
  dataUrl?: string
  status: "loading" | "ready" | "error"
  error?: string
}

function getSizeCategory(mimeType: string): "image" | "video" | "document" {
  const mime = mimeType.toLowerCase()
  if (mime.startsWith("image/")) return "image"
  if (mime.startsWith("video/")) return "video"
  return "document"
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  return `${mb.toFixed(1)} MB`
}

// If a message has a plan, data starting with "<known_node_id>:" is routed to
// that node; otherwise it's main-thread. This helper returns [nodeId|null, rest].
function splitNodeScope(data: string, plan: TeamPlan | undefined): [string | null, string] {
  if (!plan) return [null, data]
  const colon = data.indexOf(":")
  if (colon <= 0) return [null, data]
  const maybeId = data.slice(0, colon)
  if (plan.nodes.some((n) => n.id === maybeId)) {
    return [maybeId, data.slice(colon + 1)]
  }
  return [null, data]
}

function getMediaType(url: string): "image" | "video" | "audio" | "model_3d" | "other" {
  const path = url.split("?")[0].toLowerCase()
  if (/\.(jpg|jpeg|png|gif|webp|svg)$/.test(path)) return "image"
  if (/\.(mp4|webm|mov|avi)$/.test(path)) return "video"
  if (/\.(mp3|wav|ogg|aac|m4a)$/.test(path)) return "audio"
  if (/\.(glb|gltf|obj|fbx)$/.test(path)) return "model_3d"
  return "other"
}

async function downloadUrl(url: string) {
  try {
    const res = await fetch(url)
    const blob = await res.blob()
    const href = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = href
    a.download = url.split("/").pop()?.split("?")[0] || "download"
    a.click()
    URL.revokeObjectURL(href)
  } catch {
    window.open(url, "_blank")
  }
}

function MediaCard({ url, expired }: { url: string; expired: boolean }) {
  const type = getMediaType(url)
  const filename = url.split("/").pop()?.split("?")[0] || "file"

  if (expired) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 text-xs text-primary underline-offset-2 hover:underline"
      >
        <ExternalLink className="w-3 h-3 shrink-0" />
        {filename}
      </a>
    )
  }

  return (
    <div className="rounded-xl overflow-hidden border bg-card">
      {type === "image" && (
        <img src={url} alt={filename} className="w-full h-auto max-h-96 object-contain bg-black/5" />
      )}
      {type === "video" && (
        <video src={url} controls className="w-full max-h-96" />
      )}
      {type === "audio" && (
        <div className="p-3">
          <audio src={url} controls className="w-full" />
        </div>
      )}
      {(type === "model_3d" || type === "other") && (
        <div className="flex items-center gap-3 p-3">
          <FileBox className="w-8 h-8 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{filename}</p>
            <p className="text-xs text-muted-foreground capitalize">{type.replace("_", " ")}</p>
          </div>
        </div>
      )}
      <div className="flex items-center justify-between px-3 py-2 border-t bg-muted/30">
        <span className="text-xs text-muted-foreground truncate max-w-[60%]">{filename}</span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 gap-1 text-xs"
          onClick={() => downloadUrl(url)}
        >
          <Download className="w-3 h-3" />
          Download
        </Button>
      </div>
    </div>
  )
}

function PlanCard({ plan }: { plan: TeamPlan }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl border bg-card/60 text-xs">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        aria-controls="plan-details"
        className="flex w-full items-center justify-between px-3 py-2 font-mono uppercase tracking-wider text-muted-foreground hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span>Plan — {plan.summary}</span>
        <span>{plan.estimated_credits} cr · {plan.nodes.length} steps</span>
      </button>
      {open && (
        <ul id="plan-details" className="space-y-1 border-t px-3 py-2">
          {plan.nodes.map((n) => (
            <li key={n.id} className="font-mono">
              <span className="text-muted-foreground">{n.id}</span>{" "}
              <span className="text-foreground">{n.member}</span>
              {n.depends_on.length > 0 && (
                <span className="text-muted-foreground"> ← {n.depends_on.join(", ")}</span>
              )}
              <div className="pl-6 text-muted-foreground truncate">{n.request}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function statusBadge(status: NodeStatus) {
  const map: Record<NodeStatus, { label: string; className: string }> = {
    pending:  { label: "·",   className: "text-muted-foreground" },
    running:  { label: "…",   className: "text-primary animate-pulse" },
    done:     { label: "✓",   className: "text-foreground" },
    failed:   { label: "✗",   className: "text-destructive" },
    skipped:  { label: "↷",   className: "text-muted-foreground" },
  }
  const entry = map[status]
  return (
    <span
      role="img"
      aria-label={status}
      className={`font-mono text-xs ${entry.className}`}
    >
      {entry.label}
    </span>
  )
}

function LaneCard({
  nodeId,
  member,
  state,
  expired,
}: {
  nodeId: string
  member: string
  state: NodeState
  expired: boolean
}) {
  return (
    <div className="rounded-xl border bg-card">
      <div className="flex items-center justify-between border-b px-3 py-1.5">
        <div className="flex items-center gap-2">
          {statusBadge(state.status)}
          <span className="font-mono text-xs text-muted-foreground">{nodeId}</span>
          <span className="text-sm">{member}</span>
        </div>
        {state.spent !== null && (
          <span className="font-mono text-[10px] text-muted-foreground">{state.spent} cr</span>
        )}
      </div>
      {state.text && (
        <p className="whitespace-pre-wrap px-3 py-2 text-sm">{state.text}</p>
      )}
      {state.urls.length > 0 && (
        <div className="grid gap-2 p-2" style={{ gridTemplateColumns: state.urls.length > 1 ? "repeat(auto-fill, minmax(220px, 1fr))" : "1fr" }}>
          {state.urls.map((u) => <MediaCard key={u} url={u} expired={expired} />)}
        </div>
      )}
    </div>
  )
}

interface ChatPanelProps {
  boardId: string
  agentId?: string
  capability?: string
  teamId?: string
  activeTeam?: Team | null
}

export function ChatPanel({
  boardId,
  agentId,
  capability,
  teamId,
  activeTeam,
}: ChatPanelProps) {
  const {
    messages, isGenerating,
    addMessage, updateLastMessage, addUrlToLastMessage, setGenerating,
    setLastMessagePlan, updateLastMessageNode,
  } = useChatStore()
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [quickActionsOpen, setQuickActionsOpen] = useState(false)
  const hoverCloseTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Running credit spend for the current team run; resets each new submit.
  const [runSpent, setRunSpent] = useState(0)

  // Attachment states
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([])
  const [attachPopupOpen, setAttachPopupOpen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [fileAcceptType, setFileAcceptType] = useState("")
  const clickPendingRef = useRef(false)
  const attachButtonRef = useRef<HTMLButtonElement>(null)
  const attachPopoverRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (clickPendingRef.current && fileAcceptType) {
      clickPendingRef.current = false
      fileInputRef.current?.click()
    }
  }, [fileAcceptType])

  useEffect(() => {
    if (!attachPopupOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAttachPopupOpen(false)
      }
    }

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node
      if (
        attachPopoverRef.current &&
        !attachPopoverRef.current.contains(target) &&
        attachButtonRef.current &&
        !attachButtonRef.current.contains(target)
      ) {
        setAttachPopupOpen(false)
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    document.addEventListener("mousedown", handleClickOutside)

    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [attachPopupOpen])

  const handleAttachType = (type: "image" | "video" | "document") => {
    const accept = FILE_ACCEPT[type]
    setAttachPopupOpen(false)
    clickPendingRef.current = true
    if (fileAcceptType === accept) {
      clickPendingRef.current = false
      fileInputRef.current?.click()
    } else {
      setFileAcceptType(accept)
    }
  }

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const selectedFiles = Array.from(files)
    const currentReadyAndLoading = pendingAttachments.filter(a => a.status === "ready" || a.status === "loading")

    if (currentReadyAndLoading.length + selectedFiles.length > MAX_ATTACHMENTS) {
      alert(`You can only attach up to ${MAX_ATTACHMENTS} files in total.`)
      e.target.value = ""
      return
    }

    selectedFiles.forEach((file) => {
      const isDuplicate = pendingAttachments.some(
        (a) => a.filename === file.name && a.size === file.size
      )
      if (isDuplicate) {
        alert(`File "${file.name}" is already attached.`)
        return
      }

      // MIME type validation
      const mimeType = (file.type || "").split(";")[0].trim().toLowerCase()
      const allowedTypesString = fileAcceptType || Object.values(FILE_ACCEPT).join(",")
      const allowedList = allowedTypesString.split(",").map((t) => t.trim().toLowerCase())

      if (!allowedList.includes(mimeType)) {
        alert(`File "${file.name}" has an unsupported format (${mimeType || "unknown"}).`)
        return
      }

      const category = getSizeCategory(mimeType)
      const limit = SIZE_LIMITS[category]
      if (file.size > limit) {
        alert(`File "${file.name}" exceeds the size limit for ${category}s (${formatFileSize(limit)}).`)
        return
      }

      const id = crypto.randomUUID()
      const newAttachment: PendingAttachment = {
        id,
        filename: file.name,
        mimeType: file.type || "application/octet-stream",
        size: file.size,
        status: "loading",
      }

      setPendingAttachments((prev) => [...prev, newAttachment])

      const reader = new FileReader()
      reader.onload = (event) => {
        const dataUrl = event.target?.result as string
        setPendingAttachments((prev) =>
          prev.map((a) =>
            a.id === id ? { ...a, status: "ready", dataUrl } : a
          )
        )
      }
      reader.onerror = () => {
        setPendingAttachments((prev) =>
          prev.map((a) =>
            a.id === id ? { ...a, status: "error", error: "Failed to read file" } : a
          )
        )
      }
      reader.readAsDataURL(file)
    })

    e.target.value = ""
  }

  const removeAttachment = (id: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.id !== id))
  }

  const openQuickActions = () => {
    if (hoverCloseTimer.current) clearTimeout(hoverCloseTimer.current)
    setQuickActionsOpen(true)
  }

  const closeQuickActions = () => {
    hoverCloseTimer.current = setTimeout(() => setQuickActionsOpen(false), 150)
  }

  const QUICK_COMMANDS = [
    { group: "Generate", items: [
      { label: "Generate Image",   prefix: "/image " },
      { label: "Generate Video",   prefix: "/video " },
      { label: "Generate Music",   prefix: "/music " },
      { label: "Human Motion",     prefix: "/motion " },
    ]},
    { group: "Analyze", items: [
      { label: "Analyze Image",    prefix: "/vision " },
      { label: "Analyze Video",    prefix: "/analyze-video " },
      { label: "Research Topic",   prefix: "/research " },
    ]},
    { group: "3D", items: [
      { label: "Text to 3D",       prefix: "/3d " },
      { label: "Image to 3D",      prefix: "/image-to-3d " },
      { label: "Remesh 3D",        prefix: "/remesh " },
      { label: "Retexture 3D",     prefix: "/retexture " },
    ]},
    { group: "Utility", items: [
      { label: "Create Agent",     prefix: "/create_agent " },
      { label: "Help",             prefix: "/help" },
    ]},
  ]

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (
      (!input.trim() && pendingAttachments.length === 0) ||
      isGenerating ||
      pendingAttachments.some((a) => a.status === "loading") ||
      pendingAttachments.some((a) => a.status === "error")
    ) {
      if (pendingAttachments.some((a) => a.status === "error")) {
        alert("Please remove failed attachments before sending.")
      }
      return
    }

    const userMessage = input.trim()
    const readyAttachments = pendingAttachments
      .filter((a) => a.status === "ready")
      .map((a) => ({
        filename: a.filename,
        mime_type: a.mimeType,
        data_url: a.dataUrl || "",
        size: a.size,
      }))

    setInput("")
    setPendingAttachments([])

    addMessage({
      role: "user",
      content: userMessage,
      ...(readyAttachments.length > 0 ? { attachments: readyAttachments } : {}),
    })
    
    setGenerating(true)
    setRunSpent(0)

    try {
      const token = localStorage.getItem("token")
      
      const history = messages.map((m) => {
        if (m.attachments && m.attachments.length > 0) {
          const attachmentTags = m.attachments
            .map((a) => `[attached: ${a.filename}]`)
            .join("\n")
          return {
            role: m.role,
            content: `${attachmentTags}\n${m.content}`.trim(),
          }
        }
        return { role: m.role, content: m.content }
      })

      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          board_id: boardId,
          message: userMessage,
          history,
          ...(agentId ? { agent_id: agentId } : {}),
          ...(capability ? { capability } : {}),
          ...(teamId ? { team_id: teamId } : {}),
          ...(readyAttachments.length > 0 ? { attachments: readyAttachments } : {}),
        }),
      })

      if (!response.ok) {
        let errorText = "Chat request failed"
        try {
          const errorData = await response.json()
          if (errorData && errorData.detail) {
            errorText = errorData.detail
          }
        } catch {
          errorText = response.statusText || errorText
        }
        throw new Error(errorText)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error("No response body")

      addMessage({ role: "assistant", content: "" })
      let accumulated = ""

      const decoder = new TextDecoder()
      let buffer = ""
      let currentEvent = "message"

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const rawLine of lines) {
          const line = rawLine.replace(/\r$/, "")
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith("data: ")) {
            const data = line.slice(6)
            // Look up the current plan on the last assistant message so we can
            // decide whether to route this event into a node lane.
            const lastMsg = useChatStore.getState().messages.slice(-1)[0]
            const currentPlan = lastMsg?.plan

            if (currentEvent === "plan") {
              try {
                const plan: TeamPlan = JSON.parse(data)
                setLastMessagePlan(plan)
              } catch (err) {
                console.error("Failed to parse plan event", err)
              }
            } else if (currentEvent === "message") {
              const [nodeId, rest] = splitNodeScope(data, currentPlan)
              if (nodeId) {
                // Append to the node's text rather than overwriting.
                const existing = lastMsg?.nodes?.[nodeId]?.text ?? ""
                updateLastMessageNode(nodeId, { text: existing + rest })
              } else {
                accumulated += data
                updateLastMessage(accumulated)
              }
            } else if (currentEvent === "url") {
              const [nodeId, rest] = splitNodeScope(data, currentPlan)
              if (nodeId) {
                const existing = lastMsg?.nodes?.[nodeId]?.urls ?? []
                updateLastMessageNode(nodeId, { urls: [...existing, rest] })
              } else {
                addUrlToLastMessage(data)
              }
            } else if (currentEvent === "credits") {
              const [nodeId, rest] = splitNodeScope(data, currentPlan)
              const spent = parseInt(nodeId ? rest : data, 10)
              if (Number.isFinite(spent)) {
                setRunSpent(spent)
                if (nodeId) updateLastMessageNode(nodeId, { spent })
              }
            } else if (currentEvent === "status") {
              const [nodeId, rest] = splitNodeScope(data, currentPlan)
              if (nodeId) {
                updateLastMessageNode(nodeId, { status: rest as NodeStatus })
              }
              // Run-level statuses (processing/completed) are informational — no UI mutation here.
            } else if (currentEvent === "error") {
              try {
                const detail = JSON.parse(data)
                if (detail?.code === "insufficient_credits") {
                  window.dispatchEvent(new CustomEvent("insufficient_credits"))
                }
              } catch {}
              accumulated += (accumulated ? "\n\n" : "") + `Error: ${data}`
              updateLastMessage(accumulated)
            } else if (currentEvent === "generation_start") {
              setGenerating(true, data)
            }
          } else if (line === "") {
            currentEvent = "message"
          }
        }
      }

      setGenerating(false)
    } catch (error) {
      console.error("Chat error:", error)
      const errorMsg = error instanceof Error ? error.message : "Sorry, something went wrong. Please try again."
      updateLastMessage(errorMsg)
      setGenerating(false)
    }
  }

  const handleQuickCommand = (prefix: string) => {
    setInput(prefix)
    setQuickActionsOpen(false)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-col h-full">
      {activeTeam && <ActiveTeamBanner team={activeTeam} boardId={boardId} spent={runSpent} />}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-2xl bg-linear-to-br from-primary via-brand-pink to-accent flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-primary-foreground" />
              </div>
              <h2 className="text-xl font-semibold mb-2">What would you like to create?</h2>
              <p className="text-muted-foreground mb-6 max-w-md">
                Describe your vision and I&apos;ll help you bring it to life with images, videos, and more.
              </p>
              <p className="text-sm text-muted-foreground">
                Use the <span className="font-medium">Quick Actions</span> button below to get started.
              </p>
            </div>
          )}

          {messages.map((message, i) => {
            const expired = !!message.timestamp && Date.now() - message.timestamp > ONE_HOUR_MS
            const hasMedia = (message.urls?.length ?? 0) > 0
            return (
              <div
                key={i}
                className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.role === "assistant" && (
                  <Avatar className="w-8 h-8 shrink-0">
                    <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                      L
                    </AvatarFallback>
                  </Avatar>
                )}
                <div className={`flex flex-col gap-2 ${hasMedia ? "max-w-[90%] w-full" : "max-w-[80%]"}`}>
                  {/* user message attachments */}
                  {message.role === "user" && message.attachments && message.attachments.length > 0 && (
                    <div className="flex flex-wrap gap-2 justify-end mb-1">
                      {message.attachments.map((att, idx) => {
                        const category = getSizeCategory(att.mime_type)
                        let icon = <FileText className="w-3.5 h-3.5" />
                        let chipClass = "bg-cyan-500/10 border-cyan-500/20 text-cyan-600 dark:text-cyan-400"
                        if (category === "image") {
                          icon = <Image className="w-3.5 h-3.5" />
                          chipClass = "bg-purple-500/10 border-purple-500/20 text-purple-600 dark:text-purple-400"
                        } else if (category === "video") {
                          icon = <Video className="w-3.5 h-3.5" />
                          chipClass = "bg-pink-500/10 border-pink-500/20 text-pink-600 dark:text-pink-400"
                        }

                        return (
                          <div
                            key={idx}
                            className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-medium ${chipClass}`}
                          >
                            {icon}
                            <span className="max-w-[180px] truncate" title={att.filename}>
                              {att.filename}
                            </span>
                            <span className="text-[10px] opacity-70">
                              ({formatFileSize(att.size)})
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {/* text bubble */}
                  {message.content && (
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </div>
                  )}
                  {/* plan peek */}
                  {message.plan && <PlanCard plan={message.plan} />}

                  {/* lane cards — render in plan order so the layout is stable */}
                  {message.plan && message.nodes && (
                    <div className="flex flex-col gap-2">
                      {message.plan.nodes.map((n) => {
                        const state = message.nodes![n.id]
                        if (!state) return null
                        return (
                          <LaneCard
                            key={n.id}
                            nodeId={n.id}
                            member={n.member}
                            state={state}
                            expired={expired}
                          />
                        )
                      })}
                    </div>
                  )}
                  {/* media cards */}
                  {hasMedia && (
                    <div className="grid gap-3" style={{ gridTemplateColumns: message.urls!.length > 1 ? "repeat(auto-fill, minmax(260px, 1fr))" : "1fr" }}>
                      {message.urls!.map((url) => (
                        <MediaCard key={url} url={url} expired={expired} />
                      ))}
                    </div>
                  )}
                </div>
                {message.role === "user" && (
                  <Avatar className="w-8 h-8 shrink-0">
                    <AvatarFallback>Y</AvatarFallback>
                  </Avatar>
                )}
              </div>
            )
          })}

          {isGenerating && messages[messages.length - 1]?.role === "user" && (
            <div className="flex gap-3 justify-start">
              <Avatar className="w-8 h-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs">L</AvatarFallback>
              </Avatar>
              <div className="bg-muted rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t bg-card p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative">
          {/* Hidden file input */}
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            multiple
            onChange={handleFileSelected}
            accept={fileAcceptType}
          />

          {/* Attach type popup menu (glassmorphism) */}
          {attachPopupOpen && (
            <div
              ref={attachPopoverRef}
              className="absolute bottom-full left-0 mb-2 p-1.5 flex gap-1 rounded-full border border-border/40 bg-background/80 backdrop-blur-md shadow-lg z-50 animate-in fade-in slide-in-from-bottom-2 duration-200"
            >
              <button
                type="button"
                onClick={() => handleAttachType("image")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-purple-500 hover:bg-purple-500/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Image className="w-3.5 h-3.5" />
                Image
              </button>
              <button
                type="button"
                onClick={() => handleAttachType("video")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-pink-500 hover:bg-pink-500/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Video className="w-3.5 h-3.5" />
                Video
              </button>
              <button
                type="button"
                onClick={() => handleAttachType("document")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-cyan-500 hover:bg-cyan-500/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <FileText className="w-3.5 h-3.5" />
                Document
              </button>
            </div>
          )}

          <div className="flex gap-2 items-center">
            {/* '+' Attach button */}
            <Button
              ref={attachButtonRef}
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setAttachPopupOpen(!attachPopupOpen)}
              className="shrink-0"
              aria-label="Attach file"
              aria-expanded={attachPopupOpen}
              aria-haspopup="dialog"
            >
              <Plus className={`w-5 h-5 transition-transform duration-200 ${attachPopupOpen ? 'rotate-45' : ''}`} />
            </Button>

            <label htmlFor="chat-input" className="sr-only">
              Chat message
            </label>
            <Input
              id="chat-input"
              ref={inputRef}
              placeholder="Describe what you want to create..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isGenerating}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={(!input.trim() && pendingAttachments.length === 0) || isGenerating || pendingAttachments.some(a => a.status === "loading") || pendingAttachments.some(a => a.status === "error")}
              size="icon"
              aria-label="Send message"
            >
              {isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>

          {/* Inline pending attachments chips */}
          {pendingAttachments.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3 animate-in fade-in duration-200">
              {pendingAttachments.map((att) => {
                const category = getSizeCategory(att.mimeType)
                let icon = <FileText className="w-3.5 h-3.5" />
                let chipClass = ""

                if (att.status === "error") {
                  icon = <X className="w-3.5 h-3.5 text-red-500 dark:text-red-400" />
                  chipClass = "border-destructive bg-destructive/10 text-destructive dark:text-red-400 animate-none"
                } else {
                  const isReady = att.status === "ready"
                  if (category === "image") {
                    icon = <Image className="w-3.5 h-3.5" />
                    chipClass = isReady
                      ? "bg-purple-500/10 border-purple-500/20 text-purple-600 dark:text-purple-400"
                      : "bg-purple-500/10 border-purple-500/20 text-purple-600 dark:text-purple-400 animate-pulse"
                  } else if (category === "video") {
                    icon = <Video className="w-3.5 h-3.5" />
                    chipClass = isReady
                      ? "bg-pink-500/10 border-pink-500/20 text-pink-600 dark:text-pink-400"
                      : "bg-pink-500/10 border-pink-500/20 text-pink-600 dark:text-pink-400 animate-pulse"
                  } else {
                    icon = <FileText className="w-3.5 h-3.5" />
                    chipClass = isReady
                      ? "bg-cyan-500/10 border-cyan-500/20 text-cyan-600 dark:text-cyan-400"
                      : "bg-cyan-500/10 border-cyan-500/20 text-cyan-600 dark:text-cyan-400 animate-pulse"
                  }
                }

                return (
                  <div
                    key={att.id}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-medium transition-colors ${chipClass}`}
                  >
                    {att.status === "loading" ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      icon
                    )}
                    <span className="max-w-[150px] truncate" title={att.filename}>
                      {att.filename}
                    </span>
                    <span className="text-[10px] opacity-70">
                      ({formatFileSize(att.size)})
                    </span>
                    <button
                      type="button"
                      onClick={() => removeAttachment(att.id)}
                      className="ml-1 p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label={`Remove ${att.filename}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                )
              })}
            </div>
          )}

          <div className="flex items-center justify-between mt-2">
            <div onMouseEnter={openQuickActions} onMouseLeave={closeQuickActions}>
              <DropdownMenu open={quickActionsOpen} onOpenChange={(open) => setQuickActionsOpen(open)}>
                <DropdownMenuTrigger
                  className="inline-flex items-center gap-1.5 text-xs text-muted-foreground h-7 px-2 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  <Zap className="w-3 h-3" />
                  Quick Actions
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  side="top"
                  align="start"
                  className="w-52"
                  onMouseEnter={openQuickActions}
                  onMouseLeave={closeQuickActions}
                >
                  {QUICK_COMMANDS.map((group, gi) => (
                    <DropdownMenuGroup key={group.group}>
                      {gi > 0 && <DropdownMenuSeparator />}
                      <DropdownMenuLabel>{group.group}</DropdownMenuLabel>
                      {group.items.map((item) => (
                        <DropdownMenuItem
                          key={item.prefix}
                          onClick={() => handleQuickCommand(item.prefix)}
                        >
                          {item.label}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuGroup>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <p className="text-xs text-muted-foreground">
              Or just describe what you want to create
            </p>
          </div>
        </form>
      </div>
    </div>
  )
}

function ActiveTeamBanner({
  team,
  boardId,
  spent,
}: {
  team: Team
  boardId: string
  spent: number
}) {
  const memberCount =
    (team.members?.capabilities?.length ?? 0) + (team.members?.agent_ids?.length ?? 0)
  const modelLabel =
    team.orchestrator?.model?.split("/").slice(-1)[0] ?? "default"
  const routingLabel = team.orchestrator?.routing_strategy
    ? team.orchestrator.routing_strategy.replace(/_/g, " ")
    : "llm routed"
  const cap = team.orchestrator?.max_credits ?? null
  const overCap = cap != null && spent >= cap

  return (
    <div className="relative border-b bg-card/60 backdrop-blur-xl">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[2px]"
        style={{
          background:
            "linear-gradient(90deg, var(--brand-pink), var(--primary), var(--brand-turquoise))",
        }}
      />
      <div className="flex items-center gap-3 px-6 py-2.5">
        <div
          className="flex size-8 shrink-0 items-center justify-center rounded-md"
          style={{
            background:
              "linear-gradient(135deg, oklch(0.72 0.2 350 / 22%), oklch(0.62 0.22 295 / 18%), oklch(0.72 0.13 195 / 22%))",
          }}
        >
          <Users className="size-4 text-foreground" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-muted-foreground">
            Active team
          </p>
          <h2 className="truncate text-sm font-medium">{team.name}</h2>
        </div>
        <div className="hidden items-center gap-3 text-[10px] text-muted-foreground sm:flex">
          <div className="flex items-center gap-1">
            <Users className="size-3" />
            <span className="font-mono tabular-nums">{memberCount}</span>
            <span>members</span>
          </div>
          <div className="flex items-center gap-1">
            <Cpu className="size-3" />
            <code className="font-mono">{modelLabel}</code>
          </div>
          <div className="flex items-center gap-1">
            <Radar className="size-3" />
            <span className="capitalize">{routingLabel}</span>
          </div>
          <div
            className={
              "flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono tabular-nums " +
              (overCap
                ? "border-destructive/50 bg-destructive/10 text-destructive"
                : spent > 0
                ? "border-[color:var(--brand-pink)]/40 bg-[color:var(--brand-pink)]/5 text-foreground"
                : "border-border/60")
            }
            title="Credits spent on this team run"
          >
            <span>{spent}</span>
            {cap != null && <span className="text-muted-foreground">/ {cap}</span>}
            <span className="text-muted-foreground"> cr</span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 text-xs"
          asChild
        >
          <Link href={`/boards/${boardId}/agent-creator`}>
            Configure
          </Link>
        </Button>
        <Button variant="ghost" size="icon" className="size-7" asChild title="Exit team">
          <Link href={`/boards/${boardId}`} aria-label="Exit team">
            <X className="size-3.5" />
          </Link>
        </Button>
      </div>
    </div>
  )
}
