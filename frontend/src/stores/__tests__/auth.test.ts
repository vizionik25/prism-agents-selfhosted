import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '../index'
import { api } from '@/lib/api'

// Mock the API
vi.mock('@/lib/api', () => ({
  api: {
    auth: {
      me: vi.fn(),
    },
  },
}))

describe('useAuthStore', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()

    // Reset store state
    useAuthStore.setState({
      user: null,
      token: null,
      isLoading: true,
    })

    // Reset mocks
    vi.clearAllMocks()

    // Disable DEMO_MODE for standard tests
    process.env.NEXT_PUBLIC_DEMO_MODE = 'false'
  })

  it('should have correct initial state', () => {
    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
    expect(state.isLoading).toBe(true)
  })

  it('setAuth should set user, token and update localStorage', () => {
    const mockUser = { id: '1', username: 'testuser', email: 'test@example.com', avatar_url: null }
    const token = 'test-token'

    useAuthStore.getState().setAuth(token, mockUser)

    const state = useAuthStore.getState()
    expect(state.user).toEqual(mockUser)
    expect(state.token).toEqual(token)
    expect(localStorage.getItem('token')).toBe(token)
  })

  it('logout should clear user, token and localStorage', () => {
    const mockUser = { id: '1', username: 'testuser', email: 'test@example.com', avatar_url: null }
    useAuthStore.setState({ user: mockUser, token: 'test-token', isLoading: false })
    localStorage.setItem('token', 'test-token')

    useAuthStore.getState().logout()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('checkAuth should set isLoading to false if no token in localStorage', async () => {
    await useAuthStore.getState().checkAuth()

    const state = useAuthStore.getState()
    expect(state.isLoading).toBe(false)
    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
  })

  it('checkAuth should fetch user and set state if token exists', async () => {
    const mockUser = { id: '1', username: 'testuser', email: 'test@example.com', avatar_url: null }
    localStorage.setItem('token', 'valid-token')

    // Setup mock return value
    vi.mocked(api.auth.me).mockResolvedValueOnce(mockUser)

    await useAuthStore.getState().checkAuth()

    const state = useAuthStore.getState()
    expect(state.isLoading).toBe(false)
    expect(state.user).toEqual(mockUser)
    expect(state.token).toBe('valid-token')
    expect(api.auth.me).toHaveBeenCalledTimes(1)
  })

  it('checkAuth should clear state and localStorage if api.auth.me fails', async () => {
    localStorage.setItem('token', 'invalid-token')
    useAuthStore.setState({ token: 'invalid-token' })

    // Setup mock to throw error
    vi.mocked(api.auth.me).mockRejectedValueOnce(new Error('Invalid token'))

    await useAuthStore.getState().checkAuth()

    const state = useAuthStore.getState()
    expect(state.isLoading).toBe(false)
    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
    expect(api.auth.me).toHaveBeenCalledTimes(1)
  })
})
