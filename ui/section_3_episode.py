# -*- coding: utf-8 -*-
import json
import re
import streamlit as st

from core.data_models import Project, Episode 
from core.prompt_builders import build_episode_prompt
from core.gemini_helpers import gemini_json 
from core.gemini_image import  gemini25_image_generate
from core.project_io import save_project
from core.text_utils import (
    clean_tts_text, extract_characters, _safe_name, capcut_sfx_name
)
from core.character_bible import ai_generate_character_bible, seed_from_text
from core.veo31_helpers import build_veo31_segments_prompt

# --- Optional TTS deps ---
try:
    from gtts import gTTS  # noqa: F401
    HAS_GTTS = True
except Exception:
    HAS_GTTS = False


# ===================== Helpers =====================

def _normalize_to_table(text: str) -> str:
    """
    Chuẩn hoá về bảng 3 cột + tự chèn gợi ý CapCut (FX + BGM) CHO TỪNG HÀNG,
    kể cả khi input đã là bảng Markdown.
    Không thêm/xoá hàng; chỉ bổ sung gợi ý vào cột Technical Notes nếu thiếu.
    """
    import re
    from core.text_utils import capcut_sfx_name  # gợi ý FX có sẵn

    if not text:
        return ""

    # Gợi ý BGM theo loại
    CAPCUT_BGM_MAP = {
        "narration":   "CapCut BGM: Calm Piano, Emotional Strings, Ambient Pad, Soft Wind …",
        "dialogue":    "CapCut BGM: Soft Piano, Gentle Guitar, Light Ambient, Romantic Background …",
        "voice system":"CapCut BGM: Digital Drone, Synth Pad, Sci-Fi Ambient, Echo Pulse …",
        "bgm":         "CapCut BGM: Epic Battle, Dark Ambient, Mystery Drone, Cinematic Rise …",
    }
    CAPCUT_FX_FALLBACK = "CapCut FX: Whoosh Short, Flash Transition, Riser Hit …"

    def _bgm_hint(ctype_lc: str) -> str:
        for k, v in CAPCUT_BGM_MAP.items():
            if k in ctype_lc:
                return v
        return ""

    def _augment_notes(ctype: str, notes: str) -> str:
        """Ghép thêm CapCut FX/BGM nếu notes chưa có."""
        c_lc = (ctype or "").strip().lower()
        notes = notes or ""
        if "capcut" in notes.lower():
            return notes  # đã có gợi ý, giữ nguyên

        fx_hint = capcut_sfx_name(ctype) or ""
        if "transition" in c_lc and not fx_hint:
            fx_hint = CAPCUT_FX_FALLBACK
        bgm_hint = _bgm_hint(c_lc)

        # Quy tắc: SFX/Transition → ưu tiên FX; Narration/Dialogue/BGM/Voice → BGM
        extra = fx_hint if any(k in c_lc for k in ["sound effects", "transition"]) else bgm_hint
        merged = (notes + (" " + extra if extra else "")).strip()
        return merged

    header_regex = r'^\|\s*Content Type\s*\|\s*Detailed Content\s*\|\s*Technical Notes\s*\|\s*$'
    has_header = bool(re.search(header_regex, text, flags=re.I | re.M))

    out = ["| Content Type | Detailed Content | Technical Notes |", "|---|---|---|"]

    if has_header:
        # Parse lại bảng hiện có -> augment notes cho từng hàng
        for ln in text.splitlines():
            line = ln.strip()
            if not line or line.startswith("|---"):
                continue
            if re.search(header_regex, line, flags=re.I):
                continue
            if not line.startswith("|"):
                continue

            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) < 3:
                continue
            ctype, content, notes = cols[:3]

            notes2 = _augment_notes(ctype, notes)
            # Escape '|' để không vỡ bảng
            content2 = (content or "").replace("|", r"\|")
            notes2 = (notes2 or "").replace("|", r"\|")
            out.append(f"| {ctype} | {content2} | {notes2} |")
        return "\n".join(out)

    # Input chưa là bảng → chuyển từng dòng + bơm gợi ý
    rows = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        ctype, content, notes = "Narration", s, ""
        low = s.lower()

        if low.startswith("narration:"):
            ctype, content = "Narration", s.split(":", 1)[1].strip()
        elif low.startswith("dialogue:") or low.startswith("dialog:"):
            ctype, content = "Dialogue", s.split(":", 1)[1].strip()
        elif low.startswith("voice system:") or low.startswith("system:"):
            ctype, content = "Voice System", s.split(":", 1)[1].strip()
        elif low.startswith("sfx:") or s.startswith("[SFX]"):
            ctype = "Sound Effects"
            content = s.split("]", 1)[1].strip() if s.startswith("[SFX]") and "]" in s else s.split(":", 1)[1].strip()
        elif low.startswith("bgm:"):
            ctype, content = "BGM", s.split(":", 1)[1].strip()
        elif low.startswith("transition:"):
            ctype, content = "Transition", s.split(":", 1)[1].strip()

        notes2 = _augment_notes(ctype, notes)
        rows.append((ctype, content, notes2))

    for ctype, content, notes in rows:
        out.append(f"| {ctype} | {str(content).replace('|', r'\\|')} | {str(notes).replace('|', r'\\|')} |")

    return "\n".join(out)


