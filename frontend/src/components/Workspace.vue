<template>
  <main class="workspace">
    <!-- 顶部标题 -->
    <div class="workspace-header">
      <div class="header-left">
        <span class="header-icon">{{ tool?.icon }}</span>
        <h1 class="header-title">{{ tool?.label }}</h1>
      </div>
    </div>

    <div class="workspace-body">
      <div class="card">
        <!-- ============ PDF 转图片 ============ -->
        <template v-if="tool?.id === 'pdf-to-image'">
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div
              class="drop-zone"
              @dragover.prevent
              @drop.prevent="handleDrop($event, 'pdf')"
            >
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input
                  type="file"
                  accept=".pdf"
                  ref="fileInput"
                  @change="handleFileSelect"
                  class="file-input"
                />
                <button class="btn-outline" @click="$refs.fileInput?.click()">
                  选择文件
                </button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>

          <div class="form-section">
            <label class="form-label">输出图片格式</label>
            <select v-model="form.imageFormat" class="form-input">
              <option value="png">PNG（无损，支持透明）</option>
              <option value="jpeg">JPEG / JPG（有损，体积小）</option>
              <option value="webp">WebP（现代格式，体积更小）</option>
              <option value="bmp">BMP（无损，无压缩）</option>
              <option value="tiff">TIFF（无损，印刷常用）</option>
            </select>
          </div>

          <div class="form-section">
            <label class="form-label">输出分辨率 (DPI)</label>
            <select v-model.number="form.dpi" class="form-input">
              <option :value="72">72 DPI（屏幕预览）</option>
              <option :value="96">96 DPI（网页常用）</option>
              <option :value="150">150 DPI（推荐）</option>
              <option :value="200">200 DPI（较清晰）</option>
              <option :value="300">300 DPI（印刷级）</option>
              <option :value="600">600 DPI（超高清）</option>
            </select>
          </div>
        </template>

        <!-- ============ 图片 转 PDF ============ -->
        <template v-else-if="tool?.id === 'image-to-pdf'">
          <div class="form-section">
            <label class="form-label">选择图片（可多选）</label>
            <div
              class="drop-zone"
              @dragover.prevent
              @drop.prevent="handleDrop($event, 'image-multi')"
            >
              <div class="drop-zone-content">
                <span class="drop-icon">🖼️</span>
                <p>拖拽图片到此处，或点击选择</p>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif"
                  multiple
                  ref="fileInput"
                  @change="handleMultiFileSelect"
                  class="file-input"
                />
                <button class="btn-outline" @click="$refs.fileInput?.click()">
                  选择图片
                </button>
              </div>
            </div>

            <div v-if="uploadedFiles.length > 1" class="form-section" style="margin-top: 16px; margin-bottom: 0;">
              <label class="form-label">合并顺序</label>
              <div class="radio-group">
                <label class="radio-item">
                  <input type="radio" v-model="form.sortMode" value="upload" />
                  <span>按上传顺序</span>
                </label>
                <label class="radio-item">
                  <input type="radio" v-model="form.sortMode" value="filename" />
                  <span>按文件名排序</span>
                </label>
              </div>
            </div>

            <div v-if="uploadedFiles.length" class="file-list">
              <div v-for="(f, i) in orderedFiles" :key="f.name + '@' + f.size + '@' + f.lastModified" class="file-info">
                <span class="file-index">{{ i + 1 }}.</span>
                <span class="file-icon">🖼️</span>
                <span>{{ f.name }}</span>
                <span class="file-size">({{ formatSize(f.size) }})</span>
                <button class="btn-remove" @click="removeFileByRef(f)">✕</button>
              </div>
            </div>

            <p v-if="uploadedFiles.length" class="form-hint">
              共 {{ uploadedFiles.length }} 张图片，将按上述顺序生成 {{ uploadedFiles.length }} 页 PDF
            </p>
            <p v-else class="form-hint">
              生成的文件名格式：首图名_merged_时间戳.pdf
            </p>
          </div>
        </template>

        <!-- ============ PDF 拆分 ============ -->
        <template v-else-if="tool?.id === 'pdf-split'">
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>

          <div class="form-section">
            <label class="form-label">拆分方式</label>
            <div class="radio-group radio-vertical">
              <label class="radio-item">
                <input type="radio" v-model="form.splitMode" value="extract" />
                <span>提取指定页</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.splitMode" value="per-page" />
                <span>每页拆开</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.splitMode" value="chunk" />
                <span>每隔 N 页抽取</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.splitMode" value="parity" />
                <span>奇数页 / 偶数页</span>
              </label>
            </div>
          </div>

          <div v-if="form.splitMode === 'extract'" class="form-section">
            <label class="form-label">页码</label>
            <input
              v-model="form.pages"
              type="text"
              class="form-input"
              placeholder="例: 1-3, 5, 7-9"
            />
            <p class="form-hint">支持单个页码、连续范围，用逗号分隔</p>
          </div>

          <div v-if="form.splitMode === 'per-page'" class="form-section">
            <p class="form-hint">
              将 PDF 的每一页拆成一个独立 PDF，输出 N 个文件，请到下方「我的文件」逐个下载。
            </p>
          </div>

          <div v-if="form.splitMode === 'chunk'" class="form-section">
            <label class="form-label">每隔几页抽取一页</label>
            <input
              v-model.number="form.chunkSize"
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

          <div v-if="form.splitMode === 'parity'" class="form-section">
            <label class="form-label">提取</label>
            <div class="radio-group">
              <label class="radio-item">
                <input type="radio" v-model="form.parity" value="odd" />
                <span>奇数页（1, 3, 5...）</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.parity" value="even" />
                <span>偶数页（2, 4, 6...）</span>
              </label>
            </div>
          </div>
        </template>

        <!-- ============ PDF 合并 ============ -->
        <template v-else-if="tool?.id === 'pdf-merge'">
          <div class="form-section">
            <label class="form-label">选择多个 PDF 文件（可多选）</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf-multi')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input
                  type="file"
                  accept=".pdf"
                  multiple
                  ref="fileInput"
                  @change="handleMultiFileSelect"
                  class="file-input"
                />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
          </div>

          <div v-if="uploadedFiles.length > 1" class="form-section">
            <label class="form-label">合并顺序</label>
            <div class="radio-group">
              <label class="radio-item">
                <input type="radio" v-model="form.sortMode" value="upload" />
                <span>按上传顺序</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.sortMode" value="filename" />
                <span>按文件名排序</span>
              </label>
            </div>
          </div>

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
                  v-if="form.sortMode === 'upload'"
                  class="merge-btn"
                  :disabled="idx === 0"
                  @click="moveMergeItem(item.originalIndex, -1)"
                  title="上移"
                >↑</button>
                <button
                  v-if="form.sortMode === 'upload'"
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

          <div class="form-section">
            <label class="form-label">输出文件名（可选）</label>
            <input
              v-model="form.mergeOutputName"
              type="text"
              class="form-input"
              placeholder="留空使用 merged_时间戳.pdf"
            />
            <p class="form-hint">不需要输入 .pdf 后缀，会自动补上</p>
          </div>
        </template>

        <!-- ============ 压缩 ============ -->
        <template v-else-if="tool?.id === 'pdf-compress'">
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>

          <div class="form-section">
            <label class="form-label">压缩级别</label>
            <div class="radio-group radio-vertical">
              <label class="radio-item">
                <input type="radio" v-model="form.compressLevel" value="light" />
                <span>
                  <b>轻度</b> — 无损，仅清理冗余对象
                  <span class="form-hint-inline">（画质不变）</span>
                </span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.compressLevel" value="medium" />
                <span>
                  <b>中度</b> — 图片降采样到 150 DPI
                  <span class="form-hint-inline">（画质轻微下降）</span>
                </span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.compressLevel" value="high" />
                <span>
                  <b>重度</b> — 图片降采样到 96 DPI
                  <span class="form-hint-inline">（体积最小，画质明显下降）</span>
                </span>
              </label>
            </div>
            <p class="form-hint">
              未压缩过的 PDF 通常能显著瘦身；已经压缩过的 PDF 提升有限。
            </p>
          </div>
        </template>

        <!-- ============ 加密 ============ -->
        <template v-else-if="tool?.id === 'pdf-encrypt'">
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>

          <div class="form-section">
            <label class="form-label">打开密码（必填，打开 PDF 时需输入）</label>
            <input
              v-model="form.encryptPassword"
              type="password"
              class="form-input"
              placeholder="请输入打开密码"
              autocomplete="new-password"
              maxlength="64"
            />
          </div>

          <div class="form-section">
            <label class="form-label">确认打开密码</label>
            <input
              v-model="form.encryptPassword2"
              type="password"
              class="form-input"
              placeholder="请再次输入打开密码"
              autocomplete="new-password"
              maxlength="64"
            />
            <p v-if="encryptPasswordMismatch" class="form-hint error-hint">
              ⚠️ 两次输入的密码不一致
            </p>
          </div>

          <div class="form-section">
            <label class="form-label">权限密码（可选，用于修改权限设置）</label>
            <input
              v-model="form.ownerPassword"
              type="password"
              class="form-input"
              placeholder="留空则自动生成随机权限密码"
              autocomplete="new-password"
              maxlength="64"
            />
            <p class="form-hint">
              拥有权限密码的人可以修改权限（打印、复制等）。留空则用随机值，更安全。
            </p>
          </div>

          <div class="form-section">
            <label class="form-label">权限级别</label>
            <div class="radio-group radio-vertical">
              <label class="radio-item">
                <input type="radio" v-model="form.permLevel" value="all" />
                <span><b>全权限</b> — 仅加密，不限制任何操作</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.permLevel" value="print-only" />
                <span><b>仅阅读 + 打印</b> — 禁止复制、修改、批注</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.permLevel" value="readonly" />
                <span><b>仅阅读</b> — 禁止打印、复制、修改等所有操作</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.permLevel" value="custom" />
                <span><b>自定义</b> — 逐项选择允许的操作</span>
              </label>
            </div>
          </div>

          <div v-if="form.permLevel === 'custom'" class="form-section">
            <label class="form-label">允许的操作</label>
            <div class="checkbox-grid">
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.permPrint" />
                <span>打印</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.permCopy" />
                <span>复制文字</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.permModify" />
                <span>修改内容</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.permAnnotate" />
                <span>添加批注</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.permForm" />
                <span>填写表单</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.permAccessibility" />
                <span>无障碍访问</span>
              </label>
            </div>
          </div>
        </template>

        <!-- ============ 解密（破解） ============ -->
        <template v-else-if="tool?.id === 'pdf-decrypt'">
          <!-- 警告 -->
          <div class="form-section warn-banner">
            ⚠️ 本功能仅供破解您本人遗忘密码的 PDF。请勿用于他人文件。
          </div>

          <!-- 选择文件 -->
          <div class="form-section">
            <label class="form-label">选择已加密的 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>

          <!-- 破解模式 -->
          <div class="form-section">
            <label class="form-label">破解方式</label>
            <div class="radio-group radio-vertical">
              <label class="radio-item">
                <input type="radio" v-model="form.crackMode" value="smart" />
                <span><b>智能尝试（推荐）</b> — 空密码 → 常见弱密码 → 短数字</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.crackMode" value="dictionary" />
                <span><b>字典破解</b> — 从内置字典或自定义字典中尝试</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.crackMode" value="brute" />
                <span><b>暴力破解</b> — 指定字符集和长度范围</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.crackMode" value="mask" />
                <span><b>掩码破解</b> — 已知部分 + 未知部分（?）</span>
              </label>
            </div>
          </div>

          <!-- 字典模式 -->
          <div v-if="form.crackMode === 'dictionary'" class="form-section">
            <label class="form-label">字典来源</label>
            <div class="radio-group radio-vertical">
              <label class="radio-item">
                <input type="radio" v-model="form.dictSource" value="builtin-simple" />
                <span><b>内置简单</b> — 常见弱密码 + 4/6 位纯数字</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.dictSource" value="builtin-medium" />
                <span><b>内置中等</b> — 需管理员放置字典文件</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.dictSource" value="builtin-complex" />
                <span><b>内置复杂</b> — 需管理员放置字典文件</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.dictSource" value="custom" />
                <span><b>自定义上传</b></span>
              </label>
            </div>

            <div v-if="form.dictSource === 'custom'" style="margin-top: 14px;">
              <label class="form-label">上传字典文件（每行一个密码）</label>
              <input
                type="file"
                accept=".txt,.dict,.dic"
                ref="dictInput"
                @change="handleDictFile"
                class="native-file-input"
              />
              <div v-if="dictFile" class="file-info">
                <span class="file-icon">📝</span>
                <span>{{ dictFile.name }}</span>
                <span class="file-size">({{ formatSize(dictFile.size) }})</span>
              </div>
              <p class="form-hint">
                上传的字典会保存到您的专属目录，多个任务可复用
              </p>
            </div>
          </div>

          <!-- 暴力模式 -->
          <div v-if="form.crackMode === 'brute'" class="form-section">
            <label class="form-label">字符集</label>
            <div class="checkbox-grid">
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.bruteDigits" />
                <span>数字 0-9</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.bruteLower" />
                <span>小写字母</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.bruteUpper" />
                <span>大写字母</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.bruteSymbols" />
                <span>特殊符号</span>
              </label>
            </div>
            <label class="form-label" style="margin-top: 14px;">长度范围</label>
            <div style="display: flex; align-items: center; gap: 10px;">
              <input
                v-model.number="form.bruteMinLen"
                type="number" min="1" max="11"
                class="form-input" style="width: 80px;" />
              <span>~</span>
              <input
                v-model.number="form.bruteMaxLen"
                type="number" min="1" max="11"
                class="form-input" style="width: 80px;" />
              <span class="form-hint" style="margin: 0;">（最长 11 位，适合手机号）</span>
            </div>
            <p class="form-hint">
              ⚠️ 11 位纯数字有 1000 亿种，正常机器要跑几天几夜。建议先用掩码模式缩小范围。
            </p>
          </div>

          <!-- 掩码模式 -->
          <div v-if="form.crackMode === 'mask'" class="form-section">
            <label class="form-label">掩码（? = 未知位）</label>
            <input
              v-model="form.maskPattern"
              type="text"
              class="form-input"
              placeholder="例：138????????  或  ????????1234"
              maxlength="16"
            />
            <label class="form-label" style="margin-top: 14px;">未知位字符集</label>
            <div class="checkbox-grid">
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.maskDigits" />
                <span>数字 0-9</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.maskLower" />
                <span>小写字母</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="form.maskUpper" />
                <span>大写字母</span>
              </label>
            </div>
            <p class="form-hint">
              示例：<br>
              • 手机号前 3 位已知 → <code>138????????</code>（11 位）<br>
              • 手机号后 4 位已知 → <code>???????1234</code>（11 位）<br>
              • 8 位纯数字密码 → <code>????????</code>
            </p>
          </div>

          <!-- 运行中的进度面板 -->
          <div v-if="crackTaskId && crackStatus && crackStatus.status === 'running'" class="form-section crack-panel">
            <div class="crack-header">
              <span class="crack-spinner"></span>
              <span>正在破解…（{{ crackStatus.phase }}）</span>
            </div>
            <div class="crack-progress-bar">
              <div class="crack-progress-fill" :style="{ width: (crackStatus.progress * 100) + '%' }"></div>
            </div>
            <div class="crack-stats">
              <div>已尝试：<b>{{ crackStatus.attempts.toLocaleString() }}</b> 次</div>
              <div v-if="crackStatus.total_estimate">
                总数：<b>{{ crackStatus.total_estimate.toLocaleString() }}</b>
              </div>
              <div>速度：<b>{{ crackStatus.speed.toLocaleString() }}</b> 次/秒</div>
              <div>已用时：<b>{{ formatDuration(crackStatus.elapsed) }}</b></div>
              <div v-if="crackStatus.eta_seconds">
                预计剩余：<b>{{ formatDuration(crackStatus.eta_seconds) }}</b>
              </div>
              <div v-if="crackStatus.workers">
                并行：<b>{{ crackStatus.workers }}</b> 线程
                <span v-if="crackStatus.hardware" style="color: #6b7280;">
                  （CPU {{ crackStatus.hardware.cpu_logical }} 核 × {{ crackStatus.hardware.cpu_target_pct }}%）
                </span>
              </div>
            </div>
            <button class="btn-ghost danger" @click="cancelCrack">⏹ 取消</button>
          </div>

          <!-- 破解成功 -->
          <div v-if="crackStatus && crackStatus.status === 'done' && crackStatus.success" class="result-card success" style="margin-top: 16px;">
            <span class="result-icon">✅</span>
            <div class="result-body">
              <h4>破解成功！</h4>
              <p class="result-msg">
                找到密码：<code class="crack-password">{{ crackStatus.found_password }}</code>
              </p>
              <p class="result-hint">
                用时 {{ formatDuration(crackStatus.elapsed) }}，
                共尝试 {{ crackStatus.attempts.toLocaleString() }} 次
              </p>
              <button class="btn-primary" style="margin-top: 12px;" @click="applyDecrypt" :disabled="loading">
                🔓 用此密码解密并保存
              </button>
            </div>
          </div>

          <!-- 破解完成：未找到 -->
          <div v-if="crackStatus && crackStatus.status === 'done' && !crackStatus.success" class="result-card error" style="margin-top: 16px;">
            <span class="result-icon">❌</span>
            <div class="result-body">
              <h4>未找到密码</h4>
              <p class="result-msg">{{ crackStatus.error }}</p>
              <p class="result-hint">
                已尝试 {{ crackStatus.attempts.toLocaleString() }} 次，用时 {{ formatDuration(crackStatus.elapsed) }}
              </p>
            </div>
          </div>

          <!-- 破解失败（出错） -->
          <div v-if="crackStatus && crackStatus.status === 'failed'" class="result-card error" style="margin-top: 16px;">
            <span class="result-icon">❌</span>
            <div class="result-body">
              <h4>破解失败</h4>
              <p class="result-msg">{{ crackStatus.error }}</p>
            </div>
          </div>

          <!-- 已取消 -->
          <div v-if="crackStatus && crackStatus.status === 'cancelled'" class="result-card error" style="margin-top: 16px;">
            <span class="result-icon">⏹</span>
            <div class="result-body">
              <h4>已取消</h4>
              <p class="result-hint">
                已尝试 {{ crackStatus.attempts.toLocaleString() }} 次，用时 {{ formatDuration(crackStatus.elapsed) }}
              </p>
            </div>
          </div>
		  
		  <!-- 服务重启中断 -->
          <div v-if="crackStatus && crackStatus.status === 'interrupted'" class="result-card error" style="margin-top: 16px;">
            <span class="result-icon">⚠️</span>
            <div class="result-body">
              <h4>任务已中断</h4>
              <p class="result-msg">{{ crackStatus.error || '服务重启，任务未完成' }}</p>
              <p class="result-hint">
                已尝试 {{ crackStatus.attempts.toLocaleString() }} 次
              </p>
            </div>
          </div>
        </template>

        <!-- ============ 文字替换 ============ -->
        <template v-else-if="tool?.id === 'text-replace'">
          <!-- 选择文件 -->
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>

          <!-- 查找文字 -->
          <div class="form-section">
            <label class="form-label">查找文字</label>
            <input
              v-model="form.oldText"
              type="text"
              class="form-input"
              placeholder="请输入要替换的文字"
            />
          </div>

          <!-- 替换为 -->
          <div class="form-section">
            <label class="form-label">替换为</label>
            <input
              v-model="form.newText"
              type="text"
              class="form-input"
              placeholder="留空则删除查找的文字"
            />
          </div>

          <!-- ⭐ 搜索范围 -->
          <div class="form-section">
            <label class="form-label">搜索范围</label>
            <div class="radio-group radio-vertical">
              <label class="radio-item">
                <input type="radio" v-model="form.replaceScope" value="all" />
                <span>全文（所有页面）</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.replaceScope" value="pages" />
                <span>指定页面</span>
              </label>
            </div>
            <div v-if="form.replaceScope === 'pages'" style="margin-top: 12px;">
              <input
                v-model="form.replacePages"
                type="text"
                class="form-input"
                placeholder="例: 1, 3, 5-7"
              />
              <p class="form-hint">
                页码用逗号分隔，支持范围（如 <code>1-3</code>）。页码从 1 开始。
              </p>
            </div>
          </div>
        </template>

        <!-- ============ 骑缝章替换/擦除 ============ -->
        <template v-else-if="tool?.id === 'perforated-stamp'">
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>
          <div class="form-section">
            <label class="form-label">操作类型</label>
            <div class="radio-group">
              <label class="radio-item">
                <input type="radio" v-model="form.action" value="replace" />
                <span>替换骑缝章</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.action" value="erase" />
                <span>擦除骑缝章</span>
              </label>
            </div>
          </div>
          <div v-if="form.action === 'replace'" class="form-section">
            <label class="form-label">新骑缝章图片</label>
            <input type="file" accept=".png,.jpg" @change="handleStampFile" class="native-file-input" />
          </div>
        </template>

        <!-- ============ 印章替换/擦除 ============ -->
        <template v-else-if="tool?.id === 'stamp-operation'">
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>
          <div class="form-section">
            <label class="form-label">操作类型</label>
            <div class="radio-group">
              <label class="radio-item">
                <input type="radio" v-model="form.action" value="replace" />
                <span>替换印章</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.action" value="erase" />
                <span>擦除印章</span>
              </label>
            </div>
          </div>
          <div v-if="form.action === 'replace'" class="form-section">
            <label class="form-label">新印章图片</label>
            <input type="file" accept=".png,.jpg" @change="handleStampFile" class="native-file-input" />
          </div>
        </template>

        <!-- ============ 文字遮掩/擦除 ============ -->
        <template v-else-if="tool?.id === 'text-redact'">
          <div class="form-section">
            <label class="form-label">选择 PDF 文件</label>
            <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop($event, 'pdf')">
              <div class="drop-zone-content">
                <span class="drop-icon">📁</span>
                <p>拖拽 PDF 文件到此处，或点击选择</p>
                <input type="file" accept=".pdf" ref="fileInput" @change="handleFileSelect" class="file-input" />
                <button class="btn-outline" @click="$refs.fileInput?.click()">选择文件</button>
              </div>
            </div>
            <div v-if="uploadedFile" class="file-info">
              <span class="file-icon">📄</span>
              <span>{{ uploadedFile.name }}</span>
              <span class="file-size">({{ formatSize(uploadedFile.size) }})</span>
              <button class="btn-remove" @click="removeFile">✕</button>
            </div>
          </div>
          <div class="form-section">
            <label class="form-label">遮掩操作</label>
            <div class="radio-group">
              <label class="radio-item">
                <input type="radio" v-model="form.redactAction" value="mask" />
                <span>文字遮掩（覆盖黑块）</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="form.redactAction" value="erase" />
                <span>文字擦除（删除文字）</span>
              </label>
            </div>
          </div>
          <div class="form-section">
            <label class="form-label">需要遮掩/擦除的文字</label>
            <textarea
              v-model="form.textToRedact"
              class="form-textarea"
              placeholder="请输入需要遮掩或擦除的文字内容"
              rows="3"
            ></textarea>
          </div>
        </template>

        <!-- ============ 兜底 ============ -->
        <template v-else>
          <p class="form-hint">该功能尚未实现。</p>
        </template>

        <!-- ============ 操作按钮 ============ -->
        <div class="action-bar">
          <button
            class="btn-primary"
            :disabled="!canSubmit || loading"
            @click="submitTask"
          >
            <span v-if="loading" class="spinner"></span>
            <span v-else class="btn-icon">🚀</span>
            <span v-if="loading" class="btn-text">处理中...</span>
            <span v-else class="btn-text">开始处理</span>
          </button>
          <button class="btn-secondary" @click="resetForm">
            <span class="btn-icon">🔄</span>
            <span class="btn-text">重置</span>
          </button>
        </div>

        <!-- ============ 结果提示 ============ -->
        <div v-if="result" class="result-section">
          <div :class="['result-card', result.success ? 'success' : 'error']">
            <span class="result-icon">{{ result.success ? '✅' : '❌' }}</span>
            <div class="result-body">
              <h4>{{ result.success ? '处理成功' : '处理失败' }}</h4>
              <p class="result-msg">{{ result.message }}</p>
              <p v-if="result.success" class="result-hint">
                生成的文件已保存到下方「我的文件」，可展开下载。
              </p>
            </div>
          </div>
        </div>
      </div>

      <FileManager ref="fileManagerRef" :tool-id="tool?.id" />
    </div>
  </main>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount, onMounted } from 'vue'
