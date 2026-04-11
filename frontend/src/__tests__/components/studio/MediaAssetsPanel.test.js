import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MediaAssetsPanel from '@/components/studio/MediaAssetsPanel.vue'

const MOCK_VIDEOS = [
  { video_id: 'v1', original_filename: 'clip-a.mp4', created_at: '2024-01-01T10:00:00Z' },
  { video_id: 'v2', original_filename: 'clip-b.mp4', created_at: '2024-01-02T10:00:00Z' },
]

describe('MediaAssetsPanel', () => {
  function factory(props = {}) {
    return mount(MediaAssetsPanel, {
      props: { videos: MOCK_VIDEOS, activeVideoId: null, ...props },
    })
  }

  it('renders tab buttons', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="tab-video"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tab-audio"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="tab-text"]').exists()).toBe(true)
  })

  it('renders video items when video tab is active', () => {
    const wrapper = factory()
    const items = wrapper.findAll('[data-testid="asset-item"]')
    expect(items).toHaveLength(2)
  })

  it('shows filenames of videos', () => {
    const wrapper = factory()
    expect(wrapper.text()).toContain('clip-a.mp4')
    expect(wrapper.text()).toContain('clip-b.mp4')
  })

  it('marks active video with active modifier class', () => {
    const wrapper = factory({ activeVideoId: 'v1' })
    const items = wrapper.findAll('[data-testid="asset-item"]')
    expect(items[0].classes()).toContain('media-assets-panel__asset-item--active')
    expect(items[1].classes()).not.toContain('media-assets-panel__asset-item--active')
  })

  it('emits select-video with videoId when item clicked', async () => {
    const wrapper = factory()
    await wrapper.findAll('[data-testid="asset-item"]')[1].trigger('click')
    const emitted = wrapper.emitted('select-video')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toBe('v2')
  })

  it('shows empty state when no videos', () => {
    const wrapper = factory({ videos: [] })
    expect(wrapper.find('[data-testid="assets-empty"]').exists()).toBe(true)
  })
})