def _assets_list_from_json(data: dict) -> list:
    """
    Lấy list scene từ JSON trả về của model (FULL/ASSETS/TTS).
    """
    scenes = []
    try:
        raw = data.get("ASSETS") or data.get("assets") or []
        if isinstance(raw, list):
            for it in raw:
                scenes.append({
                    "scene": (it.get("scene") or "").strip(),
                    "image_prompt": (it.get("image_prompt") or "").strip(),
                    "sfx_prompt": (it.get("sfx_prompt") or "").strip(),
                    "characters": it.get("characters", []),
                })
    except Exception:
        pass
    return scenes


# --------- Scene suggestion from Narration (auto-split) ---------

def _parse_markdown_script_table(md: str):
    """Trả về list hàng: [{'ctype','content','notes'}] từ bảng 3 cột."""
    if not md:
        return []
    rows = []
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("|") or "|---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue
        c0, c1, c2 = parts[:3]
        # bỏ header
        header = c0.lower()
        if "content type" in header:
            continue
        rows.append({"ctype": c0.strip(), "content": c1.strip(), "notes": c2.strip()})
    return rows

_VI_LOCATION_HINTS = [
    r"\bTông\b", r"\bTộc\b", r"\bTông Môn\b", r"\bTông môn\b", r"\bMôn phái\b",
    r"\bTrường\b", r"\bDiễn Võ Trường\b", r"\bSảnh\b", r"\bĐiện\b", r"\bThành\b",
    r"\bSơn\b", r"\bCốc\b", r"\bCảnh\b", r"\bPhủ\b", r"\bTụ Luyện\b", r"\bLuyện Công\b",
    r"\bDưới ánh trăng\b", r"\bÁnh trăng\b", r"\bĐêm\b", r"\bRừng\b", r"\bVách đá\b",
]
_VI_ACTION_HINTS = [
    r"\bluyện\b", r"\bluyện kiếm\b", r"\bchém\b", r"\bvung\b", r"\bra\b",
    r"\bxé gió\b", r"\bkiếm khí\b", r"\bgầm\b", r"\bnổ\b", r"\btạt\b",
    r"\blướt\b", r"\bkhí tức\b", r"\bsát khí\b",
]

def _extract_names(text: str):
    # gom cụm từ viết hoa liên tiếp (VD: 'Diệp Minh', 'Thái Hư Tông')
    cand = re.findall(r"(?:[A-ZĐ][\wÀ-ỹ]+(?:\s+[A-ZĐ][\wÀ-ỹ]+)+)", text)
    return list(dict.fromkeys([c.strip() for c in cand]))  # unique order

def _match_any(patterns, text):
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

def _expand_narration_to_scenes(n_text: str):
    """Từ một câu Narration, đề xuất 2-3 scene: establishing / introduce char / action."""
    scenes = []
    text = (n_text or "").strip()
    names = _extract_names(text)
    has_location = _match_any(_VI_LOCATION_HINTS, text)
    has_action = _match_any(_VI_ACTION_HINTS, text)

    # 1) Establishing
    if has_location or any(("Tông" in n or "Trường" in n or "Điện" in n or "Thành" in n or "Sơn" in n or "Cốc" in n or "Phủ" in n) for n in names):
        place_name = None
        for n in names:
            if any(k in n for k in ["Tông", "Trường", "Điện", "Thành", "Sơn", "Cốc", "Phủ"]):
                place_name = n
                break
        title = place_name or "Thiết lập bối cảnh"
        img_prompt = f"Toàn cảnh {place_name or 'khu vực'} ban đêm; kiến trúc tu chân; sương mù mỏng; đèn lồng xa; ánh trăng lạnh; không khí huyền ảo."
        scenes.append({
            "scene": f"Establishing — {title}",
            "image_prompt": img_prompt,
            "sfx_prompt": "Wind Whoosh nhẹ, đêm tĩnh; tiếng côn trùng xa.",
            "characters": []
        })

    # 2) Introduce character
    char_name = None
    for n in names:
        if len(n.split()) == 2 and not any(k in n for k in ["Tông", "Trường", "Điện", "Thành", "Sơn", "Cốc", "Phủ"]):
            char_name = n
            break
    if char_name:
        img_prompt = f"{char_name} trong sân luyện; mồ hôi rịn; viền sáng ánh trăng; ánh mắt quyết liệt; medium/close shot; nền trường luyện mờ xa."
        scenes.append({
            "scene": f"Giới thiệu {char_name}",
            "image_prompt": img_prompt,
            "sfx_prompt": "Nhịp thở đều; vải khẽ động; bước chân xa.",
            "characters": [char_name]
        })

    # 3) Action
    if has_action:
        action_hint = "vung kiếm mạnh, đường kiếm xé gió; kiếm khí lóe sáng rạch bóng đêm; motion blur nhẹ; bụi bay."
        scenes.append({
            "scene": "Luyện kiếm — hành động",
            "image_prompt": action_hint,
            "sfx_prompt": "Sword Whoosh, Cloth Rustle; nhịp gấp dần.",
            "characters": [char_name] if char_name else []
        })

    if not scenes:
        scenes.append({"scene": "Narration — minh hoạ", "image_prompt": text, "sfx_prompt": "", "characters": []})
    return scenes

