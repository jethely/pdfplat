# PDF Tools — 智能 PDF 处理平台

基于 FastAPI + PyMuPDF + OpenCV 构建的一站式 PDF 在线处理工具集，覆盖印章擦除、加解密、水印、压缩、格式转换、页面操作等 30+ 项常用场景。目前只有中文版，稍后增加多语言版。

---

## ⚠️ 重要提示

> **本项目中涉及印章擦除、PDF 加解密、水印移除等操作的代码与功能，仅用于技术研究与验证目的，不得用于任何违法违规用途。使用者须自行承担使用本工具产生的一切后果，作者不承担任何连带责任。**

---

## ✨ 软件特性

- **全栈架构**：后端 FastAPI (Python 3.10+) + 前端 Vue 3 + Vite，部署简单
- **高性能处理**：PyMuPDF 负责 PDF 解析与重组，OpenCV 负责图像级操作，PaddleOCR 负责文字识别
- **算法级印章擦除**：红通道 levels 重建 + 连通域笔画补全，专骑缝章擦除，不破坏章下文字
- **本地运行**：所有处理在本地/私有化服务器完成，不上传云端，文档隐私可控
- **RESTful API**：每个功能都是独立接口，可单独调用或集成到其它系统
- **异步任务**：大文件加密/解密走后台任务队列，支持进度查询与取消

---

## 📋 主要功能列表

| 分类          | 功能                    | 接口路径                                |
| ----------- | --------------------- | ----------------------------------- |
| **印章处理**    | 完整印章擦除（保留骑缝章与章下文字）    | `/api/stamp-operation`              |
|             | 骑缝章擦除                 | `/api/perforated-stamp`             |
| **加解密**     | PDF 加密（密码保护）          | `/api/pdf-encrypt`                  |
|             | PDF 解密（密码移除）          | `/api/pdf-decrypt`                  |
| **水印**      | 添加文字/图片水印             | `/api/pdf-watermark`                |
|             | 智能移除水印                | `/api/remove-watermark`             |
| **文字**      | 文字替换                  | `/api/text-replace`                 |
|             | 文字涂黑（敏感信息擦除）          | `/api/text-redact`                  |
|             | 区域涂黑                  | `/api/pdf-redact-area`              |
|             | PDF 提取文本              | `/api/pdf-to-text`                  |
| **压缩 & 优化** | PDF 压缩（图像降采样 + 内容流精简） | `/api/pdf-compress`                 |
|             | 尺寸统一（多文件页面规格标准化）      | `/api/pdf-unify-size`               |
| **格式转换**    | PDF → Word            | `/api/pdf-to-word`                  |
|             | PDF → Excel           | `/api/pdf-to-excel`                 |
|             | PDF → 图片 / 长图         | `/api/pdf-to-image`                 |
|             | 图片 → PDF              | `/api/image-to-pdf`                 |
| **页面操作**    | 页面删除 / 旋转 / 重排        | `/api/pdf-delete-pages` 等           |
|             | PDF 合并 / 拆分           | `/api/pdf-merge` / `/api/pdf-split` |
|             | 页码添加                  | `/api/pdf-page-number`              |
|             | N-up（多页合一）            | `/api/pdf-nup`                      |
| **其它**      | 书签读写                  | `/api/pdf-bookmark`                 |
|             | 元数据读写                 | `/api/pdf-metadata`                 |
|             | 文档对比                  | `/api/pdf-compare`                  |
|             | 字体检查                  | `/api/font`                         |
|             | 图片提取                  | `/api/extract-images`               |

---

## 🛠️ 安装和部署

### 环境要求

- Python ≥ 3.10
- Node.js ≥ 18（前端构建）
- Ubuntu 22.04 / 24.04 LTS（推荐）

### 快速启动（后端）

```bash
git clone https://github.com/jethely/pdfplat.git
cd pdfplat

# 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 启动后端 (默认端口 8080)
cd backend && uvicorn app_server.main:app --host 0.0.0.0 --port 8080 --reload

```

或使用项目自带的 Makefile：

```bash
make install-backend
make run-backend
```

### 启动前端

```bash
make run-frontendd
或者如下操作：
cd frontend
npm install
npm run dev       # 默认端口 8090
```

### 一键开发模式

```bash
make dev          # 后台同时启动前后端
make stop-dev     # 停止所有服务
```



### 单端口启动，默认8080

```bash
make build-frontend       
make run-backend
浏览器访问：本地：http://127.0.0.1：8080；远程：http://X.X.X.X:8080
```



默认账户

```bash
默认账户：admin
密码：admin123
```



---

## 📬 联系方式

- **邮箱**：secjia@126.com
- 欢迎交流技术问题、提交 Issue 或 Pull Request

---

## 📄 License

本项目仅供学习与研究使用。使用本项目产生的任何直接或间接后果，由使用者自行承担。
