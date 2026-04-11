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
import TextToSpeechView from '@/views/TextToSpeechView.vue'

describe('TextToSpeechView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    ttsApi.getVoices.mockResolvedValue({
      data: [
        { name: 'Ana Florence', gender: 'F', language: 'en' },
        { name: 'Damien Black', gender: 'M', language: 'en' },
      ],
    })
  })

  it('renders without error', () => {
    const wrapper = mount(TextToSpeechView)
    expect(wrapper.exists()).toBe(true)
  })

  it('renders the text input area', () => {
    const wrapper = mount(TextToSpeechView)
    expect(wrapper.find('[data-testid="tts-textarea"]').exists()).toBe(true)
  })

  it('renders the generate button', () => {
    const wrapper = mount(TextToSpeechView)
    expect(wrapper.find('[data-testid="generate-btn"]').exists()).toBe(true)
  })

  it('generate button is disabled when text is empty', () => {
    const wrapper = mount(TextToSpeechView)
    const btn = wrapper.find('[data-testid="generate-btn"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('shows character count', () => {
    const wrapper = mount(TextToSpeechView)
    expect(wrapper.find('[data-testid="char-count"]').exists()).toBe(true)
  })

  it('renders voice selection area', () => {
    const wrapper = mount(TextToSpeechView)
    expect(wrapper.find('[data-testid="voice-select"]').exists()).toBe(true)
  })

  it('renders format toggle buttons', () => {
    const wrapper = mount(TextToSpeechView)
    expect(wrapper.find('[data-testid="format-wav"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="format-mp3"]').exists()).toBe(true)
  })

  it('updates character count when text is typed', async () => {
    const wrapper = mount(TextToSpeechView)
    const textarea = wrapper.find('[data-testid="tts-textarea"]')
    await textarea.setValue('Hello world')
    expect(wrapper.find('[data-testid="char-count"]').text()).toContain('11')
  })
})
