"use client"

import { useEffect, useState } from "react"
import { ExternalLink, Copy, Trash2, Image, Film, FileText, Loader2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useHistoryStore } from "@/stores"
import { api, type Generation } from "@/lib/api"

interface HistoryPanelProps {
  boardId: string
}

export function HistoryPanel({ boardId }: HistoryPanelProps) {
  const { generations, setGenerations, selectedGeneration, setSelectedGeneration } = useHistoryStore()
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)

  const loadGenerations = async () => {
    try {
      const { generations } = await api.generations.list(boardId)
      setGenerations(generations)
    } catch (error) {
      console.error("Failed to load generations:", error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadGenerations()
  }, [boardId])

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this generation?")) return

    setIsDeleting(true)
    try {
      await api.generations.delete(id)
      setGenerations(generations.filter((g) => g.id !== id))
      if (selectedGeneration?.id === id) {
        setSelectedGeneration(null)
      }
    } catch (error) {
      console.error("Failed to delete generation:", error)
    } finally {
      setIsDeleting(false)
    }
  }

  const getTypeIcon = (type: string | null) => {
    switch (type) {
      case "image":
        return <Image className="w-4 h-4" />
      case "video":
        return <Film className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500"
      case "failed":
        return "bg-red-500"
      case "processing":
        return "bg-yellow-500"
      default:
        return "bg-gray-500"
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full">
        <div className="w-80 border-r p-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-48" />
              <Skeleton className="h-20 w-full" />
            </div>
          ))}
        </div>
        <div className="flex-1 p-8">
          <Skeleton className="h-64 w-full max-w-md" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full">
      <div className="w-80 border-r p-4 overflow-auto">
        <h3 className="font-semibold mb-4">Generation History</h3>
        {generations.length === 0 ? (
          <p className="text-sm text-muted-foreground">No generations yet</p>
        ) : (
          <div className="space-y-3">
            {generations.map((gen) => (
              <Card
                key={gen.id}
                className={`cursor-pointer transition-colors ${
                  selectedGeneration?.id === gen.id ? "ring-2 ring-primary" : ""
                }`}
                onClick={() => setSelectedGeneration(gen)}
              >
                <CardHeader className="p-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(gen.status)}`} />
                    <Badge variant="secondary" className="text-xs">
                      {getTypeIcon(gen.result_type)}
                      <span className="ml-1">{gen.result_type || "text"}</span>
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-3 pt-0">
                  <p className="text-sm line-clamp-2">{gen.prompt}</p>
                  <p className="text-xs text-muted-foreground mt-2">{formatDate(gen.created_at)}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 p-8 overflow-auto">
        {selectedGeneration ? (
          <div className="max-w-2xl mx-auto space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-2">Generation Details</h2>
              <p className="text-muted-foreground">{selectedGeneration.prompt}</p>
            </div>

            <Separator />

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Result</h3>
                <div className="flex gap-2">
                  {selectedGeneration.result_url && (
                    <>
                      <Button variant="outline" size="sm" asChild>
                        <a href={selectedGeneration.result_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="w-4 h-4 mr-2" />
                          Open
                        </a>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigator.clipboard.writeText(selectedGeneration.result_url!)}
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        Copy URL
                      </Button>
                    </>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive"
                    onClick={() => handleDelete(selectedGeneration.id)}
                    disabled={isDeleting}
                    aria-label="Delete generation"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />
                    ) : (
                      <Trash2 className="w-4 h-4 mr-2" aria-hidden="true" />
                    )}
                    {isDeleting ? "Deleting..." : "Delete"}
                  </Button>
                </div>
              </div>

              {selectedGeneration.result_url && (
                selectedGeneration.result_type === "image" ? (
                  <div className="rounded-lg overflow-hidden border">
                    <img
                      src={selectedGeneration.result_url}
                      alt="Generated image"
                      className="w-full h-auto"
                    />
                  </div>
                ) : selectedGeneration.result_type === "video" ? (
                  <div className="rounded-lg overflow-hidden border">
                    <video
                      src={selectedGeneration.result_url}
                      controls
                      className="w-full"
                    />
                  </div>
                ) : (
                  <Card>
                    <CardContent className="p-4">
                      <p className="whitespace-pre-wrap">{selectedGeneration.result_url}</p>
                    </CardContent>
                  </Card>
                )
              )}

              {!selectedGeneration.result_url && selectedGeneration.status === "completed" && (
                <p className="text-muted-foreground">No result URL available</p>
              )}
            </div>

            {selectedGeneration.variants.length > 0 && (
              <>
                <Separator />
                <div>
                  <h3 className="font-medium mb-4">Variants ({selectedGeneration.variants.length})</h3>
                  <div className="grid grid-cols-3 gap-4">
                    {selectedGeneration.variants.map((variant) => (
                      <div key={variant.id} className="rounded-lg overflow-hidden border">
                        {variant.result_url ? (
                          variant.result_type === "image" ? (
                            <img src={variant.result_url} alt={`Variant ${variant.variant_index}`} />
                          ) : (
                            <video src={variant.result_url} controls className="w-full" />
                          )
                        ) : (
                          <div className="aspect-square bg-muted flex items-center justify-center">
                            <p className="text-sm text-muted-foreground">No preview</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-muted-foreground">Select a generation to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
