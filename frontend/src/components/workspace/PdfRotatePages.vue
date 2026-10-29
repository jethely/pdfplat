<template>
  <div class="tool-pdf-rotate-pages">
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

    <!-- 旋转角度 -->
    <div class="form-section">
      <label class="form-label">旋转角度</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model.number="angle" :value="90" />
          <span>顺时针 90°</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="angle" :value="180" />
          <span>旋转 180°（倒转）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="angle" :value="270" />
          <span>顺时针 270°（= 逆时针 90°）</span>
        </label>
      </div>
    </div>

    <!-- 应用范围 -->
    <div class="form-section">
      <label class="form-label">应用范围</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="scope" value="all" />
          <span>全部页面</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="scope" value="pages" />
          <span>指定页面</span>
        </label>
      </div>
      <div v-if="scope === 'pages'" style="margin-top: 12px;">
        <input
          v-model="pages"
          type="text"
          class="form-input"
          placeholder="例: 1, 3, 5-7"
        />
        <p class="form-hint">
          页码用逗号分隔，支持范围。
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
const angle = ref(90)
const scope = ref('all')
const pages = ref('')
const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (scope.value === 'pages' && !pages.value.trim()) return false
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
  angle.value = 90
  scope.value = 'all'
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
    fd.append('angle', String(angle.value))
    fd.append('pages', scope.value === 'pages' ? pages.value : '')

    const res = await api.post('/pdf-rotate-pages', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '旋转完成',
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