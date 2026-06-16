"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, LogOut, Sparkles, Ghost, CreditCard, Shield } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuthStore, useBillingStore } from "@/stores"
import { api } from "@/lib/api"
import { UpgradeModal } from "@/components/billing/upgrade-modal"

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
const SELF_HOSTED = process.env.NEXT_PUBLIC_SELF_HOSTED === "true"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, token, isLoading, logout, checkAuth } = useAuthStore()
  const { subscriptionCredits, packCredits, fetchStatus, isLoaded } = useBillingStore()
  const [upgradeOpen, setUpgradeOpen] = useState(false)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  useEffect(() => {
    if (token && !isLoaded) fetchStatus()
  }, [token, isLoaded, fetchStatus])

  useEffect(() => {
    if (DEMO_MODE || SELF_HOSTED) return  // no upgrade modal in demo mode or self-hosted
    const handler = () => setUpgradeOpen(true)
    window.addEventListener("insufficient_credits", handler)
    return () => window.removeEventListener("insufficient_credits", handler)
  }, [])

  useEffect(() => {
    if (DEMO_MODE) return  // never redirect to login in demo mode
    if (!isLoading && !token) {
      router.push("/login")
    }
  }, [isLoading, token, router])

  if (isLoading || !token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Ghost className="w-8 h-8 animate-pulse text-primary" />
      </div>
    )
  }

  const handleLogout = async () => {
    if (DEMO_MODE) return  // no logout in demo mode
    try {
      await api.auth.logout()
    } catch {}
    logout()
    router.push("/login")
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 border-r bg-card flex flex-col">
        <div className="p-4 border-b">
          <Link href="/boards" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-linear-to-br from-primary via-brand-pink to-accent flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-lg bg-linear-to-r from-primary via-brand-pink to-accent bg-clip-text text-transparent">
              Prism Agents
            </span>
          </Link>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          <Link
            href="/boards"
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              pathname === "/boards"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            Boards
          </Link>
          {!DEMO_MODE && (
            <>
              {!SELF_HOSTED && (
                <>
                  <Link
                    href="/settings/billing"
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      pathname === "/settings/billing"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <CreditCard className="w-4 h-4" />
                    Billing
                  </Link>
                  <button
                    onClick={() => setUpgradeOpen(true)}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm w-full text-left text-muted-foreground"
                  >
                    <span className="text-xs">Credits:</span>
                    <span className="text-xs font-bold" style={{ color: "#00f5ff" }}>
                      {subscriptionCredits + packCredits}
                    </span>
                  </button>
                </>
              )}
              {user?.role && user.role !== "USER" && (
                <Link
                  href="/admin/users"
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    pathname?.startsWith("/admin")
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <Shield className="w-4 h-4" />
                  Admin
                </Link>
              )}
            </>
          )}
        </nav>

        {!DEMO_MODE && !SELF_HOSTED && (
          <div className="p-4 border-t">
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-3 w-full p-2 rounded-lg hover:bg-muted transition-colors">
                <Avatar className="w-8 h-8">
                  <AvatarImage src={user?.avatar_url || ""} />
                  <AvatarFallback>{user?.username?.[0]?.toUpperCase()}</AvatarFallback>
                </Avatar>
                <div className="flex-1 text-left">
                  <p className="text-sm font-medium">{user?.username}</p>
                  <p className="text-xs text-muted-foreground">{user?.email}</p>
                </div>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                  <LogOut className="w-4 h-4 mr-2" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </aside>

      <main className="flex-1 overflow-auto">{children}</main>
      {!DEMO_MODE && !SELF_HOSTED && <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} />}
    </div>
  )
}
