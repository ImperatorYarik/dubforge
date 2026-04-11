import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('@/api/projects', () => ({
  listProjects: vi.fn(),
  getProject: vi.fn(),
}))

vi.mock('@/api/videos', () => ({
  listVideos: vi.fn(),
  getVideo: vi.fn(),
  uploadVideo: vi.fn(),
  getStreamUrl: vi.fn(),
  getDubbedStreamUrl: vi.fn(),
  getVocalsStreamUrl: vi.fn(),
  getNoVocalsStreamUrl: vi.fn(),
  getDubbedVersionStreamUrl: vi.fn(),
  deleteDubbedVersion: vi.fn(),
}))

vi.mock('@/api/jobs', () => ({
  dubVideo: vi.fn(),
  transcribeVideo: vi.fn(),
  getJobStatus: vi.fn(),
  getRecentJobs: vi.fn(),
  getProgressWsUrl: vi.fn(() => 'ws://localhost/ws'),
}))

import * as projectsApi from '@/api/projects'
import * as videosApi from '@/api/videos'
import DubbingStudioView from '@/views/DubbingStudioView.vue'

const MOCK_PROJECT = { project_id: 'p1', title: 'Test Project' }
const MOCK_VIDEOS = [
  { video_id: 'v1', project_id: 'p1', original_filename: 'clip.mp4', created_at: '2024-01-01T00:00:00Z' },
]

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/studio/:projectId', name: 'dubbing-studio', component: DubbingStudioView },
    ],
  })
}

describe('DubbingStudioView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    projectsApi.getProject.mockResolvedValue({ data: MOCK_PROJECT })
    videosApi.listVideos.mockResolvedValue({ data: MOCK_VIDEOS })
    videosApi.getStreamUrl.mockResolvedValue({ data: { url: 'http://example.com/video.mp4' } })
  })

  async function mountView(projectId = 'p1') {
    const router = buildRouter()
    await router.push({ name: 'dubbing-studio', params: { projectId } })
    await router.isReady()
    const wrapper = mount(DubbingStudioView, {
      global: { plugins: [router] },
    })
    await wrapper.vm.$nextTick()
    return wrapper
  }

  it('renders the top bar with project name area', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="studio-topbar"]').exists()).toBe(true)
  })

  it('renders export video CTA button', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="btn-export"]').exists()).toBe(true)
  })

  it('renders editor and export tab buttons in top bar', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="tab-editor"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tab-export"]').exists()).toBe(true)
  })

  it('renders media assets panel', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="media-assets-panel"]').exists()).toBe(true)
  })

  it('renders ai dubbing panel', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="ai-dubbing-panel"]').exists()).toBe(true)
  })

  it('renders video player area', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="video-player-area"]').exists()).toBe(true)
  })

  it('renders studio timeline', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('[data-testid="studio-timeline"]').exists()).toBe(true)
  })
})
