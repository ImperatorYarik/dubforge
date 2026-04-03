<script setup>
defineProps({
  width:  { type: String, default: '100%' },
  height: { type: String, default: '20px' },
  radius: { type: String, default: 'var(--radius)' },
})
</script>

<template>
  <div class="skeleton" :style="{ width, height, borderRadius: radius }" />
</template>

