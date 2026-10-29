<template>
  <div class="tool-text-replace">
    <!-- 选择文件 -->
    <div class="form-section">
      <label class="form-label form-label--with-hint">
        <span>选择 PDF 文件</span>
        <span class="form-hint-inline" title="扫描件 PDF 暂不支持，后续版本补充">
          <svg class="hint-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.2"/>
            <path d="M8 7v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="8" cy="4.5" r="0.9" fill="currentColor"/>
          </svg>
          仅支持 text 类型 PDF，扫描件后续补充
        </span>
      </label>
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

    <!-- 查找文字 -->
    <div class="form-section">
      <label class="form-label">查找文字</label>
      <input
        v-model="oldText"
        type="text"
        class="form-input"
        placeholder="请输入要替换的文字"
      />
    </div>

    <!-- 替换为 -->
    <div class="form-section">
      <label class="form-label">替换为</label>
      <input
        v-model="newText"
        type="text"
        class="form-input"
        placeholder="留空则删除查找的文字"
      />
    </div>

    <!-- 搜索范围 -->
    <div class="form-section">
      <label class="form-label">搜索范围</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="scope" value="all" />
          <span>全文（所有页面）</span>
        </label>
        <label class="radio-item">
          <input
            type="radio"
            v-model="scope"
            value="pages"
          />
          <span>指定页面</span>
        </label>
      </div>

      <div v-if="scope === 'pages'" style="margin-top: 12px;">
        <input
          v-model="pagesText"
          type="text"
          class="form-input"
          placeholder="例: 1, 3, 5-7"
        />
        <p class="form-hint">
          页码用逗号分隔，支持范围（如 <code>1-3</code>）。页码从 1 开始。
        </p>
      </div>
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
const oldText = ref('')
const newText = ref('')

const scope = ref('all')
const pagesText = ref('')

const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (!oldText.value.trim()) return false
  if (scope.value === 'pages' && !pagesText.value.trim()) return false
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
  oldText.value = ''
  newText.value = ''
  scope.value = 'all'
  pagesText.value = ''
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
    fd.append('old_text', oldText.value)
    fd.append('new_text', newText.value)
    fd.append('pages', scope.value === 'pages' ? pagesText.value : '')

    const res = await api.post('/text-replace', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '替换完成',
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

<style scoped>
.form-label--with-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.hint-icon {
  width: 14px;
  height: 14px;
  vertical-align: -2px;
  margin-right: 2px;
  color: var(--text-secondary, #6b7280);
}
.radio-item.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>