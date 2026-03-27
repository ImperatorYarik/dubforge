<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  context: { type: String, required: true },
  model: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['confirm', 'regenerate'])

const editedContext = ref(props.context)

watch(
  () => props.context,
  (val) => { editedContext.value = val }
)

function onConfirm() {
  emit('confirm', editedContext.value)
}

function onRegenerate() {
  emit('regenerate')
}
</script>

<template>
  <div class="context-review-panel">
    <div class="crp-header">
      <h3 class="crp-title">Review Context</h3>
      <span v-if="model" data-testid="model-badge" class="crp-model-badge">{{ model }}</span>
    </div>
    <div class="crp-body">
      <textarea
        v-model="editedContext"
        class="crp-textarea"
        rows="6"
        :disabled="loading"
        data-testid="context-textarea"
      />
      <p class="crp-helper">
        This context will guide the translation agent. Edit it to correct factual errors,
        add domain terminology, or clarify tone.
      </p>
    </div>
    <div class="crp-footer">
      <button
        class="btn btn-primary btn-sm"
        data-testid="confirm-btn"
        :disabled="loading"
        @click="onConfirm"
      >
        Confirm Context →
      </button>
      <button
        class="btn btn-ghost btn-sm"
        data-testid="regenerate-btn"
        :disabled="loading"
        @click="onRegenerate"
      >
        {{ loading ? 'Regenerating…' : 'Regenerate' }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.context-review-panel {
  background: var(--surface, #1e1e1e);
  border: 1px solid var(--border, #333);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.crp-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.crp-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.crp-model-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--accent-muted, #2a2a3a);
  color: var(--accent, #7c7cff);
  font-family: monospace;
}

.crp-textarea {
  width: 100%;
  resize: vertical;
  background: var(--bg, #141414);
  color: var(--text, #e0e0e0);
  border: 1px solid var(--border, #333);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.5;
  box-sizing: border-box;
  font-family: inherit;

  &:focus {
    outline: none;
    border-color: var(--accent, #7c7cff);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.crp-helper {
  margin: 0;
  font-size: 12px;
  color: var(--text-dim, #888);
}

.crp-footer {
  display: flex;
  gap: 8px;
}
</style>