import api from '../api'
import FileManager from './FileManager.vue'

const props = defineProps({
  tool: { type: Object, default: null },
})

const fileInput = ref(null)
const uploadedFile = ref(null)
const uploadedFiles = ref([])
const filePageRanges = ref([])
const stampFile = ref(null)
const loading = ref(false)
const result = ref(null)
const fileManagerRef = ref(null)

// ⭐ PDF 解密相关
const dictInput = ref(null)
const dictFile = ref(null)
const crackTaskId = ref(null)
const crackStatus = ref(null)
let pollTimer = null

const form = reactive({
  pages: '',
  password: '',
  oldText: '',
  newText: '',
  action: 'erase',
  redactAction: 'mask',
  textToRedact: '',
  imageFormat: 'png',
  dpi: 200,
  sortMode: 'upload',
  splitMode: 'extract',
  chunkSize: 2,
  parity: 'odd',
  mergeOutputName: '',
  compressLevel: 'light',
  // PDF 加密字段
  encryptPassword: '',
  encryptPassword2: '',
  ownerPassword: '',
  permLevel: 'all',
  permPrint: true,
  permCopy: true,
  permModify: true,
  permAnnotate: true,
  permForm: true,
  permAccessibility: true,
  // PDF 解密字段
  crackMode: 'smart',
  dictSource: 'builtin-simple',
  bruteDigits: true,
  bruteLower: false,
  bruteUpper: false,
  bruteSymbols: false,
  bruteMinLen: 1,
  bruteMaxLen: 6,
  maskPattern: '',
  maskDigits: true,
  maskLower: false,
  maskUpper: false,
  replaceScope: 'all',      // ⭐ all | pages
  replacePages: '',         // ⭐ 指定页面时的页码字符串
})

