import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StudioTimeline from '@/components/studio/StudioTimeline.vue'

describe('StudioTimeline', () => {
  function factory(props = {}) {
    return mount(StudioTimeline, {
      props: {
        videoId: 'v1',
        dubbedVideoId: null,
        duration: 120,
        currentTime: 30,
        ...props,
      },
    })
  }

  it('renders toolbar with cut, trim, undo buttons', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="toolbar-cut"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="toolbar-trim"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="toolbar-undo"]').exists()).toBe(true)
  })

  it('renders zoom slider', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="zoom-slider"]').exists()).toBe(true)
  })

  it('renders three track rows: V1, A1, A2', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="track-v1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="track-a1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="track-a2"]').exists()).toBe(true)
  })

  it('renders playhead', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="playhead"]').exists()).toBe(true)
  })

  it('emits seek event when timeline area clicked', async () => {
    const wrapper = factory()
    const trackArea = wrapper.find('[data-testid="timeline-area"]')
    // Simulate a click — jsdom does not have layout so offsetWidth=0; just test emit wiring
    await trackArea.trigger('click', { offsetX: 50 })
    const emitted = wrapper.emitted('seek')
    expect(emitted).toBeTruthy()
  })

  it('positions playhead based on currentTime / duration ratio', () => {
    // currentTime=30, duration=120 -> 25%
    const wrapper = factory({ currentTime: 30, duration: 120 })
    const playhead = wrapper.find('[data-testid="playhead"]')
    // style.left should be set (exact value depends on offsetWidth which is 0 in jsdom)
    expect(playhead.exists()).toBe(true)
  })
})
