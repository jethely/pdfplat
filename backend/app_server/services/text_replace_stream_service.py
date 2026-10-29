"""
content stream 直改 — v22.0 FINAL (2026-10-22)
迁移自 backend/tests/stream_replace.py，核心算法一行不动。
"""
import os, re, io, glob as _glob, time as _time
from pathlib import Path
from typing import Optional, Dict, List

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf
from fontTools.ttLib import TTFont, TTCollection


def _find_font_path():
    _CAND = [
        os.path.join(os.environ.get("WINDIR", r"C:\\Windows"), "Fonts", "simsun.ttc"),
        os.path.join(os.path.dirname(__file__), "..", "storage", "fonts", "simsun.ttc"),
        "/mount/nvme0/pdfplat/backend/storage/fonts/simsun.ttc",
    ]
    _CAND += _glob.glob(
        os.path.join(os.path.dirname(__file__), "..", "**", "simsun.ttc"),
        recursive=True,
    )
    for _p in _CAND:
        if os.path.exists(_p):
            return os.path.abspath(_p)
    return None


def replace_text_stream(
    pdf_path,
    target_str: str,
    new_str: str,
    output_dir,
    safe_name: str = "output.pdf",
    target_pages: Optional[list] = None,
) -> dict:
    print(f"\n{'='*60}")
    print(f"[DEBUG] replace_text_stream v22.0 被调用! target={target_str!r} new={new_str!r}")
    print(f"[DEBUG] doc.save 在循环外 (已修复), REPLS 每页重置")
    print(f"{'='*60}\n")
    SIMSUN_PATH = _find_font_path()
    if not SIMSUN_PATH:
        raise FileNotFoundError(
            "simsun.ttc 未找到，请检查 backend/storage/fonts/simsun.ttc 是否存在"
        )

    OLD_STR = target_str
    NEW_STR = new_str

    OUT_NAME = f"{Path(safe_name).stem}_{int(_time.time())}.pdf"
    out_path = Path(output_dir) / OUT_NAME

    doc = pymupdf.open(str(pdf_path))
    total_pages = doc.page_count
    if target_pages is None:
        target_pages = list(range(total_pages))

    replaced_count = 0
    skipped_pages = []
    page_details = {}
    font_matched = 0
    font_fallback = 0
    bold_count = 0
    underline_count = 0

    for page_num in target_pages:
        try:
            page = doc[page_num]
            PAGE_H = page.rect.height
            PAGE_W = page.rect.width
            right_edge = PAGE_W - 10.0
            print(f"页面尺寸: {PAGE_W:.1f} x {PAGE_H:.1f}, 初始 right_edge={right_edge:.2f}")

            # ========== 扫描 PDF 字体对象，建立 font_id → DW 映射 ==========
            _font_dw_map = {}
            _font_w_map = {}

            def _parse_cidfont_w(cidfont_obj):
                dw = 1000
                dw_m = re.search(r'/DW\s+(\d+)', cidfont_obj)
                if dw_m:
                    dw = int(dw_m.group(1))
                widths = {}
                w_m = re.search(r'/W\s*\[(.*?)\]', cidfont_obj, re.DOTALL)
                if w_m:
                    tokens = w_m.group(1).split()
                    i = 0
                    while i < len(tokens):
                        try:
                            start_cid = int(tokens[i])
                        except:
                            i += 1; continue
                        i += 1
                        if i < len(tokens) and tokens[i] == '[':
                            i += 1
                            cur_cid = start_cid
                            while i < len(tokens) and tokens[i] != ']':
                                try: widths[cur_cid] = int(tokens[i]); cur_cid += 1
                                except: pass
                                i += 1
                            if i < len(tokens) and tokens[i] == ']': i += 1
                        else:
                            try:
                                end_cid = int(tokens[i]); i += 1
                                w = int(tokens[i]); i += 1
                                for c in range(start_cid, end_cid + 1): widths[c] = w
                            except: pass
                return dw, widths

            try:
                for _font_info in page.get_fonts(full=True):
                    _type0_xref = _font_info[0]
                    _fid = _font_info[4]
                    try:
                        _type0_obj = doc.xref_object(_type0_xref)
                    except: continue
                    if not _type0_obj: continue
                    _desc_m = re.search(r'/DescendantFonts\s*\[([^\]]+)\]', _type0_obj)
                    if not _desc_m: continue
                    _cidfont_refs = re.findall(r'(\d+)\s+\d+\s+R', _desc_m.group(1))
                    for _cr in _cidfont_refs:
                        try:
                            _cid_obj = doc.xref_object(int(_cr))
                        except: continue
                        if not _cid_obj: continue
                        _dw, _widths = _parse_cidfont_w(_cid_obj)
                        _font_dw_map[_fid] = _dw
                        _font_w_map[_fid] = _widths
                        print(f"  PDF字体 {_fid}: DW={_dw}, W entries={len(_widths)}")
            except Exception as _e:
                print(f"  [字体扫描警告] {_e}")

            print(f"字体扫描完成: {len(_font_dw_map)} 个字体有 DW 信息")

            def _cidfont_w_glyph_units(cid_val, font_id):
                if font_id in _font_w_map:
                    w = _font_w_map[font_id].get(cid_val)
                    if w is not None:
                        return w
                if font_id in _font_dw_map:
                    return _font_dw_map[font_id]
                return 1000

            # ========== 加载字体度量 ==========
            font = TTFont(SIMSUN_PATH, fontNumber=0)
            UPM = font['head'].unitsPerEm
            _glyph_order = font.getGlyphOrder()
            _hmtx = font['hmtx']

            def cid_pt_width(cid_val, sz_pt):
                if 0 <= cid_val < len(_glyph_order):
                    gname = _glyph_order[cid_val]
                    if gname in _hmtx.metrics:
                        gw = _hmtx.metrics[gname][0]
                        return gw * sz_pt / UPM
                return UPM * sz_pt / UPM

            _ascii_widths = []
            for ci in range(0, 128):
                _w = cid_pt_width(ci, 12)
                if _w < 11:
                    _ascii_widths.append(f'CID{ci}(0x{ci:02X})={_w:.2f}pt')
            print(f"字体 UPM={UPM}, hmtx 通过 CID→glyphName 正确查找")
            print(f"ASCII CIDs w=半宽的有 {len(_ascii_widths)} 个，示例: {_ascii_widths[:10]}")

            # ========== 提取 CID 链 ==========
            # ========== 用 fontTools 正确生成 CID (glyph number = PDF CID) ==========
            from fontTools.ttLib import TTCollection
            _col = TTCollection(SIMSUN_PATH)
            _ttf = _col.fonts[0]
            _cmap = _ttf['cmap'].getBestCmap()

            def str_to_cids(s):
                cids = []
                for ch in s:
                    cp = ord(ch)
                    gname = _cmap.get(cp)
                    if gname:
                        gid = _ttf.getGlyphID(gname)
                        cids.append(gid)
                    else:
                        cids.append(cp)
                return cids

            old_cids = str_to_cids(OLD_STR)
            new_cids = str_to_cids(NEW_STR)
            print(f"fontTools CID 编码成功")
            print(f"OLD '{OLD_STR}' -> {len(old_cids)} CIDs: {[hex(c) for c in old_cids]}")
            print(f"NEW '{NEW_STR}' -> {len(new_cids)} CIDs: {[hex(c) for c in new_cids]}")

            # ========== 获取内容流 ==========
            xrefs = page.get_contents()
            if isinstance(xrefs, int):
                xrefs = [xrefs]
            elif not isinstance(xrefs, list):
                xrefs = [xrefs]

            streams_raw = []
            for xr in xrefs:
                if isinstance(xr, int):
                    raw = doc.xref_stream(xr)
                    if raw:
                        streams_raw.append((xr, raw.decode('latin-1', errors='replace')))
                elif hasattr(xr, 'read_bytes'):
                    streams_raw.append((id(xr), xr.read_bytes().decode('latin-1', errors='replace')))

            stext = "\n".join(s for _, s in streams_raw)
            stext_up = stext.upper()
            print(f"内容流 xrefs: {[x for x,_ in streams_raw]}, 总长度: {len(stext)} 字节")

            # ========== 解析所有 BT/ET 块 ==========
            all_bt = []
            search_from = 0
            while True:
                bt_idx = stext_up.find("BT", search_from)
                if bt_idx < 0: break
                if bt_idx > 0 and stext[bt_idx-1] not in ('\n', '\r', ' ', '\t'):
                    search_from = bt_idx + 2
                    continue
                et_idx = stext_up.find("ET", bt_idx + 2)
                if et_idx < 0: break
                if et_idx > 0 and stext[et_idx-1] not in ('\n', '\r', ' ', '\t'):
                    search_from = et_idx + 2
                    continue

                block = stext[bt_idx:et_idx]
                block_up = block.upper()

                tm_m = re.search(r"([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+TM", block, re.I)
                td_m = re.search(r"([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+TD", block, re.I)

                tm_vals = [float(x) for x in tm_m.groups()] if tm_m else None
                tm_e = tm_vals[4] if tm_vals else None
                tm_f = tm_vals[5] if tm_vals else None

                cids_in_block = []
                hex_matches = re.findall(r"<([0-9A-Fa-f]+)>", block)
                for hx in hex_matches:
                    hx = hx.strip()
                    cid_len = 4 if len(hx) % 4 == 0 else 2
                    for k in range(0, len(hx), cid_len):
                        cids_in_block.append(int(hx[k:k+cid_len], 16))

                gs_m = re.search(r"([-\d.eE]+)[ \t]+GS", block, re.I)
                tr_m = re.search(r"([-\d.eE]+)[ \t]+TR", block, re.I)

                bt_inner_start = bt_idx + 2
                bt_inner_end = et_idx
                between = stext[bt_inner_start:bt_inner_end]

                x0 = tm_e if tm_e is not None else None
                y_val = tm_f if tm_f is not None else None

                sz_m = re.search(r"/([A-Za-z0-9]+)\s+([-\d.eE]+)\s+Tf", block, re.I)
                font_size = float(sz_m.group(2)) if sz_m else None
                font_id = sz_m.group(1) if sz_m else None
                font_dw = _font_dw_map.get(font_id, 1000) if font_id else 1000

                graphics_prefix = ""
                tm_in_block = re.search(r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+Tm", block, re.I)
                if tm_in_block:
                    tm_a_str, tm_b_str, tm_c_str, tm_d_str = tm_in_block.group(1), tm_in_block.group(2), tm_in_block.group(3), tm_in_block.group(4)
                    tm_full_start = bt_idx + tm_in_block.start()
                    prefix_raw = stext[bt_idx:tm_full_start]
                    graphics_prefix = prefix_raw + f"{tm_a_str} {tm_b_str} {tm_c_str} {tm_d_str}"

                all_bt.append({
                    'bt': bt_idx, 'et': et_idx + 2,
                    'tm_m': tm_m, 'td_m': td_m,
                    'tm_vals': tm_vals,
                    'cids': cids_in_block,
                    'x0': x0, 'y': y_val,
                    'font_size': font_size,
                    'font_id': font_id,
                    'font_dw': font_dw,
                    'gs': gs_m, 'tr': tr_m,
                    'between': between,
                    'graphics_prefix': graphics_prefix,
                })
                search_from = et_idx + 2

            print(f"共解析 {len(all_bt)} 个 BT 块")

            # ========== 用 get_texttrace.chars 定位 OLD_STR 的实际位置 ==========
            target_x = None
            target_y = None
            traces = page.get_texttrace()
            found_in_trace = False
            for tr in traces:
                cps = [ch[0] for ch in tr['chars']]
                text = ''.join(chr(c) for c in cps)
                if OLD_STR in text:
                    idx = text.index(OLD_STR)
                    bbox = tr['bbox']
                    total_w = bbox[2] - bbox[0]
                    char_w = total_w / max(1, len(text))
                    target_x = bbox[0] + idx * char_w
                    target_y = (bbox[1] + bbox[3]) / 2
                    print(f"\nOK get_texttrace 找到 OLD_STR: bbox={bbox}, target_x≈{target_x:.2f}, target_y≈{target_y:.2f}")
                    found_in_trace = True
                    break

            if not found_in_trace:
                print(f"\nFAIL get_texttrace 也没找到 '{OLD_STR}'")
                raise ValueError('get_texttrace 也没找到 \'{OLD_STR}\'")')

            # ========== 用 old_cids 序列匹配目标 BT 块 (收集所有匹配) ==========
            _all_cid_matches = []
            for i, b in enumerate(all_bt):
                cids = b['cids']
                for s in range(len(cids) - len(old_cids) + 1):
                    if cids[s:s+len(old_cids)] == old_cids:
                        _all_cid_matches.append((i, s, b))

            if not _all_cid_matches:
                print("FAIL: old_cids 序列在所有 BT 块里都找不到")
                raise ValueError('old_cids 序列在所有 BT 块里都找不到")')

            print(f"\nCID 序列匹配: 共 {len(_all_cid_matches)} 处匹配")
            for _mi, (_mi_idx, _mi_pos, _mi_blk) in enumerate(_all_cid_matches):
                print(f"  [{_mi}] BT#{_mi_idx} @cid[{_mi_pos}:{_mi_pos+len(old_cids)}], bt={_mi_blk['bt']}, y={_mi_blk['y']:.2f}, x0={_mi_blk['x0']:.2f}, font_size={_mi_blk['font_size']}, total_cids={len(_mi_blk['cids'])}")

            # 选择要处理的 BT 块: 默认第一处, 可通过 argv[5] 指定 y 坐标过滤

            target_idx = _all_cid_matches[0][0]
            blk0 = all_bt[target_idx]
            print(f"\n>>> 主要处理 BT#{target_idx}: bt={blk0['bt']}, et={blk0['et']}")
            print(f"  x0={blk0['x0']:.2f}, y={blk0['y']:.2f}, font_size={blk0['font_size']}")
            print(f"  CIDs: {len(blk0['cids'])} 个")

            # ========== TD 参数 ==========
            td_m_global = re.search(r"Tj[ \t]+([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+TD", stext[blk0['bt']:blk0['et']], re.I)
            if td_m_global:
                td_dx = td_m_global.group(1)
                td_dy = td_m_global.group(2)
            else:
                td_dx = "242.391"
                td_dy = "0"
            print(f"TD 参数: dx={td_dx}, dy={td_dy}")

            # ========== Y 方向检测 ==========
            YDIR = None
            for i in range(len(all_bt)):
                if all_bt[i]['y'] is None: continue
                for j in range(len(all_bt)):
                    if i == j: continue
                    if all_bt[j]['y'] is None: continue
                    if abs(all_bt[i]['x0'] - all_bt[j]['x0']) < 5 and abs(all_bt[i]['y'] - all_bt[j]['y']) > 20:
                        if all_bt[i]['y'] < all_bt[j]['y']:
                            YDIR = -1
                            print(f"Y 方向: 检测到 Y↓ (原点左上), YDIR=-1")
                        else:
                            YDIR = 1
                            print(f"Y 方向: 检测到 Y↑ (原点左下), YDIR=1")
                        break
                if YDIR is not None: break
            if YDIR is None:
                YDIR = -1
                print(f"Y 方向: 默认 YDIR=-1")

            target_y = blk0['y']
            tm_a = blk0['tm_vals'][0] if blk0['tm_vals'] else 1.0
            font_sz_pt = (blk0['font_size'] or 12.0) * abs(tm_a)
            print(f"实际字号: Tf={blk0['font_size']}, Tm.a={tm_a}, pt={font_sz_pt:.2f}")

            YT = min(font_sz_pt * 0.5, 3.0)
            all_y_raw = sorted([b['y'] for b in all_bt if b['y'] is not None])
            dedup_y = []
            for y in all_y_raw:
                if not dedup_y or abs(y - dedup_y[-1]) > YT:
                    dedup_y.append(y)

            row_ys = sorted(dedup_y, reverse=(YDIR < 0))
            detected_lh = None
            if len(row_ys) >= 2:
                diffs = [abs(row_ys[i+1] - row_ys[i]) for i in range(len(row_ys)-1)]
                from collections import Counter
                freq = Counter(diffs)
                top2 = freq.most_common(2)
                detected_lh = top2[0][0]
                if detected_lh < font_sz_pt:
                    detected_lh = top2[1][0] if len(top2) > 1 else font_sz_pt * 1.5
                print(f"自动检测行间距: 去重后 {len(row_ys)} 行, 众数={detected_lh:.2f}pt (所有差值: {[f'{d:.1f}' for d in diffs]})")
            else:
                print("自动检测行间距: 样本不足")

            LH = detected_lh if detected_lh and detected_lh > font_sz_pt else font_sz_pt * 1.5
            print(f"使用 LH={LH:.2f}pt (检测值={detected_lh}, 公式值={font_sz_pt*1.5:.2f})")

            # ========== 下划线检测 ==========
            underline_info = None
            for _m in re.finditer(r'(Q\r[-\d.]+\s+w\r[-\d.]+\s+J\rq\r/\S+\s+gs\r)([-\d.]+)\s+([-\d.]+)\s+m\r([-\d.]+)\s+([-\d.]+)\s+l\rS\r(Q\r[-\d.]+\s+w\r[-\d.]+\s+J\rq\r)', stext, re.I):
                _x1, _y1, _x2, _y2 = float(_m.group(2)), float(_m.group(3)), float(_m.group(4)), float(_m.group(5))
                if abs(_y1 - target_y) < 8 and abs(_y1 - _y2) < 0.5:
                    _lw_m = re.search(r'([-\d.]+)\s+w', _m.group(1))
                    _lw = float(_lw_m.group(1)) if _lw_m else 0.72
                    _gs_m = re.search(r'/(\S+)\s+gs', _m.group(1))
                    _gs = _gs_m.group(1) if _gs_m else 'GS13'
                    _ul_offset = _y1 - target_y
                    print(f"\n下划线检测: ({_x1:.2f},{_y1:.2f})->({_x2:.2f},{_y2:.2f}), 线宽={_lw}, GS=/{_gs}, y偏移={_ul_offset:.2f}pt")
                    underline_info = {
                        'x1': _x1, 'x2': _x2, 'y_line': _y1,
                        'linewidth': _lw, 'gs': _gs,
                        'y_offset': _ul_offset,
                        'full_start': _m.start(),
                        'full_end': _m.end(),
                        'orig_prefix': _m.group(1),
                        'orig_suffix': _m.group(6)
                    }
                    break

            def make_underline(x1, x2, y_line, lw=None, gs=None):
                if underline_info:
                    _lw = underline_info['linewidth']
                    _gs = underline_info['gs']
                else:
                    _lw = lw if lw else 0.72
                    _gs = gs if gs else 'GS13'
                return f"q\r{_lw} w\r0 J\r/{_gs} gs\r{x1:.2f} {y_line:.2f} m\r{x2:.2f} {y_line:.2f} l\rS\rQ\r"

            # ========== 找同行 BT 块 (全部，含前置) ==========
            orig_blk0 = blk0
            same_line = []
            for i, b in enumerate(all_bt):
                if b['y'] is None or b['x0'] is None: continue
                if abs(b['y'] - target_y) <= YT:
                    same_line.append(b)

            same_line.sort(key=lambda x: x['x0'])
            blk0 = orig_blk0
            前置同行 = [b for b in same_line if b['x0'] < blk0['x0'] - 0.5]
            后续同行 = [b for b in same_line if b['x0'] > blk0['x0'] + 0.5]
            print(f"\n同行 BT 块: 共 {len(same_line)} 个")
            for j, b in enumerate(same_line):
                if b is blk0:
                    label = ">>> BLK0 (OLD_STR here)"
                elif b['x0'] < blk0['x0']:
                    label = "前置"
                else:
                    label = "后续"
                print(f"  {label}: x0={b['x0']:.2f}, y={b['y']:.2f}, {len(b['cids'])} cids")

                inner_text = stext[b['bt']:b['et']]
                _td_dxs = re.findall(r'([-\d.eE]+)\s+[-\d.eE]+\s+TD', inner_text, re.I)
                if _td_dxs:
                    _sum_td = sum(float(d) for d in _td_dxs)
                    _last_adv = _sum_td / len(_td_dxs)
                    _tm_a = b['tm_vals'][0] if b['tm_vals'] else tm_a
                    b['_exact_w'] = (_sum_td + _last_adv) * _tm_a
                    b['_exact_w_source'] = 'TD'
                elif len(b['cids']) > 0:
                    _tm_a = b['tm_vals'][0] if b['tm_vals'] else tm_a
                    _fs = b['font_size'] or 12.0
                    _font_id = b.get('font_id')
                    _total_gu = sum(_cidfont_w_glyph_units(c, _font_id) for c in b['cids'])
                    b['_exact_w'] = _total_gu * _tm_a * _fs / 1000.0
                    b['_exact_w_source'] = 'CIDFONT'
                else:
                    b['_exact_w'] = 0.0
                    b['_exact_w_source'] = 'EMPTY'

            # ========== PyMuPDF bbox 校准 _exact_w ==========
            if page is not None:
                _pm_spans = []
                for _pb in page.get_text("dict")["blocks"]:
                    if "lines" not in _pb: continue
                    for _pl in _pb["lines"]:
                        for _ps in _pl.get("spans", []):
                            _pm_spans.append(_ps["bbox"])

                for _b in all_bt:
                    _bx0, _by = _b.get('x0'), _b.get('y')
                    if _bx0 is None or _by is None: continue
                    _best, _best_d = None, 999
                    for _sb in _pm_spans:
                        if abs(_sb[1] - _by) > 20: continue
                        if _bx0 < _sb[0] - 3 or _bx0 > _sb[2] + 3: continue
                        _d = abs(_sb[0] - _bx0)
                        if _d < _best_d:
                            _best_d, _best = _d, _sb
                    if _best:
                        _b['_pm_span'] = _best

                _pm_groups = {}
                for _b in all_bt:
                    _ps = _b.get('_pm_span')
                    if _ps is None: continue
                    _key = (round(_ps[0], 0), round(_ps[2], 0))
                    _pm_groups.setdefault(_key, []).append(_b)

                for _key, _grp in _pm_groups.items():
                    _grp2 = [g for g in _grp if g.get('_exact_w', 0) > 0 and g.get('_exact_w_source') not in ('TD', 'CIDFONT')]
                    if not _grp2: continue
                    _pm_total_w = _key[1] - _key[0]
                    _total_cids = sum(len(g['cids']) for g in _grp2)
                    if _total_cids <= 0: continue
                    _pm_per_cid = _pm_total_w / _total_cids
                    for _g in _grp2:
                        _old_w = _g['_exact_w']
                        _g['_exact_w'] = _pm_per_cid * len(_g['cids'])
                        _g['_cid_width_ratio'] = _g['_exact_w'] / max(0.01, _old_w)
                        print(f"  [PM校准] x0={_g['x0']:.2f} cids={len(_g['cids']):2d} pm_w={_pm_total_w:6.2f} w={_g['_exact_w']:6.2f} (per_cid={_pm_per_cid:.3f}, ratio={_g['_cid_width_ratio']:.4f})")


            # ========== 工具函数 ==========
            def rebuild_tm_with_new_ef(tm_match, new_e, new_f):
                parts = tm_match.groups()
                return f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {new_e:.2f} {new_f:.2f} Tm"

            def rebuild_td_with_new_dxdy(td_match, new_dx, new_dy):
                g1 = td_match.group(1)
                g2 = td_match.group(2)
                prec_dx = len(g1.split('.')[-1]) if '.' in g1 else 0
                prec_dy = len(g2.split('.')[-1]) if '.' in g2 else 0
                return f"{new_dx:.{prec_dx}f} {new_dy:.{prec_dy}f} Td"

            def strip_tm_td(s):
                lt_idx = s.find("<")
                if lt_idx >= 0:
                    s2 = s[:lt_idx]
                else:
                    s2 = s
                s2 = re.sub(r"[-\d.eE]+[ \t]+[-\d.eE]+[ \t]+[-\d.eE]+[ \t]+[-\d.eE]+[ \t]+[-\d.eE]+[ \t]+[-\d.eE]+[ \t]+Tm", "", s2, flags=re.I)
                s2 = re.sub(r"[-\d.eE]+[ \t]+[-\d.eE]+[ \t]+Td", "", s2, flags=re.I)
                s2 = re.sub(r"[-\d.eE]+[ \t]+[-\d.eE]+[ \t]+TD", "", s2, flags=re.I)
                s2 = re.sub(r"\[[^\]]*\][ \t]*(TJ|Tj)", "", s2, flags=re.I)
                s2 = s2.replace("[", "").replace("]", "")
                s2 = re.sub(r"\s*(TJ|Tj)\b", "", s2, flags=re.I)
                s2 = re.sub(r"^[\r\n]+", "", s2)
                s2 = re.sub(r"[\r\n]+$", "", s2)
                s2 = re.sub(r"[ \t]+$", "", s2)
                return s2.strip()

            def make_cid_seg(cids):
                if not cids:
                    return ""
                hex_all = "".join(f"{c:04X}" for c in cids)
                return f"[<{hex_all}>]TJ"

            def make_tj_with_gap(cids, gap_tj):
                if not cids:
                    return ""
                parts = []
                g = -gap_tj
                for i, c in enumerate(cids):
                    parts.append(f"<{c:04X}>")
                    if i < len(cids) - 1:
                        parts.append(f"{g:.3f}")
                return f"[{' '.join(parts)}]TJ"

            # ========== 找 blk0 内 OLD_STR 的起始位置 ==========
            blk0_cids = blk0['cids']
            start_in_blk0 = -1
            for s in range(len(blk0_cids) - len(old_cids) + 1):
                if blk0_cids[s:s+len(old_cids)] == old_cids:
                    start_in_blk0 = s
                    break
            if start_in_blk0 < 0:
                start_in_blk0 = 0
            end_in_blk0 = start_in_blk0 + len(old_cids)

            block_raw = stext[blk0['bt']:blk0['et']]
            first_lt = block_raw.find("<")
            last_gt = block_raw.rfind(">")
            if first_lt < 0 or last_gt < 0:
                print("FAIL blk0 里没有 <hex> cid")
                raise ValueError('blk0 里没有 <hex> cid")')

            before_lt = block_raw[:first_lt]
            lbracket_in_block = before_lt.rfind("[")
            cid_area_start = blk0['bt'] + first_lt
            seg_start_offset = 0
            if lbracket_in_block >= 0:
                cid_area_start = blk0['bt'] + lbracket_in_block
                seg_start_offset = lbracket_in_block - first_lt
                print(f"  检测到 TJ 数组格式，CID 区域起始包含 [ (偏移 {seg_start_offset})")

            cid_area_end = blk0['bt'] + last_gt + 1

            hex_str = stext[cid_area_start:cid_area_end]
            cid_positions = []
            for m in re.finditer(r"<[0-9A-Fa-f]+>", hex_str):
                cid_positions.append((cid_area_start + m.start(), cid_area_start + m.end()))

            seg_start = cid_positions[0][0] + seg_start_offset
            seg_end = cid_positions[-1][1]

            after = stext[seg_end:]
            skip_match = re.match(r"\s*\]?\s*(Tj|TJ)\b(\s+[-\d.eE]+\s+[-\d.eE]+\s*(Td|TD)\b)?", after, re.I)
            if skip_match:
                seg_end += skip_match.end()
                print(f"  向后扩展 seg_end +{skip_match.end()} 字节 (含 Tj{'+TD' if skip_match.group(2) else ''})")

            blk0_leading_cids = blk0_cids[:start_in_blk0]
            blk0_trailing_cids = blk0_cids[end_in_blk0:]
            print(f"  seg_start={seg_start}, seg_end={seg_end}, 覆盖 blk0 全部 CID 区域 (blk0 共 {len(cid_positions)} 个 cids)")
            print(f"  OLD_STR 在 [{start_in_blk0}:{end_in_blk0}], 前导 {len(blk0_leading_cids)} CID + 尾部 {len(blk0_trailing_cids)} CID")
            print(f"  新 seg 包含: [前导 {len(blk0_leading_cids)} + NEW(截断后)]")

            # ========== 计算宽度 (per-CID glyph advanceWidth) ==========
            tm_a = blk0['tm_vals'][0] if blk0['tm_vals'] else 1.0
            target_x0 = blk0['x0']
            target_y = blk0['y']

            para_left = min(b['x0'] for b in same_line if b['x0'] is not None)
            page_left_margin = min(b['x0'] for b in all_bt if b['x0'] is not None)

            max_x_end = 0.0
            for _b in same_line:
                if _b['x0'] is None: continue
                _w = _b.get('_exact_w', 0)
                max_x_end = max(max_x_end, _b['x0'] + _w)

            right_edge = min(max_x_end, PAGE_W - 5)

            _blk0_fid = blk0.get('font_id')
            _blk0_fs = blk0.get('font_size') or 12.0
            _blk0_tma = blk0['tm_vals'][0] if blk0['tm_vals'] else tm_a

            def cidw(c):
                return _cidfont_w_glyph_units(c, _blk0_fid) * _blk0_fs * _blk0_tma / 1000.0

            leading_w = sum(cidw(c) for c in blk0_leading_cids)

            cid_ws_old = [cidw(c) for c in old_cids]
            cid_ws_new = [cidw(c) for c in new_cids]
            old_full_w = sum(cid_ws_old)
            new_full_w = sum(cid_ws_new)
            avg_char_w = new_full_w / max(1, len(new_cids))
            print(f"\n段落: para_left={para_left:.2f}, page_left_margin={page_left_margin:.2f}, right_edge={right_edge:.2f}, PAGE_W={PAGE_W:.2f}")
            print(f"blk0 x0={target_x0:.2f}, 前导宽={leading_w:.2f}pt ({len(blk0_leading_cids)} cids)")
            print(f"OLD 宽度: {old_full_w:.2f}pt, NEW 宽度: {new_full_w:.2f}pt, 差值: {new_full_w - old_full_w:.2f}pt")
            print(f"NEW 起始 x = {target_x0 + leading_w:.2f} (blk0.x0 + leading), 末端 = {target_x0 + leading_w + new_full_w:.2f}")

            REPLS = []
            _gap_tj_line1 = None

            # ========== 提前检测：紧随 target_y 行的独立行 (如 page_000n.png) ==========
            _captured_bt_list = []
            if len(后续同行) > 0:
                _sb_ys = set(b['y'] for b in 后续同行 if b['y'] is not None)
                _sb_ys.add(target_y)
                _first_body_y_pre = None
                for _b in all_bt:
                    if _b['y'] is None or _b['font_id'] is None:
                        continue
                    if _b['y'] > target_y + 1:
                        if _first_body_y_pre is None or _b['y'] < _first_body_y_pre:
                            _first_body_y_pre = _b['y']
                if _first_body_y_pre is None:
                    _first_body_y_pre = target_y + LH * 2
                for _b in all_bt:
                    if _b['y'] is None:
                        continue
                    if not (target_y + 0.5 < _b['y'] < _first_body_y_pre + 0.5):
                        continue
                    if _b['y'] in _sb_ys:
                        continue
                    _captured_bt_list.append(_b)
                    print(f"  [提前检测] 捕获独立行 BT@{_b['bt']}: y={_b['y']:.2f}, x0={_b['x0']:.2f}, {len(_b['cids'])} cids")
                print(f"  [提前检测] 共 {len(_captured_bt_list)} 个捕获独立行")
            else:
                print(f"  [提前检测] blk0 无后续同行块 ({len(后续同行)} 个), 跳过捕获独立行")

            # ========== Strategy A: 同行替换不溢出 ==========
            # NEW 本身不溢出的基础上，还需保证所有后续同行 + 捕获独立行整体也不溢出
            _last_sb_orig_end = 0
            for _sb in reversed(后续同行):
                if _sb['tm_m']:
                    _x = float(_sb['tm_m'].group(5))
                elif _sb['td_m']:
                    _x = float(_sb['td_m'].group(1))
                else:
                    continue
                _w = _sb.get('_exact_w', 0)
                if _w <= 0:
                    _tm_a = _sb['tm_vals'][0] if _sb['tm_vals'] else tm_a
                    _fs = _sb.get('font_size', 12.0)
                    _dw = _sb.get('font_dw', 1000)
                    _gu = sum(_cidfont_w_glyph_units(c, _sb.get('font_id')) for c in _sb['cids'])
                    _w = _gu * _tm_a * _fs / _dw * 1000.0 / 1000.0
                _last_sb_orig_end = _x + _w
                break
            _cb_total_w = 0
            for _cb in _captured_bt_list:
                _cw = _cb.get('_exact_w', 0)
                if _cw <= 0:
                    _tm_a = _cb['tm_vals'][0] if _cb['tm_vals'] else tm_a
                    _fs = _cb.get('font_size', 12.0)
                    _dw = _cb.get('font_dw', 1000)
                    _gu = sum(_cidfont_w_glyph_units(c, _cb.get('font_id')) for c in _cb['cids'])
                    _cw = _gu * _tm_a * _fs / _dw * 1000.0 / 1000.0
                _cb_total_w += _cw

            _delta_w_pre = new_full_w - old_full_w
            _all_tail_fits = (_last_sb_orig_end + _delta_w_pre <= right_edge + 0.5)
            print(f"\n  [策略选择] last_sb_orig_end={_last_sb_orig_end:.2f}, delta_w={_delta_w_pre:.2f}, cb_total_w={_cb_total_w:.2f}, right_edge={right_edge:.2f}")
            print(f"  [策略选择]  tail_total={_last_sb_orig_end + _delta_w_pre:.2f} (仅同行, 不含独立行), _all_tail_fits={_all_tail_fits}")
            print(f"  [策略选择]  NEW本身={target_x0 + leading_w + new_full_w:.2f}, NEW_fits={target_x0 + leading_w + new_full_w <= right_edge}")
            if target_x0 + leading_w + new_full_w <= right_edge and _all_tail_fits:
                print("\n>>> 策略 A: 同行替换 (不溢出)")
                new_seg_full = make_cid_seg(blk0_leading_cids + new_cids + blk0_trailing_cids)
                REPLS.append((seg_start, seg_end, new_seg_full))

                delta_w = new_full_w - old_full_w
                print(f"  宽度差 delta_w = NEW - OLD = {new_full_w:.2f} - {old_full_w:.2f} = {delta_w:.2f}pt")

                if abs(delta_w) < 0.01:
                    print("  delta_w ≈ 0, 后续同行块位置不变")
                else:
                    print(f"  调整后续同行块 x 偏移: {delta_w:+.2f}pt")
                    for sb in 后续同行:
                        if sb['tm_m']:
                            m = sb['tm_m']
                            abs_s = sb['bt'] + m.start()
                            abs_e = sb['bt'] + m.end()
                            new_e = float(m.group(5)) + delta_w
                            new_f = float(m.group(6))
                            new_tm = rebuild_tm_with_new_ef(m, new_e, new_f)
                            REPLS.append((abs_s, abs_e, new_tm))
                            print(f"    BT@{sb['bt']} Tm.x: {float(m.group(5)):.2f}→{new_e:.2f}")
                        elif sb['td_m']:
                            m = sb['td_m']
                            abs_s = sb['bt'] + m.start()
                            abs_e = sb['bt'] + m.end()
                            new_dx = float(m.group(1)) + delta_w
                            new_dy = float(m.group(2))
                            new_td = rebuild_td_with_new_dxdy(m, new_dx, new_dy)
                            REPLS.append((abs_s, abs_e, new_td))
                            print(f"    BT@{sb['bt']} Td.dx: {float(m.group(1)):.2f}→{new_dx:.2f}")

                if underline_info:
                    new_x2 = underline_info['x2'] + delta_w
                    new_ul_str = make_underline(underline_info['x1'], new_x2, underline_info['y_line'])
                    REPLS.append((underline_info['full_start'], underline_info['full_end'], new_ul_str))
                    print(f"  下划线修改: x2 {underline_info['x2']:.2f}→{new_x2:.2f} (delta_w={delta_w:+.2f})")

                # 扩展：把捕获独立行 (如 page_000n.png) 拉到 target_y 行末尾，保持 keep-together
                if _captured_bt_list:
                    last_sb_new_end = None
                    for sb in reversed(后续同行):
                        if sb['tm_m']:
                            _x = float(sb['tm_m'].group(5)) + delta_w
                            _w = sb['_exact_w']
                            last_sb_new_end = _x + _w
                            break
                        elif sb['td_m']:
                            _x = float(sb['td_m'].group(1)) + delta_w
                            _w = sb['_exact_w']
                            last_sb_new_end = _x + _w
                            break
                    if last_sb_new_end is None:
                        last_sb_new_end = target_x0 + leading_w + new_full_w

                    _run_x = last_sb_new_end
                    for _cb in _captured_bt_list:
                        _cw = _cb.get('_exact_w', 0)
                        if _cw <= 0:
                            _a = _cb['tm_vals'][0] if _cb['tm_vals'] else tm_a
                            _f = _cb.get('font_size', 12.0)
                            _d = _cb.get('font_dw', 1000)
                            _cu = sum(_cidfont_w_glyph_units(c, _cb.get('font_id')) for c in _cb['cids'])
                            _cw = _cu * _a * _f / _d * 1000.0 / 1000.0
                        _new_x = _run_x
                        if _cb['tm_m']:
                            m = _cb['tm_m']
                            abs_s = _cb['bt'] + m.start()
                            abs_e = _cb['bt'] + m.end()
                            new_tm = rebuild_tm_with_new_ef(m, _new_x, target_y)
                            REPLS.append((abs_s, abs_e, new_tm))
                            print(f"  [keep-together] 捕获行 BT@{_cb['bt']}: x={float(m.group(5)):.2f},y={float(m.group(6)):.2f} → x={_new_x:.2f},y={target_y:.2f}")
                        elif _cb['td_m']:
                            m = _cb['td_m']
                            abs_s = _cb['bt'] + m.start()
                            abs_e = _cb['bt'] + m.end()
                            new_td = rebuild_td_with_new_dxdy(m, _new_x, target_y)
                            REPLS.append((abs_s, abs_e, new_td))
                            print(f"  [keep-together] 捕获行 BT@{_cb['bt']}: Td ({float(m.group(1)):.2f},{float(m.group(2)):.2f}) → ({_new_x:.2f},{target_y:.2f})")
                        _run_x += _cw

                    # 全局上移：被合并的独立行腾出了空间，下方所有 BT 上移消除空行
                    _orig_independent_y = min(_cb['y'] for _cb in _captured_bt_list)
                    _up_actual = _orig_independent_y - target_y
                    print(f"\n  --- 全局上移: 消除 {_up_actual:.2f}pt 空行 ---")
                    _captured_bt_set = set(_cb['bt'] for _cb in _captured_bt_list)
                    _up_count = 0
                    for b in all_bt:
                        if b['y'] is None or b['bt'] in _captured_bt_set:
                            continue
                        if b['y'] <= target_y + 0.5:
                            continue
                        orig_y = b['y']
                        new_f = orig_y - _up_actual
                        if b['tm_m']:
                            m = b['tm_m']
                            abs_s = b['bt'] + m.start()
                            abs_e = b['bt'] + m.end()
                            new_tm = rebuild_tm_with_new_ef(m, float(m.group(5)), new_f)
                            REPLS.append((abs_s, abs_e, new_tm))
                            _up_count += 1
                        elif b['td_m']:
                            m = b['td_m']
                            abs_s = b['bt'] + m.start()
                            abs_e = b['bt'] + m.end()
                            new_td = rebuild_td_with_new_dxdy(m, float(m.group(1)), new_f)
                            REPLS.append((abs_s, abs_e, new_td))
                            _up_count += 1
                    print(f"  共上移 {_up_count} 个 BT 块 (每块上移 {_up_actual:.2f}pt)")
            else:
                # ========== Strategy B: 自动换行 + 左对齐 (v15.0) ==========
                print("\n>>> 策略 B: 自动换行 + 左对齐 (v15.0)")

                all_new_cids = new_cids

                break_at = len(all_new_cids)
                acc = leading_w
                for ci, w in enumerate(cid_ws_new):
                    acc += w
                    x_end = target_x0 + acc
                    if x_end > right_edge:
                        break_at = ci
                        print(f"  断点(初始): ci={ci}, x_end={x_end:.2f} > right_edge={right_edge:.2f}")
                        break

                def _is_cjk(ch):
                    if not ch: return False
                    cp = ord(ch)
                    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF

                def _is_word_char(ch):
                    if not ch: return False
                    return ch.isalpha() or ch.isdigit()

                _orig_break = break_at
                if break_at > 0 and break_at < len(NEW_STR):
                    prev_ch = NEW_STR[break_at - 1]
                    curr_ch = NEW_STR[break_at]
                    if _is_word_char(prev_ch) and _is_word_char(curr_ch) and not (_is_cjk(prev_ch) or _is_cjk(curr_ch)):
                        while break_at > 1 and _is_word_char(NEW_STR[break_at - 1]) and not _is_cjk(NEW_STR[break_at - 1]):
                            break_at -= 1
                if break_at != _orig_break:
                    print(f"  [断词保护-英文/数字] 断点回退 {_orig_break - break_at}: ci={break_at}")
                left_cids = all_new_cids[:break_at]
                if break_at < len(all_new_cids):
                    right_cids = all_new_cids[break_at:] + blk0_trailing_cids
                else:
                    right_cids = all_new_cids[break_at:]
                print(f"  blk0 断开: NEW前 {break_at}/{len(all_new_cids)} 留当前行, 余 {len(right_cids)} 换行")

                if break_at < len(all_new_cids):
                    blk0_left_end = target_x0 + leading_w + sum(cid_ws_new[:break_at])
                else:
                    _bfid = blk0.get('font_id')
                    _bfs = blk0.get('font_size') or 12.0
                    _btma = blk0['tm_vals'][0] if blk0['tm_vals'] else tm_a
                    _trailing_w = sum(_cidfont_w_glyph_units(c, _bfid) for c in blk0_trailing_cids) * _bfs * _btma / 1000.0
                    blk0_left_end = target_x0 + leading_w + sum(cid_ws_new[:break_at]) + _trailing_w
                rem = right_edge - blk0_left_end
                print(f"  blk0 左半 x_end={blk0_left_end:.2f}, 剩余空间={rem:.2f}pt")

                _pre_rem = rem
                _total_staying_sb_w = 0.0
                for _pi, _psb in enumerate(后续同行):
                    _psb_avg_w = _psb['_exact_w'] / max(1, len(_psb['cids']))
                    _psb_max_can = int(_pre_rem // _psb_avg_w)
                    if _psb_max_can <= 0:
                        break
                    _psb_keep = min(_psb_max_can, len(_psb['cids']))
                    if _psb_keep >= len(_psb['cids']):
                        _psb_w = _psb['_exact_w']
                    else:
                        _psb_w = _psb['_exact_w'] * _psb_keep / max(1, len(_psb['cids']))
                    _total_staying_sb_w += _psb_w
                    _pre_rem -= _psb_w
                rem_adjusted = max(0.0, rem - _total_staying_sb_w)
                if _total_staying_sb_w > 0.1:
                    print(f"  [预扫描] 留行 sb 总宽={_total_staying_sb_w:.2f}pt, 调整后 rem={rem_adjusted:.2f}pt")

                if break_at < len(all_new_cids):
                    left_full_cids = blk0_leading_cids + left_cids
                else:
                    left_full_cids = blk0_leading_cids + left_cids + blk0_trailing_cids
                n1 = len(left_full_cids)
                _gap_tj_line1 = None
                _gfx_sfx = blk0.get('_graphics_suffix', '') or ''
                _fs_line1 = blk0.get('font_size') or 12.0
                _max_gap_allowed = 2.0
                _per_gap_pt = rem_adjusted / max(1, n1 - 1)
                if n1 > 1 and rem_adjusted > 0.1 and _per_gap_pt <= _max_gap_allowed:
                    _gap_tj_line1 = rem_adjusted / (n1 - 1) * 1000 / (_fs_line1 * tm_a)
                    seg_left = make_tj_with_gap(left_full_cids, _gap_tj_line1)
                    print(f"  [两端对齐-行1] {n1} CIDs, gap={rem_adjusted:.2f}pt/{n1-1}间隙={_per_gap_pt:.3f}pt/gap, gap_tj={_gap_tj_line1:.1f}text_u")
                else:
                    seg_left = make_cid_seg(left_full_cids)
                    _gap_tj_line1 = None
                    if rem_adjusted > 0.1 and n1 > 1:
                        print(f"  [跳过两端对齐] gap={_per_gap_pt:.2f}pt > max={_max_gap_allowed}pt, 避免字间距拉散")
                if _gfx_sfx:
                    seg_left += " " + _gfx_sfx
                REPLS.append((seg_start, seg_end, seg_left))
                _line1_repl_idx = len(REPLS) - 1
                _line1_left_full_cids = left_full_cids
                _line1_seg_start = seg_start
                _line1_seg_end = seg_end

                _blk0_fid = blk0.get('font_id')
                _blk0_fs = blk0.get('font_size') or 12.0
                _blk0_tma = blk0['tm_vals'][0] if blk0['tm_vals'] else tm_a
                blk0_right_new_width = sum(_cidfont_w_glyph_units(c, _blk0_fid) for c in right_cids) * _blk0_fs * _blk0_tma / 1000.0
                blk0_right_new_end = para_left + blk0_right_new_width

                blk0_orig_total_w = sum(_cidfont_w_glyph_units(c, _blk0_fid) for c in blk0['cids']) * _blk0_fs * _blk0_tma / 1000.0
                blk0_orig_end = blk0['x0'] + blk0_orig_total_w

                orig_gaps_to_next = []
                for idx, sb in enumerate(后续同行):
                    if idx == 0:
                        orig_gaps_to_next.append(sb['x0'] - blk0_orig_end)
                    else:
                        orig_gaps_to_next.append(sb['x0'] - 后续同行[idx - 1]['x0'])

                print(f"  blk0 右半宽={blk0_right_new_width:.2f}, blk0_right_new_end={blk0_right_new_end:.2f}")

                new_y = target_y - YDIR * LH

                def make_bt_block(cids, graphics_prefix, x, y, td_dx_val, td_dy_val, gap_tj=None):
                    if not cids:
                        return ""
                    if gap_tj is not None and len(cids) > 1:
                        seg = make_tj_with_gap(cids, gap_tj)
                    else:
                        seg = make_cid_seg(cids)
                    if td_dx_val != td_dx:
                        seg = seg.replace(td_dx, td_dx_val)
                    if td_dy_val != td_dy:
                        seg = seg.replace(td_dy, td_dy_val)
                    return f"{graphics_prefix} {x:.2f} {y:.2f} Tm\r\n{seg}\r\nET\r\n"

                new_line_blocks_str = ""

                if underline_info:
                    target_ul_x1 = underline_info['x1']
                    target_ul_x2 = blk0_left_end
                    target_ul_y = underline_info['y_line']
                    new_line_blocks_str += make_underline(target_ul_x1, target_ul_x2, target_ul_y)
                    print(f"  target_y 行下划线: ({target_ul_x1:.2f},{target_ul_y:.2f})→({target_ul_x2:.2f},{target_ul_y:.2f}), len={target_ul_x2-target_ul_x1:.2f}")
                new_line_count = 0

                class LineBlock:
                    __slots__ = ('cids', 'prefix', 'nat_x', 'w', 'td_dx', 'td_dy', 'sb_idx_or_None', 'tm_a', 'font_size', 'font_dw', 'font_id', '_char_gap_tj', '_was_ul', '_orig_same_line')
                    def __init__(self, cids, prefix, nat_x, w, td_dx, td_dy, sb_idx_or_None, tm_a=0.05, font_size=None, font_dw=1000, font_id=None, was_ul=False, orig_same_line=True):
                        self.cids = cids
                        self.prefix = prefix
                        self.nat_x = nat_x
                        self.w = w
                        self.td_dx = td_dx
                        self.td_dy = td_dy
                        self.sb_idx_or_None = sb_idx_or_None
                        self.tm_a = tm_a
                        self.font_size = font_size if font_size else 12.0
                        self.font_dw = font_dw
                        self.font_id = font_id
                        self._char_gap_tj = None
                        self._was_ul = was_ul
                        self._orig_same_line = orig_same_line

                _newline_start = page_left_margin
                all_new_line_blocks = []
                _ul_x2 = underline_info['x2'] if underline_info else None
                if right_cids:
                    all_new_line_blocks.append(LineBlock(
                        right_cids, blk0['graphics_prefix'],
                        _newline_start, blk0_right_new_width,
                        td_dx, td_dy, None,
                        tm_a=blk0['tm_vals'][0] if blk0['tm_vals'] else 0.05,
                        font_size=blk0.get('font_size', 12.0),
                        font_dw=blk0.get('font_dw', 1000),
                        font_id=blk0.get('font_id'),
                        was_ul=True
                    ))

                running_x_cur = blk0_left_end + (rem_adjusted if _gap_tj_line1 else 0.0)
                sb_idx = 0

                def make_sb_seg(cids_to_use, sb_td_dx_val, sb_td_dy_val):
                    if not cids_to_use:
                        return ""
                    hex_all = "".join(f"{c:04X}" for c in cids_to_use)
                    return f"[<{hex_all}>]TJ"

                for i, sb in enumerate(后续同行):
                    sb_a = sb['tm_vals'][0] if sb['tm_vals'] else tm_a
                    sb_td_local = re.search(r"Tj[ \t]+([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+TD", stext[sb['bt']:sb['et']], re.I)
                    sb_td_dx = sb_td_local.group(1) if sb_td_local else td_dx
                    sb_td_dy = sb_td_local.group(2) if sb_td_local else td_dy
                    sb_avg_char_w = sb['_exact_w'] / max(1, len(sb['cids']))

                    max_can_fit = int(rem // sb_avg_char_w)
                    if max_can_fit <= 0:
                        print(f"  sb BT@{sb['bt']}: 剩余空间 {rem:.2f}pt 不够塞 1 字 (avg {sb_avg_char_w:.3f}pt), 全移新行")
                        break

                    can_keep = min(max_can_fit, len(sb['cids']))
                    sb_cids = sb['cids']

                    if can_keep >= len(sb_cids):
                        if sb['tm_m']:
                            m = sb['tm_m']
                            abs_s = sb['bt'] + m.start()
                            abs_e = sb['bt'] + m.end()
                            new_tm = rebuild_tm_with_new_ef(m, running_x_cur, target_y)
                            REPLS.append((abs_s, abs_e, new_tm))
                        elif sb['td_m']:
                            m = sb['td_m']
                            abs_s = sb['bt'] + m.start()
                            abs_e = sb['bt'] + m.end()
                            new_td = f"{running_x_cur:.2f} {target_y:.2f} Td"
                            REPLS.append((abs_s, abs_e, new_td))
                        print(f"  [留当前行] sb 全留: BT@{sb['bt']}, x={running_x_cur:.2f}, y={target_y:.2f}, 宽={sb['_exact_w']:.2f}pt")
                        running_x_cur += sb['_exact_w']
                        rem -= sb['_exact_w']
                        sb_idx = i + 1
                    else:
                        sb_block_up = stext[sb['bt']:sb['et']]
                        first_lt = sb_block_up.find("<")
                        last_gt = sb_block_up.rfind(">")
                        sb_before_lt = sb_block_up[:first_lt] if first_lt >= 0 else ""
                        sb_lbracket = sb_before_lt.rfind("[")
                        if sb_lbracket >= 0:
                            sb_cid_start = sb['bt'] + sb_lbracket
                        else:
                            sb_cid_start = sb['bt'] + first_lt
                        after_sb = stext[sb['bt'] + last_gt + 1:] if last_gt >= 0 else ""
                        sb_skip = re.match(r"\s*\]?\s*(Tj|TJ)\b", after_sb, re.I)
                        sb_cid_end = sb['bt'] + last_gt + 1
                        if sb_skip:
                            sb_cid_end += sb_skip.end()

                        sb_keep_cids = sb_cids[:can_keep]
                        sb_keep_seg = make_sb_seg(sb_keep_cids, sb_td_dx, sb_td_dy)
                        REPLS.append((sb_cid_start, sb_cid_end, sb_keep_seg))

                        if sb['tm_m']:
                            m = sb['tm_m']
                            abs_s = sb['bt'] + m.start()
                            abs_e = sb['bt'] + m.end()
                            new_tm = rebuild_tm_with_new_ef(m, running_x_cur, target_y)
                            REPLS.append((abs_s, abs_e, new_tm))
                        print(f"  [留当前行] sb 截断: BT@{sb['bt']}, 留 {can_keep}/{len(sb_cids)}, x={running_x_cur:.2f}, y={target_y:.2f}")
                        sb_keep_w = sb['_exact_w'] * can_keep / max(1, len(sb_cids))
                        running_x_cur += sb_keep_w

                        sb_left_cids = sb_cids[can_keep:]
                        left_w = sb['_exact_w'] - sb_keep_w
                        _sb_was_ul = (_ul_x2 is not None and sb['x0'] <= _ul_x2)
                        all_new_line_blocks.append(LineBlock(
                            sb_left_cids, sb['graphics_prefix'],
                            0, left_w,
                            sb_td_dx, sb_td_dy, i,
                            tm_a=sb_a if sb_a else 0.05,
                            font_size=sb.get('font_size', 12.0),
                            font_dw=sb.get('font_dw', 1000),
                            font_id=sb.get('font_id'),
                            was_ul=_sb_was_ul
                        ))
                        sb_idx = i + 1
                        break

                for sbi, sb in enumerate(后续同行):
                    if sbi < sb_idx:
                        continue
                    sb_a = sb['tm_vals'][0] if sb['tm_vals'] else tm_a
                    sb_td_local = re.search(r"Tj[ \t]+([-\d.eE]+)[ \t]+([-\d.eE]+)[ \t]+TD", stext[sb['bt']:sb['et']], re.I)
                    sb_td_dx_val = sb_td_local.group(1) if sb_td_local else td_dx
                    sb_td_dy_val = sb_td_local.group(2) if sb_td_local else td_dy
                    sb_full_w = sb['_exact_w']

                    sb_a2 = sb['tm_vals'][0] if sb['tm_vals'] else tm_a
                    _sb_was_ul2 = (_ul_x2 is not None and sb['x0'] <= _ul_x2)
                    all_new_line_blocks.append(LineBlock(
                        sb['cids'], sb['graphics_prefix'],
                        0, sb_full_w,
                        sb_td_dx_val, sb_td_dy_val, sbi,
                        tm_a=sb_a2 if sb_a2 else 0.05,
                        font_size=sb.get('font_size', 12.0),
                        font_dw=sb.get('font_dw', 1000),
                        font_id=sb.get('font_id'),
                        was_ul=_sb_was_ul2
                    ))

                # ========== 捕获紧随 target_y 行的独立行 (如 page_000n.png) ==========
                _captured_extra_bts = []
                _sb_ys = set(b['y'] for b in 后续同行 if b['y'] is not None)
                _sb_ys.add(target_y)
                _first_body_y = None
                for _b in all_bt:
                    if _b['y'] is None or _b['font_id'] is None:
                        continue
                    if _b['y'] > target_y + 1:
                        if _first_body_y is None or _b['y'] < _first_body_y:
                            _first_body_y = _b['y']
                if _first_body_y is None:
                    _first_body_y = target_y + LH * 2
                print(f"\n  --- 捕获紧随独立行: target_y={target_y:.2f}, first_body_y={_first_body_y:.2f} ---")
                for _b in all_bt:
                    if _b['y'] is None:
                        continue
                    if not (target_y + 0.5 < _b['y'] < _first_body_y + 0.5):
                        continue
                    if _b['y'] in _sb_ys:
                        continue
                    _captured_extra_bts.append(_b)
                    _w = _b.get('_exact_w')
                    if _w is None or _w <= 0:
                        _tm_a = _b['tm_vals'][0] if _b['tm_vals'] else tm_a
                        _fs = _b.get('font_size', 12.0)
                        _fid = _b.get('font_id')
                        _gu = sum(_cidfont_w_glyph_units(c, _fid) for c in _b['cids'])
                        _w = _gu * _tm_a * _fs / 1000.0
                    print(f"    捕获 BT@{_b['bt']}: y={_b['y']:.2f}, x0={_b['x0']:.2f}, {len(_b['cids'])} cids, w={_w:.2f}pt")
                    all_new_line_blocks.append(LineBlock(
                        _b['cids'], _b['graphics_prefix'],
                        0, _w,
                        td_dx, td_dy, None,
                        tm_a=_b['tm_vals'][0] if _b['tm_vals'] else 0.05,
                        font_size=_b.get('font_size', 12.0),
                        font_dw=_b.get('font_dw', 1000),
                        font_id=_b.get('font_id'),
                        orig_same_line=True
                    ))

                LINE_W_AVAIL = right_edge - _newline_start

                def _split_block_by_chars(blk, max_w):
                    cids = blk.cids
                    chunks = []
                    cur_cids = []
                    cur_w = 0.0
                    for c in cids:
                        cw = _cidfont_w_glyph_units(c, blk.font_id) * blk.font_size * blk.tm_a / 1000.0
                        if cur_cids and cur_w + cw > max_w:
                            chunks.append((cur_cids, cur_w))
                            cur_cids = [c]
                            cur_w = cw
                        else:
                            cur_cids.append(c)
                            cur_w += cw
                    if cur_cids:
                        chunks.append((cur_cids, cur_w))
                    result = []
                    for chunk_cids, chunk_w in chunks:
                        result.append(LineBlock(
                            chunk_cids, blk.prefix,
                            blk.nat_x, chunk_w,
                            blk.td_dx, blk.td_dy, blk.sb_idx_or_None,
                            tm_a=blk.tm_a,
                            font_size=blk.font_size,
                            font_dw=blk.font_dw,
                            font_id=blk.font_id,
                            was_ul=blk._was_ul
                        ))
                    return result

                _orig_count = len(all_new_line_blocks)
                _split_flat = []
                for _blk in all_new_line_blocks:
                    if _blk.w > LINE_W_AVAIL + 0.5:
                        _split_flat.extend(_split_block_by_chars(_blk, LINE_W_AVAIL))
                    else:
                        _split_flat.append(_blk)
                all_new_line_blocks = _split_flat
                if len(all_new_line_blocks) > _orig_count:
                    print(f"  [字符级拆分] {_orig_count} → {len(all_new_line_blocks)} LineBlocks (按行宽 {LINE_W_AVAIL:.2f}pt 拆分超宽块)")

                lines = []
                current_line = []
                current_line_x = _newline_start
                _nbl = all_new_line_blocks
                _i = 0
                while _i < len(_nbl):
                    blk = _nbl[_i]
                    _rem = right_edge + 0.5 - current_line_x
                    if blk._orig_same_line:
                        _chain_end = _i
                        _chain_w = 0.0
                        while _chain_end < len(_nbl) and _nbl[_chain_end]._orig_same_line:
                            _chain_w += _nbl[_chain_end].w
                            _chain_end += 1
                        if _chain_w <= _rem:
                            for _k in range(_i, _chain_end):
                                _bk = _nbl[_k]
                                _bk.nat_x = current_line_x
                                current_line.append(_bk)
                                current_line_x += _bk.w
                            _i = _chain_end
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = []
                            current_line_x = _newline_start
                            _chain_w2 = 0.0
                            for _k in range(_i, _chain_end):
                                _bk = _nbl[_k]
                                _bk.nat_x = current_line_x
                                current_line.append(_bk)
                                current_line_x += _bk.w
                            _i = _chain_end
                    else:
                        if blk.w <= _rem:
                            blk.nat_x = current_line_x
                            current_line.append(blk)
                            current_line_x += blk.w
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = [blk]
                            blk.nat_x = _newline_start
                            current_line_x = _newline_start + blk.w
                        _i += 1
                if current_line:
                    lines.append(current_line)

                for line_blocks in lines:
                    running = _newline_start
                    for bi, blk in enumerate(line_blocks):
                        blk.nat_x = running
                        running = blk.nat_x + blk.w

                total_lines = len(lines)
                for li, line_blocks in enumerate(lines):
                    nat_right = max(b.nat_x + b.w for b in line_blocks)
                    gap_line = right_edge - nat_right
                    n_blocks = len(line_blocks)
                    n_char_gaps = sum(max(0, len(b.cids) - 1) for b in line_blocks)
                    n_block_gaps = max(0, n_blocks - 1)
                    n_total_gaps = n_char_gaps + n_block_gaps

                    _line_total_w = right_edge - _newline_start
                    _gap_ratio = gap_line / _line_total_w if _line_total_w > 0 else 1.0
                    gap_pt_per = gap_line / n_total_gaps if n_total_gaps > 0 else 0
                    if gap_line > 0.5 and n_total_gaps > 0 and n_char_gaps >= 2 and _gap_ratio <= 0.12 and gap_pt_per <= 0.5:
                        running = _newline_start
                        for bi, blk in enumerate(line_blocks):
                            blk.nat_x = running
                            char_exp = max(0, len(blk.cids) - 1) * gap_pt_per
                            running += blk.w + char_exp
                            if bi < n_blocks - 1:
                                running += gap_pt_per
                            if len(blk.cids) > 1 and blk.tm_a:
                                blk._char_gap_tj = gap_pt_per * 1000 / (blk.font_size * blk.tm_a)
                            else:
                                blk._char_gap_tj = None
                        print(f"  [两端对齐-新行#{li+1}] gap={gap_line:.2f}pt/{n_total_gaps}间隙={gap_pt_per:.3f}pt/gap, char_gaps={n_char_gaps}, block_gaps={n_block_gaps}")
                    else:
                        for blk in line_blocks:
                            blk._char_gap_tj = None

                for li, line_blocks in enumerate(lines):
                    line_y = new_y - li * YDIR * LH
                    new_line_count += 1

                    right_most = max(b.nat_x + b.w for b in line_blocks)
                    stretch_info = ""
                    if any(b._char_gap_tj for b in line_blocks):
                        stretch_info = f" +gap"

                    print(f"  --- 新行 #{new_line_count}: y={line_y:.2f}, {len(line_blocks)} 块, nat_right={right_most:.2f}{stretch_info} ---")

                    for bi, blk in enumerate(line_blocks):
                        final_x = blk.nat_x

                        full_block_str = make_bt_block(
                            blk.cids, blk.prefix,
                            final_x, line_y,
                            blk.td_dx, blk.td_dy,
                            gap_tj=blk._char_gap_tj
                        )
                        new_line_blocks_str += full_block_str
                        orig_info = f"(BT@{后续同行[blk.sb_idx_or_None]['bt']})" if blk.sb_idx_or_None is not None else "(blk0右半)"
                        extra = f" +gap_tj={blk._char_gap_tj:.1f}" if blk._char_gap_tj else ""
                        print(f"    块[{bi}] {orig_info}: nat_x={blk.nat_x:.2f}→final_x={final_x:.2f}, w={blk.w:.2f}, end={final_x+blk.w:.2f}, {len(blk.cids)} cids{extra}")

                    if underline_info and line_blocks:
                        ul_y = line_y + underline_info['y_offset']
                        segments = []
                        seg_x1 = None
                        seg_x2 = None
                        for blk in line_blocks:
                            if blk._was_ul:
                                if seg_x1 is None:
                                    seg_x1 = blk.nat_x
                                    seg_x2 = blk.nat_x + blk.w
                                else:
                                    seg_x2 = blk.nat_x + blk.w
                            else:
                                if seg_x1 is not None:
                                    segments.append((seg_x1, seg_x2))
                                    seg_x1 = None
                                    seg_x2 = None
                        if seg_x1 is not None:
                            segments.append((seg_x1, seg_x2))
                        for s_x1, s_x2 in segments:
                            ul_str = make_underline(s_x1, s_x2, ul_y)
                            new_line_blocks_str += ul_str
                            print(f"    下划线段: ({s_x1:.2f},{ul_y:.2f})→({s_x2:.2f},{ul_y:.2f}), len={s_x2-s_x1:.2f}")

                _last_sb_et_for_erase = 0
                for sbi2 in range(sb_idx, len(后续同行)):
                    if 后续同行[sbi2]['et'] > _last_sb_et_for_erase:
                        _last_sb_et_for_erase = 后续同行[sbi2]['et']
                for _eb in _captured_extra_bts:
                    if _eb['et'] > _last_sb_et_for_erase:
                        _last_sb_et_for_erase = _eb['et']
                _newline_erase_start = blk0['et']
                if sb_idx < len(后续同行):
                    _first_move_bt = 后续同行[sb_idx]['bt']
                    if _first_move_bt > _newline_erase_start:
                        _newline_erase_start = _first_move_bt
                if sb_idx >= len(后续同行) and _captured_extra_bts:
                    _cap_first_bt = _captured_extra_bts[0]['bt']
                    if _cap_first_bt > _newline_erase_start:
                        _newline_erase_start = _cap_first_bt
                if underline_info:
                    print(f"  [UL pos] full_start={underline_info['full_start']}, full_end={underline_info['full_end']}, erase=[{_newline_erase_start},{_last_sb_et_for_erase}]")
                    if underline_info['full_start'] < _newline_erase_start or underline_info['full_end'] > _last_sb_et_for_erase:
                        print(f"  !! UL not fully in erase range - adding extra erase REPLS")
                        REPLS.append((underline_info['full_start'], underline_info['full_end'], ""))
                    else:
                        print(f"  OK UL inside erase range, will be replaced together")
                if _last_sb_et_for_erase > 0:
                    _newline_erase_end = _last_sb_et_for_erase
                    print(f"  [大范围替换] blk0_et={_newline_erase_start} → last_sb_et={_newline_erase_end}, 覆盖 {_newline_erase_end - _newline_erase_start} 字节的残留 q/Q 和绘图命令 (含 {len(_captured_extra_bts)} 个捕获独立行)")
                else:
                    _newline_erase_end = blk0['et']
                REPLS.append((_newline_erase_start, _newline_erase_end, new_line_blocks_str))
                _newline_repl_idx = len(REPLS) - 1
                _newline_y_list = []
                for _li2, _lbs2 in enumerate(lines):
                    _newline_y_list.append(new_y - _li2 * YDIR * LH)

                # ========== Y 下移: 目标行视觉下方所有 BT 块 ==========
                _captured_gap_total = sum(max(0, _eb['y'] - target_y) for _eb in _captured_extra_bts)
                _raw_shift = LH * new_line_count
                _net_shift = max(0.0, _raw_shift - _captured_gap_total)
                print(f"\n  --- 下移目标行视觉下方所有 BT 块 ---")
                print(f"    原始下移量: {new_line_count} × LH = {_raw_shift:.2f}pt")
                print(f"    捕获独立行腾出空间: {_captured_gap_total:.2f}pt ({len(_captured_extra_bts)} 行)")
                print(f"    净下移量: {_net_shift:.2f}pt")
                shift_count = 0
                _captured_bt_set = set(_eb['bt'] for _eb in _captured_extra_bts)
                for b in all_bt:
                    if b['y'] is None:
                        continue
                    if b['bt'] in _captured_bt_set:
                        print(f"    跳过已捕获 BT@{b['bt']} (y={b['y']:.2f})")
                        continue
                    if YDIR * (b['y'] - target_y) >= -YT:
                        continue
                    orig_y = b['y']
                    new_f = orig_y - YDIR * _net_shift
                    if b['tm_m']:
                        m = b['tm_m']
                        abs_s = b['bt'] + m.start()
                        abs_e = b['bt'] + m.end()
                        new_tm = rebuild_tm_with_new_ef(m, float(m.group(5)), new_f)
                        print(f"    BT@{b['bt']} Tm: y={orig_y:.2f}→{new_f:.2f}")
                        REPLS.append((abs_s, abs_e, new_tm))
                        shift_count += 1
                    elif b['td_m']:
                        m = b['td_m']
                        abs_s = b['bt'] + m.start()
                        abs_e = b['bt'] + m.end()
                        orig_ty_str = m.group(2)
                        prec = len(orig_ty_str.split('.')[-1]) if '.' in orig_ty_str else 0
                        new_ty = float(orig_ty_str) - YDIR * LH
                        new_td = f"{m.group(1)} {new_ty:.{prec}f} Td"
                        print(f"    BT@{b['bt']} Td: y={orig_y:.2f}→{new_f:.2f}")
                        REPLS.append((abs_s, abs_e, new_td))
                        shift_count += 1
                print(f"  共下移 {shift_count} 个 BT 块")

            # ========== 字体修补提前（两阶段标定之前必须有完整字体） ==========
            print("\n=== 字体修补（提前到标定前） ===")
            def fix_simsun_font(doc, page, full_font_path):
                ff2_xref = None
                try:
                    font_resources = page.get_fonts(full=True)
                except Exception:
                    font_resources = []
                for item in font_resources:
                    if len(item) >= 5:
                        xref = item[0]
                        try:
                            obj = doc.xref_object(xref, compressed=True)
                        except Exception:
                            continue
                        if not obj:
                            continue
                        if '/Type0' in obj or '/DescendantFonts' in obj:
                            dm = re.search(r'/DescendantFonts\s*\[(\d+)\s+0\s+R\]', obj)
                            if dm:
                                desc_xref = int(dm.group(1))
                                try:
                                    desc_obj = doc.xref_object(desc_xref, compressed=True)
                                except Exception:
                                    continue
                                if not desc_obj:
                                    continue
                                fd_m = re.search(r'/FontDescriptor\s+(\d+)\s+0\s+R', desc_obj)
                                if fd_m:
                                    fd_xref = int(fd_m.group(1))
                                    try:
                                        fd_obj = doc.xref_object(fd_xref, compressed=True)
                                    except Exception:
                                        continue
                                    if fd_obj and '/FontFile2' in fd_obj:
                                        ff2_m = re.search(r'/FontFile2\s+(\d+)\s+0\s+R', fd_obj)
                                        if ff2_m:
                                            ff2_xref = int(ff2_m.group(1))
                                            break
                if not ff2_xref:
                    print("  未找到 SimSun FontFile2，跳过字体修补")
                    return False
                full_col = TTCollection(full_font_path)
                full_ttf = full_col.fonts[0]
                remove_tags = ['GSUB', 'GPOS', 'GDEF', 'DSIG', 'GASP', 'hdmx', 'LTSH',
                               'kern', 'vhea', 'vmtx', 'BASE', 'GPK', 'MATH', 'EBDT',
                               'EBLC', 'MERG', 'meta']
                for tag in remove_tags:
                    if tag in full_ttf:
                        del full_ttf[tag]
                out_buf = io.BytesIO()
                full_ttf.save(out_buf)
                out_data = out_buf.getvalue()
                doc.update_stream(ff2_xref, out_data)
                print(f"  已修补 FontFile2 xref={ff2_xref}: {len(out_data)} bytes (完整 SimSun)")
                return True

            fix_simsun_font(doc, page, SIMSUN_PATH)

            # ========== 像素迭代标定 gap_tj（已跳过：pure formula 已正确） ==========
            if _gap_tj_line1 is not None:
                print(f"\n[行1 gap_tj] 使用 pure formula 值 = {_gap_tj_line1:.2f}（跳过像素迭代标定）")
                print(f"  formula: gap_tj = rem/(n1-1) * 1000 / (font_size * tm_a)")

            # ========== 新行 gap_tj 行1比例缩放 ==========
            _gap_tj_newline_init = None
            all_new_line_blocks = locals().get('all_new_line_blocks', [])
            for _b in all_new_line_blocks:
                if _b._char_gap_tj is not None:
                    _gap_tj_newline_init = _b._char_gap_tj
                    break

            if _gap_tj_newline_init is not None and '_newline_repl_idx' in dir() and _newline_repl_idx is not None:
                _calib_scale = 1.0
                print(f"\n[新行 gap_tj] 原始值={_gap_tj_newline_init:.2f}, 标定比例={_calib_scale:.3f}, 不缩放")
                _s = ""
                for _li3, _lbs3 in enumerate(lines):
                    _line_y3 = new_y - _li3 * YDIR * LH
                    for _bk3 in _lbs3:
                        _scaled_gap = _bk3._char_gap_tj * _calib_scale if _bk3._char_gap_tj is not None else None
                        _s += make_bt_block(
                            _bk3.cids, _bk3.prefix,
                            _bk3.nat_x, _line_y3,
                            _bk3.td_dx, _bk3.td_dy,
                            gap_tj=_scaled_gap
                        )
                REPLS[_newline_repl_idx] = (_newline_erase_start, _newline_erase_end, _s)

            # ========== 应用替换 (从后往前) ==========
            print(f"\n=== 应用 {len(REPLS)} 个替换 ===")
            REPLS.sort(key=lambda x: x[0], reverse=True)
            print(f"--- REPLS dump (sorted, {len(REPLS)} items) ---")
            for _di, (_s, _e, _r) in enumerate(REPLS):
                _preview = _r[:40].replace('\n', '\\n').replace('\r', '\\r')
                print(f"  [{_di:2d}] [{_s:6d},{_e:6d}] len={len(_r):5d} '{_preview}'")
            new_stext = stext
            for s, e, r in REPLS:
                new_stext = new_stext[:s] + r + new_stext[e:]

            # 清理 ETBT 粘连
            new_stext = re.sub(r"ET[ \t\r\n]*BT", "ET\r\nBT", new_stext)
            new_stext = re.sub(r"([\d.eE]+)[ \t]+([\d.eE]+)[ \t]+([\d.eE]+)[ \t]+([\d.eE]+)[ \t]+([\d.eE]+)[ \t]+([\d.eE]+)[ \t]+([Tt][Mm])",
                               r"\1 \2 \3 \4 \5 \6 \7", new_stext)
            new_stext = re.sub(r"([\d.eE]+)[ \t]+([\d.eE]+)[ \t]+([Tt][Dd])", r"\1 \2 \3", new_stext)

            # ========== 写回 ==========
            if len(streams_raw) == 1:
                xr = streams_raw[0][0]
                if isinstance(xr, int):
                    doc.update_stream(xr, new_stext.encode('latin-1'))
                    print(f"  单流写回: xref={xr}, 长度={len(new_stext)}")
                else:
                    xr.update_bytes(new_stext.encode('latin-1'))
            else:
                first_xr = streams_raw[0][0]
                if isinstance(first_xr, int):
                    doc.update_stream(first_xr, new_stext.encode('latin-1'))
                    print(f"  多流合并写回: xref={first_xr}, 总长度={len(new_stext)}")
                else:
                    first_xr.update_bytes(new_stext.encode('latin-1'))
                for xr, _ in streams_raw[1:]:
                    if isinstance(xr, int):
                        doc.update_stream(xr, b"")
                        print(f"  清空多余流: xref={xr}")
                    else:
                        xr.update_bytes(b"")
                if isinstance(first_xr, int):
                    doc.xref_set_key(page.xref, "Contents", "%d 0 R" % first_xr)
                    print(f"  修复 page Contents → {first_xr} 0 R")

            replaced_count += 1
            page_details[page_num + 1] = 1

        except ValueError as _ve:
            skipped_pages.append(page_num + 1)
            continue
        except Exception as _e:
            skipped_pages.append(page_num + 1)
            continue

    doc.save(str(out_path), garbage=3, deflate=True)
    doc.close()
    return {
        "out_name": OUT_NAME,
        "replaced_count": replaced_count,
        "font_matched": font_matched,
        "font_fallback": font_fallback,
        "bold_count": bold_count,
        "underline_count": underline_count,
        "skipped_pages": skipped_pages,
        "page_details": page_details,
    }
