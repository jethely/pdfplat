<template>
  <div class="tool-pdf-nup">
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
      <label class="form-label">每页份数</label>
      <div class="radio-group">
        <label class="radio-item">
          <input type="radio" v-model.number="nPerPage" :value="2" />
          <span>2 份（1×2）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="nPerPage" :value="4" />
          <span>4 份（2×2）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="nPerPage" :value="6" />
          <span>6 份（2×3）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model.number="nPerPage" :value="9" />
          <span>9 份（3×3）</span>
        </label>
      </div>
      <p class="form-hint">适合打印节省纸张。原 N 页 → 输出 1 页。</p>
    </div>

    <div class="form-section">
      <label class="form-label">纸张大小</label>
      <select v-model="paper" class="form-input">
        <option value="A4">A4（210×297mm）</option>
        <option value="A3">A3（297×420mm）</option>
        <option value="Letter">Letter（8.5×11in）</option>
      </select>
    </div>

    <div class="form-section">
      <label class="form-label">页边距：{{ margin }} pt</label>
      <input v-model.number="margin" type="range" min="0" max="50" step="5" class="slider" />
    </div>

    <div class="form-section">
      <label class="form-label">格子间距：{{ gap }} pt</label>
      <input v-model.number="gap" type="range" min="0" max="30" step="2" class="slider" />
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
const nPerPage = ref(4)
const paper = ref('A4')
const margin = ref(10)
const gap = ref(6)
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
    fd.append('n_per_page', String(nPerPage.value))
    fd.append('paper', paper.value)
    fd.append('margin', String(margin.value))
    fd.append('gap', String(gap.value))
    const res = await api.post('/pdf-nup', fd, {
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