"use client"

import Link from "next/link"
import { Shield, ArrowLeft, ExternalLink } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"

export default function EnterpriseLicensePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const returnTo = searchParams.get("returnTo") || "/boards"

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-[#05050a]">
      <div className="max-w-md w-full text-center">
        <div className="mb-6">
          <Shield className="w-16 h-16 mx-auto mb-4 text-[#00f5ff]" />
          <h1 className="text-3xl font-bold text-white mb-2">Enterprise License Required</h1>
          <p className="text-gray-400 text-lg">
            API endpoint access requires a valid PrismAgents Enterprise license.
          </p>
        </div>

        <div className="bg-[#0a0a14] border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-3">Coming Soon</h2>
          <p className="text-gray-400 mb-4">
            Self-hosted Enterprise licensing will be available for purchase on our website soon.
            For now, you can use all chat and generation features with your own API keys.
          </p>
          <p className="text-gray-500 text-sm">
            API key access will be unlocked once you configure a valid
            <code className="bg-gray-900 px-1.5 py-0.5 rounded text-[#00f5ff]">
              PRISM_LICENSE_KEY
            </code>
            in your environment.
          </p>
        </div>

        <div className="space-y-3">
          <Link
            href={returnTo}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-[#00f5ff] text-black font-semibold rounded-xl hover:opacity-90 transition-opacity"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <a
            href="https://prismagents.com/enterprise"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 px-6 py-3 border border-gray-700 text-white font-semibold rounded-xl hover:bg-gray-900 transition-colors"
          >
            Notify Me When Available
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>
    </div>
  )
}