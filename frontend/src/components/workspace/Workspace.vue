<template>
  <main class="workspace">
    <div class="workspace-header">
      <div class="header-left">
        <span class="header-icon">{{ tool?.icon }}</span>
        <h1 class="header-title">{{ tool?.label }}</h1>
      </div>
    </div>

    <div class="workspace-body">
      <div class="card">
        <component
          :is="currentComponent"
          v-if="currentComponent"
          :tool="tool"
          :key="tool?.id"
          @submitted="onSubmitted"
        />
        <p v-else class="form-hint">该功能尚未实现。</p>
      </div>

      <FileManager ref="fileManagerRef" :tool-id="tool?.id" />
    </div>
  </main>
</template>

<script setup>
import { ref, computed } from 'vue'
import FileManager from '../FileManager.vue'
import './workspace.css'
// 工具组件（分批补齐，缺的显示"未实现"）
import PdfCompress from './PdfCompress.vue'
import PdfToImage from './PdfToImage.vue'
import ImageToPdf from './ImageToPdf.vue'
import PdfSplit from './PdfSplit.vue'
import PdfMerge from './PdfMerge.vue'
import PdfEncrypt from './PdfEncrypt.vue'
import PdfDecrypt from './PdfDecrypt.vue'
import TextReplace from './TextReplace.vue'
import PerforatedStamp from './PerforatedStamp.vue'
import StampOperation from './StampOperation.vue'
import PdfWatermark from './PdfWatermark.vue'
import PdfPageNumber from './PdfPageNumber.vue'
import PdfDeletePages from './PdfDeletePages.vue'
import PdfRotatePages from './PdfRotatePages.vue'
import PdfRedact from './PdfRedact.vue'
import PdfToWord from './PdfToWord.vue'
import PdfCompare from './PdfCompare.vue'
import ExtractImages from './ExtractImages.vue'
import PdfMetadata from './PdfMetadata.vue'
import PdfBookmark from './PdfBookmark.vue'
import PdfReorder from './PdfReorder.vue'
import PdfToText from './PdfToText.vue'
import PdfToLongImage from './PdfToLongImage.vue'
import PdfNUp from './PdfNUp.vue'
import PdfUnifySize from './PdfUnifySize.vue'
import PdfToExcel from './PdfToExcel.vue'
import RemoveWatermark from './RemoveWatermark.vue'

const props = defineProps({
  tool: { type: Object, default: null },
})

const fileManagerRef = ref(null)

const componentMap = {
  'pdf-compress': PdfCompress,
  'pdf-to-image': PdfToImage,
  'image-to-pdf': ImageToPdf,
  'pdf-split': PdfSplit,
  'pdf-merge': PdfMerge,
  'pdf-encrypt': PdfEncrypt,
  'pdf-decrypt': PdfDecrypt,
  'text-replace': TextReplace,
  'perforated-stamp': PerforatedStamp,
  'stamp-operation': StampOperation,
  'pdf-watermark': PdfWatermark,
  'pdf-page-number': PdfPageNumber,
  'pdf-delete-pages': PdfDeletePages,
  'pdf-rotate-pages': PdfRotatePages,
  'pdf-redact': PdfRedact,
  'pdf-to-word': PdfToWord,
  'pdf-compare': PdfCompare,
  'extract-images': ExtractImages,
  'pdf-metadata': PdfMetadata,
  'pdf-bookmark': PdfBookmark,
  'pdf-reorder': PdfReorder,
  'pdf-to-text': PdfToText,
  'pdf-to-long-image': PdfToLongImage,
  'pdf-nup': PdfNUp,
  'pdf-unify-size': PdfUnifySize,
  'pdf-to-excel': PdfToExcel,
  'remove-watermark': RemoveWatermark,
}

const currentComponent = computed(() => componentMap[props.tool?.id] || null)

function onSubmitted() {
  fileManagerRef.value?.refresh()
}
</script>

<style scoped>
.workspace {
  position: fixed;
  top: 0; right: 0; bottom: 0;
  left: var(--sidebar-width, 260px);
  margin: 0; padding: 0;
  width: auto;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--bg, #fff);
  z-index: 1;
}

.workspace-header {
  padding: 18px 32px;
  background: var(--card-bg, #fff);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 50;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-icon { font-size: 26px; }
.header-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #111827);
  margin: 0;
}

.workspace-body { padding: 28px 32px; flex: 1; }

.card {
  background: var(--card-bg, #fff);
  border-radius: var(--radius, 8px);
  box-shadow: var(--shadow, 0 4px 12px rgba(0, 0, 0, 0.08));
  padding: 28px;
  border: 1px solid var(--border-color, #e5e7eb);
}
</style>