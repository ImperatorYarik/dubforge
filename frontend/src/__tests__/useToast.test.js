import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useToast } from '../composables/useToast'

describe('useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // Clear shared module-level toasts array
    const { toasts } = useToast()
    toasts.value.splice(0)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('adds a toast with default type info', () => {
    const { toasts, info } = useToast()
    info('Hello')
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0]).toMatchObject({ message: 'Hello', type: 'info' })
  })

  it('adds a success toast', () => {
    const { toasts, success } = useToast()
    success('Done!')
    expect(toasts.value[0].type).toBe('success')
    expect(toasts.value[0].message).toBe('Done!')
  })

  it('adds an error toast', () => {
    const { toasts, error } = useToast()
    error('Something went wrong')
    expect(toasts.value[0].type).toBe('error')
  })

  it('removes toast after default duration (4000ms)', () => {
    const { toasts, info } = useToast()
    info('Temporary')
    expect(toasts.value).toHaveLength(1)
    vi.advanceTimersByTime(4000)
    expect(toasts.value).toHaveLength(0)
  })

  it('does not remove toast before duration elapses', () => {
    const { toasts, info } = useToast()
    info('Still here')
    vi.advanceTimersByTime(3999)
    expect(toasts.value).toHaveLength(1)
  })

  it('removeToast removes by id', () => {
    const { toasts, info, removeToast } = useToast()
    info('One')
    info('Two')
    const id = toasts.value[0].id
    removeToast(id)
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].message).toBe('Two')
  })

  it('removeToast is a no-op for unknown id', () => {
    const { toasts, info, removeToast } = useToast()
    info('One')
    removeToast(99999)
    expect(toasts.value).toHaveLength(1)
  })

  it('assigns unique ids to multiple toasts', () => {
    const { toasts, info } = useToast()
    info('A')
    info('B')
    info('C')
    const ids = toasts.value.map((t) => t.id)
    expect(new Set(ids).size).toBe(3)
  })
})
