"""普通印章擦除服务（非骑缝章）。

复用 perforated_stamp_service 的红色检测，但不限制在页面右侧边缘，
可检测页面任意位置的圆形/椭圆形红色印章并擦除，支持 pages 参数过滤页码。

擦除算法（v28，红通道重建）：
  红墨几乎不吸收红光，印章处的 R 通道基本保留了纸面真实内容
  （纸白处 R 高、黑字处 R 低），而 G/B 通道被红墨压暗。
  旧版"去红后按灰度分类"在饱和红墨上会把章体判成"黑字"保留，
  且保留分支输出的是去红像素，结果印章反而变黑。
  现在只在红色墨迹像素上用 R 通道重建：
    1. ink   = excess>0 且落在印章区域内的像素（红墨）
    2. paper = 印章外侧一圈干净纸面的 R 中位数（自适应扫描纸色）
    3. 对 R 做 levels 归一：paper→paper，暗部保留（黑字、签字）
    4. 仅按羽化 alpha 把重建结果混合回 ink，黑字与纸底逐像素不动
  这样既不会把印章留下，也不会把黑字洗掉或染黑。

所有以像素为单位的阈值都按 300 DPI 标定，实际使用时按 dpi 等比换算，
因此 dpi 只影响清晰度，不影响检测口径。

已知边界：命中印章的页面整页重渲染为位图（扫描件无影响）；
文字版 PDF 的文字层会被替换，需要保留矢量文字时应改用 redaction 方案。
"""
import re
import time
from pathlib import Path

import cv2
import numpy as np
import pymupdf as fitz

from app_server.core.utils import sanitize_filename

DPI = 300
DPI_MIN = 120

# 以下像素阈值均以 300 DPI 为基准，运行时按 dpi/300 等比缩放
MIN_SEAL_AREA_PX = 15000   # 闭运算后的最小印章面积
SEAL_CLOSE_PX = 30         # 填印章内部缝隙，不跨接外侧碎片
SEAL_DILATE_PX = 40        # 覆盖淡红边缘
EDGE_TOUCH_PX = 60         # 判定"触页边"（骑缝章）的距离
INK_GROW_PX = 5            # 红墨掩膜外扩
PAPER_RING_PX = 21         # 取纸色的外圈宽度
FEATHER_SIGMA = 2.0        # 混合羽化半径

EXCESS_THRESHOLD = 3       # 整页是否有红色内容

# levels 归一参数（相对纸色，无量纲）：R/paper 低于 LO 视为墨，高于 HI 视为纸
# HI 取 0.72 而非更小值，是为了保住被印章压住的浅字笔画（文字修复）。
LEVELS_LO = 0.05
LEVELS_HI = 0.72

# 残影清理：只保留"字芯"附近的内容，远离任何字芯的灰雾一律归为纸。
# 这样既清掉印章残影，又不会像阈值法那样把浅字的笔画削掉。
GHOST_CORE = 0.35          # 灰度低于 纸色*0.35 视为字芯
GHOST_REACH_PT = 1.3       # 距字芯多远之内的像素允许保留（pt）
GHOST_SOFT = 0.94          # 灰度低于 纸色*0.94 才可能是内容

# 分级可达距离：越浅的像素越像残影，允许离字芯越近（对比度越低越严格）
GHOST_REACH_MID = 0.65     # 灰度 0.45–0.65 纸色 的放宽系数
GHOST_REACH_LOW = 0.40     # 灰度 >=0.65 纸色 的放宽系数

# 残影清除的保护线：R 通道几乎不受红墨影响，R 偏暗就说明那里确实有笔画，
# 无论离字芯多远都不能当残影删掉（否则细笔画会被削断）。
GHOST_PROTECT_R = 110
GHOST_PROTECT_MIN_AREA = 8   # 保护簇的最小面积（px），更小的孤立点按噪点处理

