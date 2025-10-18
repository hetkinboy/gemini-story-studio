import streamlit as st
from core.data_models import Project, Season
from core.prompt_builders import build_storyline_prompt
from core.gemini_helpers import gemini_json, gemini_text

def parse_storyline_blocks(raw_text: str):
    import re
    if not raw_text: return []
    lines = [ln.rstrip() for ln in raw_text.splitlines()]
    header_pat = re.compile(r"^\s*(?:Phương\s*án|PA|Option|Method|Plan)?\s*(\d{1,2})\s*[:\.\)]?\s*(.*)$", flags=re.IGNORECASE)
    idxs = []
    for i, ln in enumerate(lines):
        m = header_pat.match(ln)
        if m:
            num = int(m.group(1))
            if 1 <= num <= 10:
                idxs.append((i, m.group(2).strip() or f"Phương án {num}"))
    if not idxs:
        chunks = [blk.strip() for blk in re.split(r"\n\s*\n+", raw_text) if blk.strip()]
        out = []
        for i, blk in enumerate(chunks[:5], 1):
            title = blk.split("\n", 1)[0].strip()
            out.append({"title": f"Phương án {i} — {title[:60]}", "summary": blk})
        return out
    idxs.append((len(lines), ""))
    blocks = []
    for j in range(len(idxs) - 1):
        start, title_tail = idxs[j]
        end, _ = idxs[j+1]
        header_line = lines[start]
        title = title_tail or header_line.strip()
        body = "\n".join(lines[start+1:end]).strip()
        if body:
            blocks.append({"title": title, "summary": body})
    return blocks[:5]

from core.presets import PRESETS

def render_section_1(model):
    st.header("1) Nhập Ý Tưởng & Tạo 5 phương án")

    proj = st.session_state.project
    proj_name = st.text_input("Tên dự án", value=(proj.name if proj else "Truyen_XK_NT_HT"))
    preset_name = st.selectbox("Preset", list(PRESETS.keys()))
    if "project" in st.session_state and st.session_state.project:
            st.session_state.project.preset = preset_name

    idea_default = proj.idea if proj else ""
    idea = st.text_area("Ý tưởng khởi nguồn", height=120, value=idea_default,
                        placeholder="VD: Nữ chính bị phản bội, rơi vào cổng thời không về triều đại giả tưởng...")

    if st.button("✨ Tạo 5 gợi ý cốt truyện", disabled=not bool(model and idea)):
        with st.spinner("Đang tạo gợi ý..."):
            prompt = build_storyline_prompt(idea, preset_name)
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
                choices = parse_storyline_blocks(text_raw)
            if not choices:
                st.error("Không tách được phương án. Thử lại nhé.")
            else:
                st.session_state.storyline_choices = choices

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
            # khởi tạo project mới (Season 1 rỗng)
            st.session_state.project = Project(
                name=proj_name,
                idea=idea,
                preset=preset_name,
                storyline_choices=list_as_text,
                chosen_storyline=chosen_text,
                seasons=[Season(season_index=1, episode_count=10, outline=[], episodes=[])],
                # giữ cấu hình cũ nếu có
                aspect_ratio=(proj.aspect_ratio if proj else "16:9"),
                donghua_style=(proj.donghua_style if proj else True),
                character_bible=(proj.character_bible if proj else {"characters": []})
            )
            st.session_state.current_season_idx = 0
            st.success("Đã chọn cốt truyện. Chuyển qua bước dàn bài.")
