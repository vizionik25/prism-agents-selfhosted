"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import {
  ArrowLeft,
  MessageSquare,
  History,
  Wand2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { useBoardStore } from "@/stores"
import { api, type Team } from "@/lib/api"
import { ChatPanel } from "@/components/chat/chat-panel"
import { HistoryPanel } from "@/components/chat/history-panel"

export default function BoardPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const boardId = params.id as string
  const agentId = searchParams.get("agent_id") ?? undefined
  const capability = searchParams.get("capability") ?? undefined
  const teamId = searchParams.get("team_id") ?? undefined
  const { currentBoard, setCurrentBoard } = useBoardStore()
  const [isLoading, setIsLoading] = useState(true)
  const [activeTeam, setActiveTeam] = useState<Team | null>(null)

  useEffect(() => {
    loadBoard()
  }, [boardId])

  useEffect(() => {
    if (!teamId) {
      setActiveTeam(null)
      return
    }
    let cancelled = false
    api.teams
      .get(teamId)
      .then((t) => {
        if (!cancelled) setActiveTeam(t)
      })
      .catch(() => {
        if (!cancelled) setActiveTeam(null)
      })
    return () => {
      cancelled = true
    }
  }, [teamId])

  const loadBoard = async () => {
    try {
      const board = await api.boards.get(boardId)
      setCurrentBoard(board)
    } catch (error) {
      console.error("Failed to load board:", error)
      router.push("/")
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="h-screen flex">
        <div className="flex-1 flex items-center justify-center">
          <Skeleton className="w-64 h-8" />
        </div>
      </div>
    )
  }

  if (!currentBoard) {
    return (
      <div className="h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Board not found</p>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <header className="border-b bg-card px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild aria-label="Go back">
            <Link href="/">
              <ArrowLeft className="w-4 h-4" />
            </Link>
          </Button>
          <div className="flex-1">
            <h1 className="text-xl font-semibold">{currentBoard.name}</h1>
            {currentBoard.description && (
              <p className="text-sm text-muted-foreground">{currentBoard.description}</p>
            )}
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="chat" className="h-full flex flex-col">
          <TabsList className="w-full justify-start rounded-none border-b bg-background px-4">
            <TabsTrigger value="chat" className="gap-2">
              <MessageSquare className="w-4 h-4" />
              Chat
            </TabsTrigger>
            <TabsTrigger value="history" className="gap-2">
              <History className="w-4 h-4" />
              History
            </TabsTrigger>
            <TabsTrigger value="agents" className="gap-2" asChild>
              <Link href={`/boards/${boardId}/agent-creator`}>
                <Wand2 className="w-4 h-4" />
                Agents
              </Link>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chat" className="flex-1 m-0">
            <ChatPanel
              boardId={boardId}
              agentId={agentId}
              capability={capability}
              teamId={teamId}
              activeTeam={activeTeam}
            />
          </TabsContent>

          <TabsContent value="history" className="flex-1 m-0">
            <HistoryPanel boardId={boardId} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
