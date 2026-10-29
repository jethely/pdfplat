<template>
  <div class="tool-pdf-to-word">
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

    <!-- 提示：扫描件不支持 -->
    <div class="form-section warn-banner">
      ⚠️ 仅支持**文本型 PDF**（Word/WPS 导出的）。<br>
      扫描件、图片型 PDF 转 Word 只能得到一堆图片，无法编辑，请先使用 OCR 工具。
    </div>

    <!-- 转换策略 -->
    <div class="form-section">
      <label class="form-label">转换策略</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="strategy" value="auto" />
          <span>
            <b>自动（推荐）</b> — 检测 PDF 类型，选择最佳方案
          </span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="B" disabled />
          <span>
            <b>LibreOffice</b> — 兼容性更广
            <span class="form-hint-inline">（暂未实现）</span>
          </span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="C" disabled />
          <span>
            <b>OCR 扫描件识别</b> — 处理图片型 PDF
            <span class="form-hint-inline">（暂未实现）</span>
          </span>
        </label>
      </div>
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
const strategy = ref('auto')
const loading = ref(false)
const result = ref(null)

function onFiles(files) {
  file.value = files[0] || null
}

function onRemove() {
  file.value = null
  dropRef.value?.reset()
}

function reset() {
  file.value = null
  strategy.value = 'auto'
  result.value = null
  loading.value = false
  dropRef.value?.reset()
}

async function submit() {
  if (!file.value) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('strategy', strategy.value)

    const res = await api.post('/pdf-to-word', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '转换完成',
    }
    emit('submitted')
  } catch (err) {
    let msg = '请求失败'
    const d = err.response?.data?.detail
    if (typeof d === 'string') msg = d
    else if (Array.isArray(d)) msg = d[0]?.msg || err.message
    else if (err.message) msg = err.message
    result.value = { success: false, message: msg }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.radio-item.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>