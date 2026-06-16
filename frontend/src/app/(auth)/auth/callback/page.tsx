"use client"

import { Suspense, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Loader2 } from "lucide-react"
import { api } from "@/lib/api"
import { useAuthStore } from "@/stores"

function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)

  useEffect(() => {
    const code = searchParams.get("code")
    const state = searchParams.get("state")
    const savedState = localStorage.getItem("oauth_state")

    // 🛡️ Sentinel: Validate state parameter to prevent CSRF attacks
    if (!code || !state || state !== savedState) {
      console.error("Invalid state parameter or missing code.")
      router.push("/login")
      return
    }

    const handleCallback = async () => {
      try {
        const result = await api.auth.githubCallback(code, state)
        setAuth(result.access_token, result.user)
        localStorage.removeItem("oauth_state")
        router.push("/boards")
      } catch (error) {
        console.error("Auth callback failed:", error)
        router.push("/login")
      }
    }

    handleCallback()
  }, [searchParams, setAuth, router])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-muted-foreground">Signing you in...</p>
      </div>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-muted-foreground">Loading...</p>
      </div>
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <AuthCallbackContent />
    </Suspense>
  )
}
