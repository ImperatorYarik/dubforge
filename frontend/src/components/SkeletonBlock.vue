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

<style scoped lang="scss">
.skeleton {
  background: linear-gradient(90deg, var(--bg3) 25%, var(--bg4) 50%, var(--bg3) 75%);
  background-size: 600px 100%;
  animation: shimmer 1.4s infinite linear;
}

</style>
