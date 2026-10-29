<template>
  <div class="tool-pdf-delete-pages">
    <!-- 选择文件 -->
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

    <!-- 模式 -->
    <div class="form-section">
      <label class="form-label">操作模式</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="mode" value="delete" />
          <span><b>删除指定页</b> — 移除填写页码，保留其他页</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="mode" value="keep" />
          <span><b>保留指定页</b> — 只保留填写页码，删除其他页</span>
        </label>
      </div>
    </div>

    <!-- 页码 -->
    <div class="form-section">
      <label class="form-label">
        {{ mode === 'delete' ? '要删除的页码' : '要保留的页码' }}
      </label>
      <input
        v-model="pages"
        type="text"
        class="form-input"
        placeholder="例: 1, 3, 5-7"
      />
      <p class="form-hint">
        支持单个页码、连续范围，用逗号分隔。页码从 1 开始。
      </p>
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
const mode = ref('delete')
const pages = ref('')
const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (!pages.value.trim()) return false
  return true
})

function onFiles(files) {
  file.value = files[0] || null
}

function onRemove() {
  file.value = null
  dropRef.value?.reset()
}

function reset() {
  file.value = null
  mode.value = 'delete'
  pages.value = ''
  result.value = null
  loading.value = false
  dropRef.value?.reset()
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('pages', pages.value.trim())
    fd.append('mode', mode.value)

    const res = await api.post('/pdf-delete-pages', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '操作完成',
    }
    emit('submitted')
  } catch (err) {
    let msg = '请求失败'
    const d = err.response?.data?.detail
    if (typeof d === 'string') msg = d
    else if (Array.isArray(d)) msg = d[0]?.msg || msg
    else if (err.message) msg = err.message
    result.value = { success: false, message: msg }
  } finally {
    loading.value = false
  }
}
</script>