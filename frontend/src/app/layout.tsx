import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "Prism Agents",
  description: "AI creative agents that make you prolific",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    // Font variables must live on <html> so @theme inline can resolve them
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable}`}>
      <body className="h-full antialiased">
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  )
}
