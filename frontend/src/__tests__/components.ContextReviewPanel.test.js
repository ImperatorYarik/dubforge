import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ContextReviewPanel from '../components/ContextReviewPanel.vue'

describe('ContextReviewPanel', () => {
  it('renders textarea pre-filled with context prop', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'Spanish cooking show transcript' },
    })
    expect(wrapper.find('[data-testid="context-textarea"]').element.value).toBe(
      'Spanish cooking show transcript'
    )
  })

  it('emits confirm with current textarea value on confirm click', async () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'original context' },
    })
    await wrapper.find('[data-testid="context-textarea"]').setValue('edited context')
    await wrapper.find('[data-testid="confirm-btn"]').trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('confirm')[0][0]).toBe('edited context')
  })

  it('emits confirm with unedited context when not changed', async () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'original context' },
    })
    await wrapper.find('[data-testid="confirm-btn"]').trigger('click')
    expect(wrapper.emitted('confirm')[0][0]).toBe('original context')
  })

  it('emits regenerate when regenerate button clicked', async () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'some context' },
    })
    await wrapper.find('[data-testid="regenerate-btn"]').trigger('click')
    expect(wrapper.emitted('regenerate')).toBeTruthy()
  })

  it('shows Regenerating… text when loading is true', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'context', loading: true },
    })
    expect(wrapper.find('[data-testid="regenerate-btn"]').text()).toBe('Regenerating…')
  })

  it('shows Regenerate text when loading is false', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'context', loading: false },
    })
    expect(wrapper.find('[data-testid="regenerate-btn"]').text()).toBe('Regenerate')
  })

  it('disables confirm button when loading', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'context', loading: true },
    })
    expect(wrapper.find('[data-testid="confirm-btn"]').attributes('disabled')).toBeDefined()
  })

  it('disables regenerate button when loading', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'context', loading: true },
    })
    expect(wrapper.find('[data-testid="regenerate-btn"]').attributes('disabled')).toBeDefined()
  })

  it('enables buttons when not loading', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'context', loading: false },
    })
    expect(wrapper.find('[data-testid="confirm-btn"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.find('[data-testid="regenerate-btn"]').attributes('disabled')).toBeUndefined()
  })

  it('displays model name badge when model prop provided', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'ctx', model: 'llama3.2' },
    })
    expect(wrapper.find('[data-testid="model-badge"]').text()).toBe('llama3.2')
  })

  it('does not render model badge when model prop is empty', () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'ctx', model: '' },
    })
    expect(wrapper.find('[data-testid="model-badge"]').exists()).toBe(false)
  })

  it('updates textarea when context prop changes', async () => {
    const wrapper = mount(ContextReviewPanel, {
      props: { context: 'initial context' },
    })
    await wrapper.setProps({ context: 'updated context' })
    expect(wrapper.find('[data-testid="context-textarea"]').element.value).toBe('updated context')
  })
})