def _suggest_scenes_from_script(ep: Episode):
    """Đọc bảng 3 cột; mỗi Narration -> 2-3 scene đề xuất, không ghi đè."""
    rows = _parse_markdown_script_table(ep.script_text or "")
    suggestions = []
    for r in rows:
        if r["ctype"].lower().startswith("narration"):
            suggestions.extend(_expand_narration_to_scenes(r["content"]))
    uniq = []
    seen = set()
    for sc in suggestions:
        key = (sc["scene"], sc["image_prompt"])
        if key not in seen:
            seen.add(key)
            uniq.append(sc)
    return uniq


def _render_character_bible_block(model, proj: Project, ep: Episode, sidx: int, ep_idx: int):
    """
    Khối UI Character Bible: tạo bằng AI, seed từ FULL_SCRIPT/TTS, chỉnh nhanh & lưu.
    """
    st.subheader("📚 Character Bible")
    colA, colB, colC = st.columns([1, 1, 1])

    with colA:
        if st.button("🪄 Tạo Character Bible (AI)", key=f"cb_ai_{sidx}_{ep_idx}", disabled=not bool(model)):
            with st.spinner("Đang tạo Character Bible..."):
                cb = ai_generate_character_bible(
                    model,
                    project_name=proj.name,
                    idea=proj.idea,
                    chosen_storyline=proj.chosen_storyline,
                    outline=proj.seasons[sidx].outline,
                    max_chars=8
                )
                if cb and isinstance(cb, dict):
                    proj.character_bible = cb
                    save_project(proj)
                    st.success("Đã tạo Character Bible.")

    with colB:
        if st.button("✨ Seed từ FULL_SCRIPT/TTS", key=f"cb_seed_{sidx}_{ep_idx}"):
            base_cb = proj.character_bible or {"characters": []}
            merged = seed_from_text(base_cb, (ep.script_text or "") + "\n" + (ep.tts_text or ""))
            proj.character_bible = merged
            save_project(proj)
            st.success("Đã seed thêm tên nhân vật từ script/TTS.")

    with colC:
        if st.button("💾 Lưu Character Bible", key=f"cb_save_{sidx}_{ep_idx}"):
            save_project(proj)
            st.success("Đã lưu Character Bible.")

    # Bảng chỉnh nhanh
    cb = proj.character_bible or {"characters": []}
    chars = cb.get("characters", [])
    if not chars:
        st.info("Chưa có nhân vật. Hãy dùng hai nút ở trên để tạo/seed.")
        return

    for i, c in enumerate(chars, 1):
        with st.expander(f"{i}. {c.get('name','(chưa đặt tên)')}"):
            c["name"] = st.text_input("Name", value=c.get("name",""), key=f"cb_name_{sidx}_{ep_idx}_{i}")
            c["role"] = st.text_input("Role", value=c.get("role",""), key=f"cb_role_{sidx}_{ep_idx}_{i}")
            c["age"] = st.text_input("Age", value=c.get("age",""), key=f"cb_age_{sidx}_{ep_idx}_{i}")
            c["look"] = st.text_area("Look (ưu tiên nét Á Đông)", value=c.get("look",""), key=f"cb_look_{sidx}_{ep_idx}_{i}")
            c["hair"] = st.text_input("Hair", value=c.get("hair",""), key=f"cb_hair_{sidx}_{ep_idx}_{i}")
            c["outfit"] = st.text_input("Outfit", value=c.get("outfit",""), key=f"cb_outfit_{sidx}_{ep_idx}_{i}")
            c["color_theme"] = st.text_input("Color Theme", value=c.get("color_theme",""), key=f"cb_color_{sidx}_{ep_idx}_{i}")
            c["notes"] = st.text_area("Notes", value=c.get("notes",""), key=f"cb_notes_{sidx}_{ep_idx}_{i}")
            chars[i-1] = c
    proj.character_bible["characters"] = chars
