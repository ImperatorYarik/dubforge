import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectsStore } from '../stores/projects'

vi.mock('@/api/projects', () => ({
  listProjects: vi.fn(),
  getProject: vi.fn(),
  createProject: vi.fn(),
  createBlankProject: vi.fn(),
  deleteProject: vi.fn(),
}))

import * as projectsApi from '@/api/projects'

const STORAGE_KEY = 'dubforge_current_project_id'

describe('useProjectsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('initialises with empty projects and no loading/error', () => {
    const store = useProjectsStore()
    expect(store.projects).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('reads currentProjectId from localStorage on init', () => {
    localStorage.setItem(STORAGE_KEY, 'proj-123')
    const store = useProjectsStore()
    expect(store.currentProjectId).toBe('proj-123')
  })

  describe('setCurrentProject', () => {
    it('stores id in localStorage and updates state', () => {
      const store = useProjectsStore()
      store.setCurrentProject('proj-abc')
      expect(localStorage.getItem(STORAGE_KEY)).toBe('proj-abc')
      expect(store.currentProjectId).toBe('proj-abc')
    })

    it('removes from localStorage when called with null', () => {
      localStorage.setItem(STORAGE_KEY, 'proj-abc')
      const store = useProjectsStore()
      store.setCurrentProject(null)
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
      expect(store.currentProjectId).toBeNull()
    })
  })

  describe('currentProject computed', () => {
    it('returns matching project from the list', () => {
      const store = useProjectsStore()
      store.projects.push({ project_id: 'p1', title: 'Test' })
      store.setCurrentProject('p1')
      expect(store.currentProject).toEqual({ project_id: 'p1', title: 'Test' })
    })

    it('returns null when no project matches', () => {
      const store = useProjectsStore()
      store.setCurrentProject('nonexistent')
      expect(store.currentProject).toBeNull()
    })

    it('returns null when currentProjectId is null', () => {
      const store = useProjectsStore()
      store.projects.push({ project_id: 'p1' })
      expect(store.currentProject).toBeNull()
    })
  })

  describe('fetchProjects', () => {
    it('populates projects on success and clears loading', async () => {
      const mockProjects = [{ project_id: 'p1' }, { project_id: 'p2' }]
      projectsApi.listProjects.mockResolvedValue({ data: { projects: mockProjects } })
      const store = useProjectsStore()
      await store.fetchProjects()
      expect(store.projects).toEqual(mockProjects)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('clears currentProjectId when stored project no longer exists in list', async () => {
      localStorage.setItem(STORAGE_KEY, 'gone')
      projectsApi.listProjects.mockResolvedValue({ data: { projects: [{ project_id: 'p1' }] } })
      const store = useProjectsStore()
      await store.fetchProjects()
      expect(store.currentProjectId).toBeNull()
    })

    it('sets error and clears loading on failure', async () => {
      projectsApi.listProjects.mockRejectedValue({ message: 'Network error' })
      const store = useProjectsStore()
      await store.fetchProjects()
      expect(store.error).toBe('Network error')
      expect(store.loading).toBe(false)
    })

    it('prefers response detail over message for error', async () => {
      projectsApi.listProjects.mockRejectedValue({
        response: { data: { detail: 'Unauthorized' } },
        message: 'Request failed',
      })
      const store = useProjectsStore()
      await store.fetchProjects()
      expect(store.error).toBe('Unauthorized')
    })
  })

  describe('fetchProject', () => {
    it('updates existing project in list', async () => {
      const store = useProjectsStore()
      store.projects.push({ project_id: 'p1', title: 'Old' })
      projectsApi.getProject.mockResolvedValue({ data: { project_id: 'p1', title: 'New' } })
      await store.fetchProject('p1')
      expect(store.projects[0].title).toBe('New')
    })

    it('appends project to list if not already present', async () => {
      const store = useProjectsStore()
      projectsApi.getProject.mockResolvedValue({ data: { project_id: 'p99', title: 'Added' } })
      await store.fetchProject('p99')
      expect(store.projects).toHaveLength(1)
      expect(store.projects[0].project_id).toBe('p99')
    })
  })

  describe('deleteProject', () => {
    it('removes the project from the list', async () => {
      projectsApi.deleteProject.mockResolvedValue({})
      const store = useProjectsStore()
      store.projects.push({ project_id: 'p1' }, { project_id: 'p2' })
      await store.deleteProject('p1')
      expect(store.projects).toEqual([{ project_id: 'p2' }])
    })

    it('clears currentProjectId when the deleted project was selected', async () => {
      projectsApi.deleteProject.mockResolvedValue({})
      const store = useProjectsStore()
      store.projects.push({ project_id: 'p1' })
      store.setCurrentProject('p1')
      await store.deleteProject('p1')
      expect(store.currentProjectId).toBeNull()
    })

    it('keeps currentProjectId when a different project is deleted', async () => {
      projectsApi.deleteProject.mockResolvedValue({})
      const store = useProjectsStore()
      store.projects.push({ project_id: 'p1' }, { project_id: 'p2' })
      store.setCurrentProject('p2')
      await store.deleteProject('p1')
      expect(store.currentProjectId).toBe('p2')
    })

    it('throws and sets error on failure', async () => {
      projectsApi.deleteProject.mockRejectedValue({ message: 'Not found' })
      const store = useProjectsStore()
      await expect(store.deleteProject('p1')).rejects.toBeTruthy()
      expect(store.error).toBe('Not found')
    })
  })
})
