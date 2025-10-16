import streamlit as st
from core.data_models import Project, Episode
from core.prompt_builders import build_episode_prompt
from core.gemini_helpers import gemini_json
from core.project_io import save_project
from core.text_utils import clean_tts_text, parse_tts_lines, extract_characters, suggest_styles, _safe_name
from core.character_bible import ai_generate_character_bible, seed_from_text
from core.veo31_helpers import build_veo31_segments_prompt

try:
    from gtts import gTTS
except Exception:
    gTTS = None

try:
    from pydub import AudioSegment  # optional
except Exception:
    AudioSegment = None


# --- NEW: helper để bảo đảm default ⊆ options ---
def _sanitize_multiselect_options(options, default_list):
    """
    Trả về (options_sanitized, default_sanitized):
    - options_sanitized = options ∪ default_list, bỏ rỗng, unique
    - default_sanitized = chỉ giữ phần tử có trong options_sanitized
    - Ưu tiên: default nằm đầu, còn lại sắp xếp alpha
    """
    options = list(options or [])
    default_list = list(default_list or [])

    base_set = set([x for x in options if x])
    extra = [x for x in default_list if x and x not in base_set]
    merged = options + extra

    # Duy trì thứ tự: default trước (giữ thứ tự xuất hiện), còn lại alpha
    # 1) unique giữ theo thứ tự hiện tại
    seen = set()
    merged_unique = []
    for x in merged:
        if x and x not in seen:
            merged_unique.append(x)
            seen.add(x)

    # 2) tách default và phần còn lại
    default_sanitized = [x for x in default_list if x in merged_unique]
    rest = [x for x in merged_unique if x not in default_sanitized]
    rest_sorted = sorted(rest, key=lambda s: s.lower())

    options_sanitized = default_sanitized + rest_sorted
    return options_sanitized, default_sanitized