# --------- Veo3 helpers ---------

def _gen_veo_for_scene(model, proj: Project, ep: Episode, sc: dict, max_segments: int = 3) -> dict:
    """
    Gọi Gemini để sinh segments Veo 3.1 từ scene.
    Mỗi segment tương ứng với 1 frame/keyframe chi tiết, có prompt đồng bộ hình ảnh.
    """
    sc_name = sc.get("scene", "Cảnh")
    scene_text = sc.get("image_prompt", "") or sc.get("sfx_prompt", "") or ep.summary
    char_in_scene = sc.get("characters", [])

    # 1️⃣ Tách keyframes tương ứng scene
    try:
        txt_block, frame_list = _compose_scene_image_prompts(proj, ep)
        # chỉ lấy frames thuộc scene hiện tại
        frames = [f for f in frame_list if f["scene"] == sc_name]
    except Exception:
        frames = []

    # 2️⃣ Nếu không có frame riêng, fallback 1 frame duy nhất
    if not frames:
        frames = [{
            "scene": sc_name,
            "frame": 1,
            "frame_name": f"{sc_name} — Frame 1",
            "characters": char_in_scene,
            "image_prompt": _styleize_image_prompt(
                base=scene_text,
                aspect_ratio=proj.aspect_ratio,
                donghua_style=proj.donghua_style,
                characters=char_in_scene,
                character_bible=proj.character_bible or {}
            )
        }]

    # 3️⃣ Sinh prompt tổng cho Veo (mô tả cách chia segment theo frame)
    veo_header_prompt = f"""
Bạn là đạo diễn tiền kỳ Veo 3.1.
Phân tích cảnh: **{sc_name}**
Từ các frame key sau, hãy tạo segments video liền mạch (mỗi frame = 1 segment ~8 giây).
Mỗi segment phải mô tả:
- hành động / biểu cảm nhân vật
- chuyển động camera
- ánh sáng, âm thanh / ambience
- continuity giữa frame trước & sau
- phong cách: donghua, 24fps cinematic

Danh sách keyframe:
{json.dumps([f["image_prompt"] for f in frames], ensure_ascii=False, indent=2)}

Trả về JSON duy nhất:
{{
  "scene": "{sc_name}",
  "segments": [
    {{
      "title": "ngắn gọn 3–7 từ",
      "duration_sec": 8,
      "characters": ["Tên A","Tên B"],
      "veo_prompt": "mô tả shot chi tiết theo frame này, continuity, 24fps, {proj.aspect_ratio}",
      "sfx": "ambience/SFX gợi ý",
      "notes": "continuity / camera / ánh sáng"
    }}
  ]
}}
    """.strip()

    # 4️⃣ Gọi Gemini model
    try:
        veo_result = gemini_json(model, veo_header_prompt)
    except Exception as e:
        sc["veo_error"] = str(e)
        veo_result = None

    # 5️⃣ Lưu kết quả vào scene
    sc["veo_prompt"] = veo_header_prompt
    if isinstance(veo_result, dict) and isinstance(veo_result.get("segments"), list):
        sc["veo31_segments"] = veo_result["segments"]
    else:
        sc["veo31_segments"] = []
        sc["veo_raw_response"] = veo_result

    return sc


# ====== build image prompts per scene (anchor frames) ======

def _styleize_image_prompt(base: str, aspect_ratio: str, donghua_style: bool, characters: list, character_bible: dict) -> str:
    """Hợp nhất image_prompt + style + nhân vật để render frame/ảnh neo (anchor) cho đồng bộ video."""
    base = (base or "").strip()
    char_descriptors = []
    if character_bible and character_bible.get("characters"):
        by_name = {c.get("name"): c for c in character_bible["characters"] if c.get("name")}
        for n in characters or []:
            c = by_name.get(n)
            if not c:
                continue
            piece = f"{c.get('name')}: {c.get('look','')}; hair {c.get('hair','')}; outfit {c.get('outfit','')}; colors {c.get('color_theme','')}"
            char_descriptors.append(piece)

    style = (
        "cel-shaded, clean lineart, Chinese donghua stylization, Asian facial features, "
        "natural black/dark hair unless specified, soft skin rendering, rich fabric texture, "
        "avoid photorealism, avoid western/European facial structure"
        if donghua_style else
        "cinematic stylized look, avoid hyper-realistic faces"
    )
    neg = "low quality, blurry, extra fingers, deformed hands, photorealistic, western/European facial structure"

    ar = aspect_ratio or "16:9"
    char_block = (" | ".join(char_descriptors)).strip()
    if char_block:
        char_block = f"Characters: {char_block}. "

    return (
        f"{char_block}{base}. "
        f"Style: {style}. "
        f"Shot: keyframe still for video sync; aspect ratio {ar}; 24fps context. "
        f"Negative: {neg}."
    )

