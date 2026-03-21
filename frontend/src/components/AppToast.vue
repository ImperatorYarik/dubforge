<script setup>
import { useToast } from '@/composables/useToast'

const { toasts, removeToast } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="`toast--${t.type}`"
          role="alert"
          @click="removeToast(t.id)"
        >
          <span class="toast-dot" />
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 9999;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 500;
  letter-spacing: -0.01em;
  min-width: 260px;
  max-width: 380px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.10);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}

.toast-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--text-muted);
}
.toast--success .toast-dot { background: #16a34a; }
.toast--error   .toast-dot { background: #dc2626; }
.toast--info    .toast-dot { background: var(--text); }

.toast-enter-active, .toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(24px); }
</style>
