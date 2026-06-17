import { describe, it, expect } from 'vitest'
import { cn } from '../utils'

describe('cn utility', () => {
  it('concatenates strings', () => {
    expect(cn('class-1', 'class-2')).toBe('class-1 class-2')
  })

  it('handles arrays of strings', () => {
    expect(cn(['class-1', 'class-2'])).toBe('class-1 class-2')
  })

  it('handles conditional classes via objects', () => {
    expect(cn({ 'class-1': true, 'class-2': false, 'class-3': true })).toBe('class-1 class-3')
  })

  it('resolves tailwind class conflicts', () => {
    // Both define padding, tailwind-merge keeps the last one
    expect(cn('p-2', 'p-4')).toBe('p-4')
    expect(cn('px-2', 'p-4')).toBe('p-4')
    expect(cn('p-4', 'px-2')).toBe('p-4 px-2') // if p-4 is first, px-2 overrides the x-axis part but padding is preserved
    // Test color overrides
    expect(cn('bg-red-500', 'bg-blue-500')).toBe('bg-blue-500')
    expect(cn('text-sm', 'text-lg')).toBe('text-lg')
  })

  it('handles falsy values and empty strings', () => {
    expect(cn('class-1', undefined, 'class-2', null, false, '', 'class-3')).toBe('class-1 class-2 class-3')
  })
})
