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

<style scoped>
.skeleton {
  background: linear-gradient(90deg, #F4F4F5 25%, #EBEBEC 50%, #F4F4F5 75%);
  background-size: 600px 100%;
  animation: shimmer 1.4s infinite linear;
}
@keyframes shimmer {
  0%   { background-position: -600px 0; }
  100% { background-position:  600px 0; }
}
</style>
