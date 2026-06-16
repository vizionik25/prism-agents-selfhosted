"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuthStore } from "@/stores"
import { api, type AdminUserDetail, type AdminApiKey } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ArrowLeft, Shield, Key, CreditCard, UserCog, Loader2 } from "lucide-react"

export default function AdminUserDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user: currentUser, token, isLoading: authLoading } = useAuthStore()
  const userId = params.id as string

  const [userDetail, setUserDetail] = useState<AdminUserDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Forms states
  const [selectedTier, setSelectedTier] = useState("")
  const [subCreditsInput, setSubCreditsInput] = useState("")
  const [packCreditsInput, setPackCreditsInput] = useState("")
  const [selectedRole, setSelectedRole] = useState("")

  // Status feedback
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  // Confirmation modals
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean
    title: string
    description: string
    onConfirm: () => Promise<void>
  }>({
    open: false,
    title: "",
    description: "",
    onConfirm: async () => {},
  })

  // Redirect if not admin/super_admin
  useEffect(() => {
    if (!authLoading) {
      if (!currentUser || (currentUser.role !== "ADMIN" && currentUser.role !== "SUPER_ADMIN")) {
        router.replace("/boards")
      }
    }
  }, [currentUser, authLoading, router])

  const loadUserDetail = async () => {
    if (!token || !userId) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.admin.getUser(userId)
      setUserDetail(res)
      setSelectedTier(res.subscription_tier)
      setSubCreditsInput(String(res.subscription_credits))
      setPackCreditsInput("0") // standard behavior: grant pack delta
      setSelectedRole(res.role)
    } catch (err: any) {
      console.error(err)
      setError(err.message || "Failed to load user detail")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (currentUser && (currentUser.role === "ADMIN" || currentUser.role === "SUPER_ADMIN")) {
      loadUserDetail()
    }
  }, [userId, token, currentUser])

  const triggerAction = (
    title: string,
    description: string,
    onConfirm: () => Promise<void>
  ) => {
    setConfirmModal({
      open: true,
      title,
      description,
      onConfirm: async () => {
        setActionLoading(true)
        setSuccessMessage(null)
        setActionError(null)
        try {
          await onConfirm()
        } catch (err: any) {
          console.error(err)
          setActionError(err.message || "Action failed")
        } finally {
          setActionLoading(false)
          setConfirmModal((prev) => ({ ...prev, open: false }))
        }
      },
    })
  }

  const handleTierChange = () => {
    if (selectedTier === userDetail?.subscription_tier) return
    triggerAction(
      "Change Subscription Tier",
      `Are you sure you want to change this user's subscription tier to ${selectedTier}? This will reset their subscription credits.`,
      async () => {
        const updated = await api.admin.changeTier(userId, selectedTier)
        setUserDetail((prev) => prev ? { ...prev, ...updated } : null)
        setSuccessMessage(`Subscription tier successfully updated to ${selectedTier}.`)
      }
    )
  }

  const handleGrantCredits = () => {
    const subCredits = subCreditsInput !== "" ? parseInt(subCreditsInput, 10) : undefined
    const packCredits = packCreditsInput !== "" && packCreditsInput !== "0" ? parseInt(packCreditsInput, 10) : undefined

    if (subCredits === undefined && packCredits === undefined) return
    if (subCredits === userDetail?.subscription_credits && (packCredits === undefined || packCredits === 0)) return

    triggerAction(
      "Grant Credits",
      "Are you sure you want to grant these credits? Pack credits will be added to their existing balance, and subscription credits will be set to the new value.",
      async () => {
        const updated = await api.admin.grantCredits(userId, {
          subscription_credits: subCredits,
          pack_credits: packCredits,
        })
        setUserDetail((prev) => prev ? { ...prev, ...updated } : null)
        setPackCreditsInput("0") // reset pack delta input
        setSuccessMessage("Credits successfully granted.")
      }
    )
  }

  const handleRoleChange = () => {
    if (selectedRole === userDetail?.role) return
    triggerAction(
      "Change User Role",
      `Are you sure you want to change this user's role to ${selectedRole}?`,
      async () => {
        const updated = await api.admin.changeRole(userId, selectedRole)
        setUserDetail((prev) => prev ? { ...prev, ...updated } : null)
        setSuccessMessage(`User role successfully changed to ${selectedRole}.`)
      }
    )
  }

  const handleRevokeKey = (keyId: string, name: string) => {
    triggerAction(
      "Revoke API Key",
      `Are you sure you want to revoke the API key "${name}"? This action cannot be undone and external clients using this key will immediately be blocked.`,
      async () => {
        await api.admin.revokeApiKey(userId, keyId)
        // Refresh details to show revoked state
        const fresh = await api.admin.getUser(userId)
        setUserDetail(fresh)
        setSuccessMessage(`API key "${name}" successfully revoked.`)
      }
    )
  }

  // Guard: if not authenticated as admin, don't show content
  if (authLoading || !currentUser || (currentUser.role !== "ADMIN" && currentUser.role !== "SUPER_ADMIN")) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto space-y-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading user details...
        </div>
      </div>
    )
  }

  if (error || !userDetail) {
    return (
      <div className="p-8 max-w-5xl mx-auto space-y-6">
        <Button variant="ghost" onClick={() => router.push("/admin/users")} className="flex items-center gap-2 pl-0">
          <ArrowLeft className="w-4 h-4" /> Back to users list
        </Button>
        <div className="p-4 bg-destructive/15 text-destructive rounded-lg text-sm">
          {error || "User not found"}
        </div>
      </div>
    )
  }

  const isSuperAdmin = currentUser.role === "SUPER_ADMIN"

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      {/* Back button */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.push("/admin/users")} className="flex items-center gap-2 pl-0 hover:bg-transparent">
          <ArrowLeft className="w-4 h-4" /> Back to users
        </Button>
      </div>

      {/* Header Info */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 justify-between border-b pb-6">
        <div className="flex items-center gap-4">
          <Avatar className="w-16 h-16 border-2 border-primary/20">
            <AvatarImage src={userDetail.avatar_url || ""} />
            <AvatarFallback className="text-xl font-bold bg-muted">
              {userDetail.username?.[0]?.toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              {userDetail.username}
              <Badge variant={userDetail.role === "SUPER_ADMIN" ? "default" : "secondary"}>
                {userDetail.role.replace("_", " ")}
              </Badge>
            </h1>
            <p className="text-muted-foreground text-sm">{userDetail.email}</p>
            <p className="text-xs text-muted-foreground mt-1">ID: {userDetail.id}</p>
          </div>
        </div>
        <div className="text-sm text-muted-foreground text-left sm:text-right">
          <p>Joined: {userDetail.created_at ? new Date(userDetail.created_at).toLocaleDateString() : "Unknown"}</p>
          <p className="mt-1">
            Credits Reset:{" "}
            {userDetail.credits_reset_at
              ? new Date(userDetail.credits_reset_at).toLocaleDateString()
              : "Never"}
          </p>
        </div>
      </div>

      {/* Feedback Messages */}
      {successMessage && (
        <div className="p-4 bg-green-500/10 border border-green-500/25 text-green-500 rounded-lg text-sm font-medium">
          {successMessage}
        </div>
      )}
      {actionError && (
        <div className="p-4 bg-destructive/10 border border-destructive/25 text-destructive rounded-lg text-sm font-medium">
          {actionError}
        </div>
      )}

      {/* User Actions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Subscription Card */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-3">
            <CreditCard className="w-5 h-5 text-primary" />
            <div>
              <CardTitle className="text-base">Subscription Plan</CardTitle>
              <CardDescription>Update current user tier</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-muted-foreground">Subscription Tier</label>
              <select
                value={selectedTier}
                onChange={(e) => setSelectedTier(e.target.value)}
                className="bg-background border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-primary w-full"
              >
                <option value="FREE_TRIAL">Free Trial</option>
                <option value="STARTER">Starter</option>
                <option value="PLUS">Plus</option>
                <option value="PRO">Pro</option>
                <option value="ENTERPRISE">Enterprise</option>
              </select>
            </div>
            <Button
              onClick={handleTierChange}
              disabled={selectedTier === userDetail.subscription_tier || actionLoading}
              className="w-full"
            >
              {actionLoading ? "Updating..." : "Update Tier"}
            </Button>
          </CardContent>
        </Card>

        {/* Credits Management Card */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-3">
            <Shield className="w-5 h-5 text-primary" />
            <div>
              <CardTitle className="text-base">Grant Credits</CardTitle>
              <CardDescription>Adjust subscription and pack credits</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Sub Credits (Set)</label>
                <Input
                  type="number"
                  min="0"
                  value={subCreditsInput}
                  onChange={(e) => setSubCreditsInput(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Pack Credits (Add)</label>
                <Input
                  type="number"
                  min="0"
                  value={packCreditsInput}
                  onChange={(e) => setPackCreditsInput(e.target.value)}
                />
              </div>
            </div>
            <Button
              onClick={handleGrantCredits}
              disabled={actionLoading}
              className="w-full font-medium"
            >
              {actionLoading ? "Processing..." : "Grant Credits"}
            </Button>
          </CardContent>
        </Card>

        {/* Role Management Card (Super Admin Only) */}
        {isSuperAdmin && (
          <Card>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-3">
              <UserCog className="w-5 h-5 text-primary" />
              <div>
                <CardTitle className="text-base">System Access Role</CardTitle>
                <CardDescription>Grant admin or super admin privileges</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-muted-foreground">Role</label>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="bg-background border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-hidden focus:ring-2 focus:ring-primary w-full"
                >
                  <option value="USER">User (Regular Access)</option>
                  <option value="ADMIN">Admin (Dashboard & Logs Access)</option>
                  <option value="SUPER_ADMIN">Super Admin (Full System Privileges)</option>
                </select>
              </div>
              <Button
                onClick={handleRoleChange}
                disabled={selectedRole === userDetail.role || actionLoading}
                className="w-full"
              >
                {actionLoading ? "Updating..." : "Update Role"}
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* API Keys Table Card */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-3">
          <Key className="w-5 h-5 text-primary" />
          <div>
            <CardTitle className="text-base">User API Keys</CardTitle>
            <CardDescription>Monitor and revoke programmatic access keys</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-hidden">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="p-4 font-medium text-muted-foreground">Key Name</th>
                  <th className="p-4 font-medium text-muted-foreground">Prefix</th>
                  <th className="p-4 font-medium text-muted-foreground">Created</th>
                  <th className="p-4 font-medium text-muted-foreground">Last Used</th>
                  <th className="p-4 font-medium text-muted-foreground">Status</th>
                  <th className="p-4 font-medium text-muted-foreground text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {userDetail.api_keys.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-muted-foreground">
                      No active or revoked API keys for this user.
                    </td>
                  </tr>
                ) : (
                  userDetail.api_keys.map((k) => {
                    const isRevoked = k.revoked_at !== null
                    return (
                      <tr key={k.id} className="hover:bg-muted/20">
                        <td className="p-4 font-medium">{k.name}</td>
                        <td className="p-4 font-mono text-xs">{k.key_prefix}</td>
                        <td className="p-4 text-muted-foreground">
                          {k.created_at ? new Date(k.created_at).toLocaleDateString() : "-"}
                        </td>
                        <td className="p-4 text-muted-foreground">
                          {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                        </td>
                        <td className="p-4">
                          <Badge variant={isRevoked ? "destructive" : "outline"}>
                            {isRevoked ? "Revoked" : "Active"}
                          </Badge>
                        </td>
                        <td className="p-4 text-right">
                          {!isRevoked && (
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleRevokeKey(k.id, k.name)}
                              disabled={actionLoading}
                            >
                              Revoke
                            </Button>
                          )}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <Dialog open={confirmModal.open} onOpenChange={(open) => !open && setConfirmModal((prev) => ({ ...prev, open: false }))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{confirmModal.title}</DialogTitle>
            <DialogDescription>{confirmModal.description}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmModal((prev) => ({ ...prev, open: false }))}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmModal.onConfirm}
              disabled={actionLoading}
            >
              {actionLoading ? "Processing..." : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
