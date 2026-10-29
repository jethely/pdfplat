<template>
  <div class="tool-pdf-to-excel">
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

    <div class="form-section warn-banner">
      ⚠️ 只支持**文本型 PDF 中的规则表格**（Word/Excel 导出）。<br>
      无边框表格、复杂排版、扫描件可能识别失败，请先手动核对。
    </div>

    <div class="form-section">
      <label class="form-label">转换策略</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="strategy" value="auto" />
          <span><b>自动（推荐）</b> — pdfplumber 提取规则表格</span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="B" disabled />
          <span><b>复杂表格</b> — camelot 引擎<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="C" disabled />
          <span><b>扫描件表格</b> — OCR 识别<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
      </div>
    </div>

    <div class="form-section">
      <label class="form-label">Sheet 组织方式</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="sheetMode" value="per-page" />
          <span><b>每页一个 Sheet</b>（推荐，页标题为「第N页」）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="sheetMode" value="merged" />
          <span><b>全部汇总到一个 Sheet</b>（每页间加分隔标题）</span>
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
const sheetMode = ref('per-page')
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
    fd.append('strategy', strategy.value)
    fd.append('per_page_sheet', String(sheetMode.value === 'per-page'))
    const res = await api.post('/pdf-to-excel', fd, {
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

<style scoped>
.radio-item.disabled { opacity: 0.55; cursor: not-allowed; }
</style>