def _compose_scene_image_prompts(proj: Project, ep: Episode):
    """
    Sinh danh sách prompt ảnh chi tiết (keyframes) từ 1 scene:
    - Mỗi Narration / Sound Effects → 1 frame riêng.
    - Bảo toàn characters + phong cách.
    """
    scenes = (ep.assets or {}).get("scenes", []) or []
    out_lines, out_json = [], []
    for i, sc in enumerate(scenes, 1):
        name = sc.get("scene", f"Cảnh {i}")
        base_text = sc.get("image_prompt", "") or sc.get("sfx_prompt", "") or ep.summary
        chars = sc.get("characters", [])

        # Lấy nội dung script tương ứng scene này để chia nhỏ frame
        raw_script = (ep.script_text or "")
        # tìm các dòng chứa từ khóa trong tên scene
        sublines = []
        for ln in raw_script.splitlines():
            if not ln.strip().startswith("|"):
                continue
            if any(k in ln for k in [name.split()[0], "Narration", "Sound Effects"]):
                sublines.append(ln)
        # nếu không có -> 1 frame
        if not sublines:
            sublines = [base_text]

        for j, ln in enumerate(sublines, 1):
            desc = ln
            if "|" in ln:
                parts = [p.strip() for p in ln.strip("|").split("|")]
                if len(parts) >= 2:
                    desc = parts[1]
            # hợp nhất style + char
            full_prompt = _styleize_image_prompt(
                base=desc,
                aspect_ratio=proj.aspect_ratio,
                donghua_style=proj.donghua_style,
                characters=chars,
                character_bible=proj.character_bible or {}
            )
            frame_name = f"{name} — Frame {j}"
            out_lines.append(
                f"### Scene {i}: {frame_name}\n"
                f"- Characters: {', '.join(chars) if chars else '(none)'}\n"
                f"- Image Prompt:\n{full_prompt}\n"
            )
            out_json.append({
                "scene_index": i,
                "scene": name,
                "frame": j,
                "frame_name": frame_name,
                "characters": chars,
                "image_prompt": full_prompt
            })
    return ("\n".join(out_lines)).strip(), out_json


# ===================== Main UI =====================

