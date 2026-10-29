# app_server/services/pdf_common.py
"""PDF 处理共用：格式映射、类型检测等。

注意：
- 这里只放纯逻辑，不依赖 FastAPI
- 路由层负责参数校验和 HTTPException
"""
import fitz


# ==================== 图片格式映射 ====================
# 值：(PyMuPDF tobytes 参数, 文件扩展名, MIME)
IMAGE_FORMAT_MAP = {
    "png":  ("png",  "png",  "image/png"),
    "jpeg": ("jpg",  "jpg",  "image/jpeg"),
    "jpg":  ("jpg",  "jpg",  "image/jpeg"),
    "webp": ("webp", "webp", "image/webp"),
    "bmp":  ("bmp",  "bmp",  "image/bmp"),
    "tiff": ("tiff", "tiff", "image/tiff"),
}

# 图片转 PDF 时允许的扩展名（复用 IMAGE_FORMAT_MAP + .tif / .gif）
ALLOWED_IMAGE_EXTS = {f".{k}" for k in IMAGE_FORMAT_MAP} | {".tif", ".gif"}


# ==================== PDF 类型检测 ====================
def detect_pdf_type(doc: fitz.Document) -> str:
    """判断 PDF 类型：
    - "text"    ：文本型（Word / 打印 / 电子书）
    - "image"   ：纯图片型（扫描件 / 拍照）
    - "mixed"   ：混合型（部分页有文字、部分页是图）
    - "unknown" ：无法判定（空文档 / 全部页异常）
    """
    total = doc.page_count
    sample = min(total, 10)
    text_pages = 0
    image_only_pages = 0
    valid_pages = 0

    for i in range(sample):
        try:
            page = doc.load_page(i)
            text = page.get_text("text").strip()
            images = page.get_images()
            has_text = len(text) > 20
            has_images = len(images) > 0
            valid_pages += 1

            if has_text:
                text_pages += 1
            elif has_images:
                image_only_pages += 1
        except Exception:
            continue

    if valid_pages == 0:
        return "unknown"
    if text_pages == 0 and image_only_pages > 0:
        return "image"
    if text_pages > 0 and image_only_pages > 0:
        return "mixed"
    if text_pages > 0:
        return "text"
    return "unknown"