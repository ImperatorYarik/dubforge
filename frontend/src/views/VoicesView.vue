<script setup>
const speakers = [
  { name: 'Claribel Dervla',    gender: 'F' },
  { name: 'Daisy Studious',     gender: 'F' },
  { name: 'Gracie Wise',        gender: 'F' },
  { name: 'Tammie Ema',         gender: 'F' },
  { name: 'Alison Dietlinde',   gender: 'F' },
  { name: 'Ana Florence',       gender: 'F' },
  { name: 'Annmarie Nele',      gender: 'F' },
  { name: 'Asya Anara',         gender: 'F' },
  { name: 'Brenda Borne',       gender: 'F' },
  { name: 'Eldora Nonaka',      gender: 'F' },
  { name: 'Lone Sunness',       gender: 'F' },
  { name: 'Samantha Trice',     gender: 'F' },
  { name: 'Viktor Eka',         gender: 'F' },
  { name: 'Abrahan Mack',       gender: 'M' },
  { name: 'Andrew Chipper',     gender: 'M' },
  { name: 'Baldur Sanjin',      gender: 'M' },
  { name: 'Craig Gutsy',        gender: 'M' },
  { name: 'Damien Black',       gender: 'M' },
  { name: 'Ethan Flemming',     gender: 'M' },
  { name: 'Ferdie Sayers',      gender: 'M' },
]
</script>

<template>
  <div class="view">
    <div class="page-header">
      <h1 class="page-title">Voices</h1>
      <p class="page-sub">XTTS v2 built-in speakers — set <code>DEFAULT_SPEAKER</code> in worker/app/tasks/tts.py</p>
    </div>

    <div class="grid">
      <div
        v-for="s in speakers"
        :key="s.name"
        class="voice-card"
      >
        <div class="avatar">{{ s.name[0] }}</div>
        <div class="voice-info">
          <p class="voice-name">{{ s.name }}</p>
          <p class="voice-gender">{{ s.gender === 'F' ? 'Female' : 'Male' }}</p>
        </div>
        <div class="badge">XTTS v2</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view { padding: 40px 48px; max-width: 860px; }

.page-header { margin-bottom: 32px; }
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.025em; }
.page-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
code { font-family: monospace; background: var(--surface-subtle); padding: 1px 5px; border-radius: 4px; }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}

.voice-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  transition: background 0.1s;
}
.voice-card:hover { background: var(--surface-hover); }

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  flex-shrink: 0;
}

.voice-info { flex: 1; min-width: 0; }
.voice-name { font-size: 13.5px; font-weight: 500; letter-spacing: -0.01em; }
.voice-gender { font-size: 12px; color: var(--text-muted); margin-top: 1px; }

.badge {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-placeholder);
  border: 1px solid var(--border);
  padding: 2px 7px;
  border-radius: 99px;
}
</style>
