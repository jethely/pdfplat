<template>
  <div class="tool-pdf-to-text">
    <div class="form-section">
      <label class="form-label">选择 PDF 文件</label>
      <DropZone
        ref="dropRef"
        accept=".pdf"
        icon="📁"
        text="拖拽 PDF 文件到此处，或点击选择"
        @files="onFiles"
      />
      <FileList :files="file ? [file] : []" icon="📄" @remove="onRemove" />
    </div>

    <div class="form-section">
      <label class="checkbox-item">
        <input type="checkbox" v-model="withPageSep" />
        <span>在每页之间插入分隔符</span>
      </label>
      <p class="form-hint">
        输出为 .txt 文件，可到「我的文件」中下载。
      </p>
    </div>

    <ActionBar
      :can-submit="!!file"
      :loading="loading"
      @submit="submit"
      @reset="reset"
    />
    <ResultCard :result="result" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../api'
import DropZone from './common/DropZone.vue'
import FileList from './common/FileList.vue'
import ActionBar from './common/ActionBar.vue'
import ResultCard from './common/ResultCard.vue'

const emit = defineEmits(['submitted'])
const dropRef = ref(null)
const file = ref(null)
const withPageSep = ref(true)
const loading = ref(false)
const result = ref(null)

function onFiles(files) { file.value = files[0] || null }
function onRemove() { file.value = null; dropRef.value?.reset() }
function reset() { result.value = null; loading.value = false }

async function submit() {
  if (!file.value) return
  loading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('with_page_sep', String(withPageSep.value))
    const res = await api.post('/pdf-to-text', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = { success: true, message: res.data.message }
    emit('submitted')
  } catch (err) {
    const d = err.response?.data?.detail
    result.value = { success: false, message: typeof d === 'string' ? d : err.message }
  } finally {
    loading.value = false
  }
}
</script>