// ============ 是否可提交 ============
const needSingle = [
  'pdf-to-image', 'pdf-split', 'pdf-compress', 'pdf-encrypt',
  'pdf-decrypt', 'text-replace', 'perforated-stamp',
  'stamp-operation', 'text-redact',
]
const needMulti = ['image-to-pdf', 'pdf-merge']

const canSubmit = computed(() => {
  const id = props.tool?.id
  if (!id) return false

  if (needSingle.includes(id)) {
    if (!uploadedFile.value) return false

    if (id === 'pdf-split') {
      if (form.splitMode === 'extract' && !form.pages.trim()) return false
      if (form.splitMode === 'chunk' && (!form.chunkSize || form.chunkSize < 1)) return false
    }
    if (id === 'pdf-encrypt') {
      if (!form.encryptPassword) return false
      if (form.encryptPassword !== form.encryptPassword2) return false
    }
    // ⭐ pdf-decrypt 有破解任务在进行时不重复提交
    if (id === 'pdf-decrypt') {
      if (crackTaskId.value && crackStatus.value?.status === 'running') return false
    }
	// ⭐ text-replace 参数校验
    if (id === 'text-replace') {
      if (!form.oldText.trim()) return false
      if (form.replaceScope === 'pages' && !form.replacePages.trim()) return false
    }
    return true
  }
  if (id === 'pdf-merge') return uploadedFiles.value.length >= 2
  if (needMulti.includes(id)) return uploadedFiles.value.length > 0
  return false
})

