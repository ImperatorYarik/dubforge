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

<style scoped lang="scss">@use '../assets/scss/components/AppToast';</style>
