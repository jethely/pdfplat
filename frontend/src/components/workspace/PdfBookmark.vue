<template>
  <div class="tool-pdf-bookmark">
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
      <label class="form-label">书签列表</label>
      <textarea
        v-model="bookmarksText"
        class="form-textarea"
        rows="12"
        placeholder="每行格式：页码 标题
用 2 个空格缩进表示下一级。

例：
1 第一章
  3 第一节
  8 第二节
2 第九章"
      ></textarea>
      <p class="form-hint">
        页码从 1 开始。每多 2 个前导空格代表一级缩进。
      </p>
    </div>

    <ActionBar
      :can-submit="!!file && !!bookmarksText.trim()"
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
const bookmarksText = ref('')
const loading = ref(false)
const result = ref(null)

function onFiles(files) { file.value = files[0] || null }
function onRemove() { file.value = null; dropRef.value?.reset() }
function reset() { bookmarksText.value = ''; result.value = null; loading.value = false }

async function submit() {
  if (!file.value || !bookmarksText.value.trim()) return
  loading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('bookmarks_text', bookmarksText.value)
    const res = await api.post('/pdf-bookmark', fd, {
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