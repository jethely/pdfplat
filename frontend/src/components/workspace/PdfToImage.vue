<template>
  <div class="tool-pdf-to-image">
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

    <!-- 输出格式 -->
    <div class="form-section">
      <label class="form-label">输出图片格式</label>
      <select v-model="imageFormat" class="form-input">
        <option value="png">PNG（无损，支持透明）</option>
        <option value="jpeg">JPEG / JPG（有损，体积小）</option>
        <option value="webp">WebP（现代格式，体积更小）</option>
        <option value="bmp">BMP（无损，无压缩）</option>
        <option value="tiff">TIFF（无损，印刷常用）</option>
      </select>
    </div>

    <!-- DPI -->
    <div class="form-section">
      <label class="form-label">输出分辨率 (DPI)</label>
      <select v-model.number="dpi" class="form-input">
        <option :value="72">72 DPI（屏幕预览）</option>
        <option :value="96">96 DPI（网页常用）</option>
        <option :value="150">150 DPI（推荐）</option>
        <option :value="200">200 DPI（较清晰）</option>
        <option :value="300">300 DPI（印刷级）</option>
        <option :value="600">600 DPI（超高清）</option>
      </select>
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
const imageFormat = ref('png')
const dpi = ref(200)
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
  imageFormat.value = 'png'
  dpi.value = 200
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
    fd.append('image_format', imageFormat.value)
    fd.append('dpi', String(dpi.value))

    const res = await api.post('/pdf-to-image', fd, {
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
    else if (Array.isArray(d)) msg = d[0]?.msg || msg
    else if (err.message) msg = err.message
    result.value = { success: false, message: msg }
  } finally {
    loading.value = false
  }
}
</script>