import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AiDubbingPanel from '@/components/studio/AiDubbingPanel.vue'

describe('AiDubbingPanel', () => {
  function factory(props = {}) {
    return mount(AiDubbingPanel, {
      props: { loading: false, ...props },
    })
  }

  it('renders target language dropdown', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="language-select"]').exists()).toBe(true)
  })

  it('renders voice profile tabs', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="voice-tab-clone"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="voice-tab-library"]').exists()).toBe(true)
  })

  it('renders emotion preservation toggle defaulting to ON', () => {
    const wrapper = factory()
    const toggle = wrapper.find('[data-testid="toggle-emotion"]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.element.checked).toBe(true)
  })

  it('renders pacing match toggle defaulting to ON', () => {
    const wrapper = factory()
    const toggle = wrapper.find('[data-testid="toggle-pacing"]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.element.checked).toBe(true)
  })

  it('renders lip sync toggle defaulting to OFF', () => {
    const wrapper = factory()
    const toggle = wrapper.find('[data-testid="toggle-lipsync"]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.element.checked).toBe(false)
  })

  it('renders generate dub button', () => {
    const wrapper = factory()
    expect(wrapper.find('[data-testid="btn-generate-dub"]').exists()).toBe(true)
  })

  it('disables generate button when loading is true', () => {
    const wrapper = factory({ loading: true })
    expect(wrapper.find('[data-testid="btn-generate-dub"]').element.disabled).toBe(true)
  })

  it('emits generate-dub with options when button clicked', async () => {
    const wrapper = factory()
    await wrapper.find('[data-testid="btn-generate-dub"]').trigger('click')
    const emitted = wrapper.emitted('generate-dub')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toMatchObject({
      targetLanguage: expect.any(String),
      voiceMode: expect.any(String),
      emotionPreservation: true,
      pacingMatch: true,
      lipSync: false,
    })
  })

  it('switches active voice tab when library tab clicked', async () => {
    const wrapper = factory()
    const libraryTab = wrapper.find('[data-testid="voice-tab-library"]')
    await libraryTab.trigger('click')
    // library tab should now be active (has active modifier class)
    expect(libraryTab.classes()).toContain('ai-dubbing-panel__voice-tab--active')
  })

  it('includes voiceMode library in emitted options after switching tab', async () => {
    const wrapper = factory()
    await wrapper.find('[data-testid="voice-tab-library"]').trigger('click')
    await wrapper.find('[data-testid="btn-generate-dub"]').trigger('click')
    const emitted = wrapper.emitted('generate-dub')
    expect(emitted[0][0].voiceMode).toBe('library')
  })
})
