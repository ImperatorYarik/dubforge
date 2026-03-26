import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useJobsStore } from '../stores/jobs'

vi.mock('@/api/jobs', () => ({
  getProgressWsUrl: vi.fn(() => 'ws://localhost/ws'),
  getJobStatus: vi.fn(),
  transcribeVideo: vi.fn(),
  dubVideo: vi.fn(),
  separateAudio: vi.fn(),
  getRecentJobs: vi.fn(),
}))

const HISTORY_KEY = 'dubforge_job_history'

describe('useJobsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('initialises with null activeJob, false loading, null error', () => {
    const store = useJobsStore()
    expect(store.activeJob).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.recentJobs).toEqual([])
  })

  describe('startJob', () => {
    it('sets activeJob with all fields', () => {
      const store = useJobsStore()
      store.startJob('task-1', 'dub', 'vid-1', 'proj-1')
      expect(store.activeJob).toEqual({
        taskId: 'task-1',
        type: 'dub',
        videoId: 'vid-1',
        projectId: 'proj-1',
      })
    })

    it('prepends entry to jobHistory', () => {
      const store = useJobsStore()
      store.startJob('task-1', 'dub', 'vid-1', 'proj-1')
      store.startJob('task-2', 'transcribe', 'vid-2', 'proj-1')
      expect(store.jobHistory[0].taskId).toBe('task-2')
      expect(store.jobHistory[1].taskId).toBe('task-1')
    })

    it('persists history to localStorage', () => {
      const store = useJobsStore()
      store.startJob('task-1', 'dub', 'vid-1', 'proj-1')
      const saved = JSON.parse(localStorage.getItem(HISTORY_KEY))
      expect(saved).toHaveLength(1)
      expect(saved[0].taskId).toBe('task-1')
    })

    it('saves startedAt timestamp', () => {
      const before = Date.now()
      const store = useJobsStore()
      store.startJob('task-1', 'dub', 'vid-1', 'proj-1')
      expect(store.jobHistory[0].startedAt).toBeGreaterThanOrEqual(before)
    })

    it('caps saved history at MAX_HISTORY (20) entries', () => {
      const store = useJobsStore()
      for (let i = 0; i < 25; i++) {
        store.startJob(`task-${i}`, 'dub', 'vid', 'proj')
      }
      const saved = JSON.parse(localStorage.getItem(HISTORY_KEY))
      expect(saved).toHaveLength(20)
    })
  })

  describe('clearJob', () => {
    it('resets activeJob, loading, and error', () => {
      const store = useJobsStore()
      store.startJob('task-1', 'dub', 'vid-1', 'proj-1')
      store.loading = true
      store.error = 'some error'
      store.clearJob()
      expect(store.activeJob).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('does not wipe jobHistory', () => {
      const store = useJobsStore()
      store.startJob('task-1', 'dub', 'vid-1', 'proj-1')
      store.clearJob()
      expect(store.jobHistory).toHaveLength(1)
    })
  })

  describe('history loading from localStorage', () => {
    it('loads existing history on store init', () => {
      const history = [{ taskId: 'old-task', type: 'dub', videoId: 'v1', projectId: 'p1' }]
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history))
      const store = useJobsStore()
      expect(store.jobHistory).toEqual(history)
    })

    it('returns empty array for corrupted localStorage data', () => {
      localStorage.setItem(HISTORY_KEY, '{invalid json')
      const store = useJobsStore()
      expect(store.jobHistory).toEqual([])
    })

    it('returns empty array when key is missing', () => {
      const store = useJobsStore()
      expect(store.jobHistory).toEqual([])
    })
  })
})
