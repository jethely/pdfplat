"""骑缝章擦除 / 替换服务。

action:
    erase   — 仅擦除 PDF 右侧的旧骑缝章（白色覆盖）
    replace — 擦除旧骑缝章，贴入新骑缝章切片（需要 stamp_file）
"""
import io
import time
from pathlib import Path

import cv2
import numpy as np
import pymupdf as fitz

from app_server.core.utils import sanitize_filename

DPI = 200
W_LO, W_HI = 5, 250


# ==================== 图像处理核心 ====================
def extract_red_mask(img_bgr):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0, 40, 40]), np.array([12, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([160, 40, 40]), np.array([180, 255, 255]))
    red_hsv = cv2.bitwise_or(m1, m2)

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    _, a_channel, _ = cv2.split(lab)
    _, red_lab = cv2.threshold(a_channel, 138, 255, cv2.THRESH_BINARY)

    return cv2.bitwise_or(red_hsv, red_lab)


def locate_all_seals_on_page(img, mask):
    h, w = mask.shape
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
    if num_labels <= 1:
        return []

    valid_components = []
    right_edge_threshold = w - 220

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        top = stats[i, cv2.CC_STAT_TOP]
        left = stats[i, cv2.CC_STAT_LEFT]
        width = stats[i, cv2.CC_STAT_WIDTH]
        height = stats[i, cv2.CC_STAT_HEIGHT]
        right = left + width

        if area < 80 or right < right_edge_threshold or width > W_HI:
            continue

        cy = top + height / 2.0
        valid_components.append({
            'idx': i, 'top': top, 'bottom': top + height,
            'left': left, 'right': right, 'width': width,
            'height': height, 'area': area, 'cy': cy,
        })

    if not valid_components:
        return []

    valid_components.sort(key=lambda c: c['cy'])
    clusters = []
    for comp in valid_components:
        if not clusters:
            clusters.append([comp])
        else:
            cluster_mean_cy = np.mean([c['cy'] for c in clusters[-1]])
            if abs(comp['cy'] - cluster_mean_cy) < 180:
                clusters[-1].append(comp)
            else:
                clusters.append([comp])

    results = []
    for cluster in clusters:
        cys = [c['cy'] for c in cluster]
        lefts = [c['left'] for c in cluster]
        rights = [c['right'] for c in cluster]
        tops = [c['top'] for c in cluster]
        bottoms = [c['bottom'] for c in cluster]

        results.append({
            'abs_top': min(tops),
            'abs_bottom': max(bottoms),
            'left_x': min(lefts),
            'right_x': max(rights),
            'cy': float(np.median(cys)),
        })

    return results


def get_seal_diameter(paginated_images, paginated_masks):
    best_d = 0
    best_reason = "fallback"

    for img_bgr, mask in zip(paginated_images, paginated_masks):
        h, w = mask.shape
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            top = stats[i, cv2.CC_STAT_TOP]
            left = stats[i, cv2.CC_STAT_LEFT]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]
            right = left + width

            if area > 5000 and 0.5 < width / max(height, 1) < 2.0:
                if right < w - 10:
                    d = max(width, height)
                    if d > best_d:
                        best_d = d
                        best_reason = f"完整圆章(W={width},H={height},area={area})"

    if best_d > 0:
        return best_d, best_reason

    max_h = 0
    for mask in paginated_masks:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        for i in range(1, num_labels):
            h = stats[i, cv2.CC_STAT_HEIGHT]
            if h > max_h:
                max_h = h

    return max_h if max_h > 0 else 340, f"骑缝章最大高度 fallback H={max_h}"