// ⭐ 按当前排序模式返回有序的文件列表
const orderedFiles = computed(() => {
  const list = uploadedFiles.value
  if (form.sortMode !== 'filename') return list
  return [...list].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, {
      numeric: true,
      sensitivity: 'base',
    })
  )
})

// ⭐ PDF 合并的文件列表
const mergeItems = computed(() => {
  const list = uploadedFiles.value.map((file, i) => ({
    file,
    originalIndex: i,
    key: `${i}-${file.name}-${file.size}-${file.lastModified}`,
  }))
  if (form.sortMode === 'filename') {
    list.sort((a, b) =>
      a.file.name.localeCompare(b.file.name, undefined, {
        numeric: true,
        sensitivity: 'base',
      })
    )
  }
  return list
})

// ⭐ 加密：确认密码不一致时的提示
const encryptPasswordMismatch = computed(() => {
  if (props.tool?.id !== 'pdf-encrypt') return false
  return (
    form.encryptPassword &&
    form.encryptPassword2 &&
    form.encryptPassword !== form.encryptPassword2
  )
})

// ============ 文件选择 ============
function handleFileSelect(e) {
  const f = e.target.files?.[0]
  if (f) uploadedFile.value = f
}

function handleMultiFileSelect(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  uploadedFiles.value = [...uploadedFiles.value, ...files]
  filePageRanges.value = [...filePageRanges.value, ...files.map(() => '')]
}

