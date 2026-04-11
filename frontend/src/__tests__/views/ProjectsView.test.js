import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

vi.mock('@/api/projects', () => ({
  listProjects: vi.fn(),
  getProject: vi.fn(),
  createProject: vi.fn(),
  createBlankProject: vi.fn(),
  deleteProject: vi.fn(),
}))

vi.mock('@/api/videos', () => ({
  uploadVideo: vi.fn(),
  listVideos: vi.fn(),
  getVideo: vi.fn(),
  getStreamUrl: vi.fn(),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

import * as projectsApi from '@/api/projects'
import ProjectsView from '@/views/ProjectsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/projects', name: 'projects', component: ProjectsView },
    { path: '/projects/:id', name: 'project-detail', component: { template: '<div />' } },
  ],
})

describe('ProjectsView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    projectsApi.listProjects.mockResolvedValue({ data: { projects: [] } })
  })

  it('renders without error', async () => {
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders the page title', async () => {
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    expect(wrapper.text()).toContain('Projects')
  })

  it('renders New Project button', async () => {
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    expect(wrapper.find('[data-testid="new-project-btn"]').exists()).toBe(true)
  })

  it('shows create panel when New Project button clicked', async () => {
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    await wrapper.find('[data-testid="new-project-btn"]').trigger('click')
    expect(wrapper.find('[data-testid="create-panel"]').exists()).toBe(true)
  })

  it('renders search input', async () => {
    projectsApi.listProjects.mockResolvedValue({
      data: { projects: [{ project_id: 'p1', metadata: { title: 'Test' }, created_at: new Date().toISOString() }] },
    })
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    // Wait for onMounted to complete
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="search-input"]').exists()).toBe(true)
  })

  it('renders project cards when projects exist', async () => {
    projectsApi.listProjects.mockResolvedValue({
      data: {
        projects: [
          { project_id: 'p1', metadata: { title: 'Project Alpha' }, created_at: new Date().toISOString() },
          { project_id: 'p2', metadata: { title: 'Project Beta' }, created_at: new Date().toISOString() },
        ],
      },
    })
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const cards = wrapper.findAll('[data-testid="project-card"]')
    expect(cards.length).toBe(2)
  })

  it('renders empty state when no projects', async () => {
    projectsApi.listProjects.mockResolvedValue({ data: { projects: [] } })
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="empty-state"]').exists()).toBe(true)
  })

  it('shows create mode tabs in create panel', async () => {
    const wrapper = mount(ProjectsView, {
      global: { plugins: [router] },
    })
    await wrapper.find('[data-testid="new-project-btn"]').trigger('click')
    expect(wrapper.find('[data-testid="tab-file"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tab-youtube"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tab-blank"]').exists()).toBe(true)
  })
})
