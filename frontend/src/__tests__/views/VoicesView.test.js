import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/tts', () => ({
  getVoices: vi.fn(),
  generateTts: vi.fn(),
  getTtsStatus: vi.fn(),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

import * as ttsApi from '@/api/tts'
import VoicesView from '@/views/VoicesView.vue'

describe('VoicesView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    ttsApi.getVoices.mockResolvedValue({
      data: [
        { name: 'Ana Florence', gender: 'F', language: 'en' },
        { name: 'Damien Black', gender: 'M', language: 'en' },
        { name: 'Marie Claire', gender: 'F', language: 'fr' },
      ],
    })
  })

  it('renders without error', () => {
    const wrapper = mount(VoicesView)
    expect(wrapper.exists()).toBe(true)
  })

  it('renders the Voice Library heading', () => {
    const wrapper = mount(VoicesView)
    expect(wrapper.text()).toContain('Voice Library')
  })

  it('renders language filter tabs after loading', async () => {
    const wrapper = mount(VoicesView)
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="lang-filters"]').exists()).toBe(true)
  })

  it('renders voice cards after loading', async () => {
    const wrapper = mount(VoicesView)
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const cards = wrapper.findAll('[data-testid="voice-card"]')
    expect(cards.length).toBeGreaterThan(0)
  })

  it('each voice card has a preview button', async () => {
    const wrapper = mount(VoicesView)
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const previewBtns = wrapper.findAll('[data-testid="preview-btn"]')
    expect(previewBtns.length).toBeGreaterThan(0)
  })
})