function handleDrop(e, type) {
  const files = Array.from(e.dataTransfer.files || [])
  if (!files.length) return
  if (type === 'pdf' || type === 'image') {
    uploadedFile.value = files[0]
  } else {
    uploadedFiles.value = [...uploadedFiles.value, ...files]
    filePageRanges.value = [...filePageRanges.value, ...files.map(() => '')]
  }
}

function handleStampFile(e) {
  stampFile.value = e.target.files?.[0] || null
}

function handleDictFile(e) {
  dictFile.value = e.target.files?.[0] || null
}

function removeFile() {
  uploadedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function removeFileAt(index) {
  uploadedFiles.value.splice(index, 1)
  if (fileInput.value) fileInput.value.value = ''
}

function removeFileByRef(file) {
  const idx = uploadedFiles.value.indexOf(file)
  if (idx >= 0) uploadedFiles.value.splice(idx, 1)
  if (fileInput.value) fileInput.value.value = ''
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
  if (fileInput.value) fileInput.value.value = ''
}

function removeMergeItem(index) {
  uploadedFiles.value.splice(index, 1)
  filePageRanges.value.splice(index, 1)
  if (fileInput.value) fileInput.value.value = ''
}

function resetForm() {
  uploadedFile.value = null
  uploadedFiles.value = []
  filePageRanges.value = []
  form.mergeOutputName = ''
  stampFile.value = null
  result.value = null
  loading.value = false
  form.pages = ''
  form.password = ''
  form.oldText = ''
  form.newText = ''
  form.action = 'erase'
  form.redactAction = 'mask'
  form.textToRedact = ''
  form.imageFormat = 'png'
  form.dpi = 200
  form.sortMode = 'upload'
  form.splitMode = 'extract'
  form.chunkSize = 2
  form.parity = 'odd'
  form.compressLevel = 'light'
  form.encryptPassword = ''
  form.encryptPassword2 = ''
  form.ownerPassword = ''
  form.permLevel = 'all'
  form.permPrint = true
  form.permCopy = true
  form.permModify = true
  form.permAnnotate = true
  form.permForm = true
  form.permAccessibility = true
  // ⭐ 解密状态重置
  dictFile.value = null
  crackTaskId.value = null
  crackStatus.value = null
  stopPolling()
  if (dictInput.value) dictInput.value.value = ''
  form.crackMode = 'smart'
  form.dictSource = 'builtin-simple'
  form.bruteDigits = true
  form.bruteLower = false
  form.bruteUpper = false
  form.bruteSymbols = false
  form.bruteMinLen = 1
  form.bruteMaxLen = 6
  form.maskPattern = ''
  form.maskDigits = true
  form.maskLower = false
  form.maskUpper = false
  form.replaceScope = 'all'
  form.replacePages = ''
  if (fileInput.value) fileInput.value.value = ''
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDuration(sec) {
  if (!sec && sec !== 0) return '—'
  sec = Math.floor(sec)
  if (sec < 60) return `${sec} 秒`
  if (sec < 3600) return `${Math.floor(sec / 60)} 分 ${sec % 60} 秒`
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return `${h} 小时 ${m} 分`
}

// ⭐ 恢复最近一次破解任务
async function restoreCrackTask() {
  if (crackTaskId.value) return
  try {
    const res = await api.get('/pdf-decrypt/tasks')
    const tasks = res.data.tasks || []
    if (!tasks.length) return
    const latest = tasks[0]
    crackTaskId.value = latest.task_id
    crackStatus.value = {
      status: latest.status,
      phase: latest.phase,
      attempts: latest.attempts,
      speed: latest.speed,
      progress: latest.progress,
      elapsed: latest.elapsed,
      total_estimate: latest.total_estimate,
      eta_seconds: latest.eta_seconds,
      found_password: latest.found_password,
      success: latest.success,
      error: latest.error,
      workers: latest.workers,
      hardware: latest.hardware,
    }
    if (latest.status === 'running') {
      startPolling()
    }
  } catch (e) {
    console.warn('恢复破解任务失败', e)
  }
}

// ============ PDF 解密：构建字符集 ============
function buildBruteCharset() {
  let cs = ''
  if (form.bruteDigits) cs += '0123456789'
  if (form.bruteLower) cs += 'abcdefghijklmnopqrstuvwxyz'
  if (form.bruteUpper) cs += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  if (form.bruteSymbols) cs += '!@#$%^&*()_+-=[]{}|;:,.<>?'
  return cs
}

function buildMaskCharset() {
  let cs = ''
  if (form.maskDigits) cs += '0123456789'
  if (form.maskLower) cs += 'abcdefghijklmnopqrstuvwxyz'
  if (form.maskUpper) cs += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  return cs
}

// ============ PDF 解密：发起破解 ============
async function startCrack() {
  if (!uploadedFile.value) return
  if (crackTaskId.value && crackStatus.value?.status === 'running') return

  loading.value = true
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', uploadedFile.value)
    fd.append('mode', form.crackMode)

    if (form.crackMode === 'dictionary') {
      fd.append('dict_source', form.dictSource)
      if (form.dictSource === 'custom') {
        if (!dictFile.value) {
          result.value = { success: false, message: '请上传字典文件' }
          loading.value = false
          return
        }
        fd.append('dict_file', dictFile.value)
      }
    }

    if (form.crackMode === 'brute') {
      const cs = buildBruteCharset()
      if (!cs) {
        result.value = { success: false, message: '请至少选择一种字符集' }
        loading.value = false
        return
      }
      if (form.bruteMinLen < 1 || form.bruteMaxLen < form.bruteMinLen || form.bruteMaxLen > 11) {
        result.value = { success: false, message: '长度范围需在 1~11 之间' }
        loading.value = false
        return
      }
      fd.append('charset', cs)
      fd.append('min_len', String(form.bruteMinLen))
      fd.append('max_len', String(form.bruteMaxLen))
    }

    if (form.crackMode === 'mask') {
      if (!form.maskPattern || !form.maskPattern.includes('?')) {
        result.value = { success: false, message: '掩码必须包含至少一个 ?' }
        loading.value = false
        return
      }
      const cs = buildMaskCharset()
      if (!cs) {
        result.value = { success: false, message: '请至少选择一种字符集' }
        loading.value = false
        return
      }
      fd.append('mask', form.maskPattern)
      fd.append('charset', cs)
    }

    const res = await api.post('/pdf-decrypt/start', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    crackTaskId.value = res.data.task_id
    crackStatus.value = {
      status: 'running',
      phase: '初始化',
      attempts: 0,
      speed: 0,
      progress: 0,
      elapsed: 0,
      total_estimate: null,
      eta_seconds: null,
      found_password: null,
      success: null,
      error: null,
      workers: 0,
      hardware: null,
    }
    startPolling()
  } catch (err) {
    const d = err.response?.data?.detail
    result.value = {
      success: false,
      message: typeof d === 'string' ? d : err.message,
    }
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!crackTaskId.value) {
      stopPolling()
      return
    }
    try {
      const res = await api.get(`/pdf-decrypt/status/${crackTaskId.value}`)
      crackStatus.value = res.data
      if (res.data.status !== 'running') {
        stopPolling()
      }
    } catch (e) {
      if (e.response?.status === 404) stopPolling()
    }
  }, 500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function cancelCrack() {
  if (!crackTaskId.value) return
  if (!confirm('确定要取消破解吗？')) return
  try {
    await api.post(`/pdf-decrypt/cancel/${crackTaskId.value}`)
  } catch (e) {
    console.warn(e)
  }
}

async function applyDecrypt() {
  if (!crackTaskId.value) return
  loading.value = true
  try {
    const res = await api.post(`/pdf-decrypt/apply/${crackTaskId.value}`)
    result.value = { success: true, message: res.data.message }
    fileManagerRef.value?.refresh()
  } catch (err) {
    const d = err.response?.data?.detail
    result.value = {
      success: false,
      message: typeof d === 'string' ? d : err.message,
    }
  } finally {
    loading.value = false
  }
}

// ============ 提交 ============
async function submitTask() {
  if (!canSubmit.value) return

  // ⭐ pdf-decrypt 走破解流程
  if (props.tool?.id === 'pdf-decrypt') {
    await startCrack()
    return
  }

  loading.value = true
  result.value = null

  try {
    const formData = new FormData()
    const id = props.tool.id

    if (uploadedFile.value) formData.append('file', uploadedFile.value)

    // ⭐ 多文件按工具分流
    if (id === 'pdf-merge') {
      for (const item of mergeItems.value) {
        formData.append('files', item.file)
        formData.append('page_ranges', filePageRanges.value[item.originalIndex] || '')
      }
      if (form.mergeOutputName.trim()) {
        formData.append('output_name', form.mergeOutputName.trim())
      }
    } else if (id === 'image-to-pdf') {
      orderedFiles.value.forEach((f) => formData.append('files', f))
    } else if (uploadedFiles.value.length) {
      uploadedFiles.value.forEach((f) => formData.append('files', f))
    }

    if (stampFile.value) formData.append('stamp_file', stampFile.value)

    if (id === 'pdf-to-image') {
      formData.append('image_format', form.imageFormat)
      formData.append('dpi', String(form.dpi))
    }

    if (id === 'pdf-split') {
      formData.append('mode', form.splitMode)
      if (form.splitMode === 'extract') {
        formData.append('pages', form.pages)
      } else if (form.splitMode === 'chunk') {
        formData.append('chunk_size', String(form.chunkSize))
      } else if (form.splitMode === 'parity') {
        formData.append('parity', form.parity)
      }
    }

    if (id === 'pdf-compress') {
      formData.append('level', form.compressLevel)
    }

    if (id === 'pdf-encrypt') {
      formData.append('password', form.encryptPassword)
      formData.append('owner_password', form.ownerPassword)
      formData.append('perm_level', form.permLevel)
      formData.append('perm_print', String(form.permPrint))
      formData.append('perm_copy', String(form.permCopy))
      formData.append('perm_modify', String(form.permModify))
      formData.append('perm_annotate', String(form.permAnnotate))
      formData.append('perm_form', String(form.permForm))
      formData.append('perm_accessibility', String(form.permAccessibility))
    }

    if (id === 'text-replace') {
      formData.append('old_text', form.oldText)
      formData.append('new_text', form.newText)
      formData.append(
        'pages',
        form.replaceScope === 'pages' ? form.replacePages : '',
      )
    }

    if (id === 'perforated-stamp' || id === 'stamp-operation') {
      formData.append('action', form.action)
    }
    if (id === 'text-redact') {
      formData.append('text_to_redact', form.textToRedact)
    }
    if (id === 'stamp-operation' && form.action === 'replace') {
      formData.append('position', JSON.stringify({ x: 0, y: 0 }))
    }

    const res = await api.post(props.tool.api, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    result.value = {
      success: true,
      message: res.data.message || '处理完成',
    }

    fileManagerRef.value?.refresh()
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

onMounted(() => {
  if (props.tool?.id === 'pdf-decrypt') {
    restoreCrackTask()
  }
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.workspace {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: var(--sidebar-width, 260px);
  margin: 0 !important;
  padding: 0 !important;
  width: auto !important;
  max-width: none !important;
  text-align: left !important;
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

.form-section { margin-bottom: 22px; }
.form-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  max-width: 480px;
  padding: 10px 14px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-primary, #111827);
  background: #fff;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.form-input:focus {
  border-color: var(--primary-color, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}
select.form-input { cursor: pointer; }

.form-textarea {
  width: 100%;
  max-width: 480px;
  padding: 10px 14px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-primary, #111827);
  background: #fff;
  resize: vertical;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.form-textarea:focus {
  border-color: var(--primary-color, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.form-hint {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  margin-top: 4px;
}
.form-hint.error-hint {
  color: #dc2626;
  font-weight: 500;
}

.form-hint-inline {
  display: inline-block;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  margin-left: 4px;
}

.drop-zone {
  border: 2px dashed var(--border-color, #e5e7eb);
  border-radius: var(--radius, 8px);
  padding: 32px;
  text-align: center;
  transition: all 0.2s;
  cursor: pointer;
  background: #fafbfc;
}
.drop-zone:hover {
  border-color: var(--primary-color, #4f46e5);
  background: var(--primary-light, #eef2ff);
}
.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.drop-icon { font-size: 36px; }
.drop-zone-content p {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 0;
}
.file-input { display: none; }
.native-file-input { font-size: 14px; }

.btn-outline {
  padding: 8px 20px;
  border: 1px solid var(--primary-color, #4f46e5);
  border-radius: 6px;
  background: transparent;
  color: var(--primary-color, #4f46e5);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}
.btn-outline:hover {
  background: var(--primary-color, #4f46e5);
  color: #fff;
}

.btn-primary {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  padding: 12px 28px !important;
  background: var(--primary-color, #4f46e5) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 6px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  cursor: pointer;
  transition: background-color 0.2s, box-shadow 0.2s;
  white-space: nowrap !important;
  line-height: 1.2 !important;
}
.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover, #4338ca) !important;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}
.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 28px;
  background: #f1f5f9;
  color: var(--text-primary, #111827);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 6px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.2 !important;
}
.btn-secondary:hover { background: #e2e8f0; }

.btn-ghost {
  padding: 6px 14px;
  border: 1px solid var(--border-color, #e5e7eb);
  background: #fff;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary, #111827);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-ghost:hover:not(:disabled) {
  background: #f9fafb;
}
.btn-ghost.danger {
  color: #dc2626;
  border-color: #fecaca;
}
.btn-ghost.danger:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}

.btn-icon { font-size: 16px; }
.btn-text { display: inline; }

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  font-size: 13px;
  margin-top: 10px;
}
.file-icon { font-size: 16px; }
.file-index { font-weight: 700; color: var(--primary-color, #4f46e5); }
.file-size { color: var(--text-secondary, #6b7280); }

.btn-remove {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--danger-color, #dc2626);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.2s;
}
.btn-remove:hover { background: #fef2f2; }

.file-list { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }

.radio-group { display: flex; gap: 20px; }
.radio-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
}
.radio-item input[type="radio"] {
  accent-color: var(--primary-color, #4f46e5);
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.radio-group.radio-vertical {
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px 20px;
  max-width: 520px;
}

.checkbox-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-primary, #111827);
  cursor: pointer;
  user-select: none;
}
.checkbox-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--primary-color, #4f46e5);
  cursor: pointer;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid var(--border-color, #e5e7eb);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.result-section { margin-top: 24px; }
.result-card {
  display: flex;
  gap: 14px;
  padding: 18px;
  border-radius: var(--radius, 8px);
  border: 1px solid;
}
.result-card.success { background: #f0fdf4; border-color: #86efac; }
.result-card.error { background: #fef2f2; border-color: #fca5a5; }
.result-icon { font-size: 22px; flex-shrink: 0; margin-top: 2px; }
.result-body h4 { font-size: 15px; font-weight: 600; margin: 0 0 6px; }
.result-msg {
  font-size: 14px;
  color: var(--text-primary, #111827);
  margin: 0 0 4px;
}
.result-hint {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  margin: 0;
}

/* ===== PDF 合并列表 ===== */
.merge-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.merge-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
}
.merge-index {
  font-weight: 700;
  color: var(--primary-color, #4f46e5);
  min-width: 22px;
  flex-shrink: 0;
}
.merge-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--text-primary, #111827);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.merge-size {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  flex-shrink: 0;
  min-width: 70px;
  text-align: right;
}
.merge-range {
  width: 140px;
  padding: 6px 10px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
  color: var(--text-primary, #111827);
  outline: none;
  box-sizing: border-box;
}
.merge-range:focus {
  border-color: var(--primary-color, #4f46e5);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}
.merge-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  color: var(--text-secondary, #6b7280);
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}
.merge-btn:hover:not(:disabled) {
  background: #fff;
  color: var(--primary-color, #4f46e5);
}
.merge-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.merge-btn.danger:hover {
  color: var(--danger-color, #dc2626);
}

/* ===== PDF 解密 ===== */
.warn-banner {
  background: #fffbeb;
  border: 1px solid #fde68a;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  color: #92400e;
}

.crack-panel {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 16px 18px;
}
.crack-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #1e40af;
  margin-bottom: 12px;
}
.crack-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #93c5fd;
  border-top-color: #1e40af;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.crack-progress-bar {
  height: 8px;
  background: #dbeafe;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}
.crack-progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s ease;
}
.crack-stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 6px 16px;
  font-size: 13px;
  color: #1e3a8a;
  margin-bottom: 12px;
}
.crack-stats b { color: #1e40af; font-weight: 600; }
.crack-password {
  font-family: var(--mono, monospace);
  background: #f0fdf4;
  color: #166534;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 14px;
  border: 1px solid #bbf7d0;
}
</style>