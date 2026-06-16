"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Plus, MoreHorizontal, Trash2, Clock } from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { useBoardStore } from "@/stores"
import { api } from "@/lib/api"

export default function DashboardPage() {
  const { boards, setBoards, addBoard, updateBoard, removeBoard } = useBoardStore()
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newBoardName, setNewBoardName] = useState("")
  const [newBoardDescription, setNewBoardDescription] = useState("")

  useEffect(() => {
    loadBoards()
  }, [])

  const loadBoards = async () => {
    try {
      const { boards } = await api.boards.list()
      setBoards(boards)
    } catch (error) {
      console.error("Failed to load boards:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateBoard = async () => {
    if (!newBoardName.trim()) return

    try {
      const board = await api.boards.create({
        name: newBoardName,
        description: newBoardDescription || undefined,
      })
      addBoard(board)
      setIsCreateOpen(false)
      setNewBoardName("")
      setNewBoardDescription("")
    } catch (error) {
      console.error("Failed to create board:", error)
    }
  }

  const handleDeleteBoard = async (id: string) => {
    try {
      await api.boards.delete(id)
      removeBoard(id)
    } catch (error) {
      console.error("Failed to delete board:", error)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Boards</h1>
          <p className="text-muted-foreground mt-1">Create and manage your creative projects</p>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger
            render={
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                New Board
              </Button>
            }
          />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Board</DialogTitle>
              <DialogDescription>
                Give your board a name and optional description
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Input
                  placeholder="Board name"
                  value={newBoardName}
                  onChange={(e) => setNewBoardName(e.target.value)}
                />
                <Textarea
                  placeholder="Description (optional)"
                  value={newBoardDescription}
                  onChange={(e) => setNewBoardDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateBoard}>Create Board</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48 mt-2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : boards.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <p className="text-muted-foreground mb-4">No boards yet</p>
            <Button onClick={() => setIsCreateOpen(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Board
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {boards.map((board) => (
            <Card key={board.id} className="group">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <Link href={`/boards/${board.id}`} className="flex-1">
                    <CardTitle className="group-hover:text-primary transition-colors">
                      {board.name}
                    </CardTitle>
                  </Link>
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      className="opacity-0 group-hover:opacity-100 rounded-full"
                      render={
                        <Button variant="ghost" size="icon" aria-label="Board options">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      }
                    />
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => handleDeleteBoard(board.id)}
                        className="text-destructive"
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                {board.description && (
                  <CardDescription className="line-clamp-2">{board.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex items-center text-xs text-muted-foreground">
                  <Clock className="w-3 h-3 mr-1" />
                  {formatDate(board.updated_at)}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
