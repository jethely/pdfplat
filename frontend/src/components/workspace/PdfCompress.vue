<template>
  <div class="tool-pdf-compress">
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

    <!-- 压缩级别 -->
    <div class="form-section">
      <label class="form-label">压缩级别</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="level" value="light" />
          <span>
            <b>轻度</b> — 无损，仅清理冗余对象
            <span class="form-hint-inline">（画质不变）</span>
          </span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="level" value="medium" />
          <span>
            <b>中度</b> — 图片降采样到 150 DPI
            <span class="form-hint-inline">（画质轻微下降）</span>
          </span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="level" value="high" />
          <span>
            <b>重度</b> — 图片降采样到 96 DPI
            <span class="form-hint-inline">（体积最小，画质明显下降）</span>
          </span>
        </label>
      </div>
      <p class="form-hint">
        未压缩过的 PDF 通常能显著瘦身；已经压缩过的 PDF 提升有限。
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
const level = ref('light')
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
  level.value = 'light'
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
    fd.append('level', level.value)

    const res = await api.post('/pdf-compress', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '压缩完成',
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
.tool-pdf-compress {
  /* 该工具特有样式，暂时没有 */
}
</style>