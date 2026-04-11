import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
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
  separateAudio: vi.fn(),
  getJobStatus: vi.fn(),
  getRecentJobs: vi.fn(),
  getProgressWsUrl: vi.fn(() => 'ws://localhost/ws/test'),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

vi.mock('@/components/VideoPlayer.vue', () => ({
  default: { template: '<div data-testid="video-player-mock" />' },
}))

vi.mock('@/components/TranscriptPanel.vue', () => ({
  default: { template: '<div data-testid="transcript-panel-mock" />' },
}))

import * as projectsApi from '@/api/projects'
import * as videosApi from '@/api/videos'
import ProjectDetailView from '@/views/ProjectDetailView.vue'
import { useVideosStore } from '@/stores/videos'
import { useProjectsStore } from '@/stores/projects'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/projects', name: 'projects', component: { template: '<div />' } },
    { path: '/projects/:id', name: 'project-detail', component: ProjectDetailView, props: true },
    { path: '/studio/:projectId', name: 'dubbing-studio', component: { template: '<div />' } },
  ],
})

const VIDEO_NO_AUDIO = {
  video_id: 'v1',
  project_id: 'p1',
  video_url: 'http://example.com/video.mp4',
  vocals_url: null,
  no_vocals_url: null,
  transcription: null,
  dubbed_url: null,
  transcript_segments: [],
  dubbed_versions: [],
  detected_language: 'RU',
  duration_seconds: 184,
}

const VIDEO_WITH_AUDIO = {
  ...VIDEO_NO_AUDIO,
  vocals_url: 'http://example.com/vocals.wav',
  no_vocals_url: 'http://example.com/no_vocals.wav',
}

const VIDEO_WITH_TRANSCRIPTION = {
  ...VIDEO_WITH_AUDIO,
  transcription: '[0.00s - 2.00s] Hi everyone\n[2.00s - 5.00s] Welcome here',
  transcript_segments: [
    { start: 0, end: 2, text: 'Hi everyone' },
    { start: 2, end: 5, text: 'Welcome here' },
  ],
}

const VIDEO_DUBBED = {
  ...VIDEO_WITH_TRANSCRIPTION,
  dubbed_url: 'http://example.com/dubbed.mp4',
  dubbed_versions: [
    { job_id: 'job1', created_at: '2024-04-02T10:00:00Z' },
  ],
}

// Mount the view and optionally pre-seed the videos store with a video
function mountView(videoData = null) {
  if (videoData) {
    // Pre-populate store directly so computed `sourceVideo` is reactive immediately
    const videosStore = useVideosStore()
    videosStore.videos = [videoData]
    // Mock API to return the same data on fetchVideo calls
    videosApi.listVideos.mockResolvedValue({ data: [videoData] })
    videosApi.getDubbedStreamUrl.mockResolvedValue({ data: { url: videoData.dubbed_url ?? 'http://example.com/dubbed.mp4' } })
  } else {
    videosApi.listVideos.mockResolvedValue({ data: [] })
  }
  return mount(ProjectDetailView, {
    global: { plugins: [router] },
  })
}