def render_section_3(model, use_tts: bool):
    st.header("3) Viết nội dung cho từng tập — theo Mùa đang chọn")

    proj: Project | None = st.session_state.project
    if not proj or not proj.seasons:
        st.info("Chưa có Mùa/Outline. Vào bước 2 trước nhé.")
        return

    sidx = st.session_state.current_season_idx
    cur_season = proj.seasons[sidx]

    if not cur_season.outline:
        st.info("Mùa hiện tại chưa có dàn bài. Hãy tạo ở bước 2.")
        return

    # Project-level: Veo & Character Bible config
    with st.expander("📌 Tuỳ chọn nâng cao (Veo & Nhân vật)"):
        colx, coly = st.columns(2)
        with colx:
            proj.aspect_ratio = st.selectbox(
                "Tỉ lệ khung hình mặc định (Veo)",
                ["16:9", "9:16"],
                index=(0 if proj.aspect_ratio == "16:9" else 1),
            )
        with coly:
            proj.donghua_style = st.toggle(
                "Ưu tiên phong cách hoạt hình Trung Quốc (donghua)",
                value=proj.donghua_style,
            )

        st.caption("**Character Bible** — mô tả nhân vật (JSON).")
        cb_text = st.text_area(
            "Character Bible (JSON)",
            height=220,
            value=__import__("json").dumps(proj.character_bible, ensure_ascii=False, indent=2),
        )
        try:
            cb_parsed = __import__("json").loads(cb_text) if cb_text.strip() else {"characters": []}
            if "characters" not in cb_parsed:
                cb_parsed = {"characters": []}
        except Exception:
            cb_parsed = proj.character_bible
            st.warning("JSON Character Bible không hợp lệ. Giữ giá trị cũ.")

        col_cb1, col_cb2, col_cb3 = st.columns(3)
        with col_cb1:
            if st.button("🪄 Tạo Character Bible (AI)"):
                if not model:
                    st.warning("Chưa khởi tạo model.")
                else:
                    some_outline = cur_season.outline if cur_season.outline else None
                    data_cb = ai_generate_character_bible(
                        model, proj.name, proj.idea, proj.chosen_storyline, some_outline, 6
                    )
                    if data_cb.get("characters"):
                        proj.character_bible = data_cb
                        st.success("Đã tạo Character Bible từ AI.")
                    else:
                        st.error("Model không trả JSON hợp lệ.")
        with col_cb2:
            if st.button("✨ Seed nhân vật từ TTS/Script (tập đang chọn nếu có)"):
                ep_select_key = f"ep_select_s{sidx}"
                def_ep_idx = 0
                if st.session_state.get(ep_select_key):
                    try:
                        def_ep_idx = int(str(st.session_state.get(ep_select_key)).split()[1]) - 1
                    except Exception:
                        def_ep_idx = 0
                ep = cur_season.episodes[def_ep_idx]
                seed_text = ep.tts_text or ep.script_text
                proj.character_bible = seed_from_text(cb_parsed, seed_text)
                st.success("Đã seed tên nhân vật từ TTS/Script.")
        with col_cb3:
            if st.button("💾 Lưu Character Bible"):
                proj.character_bible = cb_parsed
                save_project(proj)
                st.success("Đã lưu Character Bible.")

        # apply to session
        st.session_state.project = proj

    # --- Episode selector ---
    ep_indices = [f"Tập {ep.index:02d}" for ep in cur_season.episodes]
    ep_label = st.selectbox("Chọn tập để viết / chỉnh sửa", ep_indices, key=f"ep_select_s{sidx}")
    ep_idx = int(ep_label.split()[1]) - 1
    ep: Episode = cur_season.episodes[ep_idx]

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "✍️ Sinh nội dung tập (FULL/ASSETS/TTS)",
            disabled=not bool(model),
            key=f"write_ep_s{sidx}_{ep_idx}",
        ):
            with st.spinner("Đang viết tập..."):
                prompt = build_episode_prompt(proj.chosen_storyline, ep.title, ep.summary)
                data = gemini_json(model, prompt)
                if isinstance(data, dict):
                    ep.script_text = (
                        data.get("FULL_SCRIPT")
                        or data.get("full_script")
                        or __import__("json").dumps(data, ensure_ascii=False)
                    )
                    assets = data.get("ASSETS") or data.get("assets") or []
                    tts_txt = data.get("TTS") or data.get("tts") or ""
                else:
                    ep.script_text = str(data)
                    assets = []
                    tts_txt = ""
                if isinstance(assets, list):
                    ep.assets = {"scenes": assets}
                elif isinstance(assets, dict):
                    ep.assets = assets
                else:
                    ep.assets = {"scenes": []}
                ep.tts_text = tts_txt or ep.script_text
                cur_season.episodes[ep_idx] = ep
                proj.seasons[sidx] = cur_season
                save_project(proj)
                st.success("Đã sinh nội dung tập.")
    with col2:
        if st.button("💾 Lưu tập hiện tại", key=f"save_ep_s{sidx}_{ep_idx}"):
            cur_season.episodes[ep_idx] = ep
            proj.seasons[sidx] = cur_season
            save_project(proj)
            st.success("Đã lưu.")

    tabs = st.tabs(["📖 Truyện", "🖼️🎚️ Prompts Ảnh & Âm Thanh", "🗣️ TTS & MP3"])

    # Tab 1
    with tabs[0]:
        ep.script_text = st.text_area(
            "Nội dung truyện (có thể chỉnh tay)",
            value=ep.script_text,
            height=500,
            key=f"script_{sidx}_{ep_idx}",
        )
        st.caption("Tip: Giữ phong cách audio-first, phân cảnh rõ, có thoại Hệ Thống.")

    # Tab 2 — Veo 3.1
    with tabs[1]:
        scenes = ep.assets.get("scenes", [])
        new_scenes = []

        st.markdown("#### 🎬 Veo 3.1 — Tạo video prompts (mỗi clip 8s)")
        col_veo_a, col_veo_b = st.columns(2)
        with col_veo_a:
            ar_local = st.selectbox(
                "Tỉ lệ khung cho tập này",
                ["16:9", "9:16"],
                index=(0 if proj.aspect_ratio == "16:9" else 1),
                key=f"ar_ep_{sidx}_{ep.index}",
            )
        with col_veo_b:
            donghua_local = st.toggle(
                "Phong cách hoạt hình Trung Quốc (donghua) cho tập",
                value=proj.donghua_style,
                key=f"donghua_ep_{sidx}_{ep.index}",
            )

        # Lấy danh sách nhân vật từ Character Bible
        char_names_all = [c.get("name", "") for c in (proj.character_bible.get("characters", []) if proj else [])]
        char_names_all = [x for x in char_names_all if x]  # bỏ rỗng

        max_segments_all = st.number_input(
            "Số clip 8s tối đa / cảnh", min_value=1, max_value=6, value=3, step=1, key=f"veo_maxseg_all_{ep.index}"
        )
        if st.button("⚡ Sinh Veo 3.1 cho TẤT CẢ cảnh", disabled=not bool(model), key=f"veo_all_{ep.index}"):
            if not scenes:
                st.warning("Chưa có scene để sinh Veo.")
            else:
                with st.spinner("Đang sinh prompts Veo 3.1 cho tất cả cảnh…"):
                    new_scenes_all = []
                    for i, sc in enumerate(scenes, 1):
                        sc_name = sc.get("scene", f"Cảnh {i}")
                        scene_text = sc.get("image_prompt", "") or sc.get("sfx_prompt", "") or ep.summary
                        char_in_scene = sc.get("characters", [])

                        # 👇 đảm bảo default nằm trong options
                        opts_scene, default_scene = _sanitize_multiselect_options(char_names_all, char_in_scene)
                        # (không vẽ widget ở đây — chỉ dùng để tránh crash khi sinh prompt theo default)

                        pv = build_veo31_segments_prompt(
                            ep.title,
                            sc_name,
                            scene_text,
                            max_segments=max_segments_all,
                            aspect_ratio=ar_local,
                            donghua_style=bool(donghua_local),
                            character_bible=proj.character_bible,
                            characters_in_scene=default_scene,
                        )
                        veo_data = gemini_json(model, pv)
                        if isinstance(veo_data, dict) and "segments" in veo_data:
                            sc["veo31"] = veo_data
                        else:
                            sc["veo31"] = {
                                "scene": sc_name,
                                "segments": [{
                                    "title": "Một shot 8s",
                                    "duration_sec": 8,
                                    "characters": default_scene,
                                    "veo_prompt": scene_text[:400] + f" | stylized, 24fps, {ar_local}",
                                    "sfx": "ambience phù hợp bối cảnh",
                                    "notes": "fallback"
                                }]
                            }
                        new_scenes_all.append(sc)
                    ep.assets["scenes"] = new_scenes_all
                    cur_season.episodes[ep_idx] = ep
                    proj.seasons[sidx] = cur_season
                    save_project(proj)
                    st.success("Đã sinh Veo 3.1 cho toàn bộ cảnh.")

        if not scenes:
            st.info("Chưa có scene. Hãy nhấn 'Sinh nội dung tập' trước hoặc tự thêm.")

        for i, sc in enumerate(scenes, 1):
            with st.expander(f"Cảnh {i}: {sc.get('scene','(chưa có tên)')}"):
                scene_name = st.text_input(
                    f"Tên cảnh {i}", value=sc.get("scene", f"Cảnh {i}"), key=f"scene_name_{sidx}_{ep.index}_{i}"
                )
                imgp = st.text_area(
                    f"Image Prompt {i}", value=sc.get("image_prompt", ""), key=f"imgp_{sidx}_{ep.index}_{i}"
                )
                sfxp = st.text_area(
                    f"SFX Prompt {i}", value=sc.get("sfx_prompt", ""), key=f"sfxp_{sidx}_{ep.index}_{i}"
                )

                # --- Scene-level characters (FIXED: sanitize options/default) ---
                scene_defaults = sc.get("characters", [])
                opts_scene, default_scene = _sanitize_multiselect_options(char_names_all, scene_defaults)
                picked = st.multiselect(
                    f"Nhân vật xuất hiện (Cảnh {i})",
                    options=opts_scene,
                    default=default_scene,
                    key=f"chars_scene_{sidx}_{ep.index}_{i}",
                )
                sc["characters"] = picked

                # --- Veo 3.1 per scene ---
                st.markdown("**🎬 Veo 3.1 (mỗi clip tối đa 8s)**")
                max_segments = st.number_input(
                    f"Số clip 8s tối đa (Cảnh {i})", min_value=1, max_value=6, value=3, step=1,
                    key=f"veo_maxseg_{sidx}_{ep.index}_{i}"
                )
                if st.button(
                    f"⚡ Sinh Veo cho Cảnh {i}", disabled=not bool(model), key=f"veo_one_{sidx}_{ep.index}_{i}"
                ):
                    with st.spinner(f"Đang sinh Veo 3.1 cho Cảnh {i}…"):
                        src_text = imgp or sfxp or ep.summary
                        pv = build_veo31_segments_prompt(
                            ep.title,
                            scene_name,
                            src_text,
                            max_segments=max_segments,
                            aspect_ratio=ar_local,
                            donghua_style=bool(donghua_local),
                            character_bible=proj.character_bible,
                            characters_in_scene=picked,
                        )
                        veo_data = gemini_json(model, pv)
                        if isinstance(veo_data, dict) and "segments" in veo_data:
                            sc["veo31"] = veo_data
                        else:
                            sc["veo31"] = {
                                "scene": scene_name,
                                "segments": [{
                                    "title": "Một shot 8s",
                                    "duration_sec": 8,
                                    "characters": picked,
                                    "veo_prompt": (src_text[:400] + f" | stylized, 24fps, {ar_local}"),
                                    "sfx": "ambience phù hợp bối cảnh",
                                    "notes": "fallback"
                                }]
                            }
                        st.success(f"Đã sinh Veo 3.1 cho Cảnh {i}.")

                # Hiển thị các segment (FIXED: sanitize options/default cho từng segment)
                veo_obj = sc.get("veo31", {})
                segments = veo_obj.get("segments", [])
                if segments:
                    st.caption("Các clip 8s đã gợi ý:")
                    merged_prompts = []
                    for si, seg in enumerate(segments, 1):
                        with st.expander(f"Clip {si}: {seg.get('title','(chưa có)')} — {seg.get('duration_sec',8)}s", expanded=False):
                            seg["title"] = st.text_input(
                                f"Tiêu đề clip {si}", value=seg.get("title",""), key=f"veo_title_{sidx}_{ep.index}_{i}_{si}"
                            )
                            seg["duration_sec"] = st.number_input(
                                f"Thời lượng clip {si} (<=8s)",
                                min_value=1, max_value=8, value=int(seg.get("duration_sec",8)),
                                key=f"veo_dur_{sidx}_{ep.index}_{i}_{si}",
                            )
                            seg_chars = seg.get("characters", sc.get("characters", []))
                            opts_seg, default_seg = _sanitize_multiselect_options(char_names_all, seg_chars)
                            seg["characters"] = st.multiselect(
                                f"Nhân vật (clip {si})",
                                options=opts_seg,
                                default=default_seg,
                                key=f"veo_chars_{sidx}_{ep.index}_{i}_{si}",
                            )
                            seg["veo_prompt"] = st.text_area(
                                f"Veo prompt {si}", value=seg.get("veo_prompt",""), height=160,
                                key=f"veo_prompt_{sidx}_{ep.index}_{i}_{si}"
                            )
                            seg["sfx"] = st.text_area(
                                f"SFX/ambience {si}", value=seg.get("sfx",""), height=80,
                                key=f"veo_sfx_{sidx}_{ep.index}_{i}_{si}"
                            )
                            seg["notes"] = st.text_area(
                                f"Ghi chú {si}", value=seg.get("notes",""), height=60,
                                key=f"veo_notes_{sidx}_{ep.index}_{i}_{si}"
                            )
                        merged_prompts.append(
                            f"# {scene_name} — Clip {si} ({seg.get('duration_sec',8)}s)\n"
                            f"[Characters] {', '.join(seg.get('characters', []))}\n"
                            f"{seg.get('veo_prompt','')}\n[SFX] {seg.get('sfx','')}"
                        )
                    sc["veo31"] = {"scene": scene_name, "segments": segments}
                    st.text_area(
                        "📋 Copy-all Veo prompts (cảnh này)",
                        value="\n\n---\n".join(merged_prompts),
                        height=200,
                        key=f"veo_copy_{sidx}_{ep.index}_{i}",
                    )

                new_scenes.append({
                    "scene": scene_name,
                    "image_prompt": imgp,
                    "sfx_prompt": sfxp,
                    **({"characters": sc.get("characters")} if sc.get("characters") else {}),
                    **({"veo31": sc.get("veo31")} if sc.get("veo31") else {})
                })

        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ Thêm cảnh trống", key=f"add_scene_{sidx}_{ep_idx}"):
                new_scenes.append({"scene": f"Cảnh {len(new_scenes)+1}", "image_prompt": "", "sfx_prompt": ""})
        with c2:
            if st.button("💾 Lưu Prompts cảnh", key=f"save_scenes_{sidx}_{ep_idx}"):
                ep.assets["scenes"] = new_scenes
                cur_season.episodes[ep_idx] = ep
                proj.seasons[sidx] = cur_season
                save_project(proj)
                st.success("Đã lưu danh sách cảnh.")
        if new_scenes:
            ep.assets["scenes"] = new_scenes

        st.json(ep.assets)

    # Tab 3 — TTS
    with tabs[2]:
        st.caption("Trước khi đọc TTS, hệ thống sẽ lọc bỏ **, SFX, heading… và tách thoại nhân vật.")
        raw = st.text_area(
            "Văn bản đầu vào TTS (có thể khác với Truyện)",
            value=ep.tts_text or ep.script_text,
            height=260,
            key=f"tts_raw_{sidx}_{ep_idx}",
        )
        cleaned = clean_tts_text(raw)
        if st.toggle("Hiển thị văn bản đã làm sạch", key=f"show_clean_{sidx}_{ep_idx}"):
            st.text_area("Đã làm sạch", value=cleaned, height=160, key=f"tts_clean_{sidx}_{ep_idx}")

        if st.button("🔎 Phân tích thoại & Nhân vật", key=f"parse_tts_{sidx}_{ep_idx}"):
            st.session_state.parsed_tts = parse_tts_lines(cleaned)
            st.success(f"Đã tách {len(st.session_state.parsed_tts)} dòng.")

        parsed = st.session_state.get("parsed_tts", [])
        if parsed:
            chars = extract_characters(parsed)
            st.write("**Nhân vật phát hiện:**", ", ".join(chars) if chars else "(Chỉ có Người Dẫn Chuyện)")
            style_suggest = suggest_styles(chars)

            if "tts_voices" not in st.session_state:
                st.session_state.tts_voices = {"Người Dẫn Chuyện": {"voice": "default", "style": "Kể chậm rãi, ấm"}}
            cfg = st.session_state.tts_voices

            with st.expander("Người Dẫn Chuyện"):
                cfg.setdefault("Người Dẫn Chuyện", {"voice": "default", "style": "Kể chậm rãi, ấm"})
                cfg["Người Dẫn Chuyện"]["voice"] = st.selectbox(
                    "Giọng", ["default", "female_soft", "male_deep"], index=0, key=f"nar_voice_{sidx}_{ep_idx}"
                )
                cfg["Người Dẫn Chuyện"]["style"] = st.text_input(
                    "Giọng điệu", value=cfg["Người Dẫn Chuyện"].get("style", "Kể chậm rãi, ấm"),
                    key=f"nar_style_{sidx}_{ep_idx}"
                )

            for ch in chars:
                with st.expander(ch):
                    default_style = style_suggest.get(ch, "Trung tính")
                    cur = cfg.get(ch, {
                        "voice": ("female_soft" if "Nữ" in ch else ("robotic" if ch == "HỆ THỐNG" else "male_deep")),
                        "style": default_style
                    })
                    cfg[ch] = cur
                    options = ["female_soft", "male_deep", "robotic", "youth_bright", "mature_calm"]
                    idx_opt = options.index(cur["voice"]) if cur["voice"] in options else 0
                    cfg[ch]["voice"] = st.selectbox(
                        "Giọng", options, index=idx_opt, key=f"voice_{sidx}_{ep_idx}_{ch}"
                    )
                    cfg[ch]["style"] = st.text_input(
                        "Giọng điệu", value=cur.get("style", default_style), key=f"style_{sidx}_{ep_idx}_{ch}"
                    )

            st.info("gTTS chỉ 1 giọng. Để đa giọng thực sự, dùng ElevenLabs/Azure + pydub.")

            colr1, colr2 = st.columns(2)
            with colr1:
                if use_tts and st.button("🎙️ Render MP3", key=f"render_tts_{sidx}_{ep_idx}"):
                    with st.spinner("Đang render TTS…"):
                        if gTTS is None:
                            st.error("gTTS chưa được cài. pip install gtts")
                        else:
                            merged_text = " ".join([it["text"] for it in parsed])
                            if not merged_text.strip():
                                st.warning("Không có văn bản để đọc.")
                            else:
                                out_path = (
                                    __import__("pathlib").Path(__file__).resolve().parents[1] / "projects" /
                                    f"{_safe_name(proj.name)}_S{sidx+1:02d}_E{ep.index:02d}.mp3"
                                )
                                gTTS(text=merged_text, lang="vi").save(str(out_path))
                                st.audio(str(out_path)); st.success(f"Đã xuất: {out_path.name}")

            with colr2:
                if AudioSegment is None:
                    st.caption("(Tuỳ chọn) Cài pydub + ffmpeg để ghép phân đoạn đa giọng.")
                else:
                    st.caption("pydub đã sẵn sàng.")

    # apply back
    cur_season.episodes[ep_idx] = ep
    proj.seasons[sidx] = cur_season
    st.session_state.project = proj