# 字重归一：把章下笔画的中位灰度对齐到正文笔画，避免"章下偏灰"的补丁感
WEIGHT_NORMALIZE = True
WEIGHT_GAIN_MAX = 2.2      # 最多加深到多少倍（相对于局部正文）
WEIGHT_GAIN_MIN = 0.75     # 允许轻微提亮，避免处理区比同行邻居更黑

# 断笔修复：印章墨迹完全不透光处，笔画在扫描里已经消失。
# 曾尝试形态学"跨接"补笔画，但印章弧线本身让任意位置都满足"两侧有字"，
# 会把弧线糊成黑块（见 _analysis/_scratch 里的对比），因此改为只做"加深"：
# 把被印章压淡的笔画恢复密度，不新增几何形状，避免凭空造出墨迹。
STROKE_REPAIR = True
STROKE_DARKEN = 0.28       # 笔画加深幅度（纸色比例）
STROKE_BAND_HI = 0.65     # 加深只作用于 0.30–0.65 纸色之间的像素（更浅的视为纸/残影）


def _odd(value, minimum=3):
    v = max(int(value), minimum)
    return v if v % 2 else v + 1


def _px(value, dpi, minimum=3):
    """把 300 DPI 下标定的像素值换算到当前 dpi。"""
    return _odd(round(value * dpi / 300.0), minimum)


def _paper_reference(img_r, area_mask, dpi):
    """用印章外侧一圈干净纸面估计纸色，避免纯白补丁与周围纸张不一致。"""
    ring_k = _px(PAPER_RING_PX, dpi, 9)
    ring = (
        cv2.dilate(area_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ring_k, ring_k))) > 0
    ) & (area_mask == 0)
    if int(ring.sum()) >= 200:
        paper = float(np.median(img_r[ring]))
    elif int((area_mask > 0).sum()) > 0:
        paper = float(np.percentile(img_r[area_mask > 0], 95))
    else:
        paper = 255.0
    return max(paper, 64.0)