describe('ProjectDetailView', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    projectsApi.listProjects.mockResolvedValue({ data: { projects: [] } })
    projectsApi.getProject.mockResolvedValue({
      data: { project_id: 'p1', metadata: { title: 'My Project' } },
    })
    videosApi.listVideos.mockResolvedValue({ data: [] })
    videosApi.getDubbedStreamUrl.mockResolvedValue({ data: { url: 'http://example.com/dubbed.mp4' } })
    videosApi.getVocalsStreamUrl.mockResolvedValue({ data: { url: 'http://example.com/vocals.wav' } })
    videosApi.getNoVocalsStreamUrl.mockResolvedValue({ data: { url: 'http://example.com/no_vocals.wav' } })

    await router.push('/projects/p1')
    await router.isReady()
  })

  describe('basic rendering', () => {
    it('renders without error', () => {
      const wrapper = mountView()
      expect(wrapper.exists()).toBe(true)
    })

    it('renders the back button', () => {
      const wrapper = mountView()
      expect(wrapper.find('[data-testid="back-btn"]').exists()).toBe(true)
    })

    it('renders the workflow stepper', () => {
      const wrapper = mountView()
      expect(wrapper.find('[data-testid="workflow-stepper"]').exists()).toBe(true)
    })

    it('renders all 3 stepper steps', () => {
      const wrapper = mountView()
      expect(wrapper.findAll('[data-testid^="step-"]').length).toBeGreaterThanOrEqual(3)
    })

    it('renders the Original/Dubbed tab bar', () => {
      const wrapper = mountView()
      expect(wrapper.find('[data-testid="tab-original"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="tab-dubbed"]').exists()).toBe(true)
    })

    it('renders the transcript panel', () => {
      const wrapper = mountView()
      expect(wrapper.find('[data-testid="transcript-pane"]').exists()).toBe(true)
    })
  })

  describe('stepper step states — no audio separated', () => {
    it('marks step 1 as active when no vocals_url', () => {
      const wrapper = mountView(VIDEO_NO_AUDIO)
      const step1 = wrapper.find('[data-testid="step-1"]')
      expect(step1.classes()).toContain('detail-view__stepper-step--active')
    })

    it('marks step 2 as locked when step 1 not done', () => {
      const wrapper = mountView(VIDEO_NO_AUDIO)
      const step2 = wrapper.find('[data-testid="step-2"]')
      expect(step2.classes()).toContain('detail-view__stepper-step--locked')
    })

    it('marks step 3 as locked when step 1 not done', () => {
      const wrapper = mountView(VIDEO_NO_AUDIO)
      const step3 = wrapper.find('[data-testid="step-3"]')
      expect(step3.classes()).toContain('detail-view__stepper-step--locked')
    })

    it('shows Separate Audio action button in active step', () => {
      const wrapper = mountView(VIDEO_NO_AUDIO)
      expect(wrapper.find('[data-testid="separate-audio-btn"]').exists()).toBe(true)
    })
  })

  describe('stepper step states — audio separated, no transcription', () => {
    it('marks step 1 as done when vocals_url exists', () => {
      const wrapper = mountView(VIDEO_WITH_AUDIO)
      const step1 = wrapper.find('[data-testid="step-1"]')
      expect(step1.classes()).toContain('detail-view__stepper-step--done')
    })

    it('marks step 2 as active when vocals_url exists but no transcription', () => {
      const wrapper = mountView(VIDEO_WITH_AUDIO)
      const step2 = wrapper.find('[data-testid="step-2"]')
      expect(step2.classes()).toContain('detail-view__stepper-step--active')
    })

    it('shows Transcribe action button in active step 2', () => {
      const wrapper = mountView(VIDEO_WITH_AUDIO)
      expect(wrapper.find('[data-testid="transcribe-btn"]').exists()).toBe(true)
    })
  })

  describe('stepper step states — transcription done, no dub', () => {
    it('marks step 1 as done', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      expect(wrapper.find('[data-testid="step-1"]').classes()).toContain('detail-view__stepper-step--done')
    })

    it('marks step 2 as done when transcription exists', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      expect(wrapper.find('[data-testid="step-2"]').classes()).toContain('detail-view__stepper-step--done')
    })

    it('marks step 3 as active when transcription done but no dub', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      expect(wrapper.find('[data-testid="step-3"]').classes()).toContain('detail-view__stepper-step--active')
    })

    it('shows Generate Dub action button', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      expect(wrapper.find('[data-testid="generate-dub-btn"]').exists()).toBe(true)
    })
  })

  describe('stepper step states — fully dubbed', () => {
    it('marks all steps as done when dubbed_url exists', async () => {
      const wrapper = mountView(VIDEO_DUBBED)
      // Wait for onMounted async to resolve the dubbed stream URL
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-testid="step-1"]').classes()).toContain('detail-view__stepper-step--done')
      expect(wrapper.find('[data-testid="step-2"]').classes()).toContain('detail-view__stepper-step--done')
      expect(wrapper.find('[data-testid="step-3"]').classes()).toContain('detail-view__stepper-step--done')
    })

    it('shows re-generate button when step 3 is done', async () => {
      const wrapper = mountView(VIDEO_DUBBED)
      await wrapper.vm.$nextTick()
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-testid="regen-btn"]').exists()).toBe(true)
    })
  })

  describe('video tabs', () => {
    it('shows Original tab as active by default', () => {
      const wrapper = mountView(VIDEO_NO_AUDIO)
      expect(wrapper.find('[data-testid="tab-original"]').classes()).toContain('active')
    })

    it('switches to Dubbed tab when clicked', async () => {
      const wrapper = mountView(VIDEO_NO_AUDIO)
      await wrapper.find('[data-testid="tab-dubbed"]').trigger('click')
      expect(wrapper.find('[data-testid="tab-dubbed"]').classes()).toContain('active')
    })

    it('shows no-dubbed-yet message when on Dubbed tab and no dub exists', async () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      await wrapper.find('[data-testid="tab-dubbed"]').trigger('click')
      expect(wrapper.find('[data-testid="no-dubbed-message"]').exists()).toBe(true)
    })

    it('shows download link when on Dubbed tab and dubbed URL resolves', async () => {
      const wrapper = mountView(VIDEO_DUBBED)
      // Wait for all async operations (onMounted -> _loadStreams -> _loadDubbedStream) to resolve
      await flushPromises()
      await wrapper.find('[data-testid="tab-dubbed"]').trigger('click')
      await wrapper.vm.$nextTick()
      expect(wrapper.find('[data-testid="download-dubbed-link"]').exists()).toBe(true)
    })
  })

  describe('transcript panel', () => {
    it('renders transcript pane', () => {
      const wrapper = mountView()
      expect(wrapper.find('[data-testid="transcript-pane"]').exists()).toBe(true)
    })

    it('renders transcript segments when available', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      const pane = wrapper.find('[data-testid="transcript-pane"]')
      expect(pane.exists()).toBe(true)
    })

    it('shows segment list when video has transcript segments', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      const segments = wrapper.findAll('[data-testid="transcript-segment"]')
      expect(segments.length).toBe(2)
    })

    it('renders timestamp for each segment', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      const firstSegment = wrapper.find('[data-testid="transcript-segment"]')
      expect(firstSegment.find('[data-testid="segment-timestamp"]').exists()).toBe(true)
    })

    it('renders segment text', () => {
      const wrapper = mountView(VIDEO_WITH_TRANSCRIPTION)
      const firstSegment = wrapper.find('[data-testid="transcript-segment"]')
      expect(firstSegment.find('[data-testid="segment-text"]').text()).toContain('Hi everyone')
    })
  })

  describe('versions section', () => {
    it('renders versions section in transcript pane', () => {
      const wrapper = mountView(VIDEO_DUBBED)
      expect(wrapper.find('[data-testid="versions-section"]').exists()).toBe(true)
    })

    it('shows version count when versions exist', () => {
      const wrapper = mountView(VIDEO_DUBBED)
      expect(wrapper.find('[data-testid="versions-section"]').text()).toContain('VERSIONS')
    })
  })

  describe('translate toggle', () => {
    it('renders translate toggle checkbox', () => {
      const wrapper = mountView()
      expect(wrapper.find('[data-testid="translate-toggle"]').exists()).toBe(true)
    })
  })
})
