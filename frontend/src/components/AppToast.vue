<script setup>
import { useToast } from '@/composables/useToast'

const { toasts, removeToast } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts.slice(0, 3)"
          :key="t.id"
          class="toast"
          :class="`toast--${t.type}`"
          role="alert"
          @click="removeToast(t.id)"
        >
          <span class="toast-dot" />
          <span class="toast-msg">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 9999;
  max-width: 380px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-radius: var(--radius);
  cursor: pointer;
  min-width: 260px;
  border: 1px solid var(--border);
  background: var(--bg3);
  color: var(--text);
  box-shadow: 0 8px 24px rgb(0,0,0,0.4);
}

.toast-msg {
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.4;
  flex: 1;
}

.toast-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--muted);
}
.toast--success { border-color: var(--b-teal); }
.toast--success .toast-dot { background: var(--teal); }
.toast--error   { border-color: var(--b-red); }
.toast--error   .toast-dot { background: var(--red); }
.toast--info    { border-color: var(--b-amber); }
.toast--info    .toast-dot { background: var(--amber); }

.toast-enter-active, .toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(24px); }
</style>
