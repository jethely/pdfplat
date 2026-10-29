<template>
  <div class="tool-stamp-operation">
    <div class="form-section">
      <label class="form-label">选择 PDF 文件</label>
      <DropZone
        ref="dropRef"
        accept=".pdf"
        icon="📁"
        text="拖拽 PDF 文件到此处，或点击选择"
        @files="onFiles"
      />
      <FileList
        :files="file ? [file] : []"
        icon="📄"
        @remove="onRemove"
      />
    </div>

    <div class="form-section">
      <label class="form-label">页面范围</label>
      <div class="radio-group">
        <label class="radio-item">
          <input type="radio" v-model="pageScope" value="all" />
          <span>所有页</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="pageScope" value="last" />
          <span>最后一页</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="pageScope" value="custom" />
          <span>自定义</span>
        </label>
      </div>

      <input
        v-if="pageScope === 'custom'"
        v-model="customPages"
        type="text"
        placeholder="例如: 1,3,5 或 2-4"
        class="native-text-input"
        style="margin-top: 10px;"
      />
    </div>

    <ActionBar
      :can-submit="canSubmit"
      :loading="loading"
      @submit="submit"
      @reset="reset"
    />

    <ResultCard :result="result" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../api'
import DropZone from './common/DropZone.vue'
import FileList from './common/FileList.vue'
import ActionBar from './common/ActionBar.vue'
import ResultCard from './common/ResultCard.vue'

const emit = defineEmits(['submitted'])

const dropRef = ref(null)
const file = ref(null)
const pageScope = ref('all')
const customPages = ref('')
const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => !!file.value)

function onFiles(files) {
  file.value = files[0] || null
}

function onRemove() {
  file.value = null
  dropRef.value?.reset()
}

function reset() {
  file.value = null
  pageScope.value = 'all'
  customPages.value = ''
  result.value = null
  loading.value = false
  dropRef.value?.reset()
}

function buildPagesValue() {
  if (pageScope.value === 'custom') {
    return customPages.value.trim()
  }
  return pageScope.value
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('pages', buildPagesValue())

    const res = await api.post('/stamp-operation', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = { success: true, message: res.data.message }
    emit('submitted')
  } catch (err) {
    const d = err.response?.data?.detail
    result.value = {
      success: false,
      message: typeof d === 'string' ? d : err.message,
    }
  } finally {
    loading.value = false
  }
}
</script>