def get_square_seal_bgra(seal_bytes, target_diameter, dpi=200):
    doc = fitz.open(stream=seal_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, colorspace="rgb")
    seal_bgr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    seal_bgr = cv2.cvtColor(seal_bgr, cv2.COLOR_RGB2BGR)
    doc.close()

    red_mask = extract_red_mask(seal_bgr)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    closed = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(closed)

    if num <= 1:
        h, w = seal_bgr.shape[:2]
        side = min(h, w)
        return cv2.resize(seal_bgr, (target_diameter, target_diameter))

    areas = stats[1:, cv2.CC_STAT_AREA]
    largest_idx = np.argmax(areas) + 1

    seal_region_mask = np.zeros_like(red_mask)
    seal_region_mask[labels == largest_idx] = 255

    final_mask = cv2.bitwise_and(red_mask, seal_region_mask)

    pts = np.argwhere(final_mask > 0)
    if len(pts) == 0:
        h, w = seal_bgr.shape[:2]
        side = min(h, w)
        return cv2.resize(seal_bgr, (target_diameter, target_diameter))

    y1, x1 = np.min(pts, axis=0)
    y2, x2 = np.max(pts, axis=0)

    cropped_bgr = seal_bgr[y1:y2 + 1, x1:x2 + 1]
    cropped_mask = final_mask[y1:y2 + 1, x1:x2 + 1]

    h, w = cropped_bgr.shape[:2]
    max_side = max(h, w)
    square = np.zeros((max_side, max_side, 4), dtype=np.uint8)
    oy = (max_side - h) // 2
    ox = (max_side - w) // 2
    square[oy:oy + h, ox:ox + w, :3] = cropped_bgr
    square[oy:oy + h, ox:ox + w, 3] = cropped_mask

    return cv2.resize(square, (target_diameter, target_diameter), interpolation=cv2.INTER_AREA)


def px_rect_to_pt(px_x0, px_x1, px_y0, px_y1, pt_height, dpi):
    scale = 72.0 / dpi
    return fitz.Rect(px_x0 * scale, px_y0 * scale, px_x1 * scale, px_y1 * scale)


