import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as systemApi from '@/api/system'

export const useSystemStore = defineStore('system', () => {
  const gpuAvailable = ref(false)
  const gpuName = ref(null)
  const gpuMemoryUsedMb = ref(0)
  const gpuMemoryTotalMb = ref(0)
  const whisperLoaded = ref(false)
  const xttsLoaded = ref(false)
  const workerOnline = ref(false)
  const activeJobs = ref(0)
  const queuedJobs = ref(0)
  const loading = ref(false)

  async function fetchStatus() {
    loading.value = true
    try {
      const { data } = await systemApi.getSystemStatus()
      gpuAvailable.value = data.gpu_available
      gpuName.value = data.gpu_name
      gpuMemoryUsedMb.value = data.gpu_memory_used_mb
      gpuMemoryTotalMb.value = data.gpu_memory_total_mb
      whisperLoaded.value = data.whisper_loaded
      xttsLoaded.value = data.xtts_loaded
      workerOnline.value = data.worker_online
      activeJobs.value = data.active_jobs
      queuedJobs.value = data.queued_jobs
    } catch {
      workerOnline.value = false
    } finally {
      loading.value = false
    }
  }

  return {
    gpuAvailable,
    gpuName,
    gpuMemoryUsedMb,
    gpuMemoryTotalMb,
    whisperLoaded,
    xttsLoaded,
    workerOnline,
    activeJobs,
    queuedJobs,
    loading,
    fetchStatus,
  }
})
