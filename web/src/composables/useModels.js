import { ref } from 'vue'
import { fetchModels as apiFetchModels } from '@/api'

const providers = ref([])
const currentModel = ref('')
const loading = ref(false)

export function useModels() {
  async function load(showCloud) {
    loading.value = true
    try {
      const data = await apiFetchModels(showCloud)
      providers.value = data.models || []
      // auto-select first model
      if (providers.value.length > 0 && providers.value[0].models.length > 0) {
        currentModel.value = providers.value[0].models[0].id
      }
    } catch (e) {
      console.error('load models error', e)
      providers.value = []
    } finally {
      loading.value = false
    }
  }

  return { providers, currentModel, loading, load }
}
