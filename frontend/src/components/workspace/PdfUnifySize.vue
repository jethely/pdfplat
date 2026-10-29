<template>
  <div class="tool-pdf-unify-size">
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

    <div class="form-section">
      <label class="form-label">目标尺寸</label>
      <select v-model="targetSize" class="form-input">
        <option value="A4">A4（210×297mm）</option>
        <option value="A3">A3（297×420mm）</option>
        <option value="A5">A5（148×210mm）</option>
        <option value="Letter">Letter（8.5×11in）</option>
      </select>
    </div>

    <div class="form-section">
      <label class="form-label">页面方向</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="orientation" value="auto" />
          <span><b>自动</b>（根据原页面的宽高比）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="orientation" value="portrait" />
          <span>强制纵向</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="orientation" value="landscape" />
          <span>强制横向</span>
        </label>
      </div>
    </div>

    <div class="form-section">
      <label class="form-label">适应方式</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="fitMode" value="fit" />
          <span><b>等比缩放 + 居中</b>（保留原比例，可能留白）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="fitMode" value="fill" />
          <span><b>拉伸铺满</b>（不留白，但可能变形）</span>
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
const targetSize = ref('A4')
const orientation = ref('auto')
const fitMode = ref('fit')
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
    fd.append('target_size', targetSize.value)
    fd.append('orientation', orientation.value)
    fd.append('fit_mode', fitMode.value)
    const res = await api.post('/pdf-unify-size', fd, {
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