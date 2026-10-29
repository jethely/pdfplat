<template>
  <div class="tool-pdf-metadata">
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
      <label class="form-label">标题 (Title)</label>
      <input v-model="form.title" class="form-input" placeholder="文档标题" />
    </div>

    <div class="form-section">
      <label class="form-label">作者 (Author)</label>
      <input v-model="form.author" class="form-input" placeholder="作者" />
    </div>

    <div class="form-section">
      <label class="form-label">主题 (Subject)</label>
      <input v-model="form.subject" class="form-input" placeholder="主题" />
    </div>

    <div class="form-section">
      <label class="form-label">关键词 (Keywords)</label>
      <input v-model="form.keywords" class="form-input" placeholder="关键词，逗号分隔" />
    </div>

    <div class="form-section">
      <label class="form-label">创建工具 (Creator)</label>
      <input v-model="form.creator" class="form-input" placeholder="例如：Microsoft Word" />
    </div>

    <div class="form-section">
      <label class="form-label">生成工具 (Producer)</label>
      <input v-model="form.producer" class="form-input" placeholder="例如：Adobe PDF Library" />
    </div>

    <p class="form-hint">只填写需要修改的字段，留空的保持不变。</p>

    <ActionBar
      :can-submit="!!file && hasAnyField"
      :loading="loading"
      @submit="submit"
      @reset="reset"
    />
    <ResultCard :result="result" />
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import api from '../../api'
import DropZone from './common/DropZone.vue'
import FileList from './common/FileList.vue'
import ActionBar from './common/ActionBar.vue'
import ResultCard from './common/ResultCard.vue'

const emit = defineEmits(['submitted'])
const dropRef = ref(null)
const file = ref(null)
const loading = ref(false)
const result = ref(null)
const form = reactive({
  title: '', author: '', subject: '', keywords: '', creator: '', producer: '',
})

const hasAnyField = computed(() =>
  Object.values(form).some(v => v && v.trim())
)

async function onFiles(files) {
  const f = files[0]
  if (!f) return
  file.value = f
  result.value = null
  // 读取现有元数据预填
  try {
    const fd = new FormData()
    fd.append('file', f)
    const res = await api.post('/pdf-metadata/read', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const md = res.data || {}
    form.title = md.title || ''
    form.author = md.author || ''
    form.subject = md.subject || ''
    form.keywords = md.keywords || ''
    form.creator = md.creator || ''
    form.producer = md.producer || ''
  } catch (e) { /* ignore */ }
}

function onRemove() {
  file.value = null
  dropRef.value?.reset()
  reset()
}

function reset() {
  form.title = ''; form.author = ''; form.subject = ''
  form.keywords = ''; form.creator = ''; form.producer = ''
  result.value = null
  loading.value = false
}

async function submit() {
  if (!file.value || !hasAnyField.value) return
  loading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    Object.entries(form).forEach(([k, v]) => fd.append(k, v || ''))
    const res = await api.post('/pdf-metadata', fd, {
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