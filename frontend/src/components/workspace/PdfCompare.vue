<template>
  <div class="tool-pdf-compare">
    <div class="form-section">
      <label class="form-label">选择 PDF 文件 A</label>
      <DropZone
        v-if="!fileA"
        accept=".pdf"
        icon="📁"
        text="拖拽文件 A 到此处，或点击选择"
        @files="(fs) => fileA = fs[0] || null"
      />
      <FileList
        :files="fileA ? [fileA] : []"
        icon="📄"
        @remove="fileA = null"
      />
    </div>

    <div class="form-section">
      <label class="form-label">选择 PDF 文件 B</label>
      <DropZone
        v-if="!fileB"
        accept=".pdf"
        icon="📁"
        text="拖拽文件 B 到此处，或点击选择"
        @files="(fs) => fileB = fs[0] || null"
      />
      <FileList
        :files="fileB ? [fileB] : []"
        icon="📄"
        @remove="fileB = null"
      />
    </div>

    <div class="form-section">
      <label class="form-label">对比策略</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="strategy" value="auto" />
          <span><b>自动（推荐）</b> — 文本内容对比，输出差异报告</span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="B" disabled />
          <span><b>视觉对比</b> — 渲染成图，像素级对比<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="C" disabled />
          <span><b>结构对比</b> — 元数据/书签/尺寸对比<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
      </div>
    </div>

    <ActionBar
      :can-submit="!!fileA && !!fileB"
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
const fileA = ref(null)
const fileB = ref(null)
const strategy = ref('auto')
const loading = ref(false)
const result = ref(null)

function reset() {
  fileA.value = null
  fileB.value = null
  strategy.value = 'auto'
  result.value = null
  loading.value = false
}

async function submit() {
  if (!fileA.value || !fileB.value) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    fd.append('files', fileA.value)
    fd.append('files', fileB.value)
    fd.append('strategy', strategy.value)

    const res = await api.post('/pdf-compare', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '对比完成',
    }
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