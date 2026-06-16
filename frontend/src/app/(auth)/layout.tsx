"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"
import { useAuthStore } from "@/stores"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
