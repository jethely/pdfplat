<template>
  <div class="tool-extract-images">
    <div class="form-section">
      <label class="form-label">选择 PDF 文件</label>
      <DropZone
        v-if="!file"
        accept=".pdf"
        icon="📁"
        text="拖拽 PDF 文件到此处，或点击选择"
        @files="(fs) => file = fs[0] || null"
      />
      <FileList
        :files="file ? [file] : []"
        icon="📄"
        @remove="file = null"
      />
    </div>

    <div class="form-section">
      <label class="form-label">提取策略</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="strategy" value="auto" />
          <span><b>提取原图（推荐）</b> — 提取所有内嵌图片的原始文件</span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="B" disabled />
          <span><b>去重提取</b> — 相同图片只保存一份<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
        <label class="radio-item disabled">
          <input type="radio" v-model="strategy" value="C" disabled />
          <span><b>智能提取</b> — 去重 + 位置报告<span class="form-hint-inline">（暂未实现）</span></span>
        </label>
      </div>
      <p class="form-hint">
        提取出来的图片会保存到「我的文件」，可逐个下载。
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
const file = ref(null)
const strategy = ref('auto')
const loading = ref(false)
const result = ref(null)

function reset() {
  file.value = null
  strategy.value = 'auto'
  result.value = null
  loading.value = false
}

async function submit() {
  if (!file.value) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('strategy', strategy.value)

    const res = await api.post('/extract-images', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '提取完成',
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