def parse_pages_spec(pages_str, total_pages):
    """解析页码表达式，返回 0-indexed 的页码集合。

    支持:
      all / "" / *   → 全部页
      last / first   → 最后一页 / 第一页
      N              → 第 N 页 (1-indexed)
      N-M / N- / -M  → 区间 (包含, 1-indexed；开区间分别表示到末页 / 从首页)
      N,M,K          → 多个页码
    """
    if not pages_str or pages_str.strip().lower() in ('all', '*'):
        return set(range(total_pages))

    result = set()
    parts = re.split(r'[,，\s]+', pages_str.strip())

    for part in parts:
        if not part:
            continue

        low = part.lower()
        if low == 'last':
            result.add(total_pages - 1)
            continue
        if low == 'first':
            result.add(0)
            continue

        m = re.match(r'^(\d+)\s*-\s*(\d+)$', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            a, b = min(a, b), max(a, b)
            result.update(p - 1 for p in range(a, b + 1) if 1 <= p <= total_pages)
            continue

        m = re.match(r'^(\d+)\s*-$', part)
        if m:
            a = int(m.group(1))
            if 1 <= a <= total_pages:
                result.update(range(a - 1, total_pages))
            continue

        m = re.match(r'^-\s*(\d+)$', part)
        if m:
            b = int(m.group(1))
            result.update(p - 1 for p in range(1, min(b, total_pages) + 1))
            continue

        if part.isdigit():
            p = int(part)
            if 1 <= p <= total_pages:
                result.add(p - 1)

    return result


def _page_native_dpi(page, fallback_dpi=DPI):
    """页面内嵌位图的实际分辨率；没有位图（矢量页）时返回 fallback。"""
    best = 0
    for xref_tuple in page.get_images(full=True):
        xref = xref_tuple[0]
        try:
            info = page.parent.extract_image(xref)
            width = info['width']
        except Exception:
            continue
        for rect in page.get_image_rects(xref):
            if rect.width > 1:
                best = max(best, int(round(width / rect.width * 72)))
    return best or fallback_dpi


def _detect_complete_stamps(excess, page_w, page_h, dpi=DPI):
    """通过高阈值分离 + 凸包形状检测，找出页内完整圆形/方形印章。

    原理:
    1. exc>=20 高阈值提取印章核心红色
    2. 闭运算只填印章内部文字缝隙，不连接外侧骑缝章碎片
    3. 连通域分析: 面积达标 + 不触页边缘 + 凸包形状近似圆/方形
    4. 用凸包填充作为印章 mask(无内部空洞) + 膨胀覆盖淡红边缘

    返回: (complete_seal_mask, 印章个数)
    """
    red_core = cv2.threshold(excess, 20, 255, cv2.THRESH_BINARY)[1]
    close_k = _px(SEAL_CLOSE_PX, dpi, 9)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_k, close_k))
    red_closed = cv2.morphologyEx(red_core, cv2.MORPH_CLOSE, kernel)

    num_cc, labels, stats, _ = cv2.connectedComponentsWithStats(red_closed, 8)
    complete_mask = np.zeros((page_h, page_w), dtype=np.uint8)

    min_area = int(round(MIN_SEAL_AREA_PX * (dpi / 300.0) ** 2))
    edge_px = int(round(EDGE_TOUCH_PX * dpi / 300.0))
    found = 0

    for i in range(1, num_cc):
        if stats[i, cv2.CC_STAT_AREA] < min_area:
            continue

        left = stats[i, cv2.CC_STAT_LEFT]
        top = stats[i, cv2.CC_STAT_TOP]
        right = left + stats[i, cv2.CC_STAT_WIDTH]
        bottom = top + stats[i, cv2.CC_STAT_HEIGHT]
        if left < edge_px or top < edge_px or right > page_w - edge_px or bottom > page_h - edge_px:
            continue

        cc_mask = (labels == i).astype(np.uint8)
        contours, _ = cv2.findContours(cc_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) != 1:
            continue
        cnt = contours[0]
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        hull_perim = cv2.arcLength(hull, True)
        if hull_perim == 0 or hull_area == 0:
            continue
        hull_circ = 4 * np.pi * hull_area / (hull_perim ** 2)
        _, _, hull_bw, hull_bh = cv2.boundingRect(hull)
        hull_aspect = hull_bw / hull_bh if hull_bh > 0 else 0
        hull_rect_fill = hull_area / (hull_bw * hull_bh) if hull_bw * hull_bh > 0 else 0

        is_round = hull_circ > 0.65 and 0.75 < hull_aspect < 1.35
        is_square = hull_rect_fill > 0.8 and 0.65 < hull_aspect < 1.6

        if is_round or is_square:
            hull_mask = np.zeros((page_h, page_w), dtype=np.uint8)
            cv2.fillPoly(hull_mask, [hull], 255)
            complete_mask = cv2.bitwise_or(complete_mask, hull_mask)
            found += 1

    if found:
        dilate_k = _px(SEAL_DILATE_PX, dpi, 9)
        seal_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_k, dilate_k))
        complete_mask = cv2.dilate(complete_mask, seal_k, iterations=1)

    return complete_mask, found


