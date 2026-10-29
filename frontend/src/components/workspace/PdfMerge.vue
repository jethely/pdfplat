<template>
  <div class="tool-pdf-merge">
    <!-- 选择文件 -->
    <div class="form-section">
      <label class="form-label">选择多个 PDF 文件（可多选，至少 2 个）</label>
      <DropZone
        ref="dropRef"
        accept=".pdf"
        :multiple="true"
        icon="📁"
        text="拖拽 PDF 文件到此处，或点击选择"
        @files="onFiles"
      />
    </div>

    <!-- 合并顺序 -->
    <div v-if="uploadedFiles.length > 1" class="form-section">
      <label class="form-label">合并顺序</label>
      <div class="radio-group">
        <label class="radio-item">
          <input type="radio" v-model="sortMode" value="upload" />
          <span>按上传顺序</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="sortMode" value="filename" />
          <span>按文件名排序</span>
        </label>
      </div>
    </div>

    <!-- 文件列表 + 页码范围 -->
    <div v-if="mergeItems.length" class="form-section">
      <label class="form-label">文件列表与页码范围（留空 = 全部页）</label>
      <div class="merge-list">
        <div
          v-for="(item, idx) in mergeItems"
          :key="item.key"
          class="merge-item"
        >
          <span class="merge-index">{{ idx + 1 }}.</span>
          <span class="merge-name" :title="item.file.name">{{ item.file.name }}</span>
          <span class="merge-size">{{ formatSize(item.file.size) }}</span>
          <input
            v-model="filePageRanges[item.originalIndex]"
            type="text"
            class="merge-range"
            placeholder="全部"
          />
          <button
            v-if="sortMode === 'upload'"
            class="merge-btn"
            :disabled="idx === 0"
            @click="moveMergeItem(item.originalIndex, -1)"
            title="上移"
          >↑</button>
          <button
            v-if="sortMode === 'upload'"
            class="merge-btn"
            :disabled="idx === mergeItems.length - 1"
            @click="moveMergeItem(item.originalIndex, 1)"
            title="下移"
          >↓</button>
          <button
            class="merge-btn danger"
            @click="removeMergeItem(item.originalIndex)"
            title="移除"
          >✕</button>
        </div>
      </div>
      <p class="form-hint">
        共 {{ mergeItems.length }} 个文件。页码范围例：1-3, 5（留空取全部页）
      </p>
    </div>

    <!-- 输出文件名 -->
    <div class="form-section">
      <label class="form-label">输出文件名（可选）</label>
      <input
        v-model="outputName"
        type="text"
        class="form-input"
        placeholder="留空使用 merged_时间戳.pdf"
      />
      <p class="form-hint">不需要输入 .pdf 后缀，会自动补上</p>
    </div>

    <ActionBar
      :can-submit="uploadedFiles.length >= 2"
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
import ActionBar from './common/ActionBar.vue'
import ResultCard from './common/ResultCard.vue'

const emit = defineEmits(['submitted'])

const dropRef = ref(null)
const uploadedFiles = ref([])
const filePageRanges = ref([])   // 与 uploadedFiles 一一对应
const sortMode = ref('upload')
const outputName = ref('')
const loading = ref(false)
const result = ref(null)

// 展示列表（含排序），保留 originalIndex 用于增删改
const mergeItems = computed(() => {
  const list = uploadedFiles.value.map((file, i) => ({
    file,
    originalIndex: i,
    key: `${i}-${file.name}-${file.size}-${file.lastModified}`,
  }))
  if (sortMode.value === 'filename') {
    list.sort((a, b) =>
      a.file.name.localeCompare(b.file.name, undefined, {
        numeric: true,
        sensitivity: 'base',
      })
    )
  }
  return list
})

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function onFiles(files) {
  uploadedFiles.value = [...uploadedFiles.value, ...files]
  filePageRanges.value = [...filePageRanges.value, ...files.map(() => '')]
}

function moveMergeItem(index, delta) {
  const target = index + delta
  if (target < 0 || target >= uploadedFiles.value.length) return

  const files = [...uploadedFiles.value]
  const ranges = [...filePageRanges.value]
  ;[files[index], files[target]] = [files[target], files[index]]
  ;[ranges[index], ranges[target]] = [ranges[target], ranges[index]]

  uploadedFiles.value = files
  filePageRanges.value = ranges
}

function removeMergeItem(index) {
  uploadedFiles.value.splice(index, 1)
  filePageRanges.value.splice(index, 1)
  if (uploadedFiles.value.length === 0) dropRef.value?.reset()
}

function reset() {
  uploadedFiles.value = []
  filePageRanges.value = []
  sortMode.value = 'upload'
  outputName.value = ''
  result.value = null
  loading.value = false
  dropRef.value?.reset()
}

async function submit() {
  if (uploadedFiles.value.length < 2) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    for (const item of mergeItems.value) {
      fd.append('files', item.file)
      fd.append('page_ranges', filePageRanges.value[item.originalIndex] || '')
    }
    if (outputName.value.trim()) {
      fd.append('output_name', outputName.value.trim())
    }

    const res = await api.post('/pdf-merge', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '合并完成',
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