"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Sparkles, Mail, Lock, User as UserIcon, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import { useAuthStore } from "@/stores"

const GithubIcon = (props: React.SVGProps<SVGSVGElement>) => (
  <svg
    viewBox="0 0 24 24"
    width="24"
    height="24"
    stroke="currentColor"
    strokeWidth="2"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={props.className}
    {...props}
  >
    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
  </svg>
)

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
const SELF_HOSTED = process.env.NEXT_PUBLIC_SELF_HOSTED === "true"
const ENABLE_GITHUB_AUTH = process.env.NEXT_PUBLIC_ENABLE_GITHUB_AUTH !== "false"

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [isLoading, setIsLoading] = useState(false)
  const [authMode, setAuthMode] = useState<"login" | "register">("login")
  
  // Local auth fields
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [errorMsg, setErrorMsg] = useState("")

  useEffect(() => {
    if (DEMO_MODE) {
      router.replace("/boards")
    }
  }, [router])

  if (DEMO_MODE) return null

  const handleGithubLogin = async () => {
    setIsLoading(true)
    setErrorMsg("")
    try {
      const { url, state } = await api.auth.githubLogin()
      localStorage.setItem("oauth_state", state)
      window.location.href = url
    } catch (error: any) {
      console.error("Login failed:", error)
      setErrorMsg(error.message || "Failed to initiate GitHub login")
      setIsLoading(false)
    }
  }

  const handleLocalSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setErrorMsg("")

    try {
      if (authMode === "register") {
        if (!username || !email || !password) {
          throw new Error("All fields are required")
        }
        if (password !== confirmPassword) {
          throw new Error("Passwords do not match")
        }
        const response = await api.auth.register({
          username,
          email,
          password,
        })
        setAuth(response.access_token, response.user)
        router.replace("/boards")
      } else {
        if (!email || !password) {
          throw new Error("Credentials are required")
        }
        const response = await api.auth.login({
          email_or_username: email,
          password,
        })
        setAuth(response.access_token, response.user)
        router.replace("/boards")
      }
    } catch (error: any) {
      console.error("Authentication failed:", error)
      setErrorMsg(error.message || "Authentication failed. Please check your credentials.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-background via-background to-muted/30 p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-primary/25 blur-3xl" />
        <div className="absolute top-1/3 -left-20 w-72 h-72 rounded-full bg-accent/25 blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 w-80 h-80 rounded-full bg-brand-pink/25 blur-3xl" />
      </div>

      <Card className="w-full max-w-md relative border-0 shadow-2xl">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-linear-to-br from-primary via-brand-pink to-accent flex items-center justify-center shadow-lg">
            <Sparkles className="w-8 h-8 text-primary-foreground" />
          </div>
          <div>
            <CardTitle className="text-3xl font-bold tracking-tight bg-linear-to-r from-primary via-brand-pink to-accent bg-clip-text text-transparent">
              Prism Agents
            </CardTitle>
            <CardDescription className="text-base mt-2">
              Creative agents that make you prolific
            </CardDescription>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {errorMsg && (
            <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-lg border border-destructive/20">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {SELF_HOSTED ? (
            <div className="space-y-4">
              {/* Login / Register Toggle */}
              <div className="flex border-b border-muted">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("login")
                    setErrorMsg("")
                  }}
                  className={`flex-1 pb-2 text-sm font-semibold border-b-2 transition-all ${
                    authMode === "login"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("register")
                    setErrorMsg("")
                  }}
                  className={`flex-1 pb-2 text-sm font-semibold border-b-2 transition-all ${
                    authMode === "register"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Register
                </button>
              </div>

              {/* Local Credentials Form */}
              <form onSubmit={handleLocalSubmit} className="space-y-4">
                {authMode === "register" && (
                  <div className="space-y-2">
                    <label htmlFor="username" className="text-sm font-medium">Username</label>
                    <div className="relative">
                      <UserIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="username"
                        type="text"
                        placeholder="john_doe"
                        className="pl-9"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium">
                    {authMode === "register" ? "Email Address" : "Email or Username"}
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="email"
                      type={authMode === "register" ? "email" : "text"}
                      placeholder={authMode === "register" ? "john@example.com" : "john@example.com or john_doe"}
                      className="pl-9"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      className="pl-9"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>

                {authMode === "register" && (
                  <div className="space-y-2">
                    <label htmlFor="confirmPassword" className="text-sm font-medium">Confirm Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="confirmPassword"
                        type="password"
                        placeholder="••••••••"
                        className="pl-9"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                      />
                    </div>
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-11 text-base font-medium mt-2 bg-linear-to-r from-primary to-accent"
                >
                  {isLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : authMode === "login" ? (
                    "Sign In"
                  ) : (
                    "Create Account"
                  )}
                </Button>
              </form>

              {/* Optional GitHub Divider & Button */}
              {ENABLE_GITHUB_AUTH && (
                <div className="space-y-4 pt-2">
                  <div className="relative flex items-center justify-center">
                    <div className="absolute inset-x-0 h-px bg-muted" />
                    <span className="relative bg-card px-3 text-xs text-muted-foreground uppercase">
                      Or continue with
                    </span>
                  </div>

                  <Button
                    onClick={handleGithubLogin}
                    disabled={isLoading}
                    variant="outline"
                    className="w-full h-11 text-sm font-medium"
                  >
                    <GithubIcon className="w-5 h-5 mr-2" />
                    GitHub
                  </Button>
                </div>
              )}
            </div>
          ) : (
            /* Cloud-only GitHub Button */
            <div className="space-y-4">
              <Button
                onClick={handleGithubLogin}
                disabled={isLoading}
                className="w-full h-12 text-base font-medium"
                size="lg"
              >
                {isLoading ? (
                  <span className="animate-pulse">Redirecting...</span>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5 mr-2" />
                    Continue with GitHub
                  </>
                )}
              </Button>
            </div>
          )}

          <p className="text-xs text-center text-muted-foreground pt-2">
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
