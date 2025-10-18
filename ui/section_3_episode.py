# -*- coding: utf-8 -*-
import json
import streamlit as st

from core.data_models import Project, Episode
from core.prompt_builders import build_episode_prompt
from core.gemini_helpers import gemini_json
from core.project_io import save_project
from core.text_utils import (
    clean_tts_text, extract_characters, _safe_name
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
    Chuẩn hoá nội dung về bảng Markdown 3 cột:
    | Content Type | Detailed Content | Technical Notes |
    |---|---|---|
    """
    import re
    if not text:
        return ""
    # Nếu đã có header đúng, giữ nguyên
    if re.search(
        r'^\|\s*Content Type\s*\|\s*Detailed Content\s*\|\s*Technical Notes\s*\|\s*$',
        text, flags=re.I | re.M
    ):
        return text

    lines = [
        "| Content Type | Detailed Content | Technical Notes |",
        "|---|---|---|",
    ]
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
            if s.startswith("[SFX]") and "]" in s:
                content = s.split("]", 1)[1].strip()
            else:
                content = s.split(":", 1)[1].strip()
        elif low.startswith("bgm:"):
            ctype, content = "BGM", s.split(":", 1)[1].strip()
        elif low.startswith("transition:"):
            ctype, content = "Transition", s.split(":", 1)[1].strip()
        content = content.replace("|", r"\|")
        notes = notes.replace("|", r"\|")
        lines.append(f"| {ctype} | {content} | {notes} |")
    return "\n".join(lines)


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


def _gen_veo_for_scene(model, proj: Project, ep: Episode, sc: dict, max_segments: int = 3) -> dict:
    """
    Gọi Gemini để sinh segments cho Veo 3.1 từ scene.
    Trả về scene đã được gắn:
      - "veo_prompt": prompt đã dùng
      - "veo31_segments": list segments (JSON) nếu sinh thành công
      - nếu không đúng schema thì gắn "veo_raw_response" để dev kiểm tra
    """
    sc_name = sc.get("scene", "Cảnh")
    scene_text = sc.get("image_prompt", "") or sc.get("sfx_prompt", "") or ep.summary
    char_in_scene = sc.get("characters", [])

    veo_prompt = build_veo31_segments_prompt(
        ep_title=ep.title,
        scene_name=sc_name,
        scene_text=scene_text,
        max_segments=max_segments,
        aspect_ratio=proj.aspect_ratio,
        donghua_style=proj.donghua_style,
        character_bible=proj.character_bible,
        characters_in_scene=char_in_scene
    )
    sc["veo_prompt"] = veo_prompt

    # Gọi model và bắt lỗi rõ ràng
    try:
        data = gemini_json(model, veo_prompt)
        if isinstance(data, dict) and isinstance(data.get("segments"), list):
            sc["veo31_segments"] = data["segments"]
        else:
            sc["veo31_segments"] = []
            sc["veo_raw_response"] = data
    except Exception as e:
        sc["veo31_segments"] = []
        sc["veo_error"] = str(e)
        raise
    return sc


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
        if st.button(
            "✍️ Sinh nội dung tập (FULL/ASSETS/TTS)",
            disabled=not bool(model),
            key=f"write_ep_s{sidx}_{ep_idx}"
        ):
            with st.spinner("Đang sinh kịch bản tập..."):
                prompt = build_episode_prompt(
                    proj.chosen_storyline,
                    ep.title,
                    ep.summary,
                    preset_name=proj.preset
                )
                data = gemini_json(model, prompt)

            if isinstance(data, dict):
                full_script = data.get("FULL_SCRIPT") or data.get("full_script") or ""
                assets_list = _assets_list_from_json(data)
                tts_text = data.get("TTS") or data.get("tts") or ""

                # Chuẩn hoá bảng 3 cột
                full_script = _normalize_to_table(full_script)

                ep.script_text = full_script
                ep.assets = {"scenes": assets_list}  # luôn là dict
                ep.tts_text = clean_tts_text(tts_text)

                # Seed tên nhân vật để dày Character Bible
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
    tabs = st.tabs(["📖 Truyện", "🖼️🎚️ Prompts Ảnh & Âm Thanh", "🗣️ TTS & MP3", "📚 Character Bible"])

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

    # ---- Tab 2: Assets + Veo 3.1
    with tabs[1]:
        scenes = (ep.assets or {}).get("scenes", [])
        st.subheader("Cảnh / Prompts")
        if not scenes:
            st.info("Chưa có scene. Hãy nhấn 'Sinh nội dung tập' trước hoặc tự thêm.")

        # Chỉnh từng scene
        for i, sc in enumerate(scenes, 1):
            with st.expander(f"Cảnh {i}: {sc.get('scene','(chưa có tên)')}"):
                scene_name = st.text_input(
                    f"Tên cảnh {i}", value=sc.get("scene", f"Cảnh {i}"),
                    key=f"scene_name_{sidx}_{ep.index}_{i}"
                )
                imgp = st.text_area(
                    f"Image Prompt {i}", value=sc.get("image_prompt", ""),
                    key=f"imgp_{sidx}_{ep.index}_{i}"
                )
                sfxp = st.text_area(
                    f"SFX Prompt {i}", value=sc.get("sfx_prompt", ""),
                    key=f"sfxp_{sidx}_{ep.index}_{i}"
                )
                chars = st.text_input(
                    f"Nhân vật xuất hiện {i} (phân tách bởi dấu phẩy)",
                    value=", ".join(sc.get("characters", []) or []),
                    key=f"chars_{sidx}_{ep.index}_{i}"
                )
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

        # ===== Veo 3.1 (tạo segments) — dùng form + state để tránh "ẩn mất"
        st.markdown("---")
        st.subheader("🎬 Veo 3.1 (tạo segments)")

        # Khóa session theo mùa/tập để giữ state sau rerun
        veo_key_base = f"veo_{sidx}_{ep.index}"
        if f"{veo_key_base}_scenes" not in st.session_state:
            st.session_state[f"{veo_key_base}_scenes"] = scenes or []
        if f"{veo_key_base}_last_error" not in st.session_state:
            st.session_state[f"{veo_key_base}_last_error"] = None
        if f"{veo_key_base}_busy" not in st.session_state:
            st.session_state[f"{veo_key_base}_busy"] = False

        ss_scenes = st.session_state[f"{veo_key_base}_scenes"]

        # Dùng FORM để tránh rerun giữa chừng
        with st.form(key=f"{veo_key_base}_form_all"):
            colV1, colV2 = st.columns([1, 1])
            with colV1:
                run_all = st.form_submit_button("⚡ Sinh Veo 3.1 cho TẤT CẢ cảnh", disabled=not bool(model))
            with colV2:
                pick = st.number_input(
                    "Sinh riêng cảnh số",
                    min_value=1, max_value=max(1, len(ss_scenes)) if ss_scenes else 1,
                    value=1, step=1, key=f"{veo_key_base}_pick"
                )
                run_one = st.form_submit_button("▶️ Sinh Veo cho cảnh đã chọn", disabled=not bool(model))

            if run_all or run_one:
                st.session_state[f"{veo_key_base}_busy"] = True
                st.session_state[f"{veo_key_base}_last_error"] = None
                try:
                    with st.spinner("Đang sinh Veo 3.1..."):
                        if run_all:
                            new_scenes = []
                            for i, sc in enumerate(ss_scenes, 1):
                                new_scenes.append(_gen_veo_for_scene(model, proj, ep, sc, max_segments=3))
                            ss_scenes = new_scenes
                        else:
                            i = int(pick) - 1
                            ss_scenes[i] = _gen_veo_for_scene(model, proj, ep, ss_scenes[i], max_segments=3)

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
        ep.tts_text = st.text_area(
            "Bản TTS (có thể chỉnh tay trước khi render giọng)",
            value=ep.tts_text or "", height=300, key=f"tts_{sidx}_{ep_idx}"
        )
        if HAS_GTTS and use_tts:
            st.caption("gTTS khả dụng. (Tạo MP3 nên chạy cục bộ để tránh giới hạn thời gian).")
        else:
            st.caption("Bạn có thể copy TTS text để dùng với công cụ TTS khác.")

    # ---- Tab 4: Character Bible
    with tabs[3]:
        _render_character_bible_block(model, proj, ep, sidx, ep_idx)
