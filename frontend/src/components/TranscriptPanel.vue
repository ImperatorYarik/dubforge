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
  <div class="panel">
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

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow-y: auto;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
}

.empty {
  padding: 32px 12px;
  color: var(--text-placeholder);
  font-size: 13px;
  text-align: center;
}

.seg {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 9px 12px;
  border-radius: var(--radius);
  transition: background 0.1s;
}
.seg:hover { background: var(--surface-hover); }

.ts {
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--text-placeholder);
  padding-top: 2px;
  flex-shrink: 0;
  width: 36px;
}

.seg-text {
  flex: 1;
  font-size: 13.5px;
  line-height: 1.55;
  color: var(--text);
  letter-spacing: -0.01em;
}

textarea.seg-text {
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  width: 100%;
  font-family: var(--font);
  padding: 0;
}
textarea.seg-text:focus {
  background: var(--surface-hover);
  border-radius: 4px;
  padding: 4px 6px;
  margin: -4px -6px;
}
</style>