def render_section_3(model, use_tts: bool):
    st.header("✍️ Viết tập & Hậu kỳ")

    proj: Project = st.session_state.get("project")
    if not proj:
        st.info("Chưa có project. Hãy tạo project và chọn cốt truyện trước.")
        return
    if not proj.seasons:
        st.warning("Chưa có Mùa nào. Tạo Mùa ở tab Dàn Ý (Outline).")
        return

    sidx = st.session_state.get("current_season_idx", 0)
    cur_season = proj.seasons[sidx]

    st.subheader("Chọn tập")
    if not cur_season.episodes:
        st.warning("Mùa hiện tại chưa có tập. Hãy tạo dàn ý để sinh các tập.")
        return

    ep_indices = [f"Tập {ep.index:02d}" for ep in cur_season.episodes]
    ep_label = st.selectbox("Chọn tập để viết / chỉnh sửa", ep_indices, key=f"ep_select_s{sidx}")
    ep_idx = int(ep_label.split()[1]) - 1
    ep: Episode = cur_season.episodes[ep_idx]

    # ===== Sinh FULL/ASSETS/TTS =====
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✍️ Sinh nội dung tập (FULL/ASSETS/TTS)", disabled=not bool(model), key=f"write_ep_s{sidx}_{ep_idx}"):
            with st.spinner("Đang sinh kịch bản tập..."):
                prompt = build_episode_prompt(proj.chosen_storyline, ep.title, ep.summary, preset_name=proj.preset)
                data = gemini_json(model, prompt)

            if isinstance(data, dict):
                full_script = data.get("FULL_SCRIPT") or data.get("full_script") or ""
                assets_list = _assets_list_from_json(data)
                tts_text = data.get("TTS") or data.get("tts") or ""

                full_script = _normalize_to_table(full_script)
                ep.script_text = full_script
                ep.assets = {"scenes": assets_list}
                ep.tts_text = clean_tts_text(tts_text)

                # Seed nhân vật vào Character Bible
                try:
                    char_from_script = extract_characters(ep.script_text)
                    char_from_tts = extract_characters(ep.tts_text or "")
                    char_names_all = sorted(set(char_from_script) | set(char_from_tts))
                    if char_names_all:
                        proj.character_bible = proj.character_bible or {"characters": []}
                        existing = {c.get("name") for c in proj.character_bible.get("characters", [])}
                        for n in char_names_all:
                            if n and n not in existing:
                                proj.character_bible.setdefault("characters", []).append({
                                    "name": n, "role": "", "age": "",
                                    "look": "gương mặt Á Đông; tránh nét siêu thực Tây phương",
                                    "hair": "", "outfit": "", "color_theme": "", "notes": "donghua/cel-shaded"
                                })
                except Exception:
                    pass

                cur_season.episodes[ep_idx] = ep
                proj.seasons[sidx] = cur_season
                save_project(proj)
                st.success("Đã sinh kịch bản & lưu vào project.")
            else:
                st.error("AI trả về dữ liệu không đúng định dạng JSON.")

    with col2:
        if st.button("💾 Lưu lại thay đổi hiện tại", key=f"save_ep_s{sidx}_{ep_idx}"):
            cur_season.episodes[ep_idx] = ep
            proj.seasons[sidx] = cur_season
            save_project(proj)
            st.success("Đã lưu.")

    # ===== Tabs =====
    tabs = st.tabs(["📖 Truyện", "🖼️🎚️ Prompts & Veo 3.1", "🗣️ TTS & MP3", "📚 Character Bible"])

    # ---- Tab 1: Script
    with tabs[0]:
        ep.script_text = st.text_area(
            "Nội dung truyện (Markdown table 3 cột: Content Type | Detailed Content | Technical Notes)",
            value=ep.script_text, height=460, key=f"script_{sidx}_{ep_idx}"
        )
        with st.expander("👀 Xem dạng bảng 3 cột (preview)", expanded=False):
            try:
                st.markdown(ep.script_text or "", unsafe_allow_html=False)
            except Exception:
                st.info("Chưa có script hoặc script không phải Markdown table.")
        if st.button("🧹 Chuẩn hoá bảng 3 cột", key=f"normalize_{sidx}_{ep_idx}"):
            ep.script_text = _normalize_to_table(ep.script_text)
            st.session_state.project.seasons[sidx].episodes[ep_idx] = ep
            save_project(st.session_state.project)
            st.success("Đã chuẩn hoá bảng 3 cột.")
        if st.button("➕ Bơm nhanh SFX/BGM/Transition vào bảng"):
            ep.script_text = _normalize_to_table(ep.script_text or "")
            st.session_state.project.seasons[sidx].episodes[ep_idx] = ep
            save_project(st.session_state.project)
            st.success("Đã kiểm tra và chèn SFX/BGM/Transition (nếu thiếu).")
    # ---- Tab 2: Assets + Veo 3.1 + Image Prompts + Scene Suggestion
    with tabs[1]:
        scenes = (ep.assets or {}).get("scenes", [])
        st.subheader("Cảnh / Prompts")
        if not scenes:
            st.info("Chưa có scene. Hãy nhấn 'Sinh nội dung tập' trước hoặc tự thêm.")

        # Chỉnh từng scene
        for i, sc in enumerate(scenes, 1):
            with st.expander(f"Cảnh {i}: {sc.get('scene','(chưa có tên)')}"):
                scene_name = st.text_input(f"Tên cảnh {i}", value=sc.get("scene", f"Cảnh {i}"), key=f"scene_name_{sidx}_{ep.index}_{i}")
                imgp = st.text_area(f"Image Prompt {i}", value=sc.get("image_prompt", ""), key=f"imgp_{sidx}_{ep.index}_{i}")
                sfxp = st.text_area(f"SFX Prompt {i}", value=sc.get("sfx_prompt", ""), key=f"sfxp_{sidx}_{ep.index}_{i}")
                chars = st.text_input(f"Nhân vật xuất hiện {i} (phân tách bởi dấu phẩy)", value=", ".join(sc.get("characters", []) or []), key=f"chars_{sidx}_{ep.index}_{i}")
                sc["scene"] = scene_name
                sc["image_prompt"] = imgp
                sc["sfx_prompt"] = sfxp
                sc["characters"] = [c.strip() for c in chars.split(",") if c.strip()]
                scenes[i-1] = sc

        if st.button("💾 Lưu thay đổi Scenes", key=f"save_scenes_{sidx}_{ep_idx}"):
            ep.assets = {"scenes": scenes}
            st.session_state.project.seasons[sidx].episodes[ep_idx] = ep
            save_project(st.session_state.project)
            st.success("Đã lưu Scenes.")

        # ====== Gợi ý SCENES từ Narration (tự phân rã 1 Narration -> 2~3 cảnh)
        st.markdown("—")
        st.subheader("🧩 Gợi ý SCENES từ Narration")
        colS1, colS2 = st.columns([1, 1])
        with colS1:
            if st.button("➕ Đề xuất cảnh từ Narration (không ghi đè)"):
                suggested = _suggest_scenes_from_script(ep)
                if not suggested:
                    st.info("Không tìm thấy Narration phù hợp để tách cảnh.")
                else:
                    st.session_state["__scene_suggest_preview__"] = suggested
                    st.success(f"Đã đề xuất {len(suggested)} cảnh. Kiểm tra Preview bên phải.")
        with colS2:
            if st.button("✅ Thêm các cảnh đề xuất vào Scenes hiện tại"):
                suggested = st.session_state.get("__scene_suggest_preview__", [])
                if not suggested:
                    st.info("Chưa có danh sách đề xuất. Bấm nút đề xuất trước.")
                else:
                    merged = scenes[:]  # copy
                    existing_names = {sc.get("scene","") for sc in merged}
                    for sc in suggested:
                        name = sc.get("scene","")
                        if name in existing_names:
                            k = 2
                            new_name = f"{name} #{k}"
                            while new_name in existing_names:
                                k += 1
                                new_name = f"{name} #{k}"
                            sc["scene"] = new_name
                        existing_names.add(sc["scene"])
                        merged.append(sc)
                    ep.assets = {"scenes": merged}
                    st.session_state.project.seasons[sidx].episodes[ep_idx] = ep
                    save_project(st.session_state.project)
                    st.success(f"Đã thêm {len(suggested)} cảnh vào Scenes.")

        with st.expander("👀 Xem trước cảnh đề xuất từ Narration"):
            preview = st.session_state.get("__scene_suggest_preview__", [])
            if preview:
                for i, sc in enumerate(preview, 1):
                    st.markdown(f"**{i}. {sc.get('scene','(no name)')}**")
                    st.write(f"- Image: {sc.get('image_prompt','')}")
                    st.write(f"- SFX: {sc.get('sfx_prompt','')}")
                    st.write(f"- Characters: {', '.join(sc.get('characters', [])) or '(none)'}")
            else:
                st.caption("Chưa có đề xuất. Bấm nút ở trên để tạo.")

        # ===== NEW: Xuất prompt Ảnh theo cảnh (anchor frames)
        st.markdown("----")
        st.subheader("📸 Xuất prompt Ảnh theo Cảnh (anchor frames)")
        txt_block, json_block = _compose_scene_image_prompts(proj, ep)
        colP1, colP2 = st.columns(2)
        with colP1:
            st.caption("Shotlist & Image Prompts (Text)")
            st.code(txt_block or "Chưa có cảnh.", language="markdown")
        with colP2:
            st.caption("Shotlist & Image Prompts (JSON)")
            st.json(json_block or [])
        
        st.markdown("----")
        st.subheader("🧠 Tạo hình ảnh từng cảnh (Gemini 2.5)")

        colI1, colI2 = st.columns([1, 1])
        with colI1:
            img_model = st.selectbox(
                "Model ảnh",
                options=["gemini-2.5-flash-image",'gemini-2.5-flash'],
                index=0,
                help="Gemini 2.5 Flash Image (Nano Banana)."
            )
        with colI2:
            img_size = st.selectbox("Kích thước gợi ý", ["1024x576", "1280x720", "1024x1024", "720x1280"], index=0)

        if st.button("🪄 Tạo ảnh cho toàn bộ cảnh (Gemini 2.5)"):
            txt_block, json_block = _compose_scene_image_prompts(proj, ep)
            images = []
            for sc in json_block:
                with st.spinner(f"Đang tạo ảnh: {sc['scene']} …"):
                    img, msg = gemini25_image_generate(sc["image_prompt"], model_name=img_model, size_hint=img_size)
                    if img is not None:
                        st.image(img, caption=sc["scene"], use_column_width=True)
                        images.append({"scene": sc["scene"], "image": img})
                    else:
                        st.warning(f"{sc['scene']}: {msg}")
            st.session_state["__gemini_images__"] = images
            if images:
                st.success(f"Đã tạo {len(images)} ảnh bằng {img_model}.")



        # ===== Veo 3.1 (tạo segments) — dùng form + state để tránh "ẩn mất"
        st.markdown("---")
        st.subheader("🎬 Veo 3.1 (tạo segments)")

        # Khóa session theo mùa/tập để giữ state sau rerun
        veo_key_base = f"veo_{sidx}_{ep.index}"
        current_scenes = scenes or []
        if f"{veo_key_base}_scenes" not in st.session_state:
            st.session_state[f"{veo_key_base}_scenes"] = current_scenes
        else:
            if len(st.session_state[f"{veo_key_base}_scenes"]) != len(current_scenes):
                st.session_state[f"{veo_key_base}_scenes"] = current_scenes

        if f"{veo_key_base}_last_error" not in st.session_state:
            st.session_state[f"{veo_key_base}_last_error"] = None
        if f"{veo_key_base}_busy" not in st.session_state:
            st.session_state[f"{veo_key_base}_busy"] = False

        ss_scenes = st.session_state[f"{veo_key_base}_scenes"]
        n_scenes = len(ss_scenes)

        # Dùng FORM để tránh rerun giữa chừng
        with st.form(key=f"{veo_key_base}_form_all"):
            colV1, colV2 = st.columns([1, 1])
            with colV1:
                run_all = st.form_submit_button("⚡ Sinh Veo 3.1 cho TẤT CẢ cảnh", disabled=(not bool(model) or n_scenes == 0))
            with colV2:
                pick_min = 1
                pick_max = n_scenes if n_scenes > 0 else 1
                _disabled_one = (not bool(model) or n_scenes == 0)
                pick = st.number_input("Sinh riêng cảnh số", min_value=pick_min, max_value=pick_max, value=pick_min, step=1, key=f"{veo_key_base}_pick", disabled=_disabled_one)
                run_one = st.form_submit_button("▶️ Sinh Veo cho cảnh đã chọn", disabled=_disabled_one)

            if run_all or run_one:
                st.session_state[f"{veo_key_base}_busy"] = True
                st.session_state[f"{veo_key_base}_last_error"] = None
                try:
                    with st.spinner("Đang sinh Veo 3.1..."):
                        if run_all:
                            new_scenes = []
                            for idx_scene, sc in enumerate(ss_scenes, 1):
                                new_scenes.append(_gen_veo_for_scene(model, proj, ep, sc, max_segments=3))
                            ss_scenes = new_scenes
                        else:
                            if n_scenes == 0:
                                st.warning("Chưa có scene để sinh Veo.")
                            else:
                                idx = max(0, min(int(pick) - 1, n_scenes - 1))
                                ss_scenes[idx] = _gen_veo_for_scene(model, proj, ep, ss_scenes[idx], max_segments=3)

                        # Cập nhật vào session_state TRƯỚC
                        st.session_state[f"{veo_key_base}_scenes"] = ss_scenes

                        # Đồng bộ ngược vào project & lưu
                        ep.assets = {"scenes": ss_scenes}
                        st.session_state.project.seasons[sidx].episodes[ep.index - 1] = ep
                        save_project(st.session_state.project)
                        st.success("Đã sinh Veo 3.1.")
                except Exception as ex:
                    st.session_state[f"{veo_key_base}_last_error"] = ex
                    st.exception(ex)
                finally:
                    st.session_state[f"{veo_key_base}_busy"] = False

        # Hiển thị kết quả & lỗi (nếu có)
        err = st.session_state.get(f"{veo_key_base}_last_error")
        if err:
            st.error(f"Lỗi khi tạo Veo: {err}")

        for i, sc in enumerate(st.session_state[f"{veo_key_base}_scenes"], 1):
            with st.expander(f"🎬 Kết quả Veo — Cảnh {i}: {sc.get('scene','(chưa có tên)')}", expanded=False):
                if "veo_prompt" in sc:
                    st.caption("Prompt đã dùng:")
                    st.code(sc["veo_prompt"], language="markdown")
                segs = sc.get("veo31_segments") or []
                if segs:
                    st.caption("Segments (JSON):")
                    st.json({"segments": segs})
                else:
                    raw = sc.get("veo_raw_response")
                    if raw:
                        st.caption("Phản hồi thô (không đúng schema segments):")
                        st.json(raw)
                    else:
                        st.caption("Chưa có segments. Hãy bấm nút sinh Veo ở trên.")

    # ---- Tab 3: TTS
    with tabs[2]:
        st.subheader("TTS Text")
        ep.tts_text = st.text_area("Bản TTS (có thể chỉnh tay trước khi render giọng)", value=ep.tts_text or "", height=300, key=f"tts_{sidx}_{ep_idx}")
        if HAS_GTTS and use_tts:
            st.caption("gTTS khả dụng. (Tạo MP3 nên chạy cục bộ để tránh giới hạn thời gian).")
        else:
            st.caption("Bạn có thể copy TTS text để dùng với công cụ TTS khác.")

    # ---- Tab 4: Character Bible
    with tabs[3]:
        _render_character_bible_block(model, proj, ep, sidx, ep_idx)