def make_seal_slice_png(seal_rgba, slice_x0, slice_x1,
                        orig_top, orig_bottom, orig_cy, D):
    slice_x0 = max(0, int(round(slice_x0)))
    slice_x1 = min(D, int(round(slice_x1)))
    if slice_x1 <= slice_x0:
        return None

    seal_y1 = int(round(orig_top - orig_cy + D / 2.0))
    seal_y2 = int(round(orig_bottom - orig_cy + D / 2.0))
    seal_y1 = max(0, seal_y1)
    seal_y2 = min(D, seal_y2)
    if seal_y2 <= seal_y1:
        return None

    final = seal_rgba[seal_y1:seal_y2, slice_x0:slice_x1]
    if final.shape[0] == 0 or final.shape[1] == 0:
        return None

    _, buf = cv2.imencode('.png', final, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    return buf.tobytes()


# ==================== 上下文准备 ====================
def _prepare_context(pdf_bytes, stamp_bytes=None, dpi=DPI):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = doc.page_count
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    page_images = []
    page_masks = []
    page_seal_list = []
    page_pt_sizes = []

    for i in range(total_pages):
        page = doc[i]
        pw_pt, ph_pt = page.rect.width, page.rect.height
        page_pt_sizes.append((pw_pt, ph_pt))

        pix = page.get_pixmap(matrix=mat)
        img_bgr = cv2.imdecode(np.frombuffer(pix.tobytes(), np.uint8), cv2.IMREAD_COLOR)
        page_images.append(img_bgr)

        mask = extract_red_mask(img_bgr)
        page_masks.append(mask)

        seals = locate_all_seals_on_page(img_bgr, mask)
        page_seal_list.append(seals)

    valid_page_indices = [i for i in range(total_pages) if len(page_seal_list[i]) > 0]
    total_seals = sum(len(page_seal_list[i]) for i in valid_page_indices)

    if not valid_page_indices:
        doc.close()
        return None

    D, d_reason = get_seal_diameter(page_images, page_masks)

    seal_rgba = None
    if stamp_bytes is not None:
        seal_rgba = get_square_seal_bgra(stamp_bytes, target_diameter=D, dpi=dpi)

    return {
        'doc': doc,
        'total_pages': total_pages,
        'page_images': page_images,
        'page_masks': page_masks,
        'page_seal_list': page_seal_list,
        'page_pt_sizes': page_pt_sizes,
        'valid_page_indices': valid_page_indices,
        'total_seals': total_seals,
        'D': D,
        'd_reason': d_reason,
        'seal_rgba': seal_rgba,
    }


# ==================== Phase 1: 擦除 ====================
def erase_old_seals(doc, ctx, dpi):
    pad = 30

    for page_idx in ctx['valid_page_indices']:
        page = doc[page_idx]
        ph_pt = ctx['page_pt_sizes'][page_idx][1]
        img_h, img_w_cur = ctx['page_images'][page_idx].shape[:2]
        seals = ctx['page_seal_list'][page_idx]

        if not seals:
            continue

        red_mask = ctx['page_masks'][page_idx]

        for ci, s in enumerate(seals):
            scan_l = max(0, s['left_x'] - 200)
            scan_r = min(img_w_cur, s['right_x'] + 200)
            scan_t = max(0, s['abs_top'] - 200)
            scan_b = min(img_h, s['abs_bottom'] + 200)

            region = red_mask[scan_t:scan_b, scan_l:scan_r]
            red_pts = np.argwhere(region > 0)

            if len(red_pts) == 0:
                left_px = max(0, s['left_x'] - pad)
                right_px = min(img_w_cur, s['right_x'] + pad)
                top_px = max(0, s['abs_top'] - pad)
                bot_px = min(img_h, s['abs_bottom'] + pad)
            else:
                actual_t = scan_t + red_pts[:, 0].min()
                actual_b = scan_t + red_pts[:, 0].max()
                actual_l = scan_l + red_pts[:, 1].min()
                actual_r = scan_l + red_pts[:, 1].max()

                left_px = max(0, actual_l - pad)
                right_px = min(img_w_cur, actual_r + pad)
                top_px = max(0, actual_t - pad)
                bot_px = min(img_h, actual_b + pad)

            bw, bh = right_px - left_px, bot_px - top_px
            if bw <= 0 or bh <= 0:
                continue

            white = np.ones((bh, bw, 3), dtype=np.uint8) * 255
            _, buf = cv2.imencode('.png', white, [cv2.IMWRITE_PNG_COMPRESSION, 9])

            rect = px_rect_to_pt(left_px, right_px, top_px, bot_px, ph_pt, dpi)
            page.insert_image(rect, stream=buf.tobytes())


# ---------------------------------------------------------------------------
# [暂不删除] Phase 2: 贴新骑缝章 (action="replace")
# ---------------------------------------------------------------------------
# 前端 PerforatedStamp.vue 已移除「替换骑缝章」选项，仅保留「擦除骑缝章」。
# 后端 action="replace" 分支的完整实现保留在此，未来如需恢复可直接启用。
#
# 实现原理：
#   骑缝章是同一枚完整圆章（直径 D）盖在合同接缝处，纸内只看到左半部分
#   （宽 R = D/2）。多页纸摞在一起盖章后翻开，每页拿到的是左半部分从左
#   到右的不同水平段。
#   因此：按 cy 把簇聚成组 → 组内按页码排序 → 累计宽度计算 seal_x 偏移，
#   第一页拿印章最左侧段 [0, w1]，第二页拿 [w1, w1+w2]，依此类推。
# ---------------------------------------------------------------------------
def _assign_seal_x_offsets(page_seal_list, total_pages):
    all_clusters = []
    for pi in range(total_pages):
        for si, s in enumerate(page_seal_list[pi]):
            all_clusters.append({
                'page': pi,
                'cy': s['cy'],
                'width': s['right_x'] - s['left_x'] + 1,
                '_ref': (pi, si),
            })

    all_clusters.sort(key=lambda c: c['cy'])
    groups = []
    for c in all_clusters:
        if not groups:
            groups.append([c])
        else:
            g_mean = np.mean([x['cy'] for x in groups[-1]])
            if abs(c['cy'] - g_mean) < 120:
                groups[-1].append(c)
            else:
                groups.append([c])

    for g in groups:
        g_sorted = sorted(g, key=lambda x: x['page'])
        cumul = 0
        for c in g_sorted:
            pi, si = c['_ref']
            w = c['width']
            page_seal_list[pi][si]['seal_x0'] = cumul
            page_seal_list[pi][si]['seal_x1'] = cumul + w
            cumul += w

    return len(groups)


# ==================== Phase 2: 贴新章 ====================
def apply_new_seals(doc, ctx, dpi):
    D = ctx['D']
    seal_rgba = ctx['seal_rgba']

    if seal_rgba is None:
        return

    _assign_seal_x_offsets(ctx['page_seal_list'], ctx['total_pages'])

    for page_idx in ctx['valid_page_indices']:
        page = doc[page_idx]
        ph_pt = ctx['page_pt_sizes'][page_idx][1]
        img_h, img_w_cur = ctx['page_images'][page_idx].shape[:2]

        for ci, seal in enumerate(ctx['page_seal_list'][page_idx]):
            left_x = seal['left_x']
            cy = seal['cy']

            W_slice = min(img_w_cur - left_x, D)
            if W_slice <= 0:
                continue

            sx0 = seal.get('seal_x0', 0)
            sx1 = seal.get('seal_x1', W_slice)
            sx0 = max(0, int(round(sx0)))
            sx1 = min(D, int(round(sx1)))
            if sx1 <= sx0:
                sx0, sx1 = 0, W_slice

            png_bytes = make_seal_slice_png(
                seal_rgba, sx0, sx1,
                seal['abs_top'], seal['abs_bottom'], cy, D,
            )
            if png_bytes is None:
                continue

            rect = px_rect_to_pt(
                left_x, left_x + W_slice,
                seal['abs_top'], seal['abs_bottom'],
                ph_pt, dpi,
            )
            page.insert_image(rect, stream=png_bytes)


# ==================== 分发入口 ====================
def dispatch_perforated_stamp(
    pdf_bytes: bytes,
    output_dir: Path,
    safe_name: str,
    action: str = "erase",
    stamp_bytes: bytes | None = None,
    dpi: int = DPI,
) -> dict:
    if action not in ("erase", "replace"):
        raise ValueError(f"不支持的操作: {action}")

    if action == "replace" and stamp_bytes is None:
        raise ValueError("替换骑缝章需要上传新印章文件")

    ctx = _prepare_context(pdf_bytes, stamp_bytes=stamp_bytes if action == "replace" else None, dpi=dpi)
    if ctx is None:
        raise ValueError("未检测到骑缝章痕迹")

    doc = ctx['doc']
    pages_affected = len(ctx['valid_page_indices'])
    total_seals = ctx['total_seals']

    try:
        erase_old_seals(doc, ctx, dpi)

        if action == "replace":
            apply_new_seals(doc, ctx, dpi)

        base = sanitize_filename(Path(safe_name).stem, default="output")
        ts = time.strftime("%Y%m%d_%H%M%S")
        suffix = "erase" if action == "erase" else "replaced"
        out_name = f"{base}_seal_{suffix}_{ts}.pdf"
        doc.save(str(output_dir / out_name), garbage=4, deflate=True)
    finally:
        doc.close()

    action_label = "擦除骑缝章" if action == "erase" else "替换骑缝章"
    return {
        "out_name": out_name,
        "pages_affected": pages_affected,
        "seal_clusters": total_seals,
        "action": action,
        "action_label": action_label,
    }
