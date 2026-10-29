<template>
  <div class="tool-pdf-split">
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

    <!-- 拆分方式 -->
    <div class="form-section">
      <label class="form-label">拆分方式</label>
      <div class="radio-group radio-vertical">
        <label class="radio-item">
          <input type="radio" v-model="splitMode" value="extract" />
          <span>提取指定页</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="splitMode" value="per-page" />
          <span>每页拆开</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="splitMode" value="chunk" />
          <span>每隔 N 页抽取</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="splitMode" value="parity" />
          <span>奇数页 / 偶数页</span>
        </label>
      </div>
    </div>

    <!-- extract 参数 -->
    <div v-if="splitMode === 'extract'" class="form-section">
      <label class="form-label">页码</label>
      <input
        v-model="pages"
        type="text"
        class="form-input"
        placeholder="例: 1-3, 5, 7-9"
      />
      <p class="form-hint">支持单个页码、连续范围，用逗号分隔</p>
    </div>

    <!-- per-page 说明 -->
    <div v-if="splitMode === 'per-page'" class="form-section">
      <p class="form-hint">
        将 PDF 的每一页拆成一个独立 PDF，输出 N 个文件，请到下方「我的文件」逐个下载。
      </p>
    </div>

    <!-- chunk 参数 -->
    <div v-if="splitMode === 'chunk'" class="form-section">
      <label class="form-label">每隔几页抽取一页</label>
      <input
        v-model.number="chunkSize"
        type="number"
        min="1"
        class="form-input"
        placeholder="例: 2"
      />
      <p class="form-hint">
        每隔 N 页抽取一页，生成 N 个 PDF。<br />
        例：5 页 PDF，N=2 → 文件1 抽第 1,3,5 页；文件2 抽第 2,4 页
      </p>
    </div>

    <!-- parity 参数 -->
    <div v-if="splitMode === 'parity'" class="form-section">
      <label class="form-label">提取</label>
      <div class="radio-group">
        <label class="radio-item">
          <input type="radio" v-model="parity" value="odd" />
          <span>奇数页（1, 3, 5...）</span>
        </label>
        <label class="radio-item">
          <input type="radio" v-model="parity" value="even" />
          <span>偶数页（2, 4, 6...）</span>
        </label>
      </div>
    </div>

    <ActionBar
      :can-submit="canSubmit"
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
const file = ref(null)
const splitMode = ref('extract')
const pages = ref('')
const chunkSize = ref(2)
const parity = ref('odd')
const loading = ref(false)
const result = ref(null)

const canSubmit = computed(() => {
  if (!file.value) return false
  if (splitMode.value === 'extract' && !pages.value.trim()) return false
  if (splitMode.value === 'chunk' && (!chunkSize.value || chunkSize.value < 1)) return false
  return true
})

function onFiles(files) {
  file.value = files[0] || null
}

function onRemove() {
  file.value = null
  dropRef.value?.reset()
}

function reset() {
  file.value = null
  splitMode.value = 'extract'
  pages.value = ''
  chunkSize.value = 2
  parity.value = 'odd'
  result.value = null
  loading.value = false
  dropRef.value?.reset()
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('mode', splitMode.value)
    if (splitMode.value === 'extract') {
      fd.append('pages', pages.value)
    } else if (splitMode.value === 'chunk') {
      fd.append('chunk_size', String(chunkSize.value))
    } else if (splitMode.value === 'parity') {
      fd.append('parity', parity.value)
    }

    const res = await api.post('/pdf-split', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '拆分完成',
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