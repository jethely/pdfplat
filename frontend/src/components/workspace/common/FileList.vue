<template>
  <div v-if="files.length" class="file-list">
    <div v-for="(f, i) in files" :key="keyOf(f, i)" class="file-info">
      <span v-if="showIndex" class="file-index">{{ i + 1 }}.</span>
      <span class="file-icon">{{ icon }}</span>
      <span>{{ f.name }}</span>
      <span class="file-size">({{ formatSize(f.size) }})</span>
      <button class="btn-remove" @click="$emit('remove', { file: f, index: i })">✕</button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  files:     { type: Array,   default: () => [] },
  showIndex: { type: Boolean, default: false },
  icon:      { type: String,  default: '📄' },
})

defineEmits(['remove'])

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function keyOf(f, i) {
  return `${f.name}-${f.size}-${f.lastModified || 0}-${i}`
}
</script>