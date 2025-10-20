import streamlit as st
from core.data_models import Project, Season
from core.prompt_builders import build_storyline_prompt
from core.gemini_helpers import gemini_json, gemini_text
from core.presets import PRESETS
try:
    from core.presets import PRESET_ALIASES
except Exception:
    PRESET_ALIASES = {}

def _normalize_presets_for_ui_and_prompt(current_value):
    """Trả về (selected_list, all_options) từ giá trị hiện có (str/list/alias)."""
    all_options = list(PRESETS.keys())
    selected = []

    if isinstance(current_value, list):
        selected = [p for p in current_value if p in all_options]
    elif isinstance(current_value, str) and current_value.strip():
        if current_value in PRESET_ALIASES:
            selected = [p for p in PRESET_ALIASES[current_value] if p in all_options]
        else:
            parts = [p.strip() for p in current_value.split(",")]
            selected = [p for p in parts if p in all_options]
    return selected, all_options


def render_section_1(model):
    st.header("1) Nhập Ý Tưởng & Tạo 5 phương án")

    proj = st.session_state.get("project")

    # Tên dự án
    proj_name = st.text_input("Tên dự án", value=(proj.name if proj else "Truyen_XK_NT_HT"))

    # Preset (đa chọn ở UI, nhưng LƯU & GỬI BUILDER DƯỚI DẠNG CHUỖI)
    current_preset_value = (proj.preset if proj else "")
    ui_selected, all_options = _normalize_presets_for_ui_and_prompt(current_preset_value)
    preset_selected = st.multiselect("Preset", all_options, default=ui_selected)

    # Cập nhật live vào project (LƯU CHUỖI để tương thích các builder hiện tại)
    if proj:
        proj.preset = ", ".join(preset_selected)
        st.session_state.project = proj

    # Ý tưởng
    idea_default = proj.idea if proj else ""
    idea = st.text_area(
        "Ý tưởng khởi nguồn",
        height=120,
        value=idea_default,
        placeholder="VD: Nữ chính bị phản bội, rơi vào cổng thời không về triều đại giả tưởng..."
    )

    # Sinh 5 phương án
    if st.button("✨ Tạo 5 gợi ý cốt truyện", disabled=not bool(model and idea)):
        with st.spinner("Đang tạo gợi ý..."):
            preset_text = ", ".join(preset_selected)  # 🔑 luôn truyền chuỗi
            prompt = build_storyline_prompt(idea, preset_text)
            data = gemini_json(model, prompt)

            choices = []
            if isinstance(data, list) and data:
                for it in data[:5]:
                    title = (it.get("title") or "").strip()
                    summary = (it.get("summary") or it.get("content") or it.get("synopsis") or "").strip()
                    if summary:
                        if not title:
                            title = summary.split(".")[0][:60]
                        choices.append({"title": title, "summary": summary})
            else:
                text_raw = data.get("raw") if isinstance(data, dict) else ""
                if not text_raw:
                    text_raw = gemini_text(model, prompt)
                # Dùng lại parser bạn đang có:
                from core.ui_utils import parse_storyline_blocks as _p  # nếu bạn đã tách ra
                try:
                    choices = _p(text_raw)
                except Exception:
                    # fallback: dùng local
                    choices = parse_storyline_blocks(text_raw)

            if not choices:
                st.error("Không tách được phương án. Thử lại nhé.")
            else:
                st.session_state.storyline_choices = choices

    # Hiển thị & chọn phương án
    storyline_choices = st.session_state.get("storyline_choices", [])
    if storyline_choices:
        st.subheader("Chọn 1 phương án")
        labels = [f"PA{i+1}: {c['title']}" for i, c in enumerate(storyline_choices)]
        pick = st.radio("Phương án", labels, index=0, horizontal=True, key="pick_storyline")
        idx_pick = labels.index(pick)

        st.text_area("Tóm tắt phương án", value=storyline_choices[idx_pick]["summary"], height=260)

        if st.button("✅ Chọn phương án này"):
            list_as_text = [f"{c['title']}\n\n{c['summary']}" for c in storyline_choices]
            chosen_text = f"{storyline_choices[idx_pick]['title']}\n\n{storyline_choices[idx_pick]['summary']}"

            preset_text = ", ".join(preset_selected)  # 🔑 lưu chuỗi trong Project
            aspect_ratio = (proj.aspect_ratio if proj else "16:9")
            donghua_style = (proj.donghua_style if proj else True)
            character_bible = (proj.character_bible if proj else {"characters": []})

            st.session_state.project = Project(
                name=proj_name,
                idea=idea,
                preset=preset_text,  # 🔑 CHUỖI để các builder hiện tại không lỗi
                storyline_choices=list_as_text,
                chosen_storyline=chosen_text,
                seasons=[Season(season_index=1, episode_count=10, outline=[], episodes=[])],
                aspect_ratio=aspect_ratio,
                donghua_style=donghua_style,
                character_bible=character_bible
            )
            st.session_state.current_season_idx = 0
            st.success("Đã chọn cốt truyện. Chuyển qua bước dàn bài.")
