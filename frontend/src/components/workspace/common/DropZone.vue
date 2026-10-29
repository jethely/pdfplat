<template>
  <div class="drop-zone" @dragover.prevent @drop.prevent="onDrop">
    <div class="drop-zone-content">
      <span class="drop-icon">{{ icon }}</span>
      <p>{{ text }}</p>
      <input
        type="file"
        :accept="accept"
        :multiple="multiple"
        ref="inputRef"
        @change="onChange"
        class="file-input"
      />
      <button class="btn-outline" @click="openPicker">{{ buttonText }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  accept:     { type: String,  default: '' },
  multiple:   { type: Boolean, default: false },
  icon:       { type: String,  default: '📁' },
  text:       { type: String,  default: '拖拽文件到此处，或点击选择' },
  buttonText: { type: String,  default: '选择文件' },
})

const emit = defineEmits(['files'])
const inputRef = ref(null)

function openPicker() {
  inputRef.value?.click()
}

function onChange(e) {
  const files = Array.from(e.target.files || [])
  if (files.length) emit('files', props.multiple ? files : [files[0]])
  e.target.value = ''      // 允许重复选同一文件
}

function onDrop(e) {
  const files = Array.from(e.dataTransfer.files || [])
  if (!files.length) return
  emit('files', props.multiple ? files : [files[0]])
}

function reset() {
  if (inputRef.value) inputRef.value.value = ''
}

defineExpose({ reset })
</script>