def _suppress_ghost(gray, area, paper, dpi, r_channel=None):
    """清掉印章残影，同时保住被印章压住的浅字笔画。

    文字笔画一定有很暗的"字芯"（灰度 < 0.35*纸色），而印章残影只是灰雾。
    因此以字芯为锚点做距离变换：距最近字芯超过可达距离的浅灰像素一律归为纸。
    另外 R 通道暗于 GHOST_PROTECT_R 的像素有确定的文字证据，绝不当残影删除。
    """
    core = ((gray < GHOST_CORE * paper) & area).astype(np.uint8) * 255
    if cv2.countNonZero(core) == 0:
        # 章区里没有任何文字，整片都是残影
        out = gray.copy()
        out[area] = int(paper)
        return out, np.full(gray.shape, 1e6, np.float32)

    dist = cv2.distanceTransform(255 - core, cv2.DIST_L2, 5)
    reach = max(2.0, GHOST_REACH_PT * dpi / 72.0)

    # 分级：笔画芯部给足余量，越浅的像素越可能是残影，收紧可达距离
    level = gray.astype(np.float32) / paper
    allow = np.full(gray.shape, reach, np.float32)
    allow[(level >= 0.45) & (level < 0.65)] = reach * GHOST_REACH_MID
    allow[level >= 0.65] = reach * GHOST_REACH_LOW

    ghost = area & (gray < GHOST_SOFT * paper) & (dist > allow)
    if r_channel is not None:
        # R 通道暗 = 确实有文字；这类像素即使在远处也不当残影删。
        # 但 1–2 像素的孤立噪点不享受保护，否则会留下黑点（细笔画至少 3px，不受影响）。
        protect = ((r_channel < GHOST_PROTECT_R) & area).astype(np.uint8)
        ncc, lab, stats, _ = cv2.connectedComponentsWithStats(protect, 8)
        keep = np.zeros(protect.shape, np.uint8)
        for i in range(1, ncc):
            # 只保护成形的笔画碎片；1–7px 的孤立点多为扫描噪点，留着会变成"黑点"
            if int(stats[i, cv2.CC_STAT_AREA]) >= GHOST_PROTECT_MIN_AREA:
                keep[lab == i] = 1
        ghost &= keep == 0
    if ghost.any():
        gray[ghost] = int(paper)
    return gray, dist


def _restore_stroke_contrast(gray, area, paper, dpi, dist, ref_rows=None):
    """把被印章压淡的笔画恢复密度（只加深，不新增几何），并归一整体字重。

    印章半透明处，笔画信号还在、只是变浅，视觉上就像"断了"。
    1) 距字芯近的浅笔画按距离加权减量，恢复笔画密度；
    2) 再以本页正文笔画的中位灰度为准做一次线性归一（锚点=纸色），
       让章下文字与页面上其它文字黑度一致，避免"补丁感"。
    """
    if not STROKE_REPAIR:
        return gray
    reach = max(2.0, GHOST_REACH_PT * dpi / 72.0)
    band = area & (dist <= reach) & (gray > 0.30 * paper) & (gray < STROKE_BAND_HI * paper)
    if band.any():
        w = 1.0 - np.clip(dist[band] / reach, 0.0, 1.0)
        values = gray[band].astype(np.float32) - STROKE_DARKEN * paper * w
        gray[band] = np.clip(values, 0, 255).astype(np.uint8)

    if WEIGHT_NORMALIZE:
        # 逐字归一：印章墨密度在章内分布不均（中心最密），全页一个 gain 会让
        # 中心区域的字偏浅。这里对每个连通字单独计算 gain，使每个字都对齐正文。
        text_mask = (area & (gray < 0.55 * paper)).astype(np.uint8)
        if cv2.countNonZero(text_mask):
            ncc, lab, stats, _ = cv2.connectedComponentsWithStats(text_mask, 8)
            fallback = 0.0
            if ref_rows is not None and np.isfinite(ref_rows).any():
                fallback = float(np.nanmedian(ref_rows))
            for i in range(1, ncc):
                if int(stats[i, cv2.CC_STAT_AREA]) < 40:
                    continue
                comp = lab == i
                ref_gray = fallback
                if ref_rows is not None:
                    cy = int(stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2)
                    v = ref_rows[min(max(cy, 0), len(ref_rows) - 1)]
                    if np.isfinite(v):
                        ref_gray = float(v)
                cur = float(np.median(gray[comp]))
                gain = (paper - ref_gray) / max(paper - cur, 1.0)
                gain = float(np.clip(gain, WEIGHT_GAIN_MIN, WEIGHT_GAIN_MAX))
                if abs(gain - 1.0) > 0.02:
                    values = paper - (paper - gray[comp].astype(np.float32)) * gain
                    gray[comp] = np.clip(values, 0, 255).astype(np.uint8)
    return gray


