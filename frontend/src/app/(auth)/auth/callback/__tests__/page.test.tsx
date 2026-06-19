import { render, waitFor } from "@testing-library/react"
import { vi, Mock } from "vitest"
import AuthCallback from "../page"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuthStore } from "@/stores"
import { api } from "@/lib/api"

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
}))

// Mock api
vi.mock("@/lib/api", () => ({
  api: {
    auth: {
      githubCallback: vi.fn(),
    },
  },
}))

// Mock stores
vi.mock("@/stores", () => ({
  useAuthStore: vi.fn(),
}))

describe("AuthCallback", () => {
  const mockPush = vi.fn()
  const mockSetAuth = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, "error").mockImplementation(() => {}) // Suppress console.error in tests

    ;(useRouter as Mock).mockReturnValue({ push: mockPush })
    ;(useAuthStore as unknown as Mock).mockImplementation((selector: (state: { setAuth: Mock }) => Mock) => selector({ setAuth: mockSetAuth }))
  })

  afterEach(() => {
    localStorage.clear()
  })

  it("should handle successful authentication", async () => {
    ;(useSearchParams as Mock).mockReturnValue({
      get: (key: string) => {
        if (key === "code") return "test-code"
        if (key === "state") return "test-state"
        return null
      }
    })

    localStorage.setItem("oauth_state", "test-state")

    const mockUser = { id: "1", username: "testuser" }
    ;(api.auth.githubCallback as Mock).mockResolvedValueOnce({
      access_token: "test-token",
      user: mockUser
    })

    render(<AuthCallback />)

    await waitFor(() => {
      expect(api.auth.githubCallback).toHaveBeenCalledWith("test-code", "test-state")
      expect(mockSetAuth).toHaveBeenCalledWith("test-token", mockUser)
      expect(localStorage.getItem("oauth_state")).toBeNull()
      expect(mockPush).toHaveBeenCalledWith("/boards")
    })
  })

  it("should handle missing code parameter", () => {
    ;(useSearchParams as Mock).mockReturnValue({
      get: (key: string) => {
        if (key === "state") return "test-state"
        return null
      }
    })

    localStorage.setItem("oauth_state", "test-state")

    render(<AuthCallback />)

    expect(console.error).toHaveBeenCalledWith("Invalid state parameter or missing code.")
    expect(mockPush).toHaveBeenCalledWith("/login")
    expect(api.auth.githubCallback).not.toHaveBeenCalled()
  })

  it("should handle invalid state parameter", () => {
    ;(useSearchParams as Mock).mockReturnValue({
      get: (key: string) => {
        if (key === "code") return "test-code"
        if (key === "state") return "invalid-state"
        return null
      }
    })

    localStorage.setItem("oauth_state", "valid-state")

    render(<AuthCallback />)

    expect(console.error).toHaveBeenCalledWith("Invalid state parameter or missing code.")
    expect(mockPush).toHaveBeenCalledWith("/login")
    expect(api.auth.githubCallback).not.toHaveBeenCalled()
  })

  it("should handle API rejection", async () => {
    ;(useSearchParams as Mock).mockReturnValue({
      get: (key: string) => {
        if (key === "code") return "test-code"
        if (key === "state") return "test-state"
        return null
      }
    })

    localStorage.setItem("oauth_state", "test-state")

    const mockError = new Error("API Error")
    ;(api.auth.githubCallback as Mock).mockRejectedValueOnce(mockError)

    render(<AuthCallback />)

    await waitFor(() => {
      expect(api.auth.githubCallback).toHaveBeenCalledWith("test-code", "test-state")
      expect(console.error).toHaveBeenCalledWith("Auth callback failed:", mockError)
      expect(mockPush).toHaveBeenCalledWith("/login")
      expect(mockSetAuth).not.toHaveBeenCalled()
    })
  })
})
