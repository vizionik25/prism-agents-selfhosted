"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/stores"
import { api, type AdminUserSummary } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Search, ChevronLeft, ChevronRight, Loader2, Shield } from "lucide-react"

export default function AdminUsersPage() {
  const router = useRouter()
  const { user, token, isLoading: authLoading } = useAuthStore()
  
  const [users, setUsers] = useState<AdminUserSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [search, setSearch] = useState("")
  const [tierFilter, setTierFilter] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Redirect if not admin/super_admin
  useEffect(() => {
    if (!authLoading) {
      if (!user || (user.role !== "ADMIN" && user.role !== "SUPER_ADMIN")) {
        router.replace("/boards")
      }
    }
  }, [user, authLoading, router])

  const loadUsers = async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.admin.listUsers({
        search,
        tier: tierFilter || undefined,
        page,
        per_page: perPage,
      })
      setUsers(res.users)
      setTotal(res.total)
    } catch (err: any) {
      console.error(err)
      setError(err.message || "Failed to load users")
    } finally {
      setLoading(false)
    }
  }

  // Reload when page or filters change
  useEffect(() => {
    if (user && (user.role === "ADMIN" || user.role === "SUPER_ADMIN")) {
      loadUsers()
    }
  }, [page, tierFilter, token, user])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadUsers()
  }

  // Guard: if not authenticated as admin, don't show content
  if (authLoading || !user || (user.role !== "ADMIN" && user.role !== "SUPER_ADMIN")) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="w-8 h-8 text-primary" />
            Admin Users Management
          </h1>
          <p className="text-muted-foreground">Manage user subscriptions, credits, and roles.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
          <CardDescription>
            Search and filter users across subscription tiers.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Filters and search */}
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search username or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={tierFilter}
              onChange={(e) => {
                setTierFilter(e.target.value)
                setPage(1)
              }}
              className="bg-card border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-primary min-w-[150px]"
            >
              <option value="">All Tiers</option>
              <option value="FREE_TRIAL">Free Trial</option>
              <option value="STARTER">Starter</option>
              <option value="PLUS">Plus</option>
              <option value="PRO">Pro</option>
              <option value="ENTERPRISE">Enterprise</option>
            </select>
            <Button type="submit" variant="default">
              Search
            </Button>
          </form>

          {error && (
            <div className="p-4 bg-destructive/15 text-destructive rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Users Table */}
          <div className="rounded-md border overflow-x-auto">
            <table className="w-full text-sm border-collapse text-left">
              <thead>
                <tr className="border-b bg-muted/50 transition-colors">
                  <th className="p-4 font-medium text-muted-foreground">Username</th>
                  <th className="p-4 font-medium text-muted-foreground">Email</th>
                  <th className="p-4 font-medium text-muted-foreground">Role</th>
                  <th className="p-4 font-medium text-muted-foreground">Tier</th>
                  <th className="p-4 font-medium text-muted-foreground text-center">Sub Credits</th>
                  <th className="p-4 font-medium text-muted-foreground text-center">Pack Credits</th>
                  <th className="p-4 font-medium text-muted-foreground">Joined Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-muted-foreground">
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Loading users...
                      </div>
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-muted-foreground">
                      No users found.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr
                      key={u.id}
                      onClick={() => router.push(`/admin/users/${u.id}`)}
                      className="border-b hover:bg-muted/40 cursor-pointer transition-colors"
                    >
                      <td className="p-4 font-medium">{u.username}</td>
                      <td className="p-4 text-muted-foreground">{u.email}</td>
                      <td className="p-4">
                        <Badge
                          variant={
                            u.role === "SUPER_ADMIN"
                              ? "default"
                              : u.role === "ADMIN"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {u.role.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="p-4">
                        <Badge variant="outline" className="capitalize">
                          {u.subscription_tier.replace("_", " ").toLowerCase()}
                        </Badge>
                      </td>
                      <td className="p-4 text-center font-mono">{u.subscription_credits}</td>
                      <td className="p-4 text-center font-mono">{u.pack_credits}</td>
                      <td className="p-4 text-muted-foreground">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <span className="text-sm text-muted-foreground">
                Showing {((page - 1) * perPage) + 1} to {Math.min(page * perPage, total)} of {total} users
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                  disabled={page === totalPages}
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
