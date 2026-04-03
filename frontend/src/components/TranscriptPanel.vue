<script setup>
import SkeletonBlock from '@/components/SkeletonBlock.vue'

const props = defineProps({
  segments: { type: Array, default: () => [] },   // [{ start, end, text }]
  loading:  { type: Boolean, default: false },
  editable: { type: Boolean, default: false },
})

const emit = defineEmits(['update:segments'])

function fmt(sec) {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

function updateText(i, value) {
  const updated = props.segments.map((s, idx) =>
    idx === i ? { ...s, text: value } : s
  )
  emit('update:segments', updated)
}
</script>

<template>
  <div class="transcript-panel">
    <!-- Skeleton while loading -->
    <template v-if="loading">
      <div v-for="n in 6" :key="n" class="skeleton-row">
        <SkeletonBlock width="52px" height="14px" />
        <SkeletonBlock width="100%" height="14px" />
      </div>
    </template>

    <!-- Empty state -->
    <div v-else-if="!segments.length" class="empty">
      No transcript available.
    </div>

    <!-- Segments -->
    <div
      v-for="(seg, i) in segments"
      :key="i"
      class="seg"
    >
      <span class="ts">{{ fmt(seg.start) }}</span>
      <textarea
        v-if="editable"
        class="seg-text editable"
        :value="seg.text"
        rows="2"
        @input="updateText(i, $event.target.value)"
      />
      <p v-else class="seg-text">{{ seg.text }}</p>
    </div>
  </div>
</template>

<style scoped lang="scss">@use '../assets/scss/components/TranscriptPanel';</style>