def _remove_isolated_dots(gray, area, paper, dpi):
    """清掉孤立小黑点：面积很小、且周围没有其它墨迹的暗色连通域。

    笔画碎片总与其它笔画相邻，而扫描噪点/残墨是孤立的。
    标点（。、，）面积远大于阈值，不受影响。
    """
    dark = ((gray < 0.55 * paper) & area).astype(np.uint8)
    if cv2.countNonZero(dark) == 0:
        return gray

    ncc, lab, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    max_area = max(6, int(round(6 * (dpi / 300.0) ** 2)))
    out = gray.copy()
    for i in range(1, ncc):
        area_i = int(stats[i, cv2.CC_STAT_AREA])
        if area_i > max_area:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        pad = 3
        y0, y1 = max(y - pad, 0), min(y + h + pad, gray.shape[0])
        x0, x1 = max(x - pad, 0), min(x + w + pad, gray.shape[1])
        win = dark[y0:y1, x0:x1]
        if int(win.sum()) == area_i:      # 窗口里只有它自己 → 孤立点
            out[lab == i] = int(paper)
    return out


def _row_text_reference(page_gray, area, half=14, min_samples=30):
    """逐行估计"该行未处理文字"的中位灰度，返回按行索引的参考值数组。

    同一页不同区域（正文 / 签署区）印刷浓淡可能差一倍。用全页或整带的中位数
    会把处理区压得比同行邻居更黑，产生"补丁感"；因此按行取局部基准。
    取不到样本的行返回 nan，由调用方回退。
    """
    h = page_gray.shape[0]
    text = (~area) & (page_gray < 120)
    ref = np.full(h, np.nan, np.float32)

    rows = np.where(area.any(axis=1))[0]
    scan_rows = range(max(0, int(rows.min()) - 40), min(h, int(rows.max()) + 41)) if rows.size else range(h)
    for y in scan_rows:
        y0, y1 = max(0, y - half), min(h, y + half + 1)
        vals = page_gray[y0:y1][text[y0:y1]]
        if vals.size >= min_samples:
            ref[y] = float(np.median(vals))
    return ref


def _erase_seal_ink(img_bgr, area_mask, excess, dpi=DPI):
    """红通道重建擦除印章（v28）。

    只在 excess>0 的红墨像素上操作：
      - R 通道近似底层纸面（纸白高、黑字低），用它替换被红墨污染的像素；
      - 白点取自印章外侧纸色，避免输出亮于周围纸张的补丁；
      - 黑字、签字等非红像素逐像素保持原样，不会被洗白或染黑。
    """
    area = area_mask > 0
    if not area.any():
        return img_bgr

    R = img_bgr[:, :, 2].astype(np.float32)
    paper = _paper_reference(R, area_mask, dpi)

    ink = ((excess >= 1) & area).astype(np.uint8) * 255
    if cv2.countNonZero(ink) == 0:
        return img_bgr
    grow_k = _px(INK_GROW_PX, dpi)
    ink = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow_k, grow_k)))

    norm = np.clip((R / paper - LEVELS_LO) / (LEVELS_HI - LEVELS_LO), 0.0, 1.0)
    gray = np.clip(norm * paper, 0, 255).astype(np.uint8)
    gray = cv2.medianBlur(gray, 3)
    gray, dist = _suppress_ghost(gray, area, paper, dpi, R)

    page_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    ref_rows = _row_text_reference(page_gray, area)
    gray = _restore_stroke_contrast(gray, area, paper, dpi, dist, ref_rows)
    gray = _remove_isolated_dots(gray, area, paper, dpi)

    alpha = cv2.GaussianBlur(
        ink.astype(np.float32) / 255.0, (0, 0), max(FEATHER_SIGMA * dpi / 300.0, 1.0)
    )[:, :, None]
    # 红像素必须 100% 替换：羽化在描边外沿只到 0.8，会留下淡淡的粉色描边
    alpha = np.maximum(alpha, ((excess >= 1) & area).astype(np.float32)[:, :, None])
    gray3 = cv2.merge([gray, gray, gray]).astype(np.float32)
    blended = img_bgr.astype(np.float32) * (1.0 - alpha) + gray3 * alpha
    return np.clip(blended, 0, 255).astype(np.uint8)


