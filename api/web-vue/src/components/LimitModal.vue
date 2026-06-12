<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '../api'

const props = defineProps({
  visible: Boolean,
  limit: Object,
})

const emit = defineEmits(['update:visible', 'saved'])

const form = ref({ system_id: '', limit_minutes: 60, enabled: true })
const saving = ref(false)
const appOptions = ref([])

const isNew = computed(() => !props.limit || !props.limit.system_id)

watch(() => props.visible, async (val) => {
  if (val) {
    if (props.limit && props.limit.system_id) {
      form.value = { ...props.limit }
    } else {
      form.value = { system_id: '', limit_minutes: 60, enabled: true }
    }
    try {
      const apps = await api.getApps()
      appOptions.value = apps.map(a => ({
        label: `${a.app_name} (${a.system_id})`,
        value: a.system_id,
      }))
    } catch { appOptions.value = [] }
  }
})

async function handleSave() {
  saving.value = true
  try {
    await api.saveLimit(form.value)
    message.success('Лимит сохранён')
    emit('saved')
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  } finally {
    saving.value = false
  }
}

function handleCancel() {
  emit('update:visible', false)
}
</script>

<template>
  <a-modal :visible="visible" :title="isNew ? 'Новый лимит' : 'Редактировать лимит'"
    @ok="handleSave" @cancel="handleCancel"
    :okText="isNew ? 'Создать' : 'Сохранить'" :confirmLoading="saving">
    <a-form layout="vertical">
      <a-form-item label="Приложение">
        <a-select v-model:value="form.system_id" :disabled="!isNew"
          :options="appOptions" placeholder="Выберите приложение" />
      </a-form-item>
      <a-form-item label="Лимит (минут)">
        <a-input-number v-model:value="form.limit_minutes" :min="1" :max="1440" style="width:100%" />
      </a-form-item>
      <a-form-item>
        <a-switch v-model:checked="form.enabled"
          checked-children="Активен" un-checked-children="Отключён" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
