<template>
  <div class="tool-pdf-to-long-image">
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
      ⚠️ 所有页面会竖向拼接成一张长图。页数多或 DPI 高时，图片会非常大，请慎用。
    </div>

    <div class="form-section">
      <label class="form-label">输出分辨率 (DPI)</label>
      <select v-model.number="dpi" class="form-input">
        <option :value="72">72 DPI（屏幕预览）</option>
        <option :value="96">96 DPI（网页分享）</option>
        <option :value="150">150 DPI（推荐）</option>
        <option :value="200">200 DPI（高清）</option>
        <option :value="300">300 DPI（印刷级）</option>
      </select>
    </div>

    <div class="form-section">
      <label class="form-label">页间空白：{{ gap }} px</label>
      <input
        v-model.number="gap"
        type="range"
        min="0" max="100" step="10"
        class="slider"
      />
      <p class="form-hint">
        相邻两页之间的空白像素，0 表示无缝拼接。
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
const dpi = ref(150)
const gap = ref(0)
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
    fd.append('dpi', String(dpi.value))
    fd.append('gap', String(gap.value))
    const res = await api.post('/pdf-to-long-image', fd, {
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

<style scoped>
.slider { width: 100%; max-width: 480px; cursor: pointer; }
</style>