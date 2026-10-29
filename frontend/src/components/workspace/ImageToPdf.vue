<template>
  <div class="tool-image-to-pdf">
    <!-- 选择文件 -->
    <div class="form-section">
      <label class="form-label">选择图片（可多选）</label>
      <DropZone
        ref="dropRef"
        accept=".png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif"
        :multiple="true"
        icon="🖼️"
        text="拖拽图片到此处，或点击选择"
        button-text="选择图片"
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

    <!-- 文件列表 -->
    <div v-if="uploadedFiles.length" class="form-section">
      <FileList
        :files="orderedFiles"
        :show-index="true"
        icon="🖼️"
        @remove="onRemove"
      />
      <p class="form-hint">
        共 {{ uploadedFiles.length }} 张图片，将按上述顺序生成 {{ uploadedFiles.length }} 页 PDF
      </p>
    </div>
    <p v-else class="form-hint">
      生成的文件名格式：首图名_merged_时间戳.pdf
    </p>

    <ActionBar
      :can-submit="uploadedFiles.length > 0"
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
const uploadedFiles = ref([])
const sortMode = ref('upload')
const loading = ref(false)
const result = ref(null)

// 按当前排序模式返回有序列表（不改原数组）
const orderedFiles = computed(() => {
  const list = uploadedFiles.value
  if (sortMode.value !== 'filename') return list
  return [...list].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, {
      numeric: true,
      sensitivity: 'base',
    })
  )
})

function onFiles(files) {
  uploadedFiles.value = [...uploadedFiles.value, ...files]
}

// 按对象引用删除（排序后索引会错位）
function onRemove({ file }) {
  const idx = uploadedFiles.value.indexOf(file)
  if (idx >= 0) uploadedFiles.value.splice(idx, 1)
  if (uploadedFiles.value.length === 0) dropRef.value?.reset()
}

function reset() {
  uploadedFiles.value = []
  sortMode.value = 'upload'
  result.value = null
  loading.value = false
  dropRef.value?.reset()
}

async function submit() {
  if (!uploadedFiles.value.length) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    // 按排序后的顺序 append
    orderedFiles.value.forEach((f) => fd.append('files', f))

    const res = await api.post('/image-to-pdf', fd, {
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