def erase_seals_on_doc(doc, page_indices, dpi=DPI):
    """逐页擦除印章，返回 (输出文档, 印章数, 实际改动页数)。

    未命中印章的页直接 insert_pdf 复制，保留原有链接与注释。
    """
    out_doc = fitz.open()
    page_set = set(page_indices)
    modified = 0
    total_erased = 0

    for page_idx in range(doc.page_count):
        src_page = doc[page_idx]

        if page_idx not in page_set:
            out_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            continue

        rect = src_page.rect
        page_dpi = min(int(dpi), max(_page_native_dpi(src_page), DPI_MIN))
        pix = src_page.get_pixmap(matrix=fitz.Matrix(page_dpi / 72, page_dpi / 72))
        img_bgr = cv2.cvtColor(
            np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n),
            cv2.COLOR_RGB2BGR,
        )

        B, G, R = cv2.split(img_bgr)
        excess = np.clip(
            R.astype(np.int16) - np.maximum(G, B).astype(np.int16), 0, 255
        ).astype(np.uint8)

        if cv2.countNonZero(cv2.threshold(excess, EXCESS_THRESHOLD, 255, cv2.THRESH_BINARY)[1]) == 0:
            out_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            continue

        page_h, page_w = img_bgr.shape[:2]
        seal_mask, seal_count = _detect_complete_stamps(excess, page_w, page_h, page_dpi)

        if seal_count == 0:
            out_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            continue

        erased = _erase_seal_ink(img_bgr, seal_mask, excess, page_dpi)

        ok, buf = cv2.imencode('.png', erased, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        if not ok:
            raise RuntimeError(f"第 {page_idx + 1} 页图像编码失败")

        new_page = out_doc.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(new_page.rect, stream=buf.tobytes())

        modified += 1
        total_erased += seal_count
        print(f"  页{page_idx + 1}: 擦除 {seal_count} 个印章 (光栅 @ {page_dpi} DPI)")

    return out_doc, total_erased, modified


def dispatch_stamp_erase(
    pdf_bytes: bytes,
    output_dir: Path,
    safe_name: str,
    pages: str = "all",
    dpi: int = DPI,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        total_pages = doc.page_count
        if total_pages == 0:
            raise ValueError("PDF 没有页面")

        page_set = parse_pages_spec(pages, total_pages)
        if not page_set:
            raise ValueError(f"无效的页码范围: {pages}")

        sorted_pages = sorted(page_set)
        print(f"\n印章擦除: 总共 {total_pages} 页, 目标 {len(sorted_pages)} 页: {[p + 1 for p in sorted_pages]}")

        out_doc, num_erased, modified = erase_seals_on_doc(doc, sorted_pages, dpi=dpi)
        try:
            out_doc.set_metadata(doc.metadata or {})
            base = sanitize_filename(Path(safe_name).stem, default="output")
            ts = time.strftime("%Y%m%d_%H%M%S")
            out_name = f"{base}_stamp_erased_{ts}.pdf"
            target = output_dir / out_name
            suffix = 1
            while target.exists():
                out_name = f"{base}_stamp_erased_{ts}_{suffix}.pdf"
                target = output_dir / out_name
                suffix += 1
            out_doc.save(str(target), garbage=4, deflate=True)
        finally:
            out_doc.close()
    finally:
        doc.close()

    return {
        "out_name": out_name,
        "pages_affected": modified,
        "pages_requested": len(sorted_pages),
        "stamps_erased": num_erased,
        "action": "erase",
        "action_label": "印章擦除",
    }
