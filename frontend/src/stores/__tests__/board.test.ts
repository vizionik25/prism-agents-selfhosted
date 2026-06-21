import { describe, it, expect, beforeEach } from 'vitest'
import { useBoardStore } from '../index'
import { Board } from '@/lib/api'

describe('useBoardStore', () => {
  beforeEach(() => {
    // Reset store state
    useBoardStore.setState({
      boards: [],
      currentBoard: null,
    })
  })

  it('should have correct initial state', () => {
    const state = useBoardStore.getState()
    expect(state.boards).toEqual([])
    expect(state.currentBoard).toBeNull()
  })

  it('setBoards should update the boards list', () => {
    const mockBoards: Board[] = [
      { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] },
      { id: '2', name: 'Board 2', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] },
    ]

    useBoardStore.getState().setBoards(mockBoards)

    const state = useBoardStore.getState()
    expect(state.boards).toEqual(mockBoards)
  })

  it('setCurrentBoard should update the current board', () => {
    const mockBoard: Board = { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }

    useBoardStore.getState().setCurrentBoard(mockBoard)

    const state = useBoardStore.getState()
    expect(state.currentBoard).toEqual(mockBoard)
  })

  it('addBoard should prepend the new board to the list', () => {
    const initialBoards: Board[] = [
      { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] },
    ]
    useBoardStore.setState({ boards: initialBoards })

    const newBoard: Board = { id: '2', name: 'Board 2', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }
    useBoardStore.getState().addBoard(newBoard)

    const state = useBoardStore.getState()
    expect(state.boards).toHaveLength(2)
    expect(state.boards[0]).toEqual(newBoard)
    expect(state.boards[1]).toEqual(initialBoards[0])
  })

  it('updateBoard should update the board in the list', () => {
    const initialBoards: Board[] = [
      { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] },
      { id: '2', name: 'Board 2', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] },
    ]
    useBoardStore.setState({ boards: initialBoards })

    useBoardStore.getState().updateBoard('1', { name: 'Updated Board 1' })

    const state = useBoardStore.getState()
    expect(state.boards[0].name).toBe('Updated Board 1')
    expect(state.boards[1].name).toBe('Board 2')
  })

  it('updateBoard should update currentBoard if it matches', () => {
    const mockBoard: Board = { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }
    useBoardStore.setState({ boards: [mockBoard], currentBoard: mockBoard })

    useBoardStore.getState().updateBoard('1', { name: 'Updated Board 1' })

    const state = useBoardStore.getState()
    expect(state.boards[0].name).toBe('Updated Board 1')
    expect(state.currentBoard?.name).toBe('Updated Board 1')
  })

  it('updateBoard should not update currentBoard if id does not match', () => {
    const board1: Board = { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }
    const board2: Board = { id: '2', name: 'Board 2', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }
    useBoardStore.setState({ boards: [board1, board2], currentBoard: board1 })

    useBoardStore.getState().updateBoard('2', { name: 'Updated Board 2' })

    const state = useBoardStore.getState()
    expect(state.boards[1].name).toBe('Updated Board 2')
    expect(state.currentBoard).toEqual(board1)
  })

  it('removeBoard should remove the board from the list', () => {
    const initialBoards: Board[] = [
      { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] },
      { id: '2', name: 'Board 2', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] },
    ]
    useBoardStore.setState({ boards: initialBoards })

    useBoardStore.getState().removeBoard('1')

    const state = useBoardStore.getState()
    expect(state.boards).toHaveLength(1)
    expect(state.boards[0].id).toBe('2')
  })

  it('removeBoard should set currentBoard to null if it matches', () => {
    const mockBoard: Board = { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }
    useBoardStore.setState({ boards: [mockBoard], currentBoard: mockBoard })

    useBoardStore.getState().removeBoard('1')

    const state = useBoardStore.getState()
    expect(state.currentBoard).toBeNull()
  })

  it('removeBoard should not affect currentBoard if id does not match', () => {
    const board1: Board = { id: '1', name: 'Board 1', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }
    const board2: Board = { id: '2', name: 'Board 2', created_at: '2024-01-01', updated_at: '2024-01-01', agents: [] }
    useBoardStore.setState({ boards: [board1, board2], currentBoard: board1 })

    useBoardStore.getState().removeBoard('2')

    const state = useBoardStore.getState()
    expect(state.currentBoard).toEqual(board1)
  })
})
