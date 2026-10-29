# app_server/routers/all_router.py
"""统一注册所有子路由。"""
from fastapi import APIRouter

from app_server.routers import (
    auth_router,
    sessions_router,
    pdf_to_image_router,
    image_to_pdf_router,
    pdf_split_router,
    pdf_merge_router,
    pdf_compress_router,
    pdf_encrypt_router,
    pdf_decrypt_router,
    text_replace_router,
    perforated_stamp_router,
    stamp_operation_router,
    text_redact_router,
    pdf_watermark_router,
    pdf_page_number_router,
    pdf_page_ops_router,
    pdf_redact_area_router,
    pdf_to_word_router,
    pdf_compare_router,
    extract_images_router,
    pdf_metadata_router,
    pdf_bookmark_router,
    pdf_reorder_router,
    pdf_to_text_router,
    pdf_to_long_image_router,
    pdf_nup_router,
    pdf_unify_size_router,
    pdf_to_excel_router,
    remove_watermark_router,
    font_router,
)

all_router = APIRouter()

# ==================== 健康检查 ====================
@all_router.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "ok", "message": "PDF Tools API is running"}


# ==================== 业务路由 ====================
all_router.include_router(auth_router.router)
all_router.include_router(sessions_router.router)
all_router.include_router(pdf_to_image_router.router)
all_router.include_router(image_to_pdf_router.router)
all_router.include_router(pdf_split_router.router)
all_router.include_router(pdf_merge_router.router)
all_router.include_router(pdf_compress_router.router)
all_router.include_router(pdf_encrypt_router.router)
all_router.include_router(pdf_decrypt_router.router)
all_router.include_router(text_replace_router.router)
all_router.include_router(perforated_stamp_router.router)
all_router.include_router(stamp_operation_router.router)
all_router.include_router(text_redact_router.router)
all_router.include_router(pdf_watermark_router.router)
all_router.include_router(pdf_page_number_router.router)
all_router.include_router(pdf_page_ops_router.router)
all_router.include_router(pdf_redact_area_router.router)
all_router.include_router(pdf_to_word_router.router)
all_router.include_router(pdf_compare_router.router)
all_router.include_router(extract_images_router.router)
all_router.include_router(pdf_metadata_router.router)
all_router.include_router(pdf_bookmark_router.router)
all_router.include_router(pdf_reorder_router.router)
all_router.include_router(pdf_to_text_router.router)
all_router.include_router(pdf_to_long_image_router.router)
all_router.include_router(pdf_nup_router.router)
all_router.include_router(pdf_unify_size_router.router)
all_router.include_router(pdf_to_excel_router.router)
all_router.include_router(remove_watermark_router.router)
all_router.include_router(font_router.router)