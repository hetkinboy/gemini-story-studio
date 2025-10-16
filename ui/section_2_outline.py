import streamlit as st
from core.data_models import Project, Season, Episode
from core.prompt_builders import build_outline_prompt_season
from core.gemini_helpers import gemini_json
from core.project_io import save_project

def _season_recap_text(p: Project) -> str:
    if not p or not p.seasons: return ""
    parts = []
    for s in p.seasons[:-1]:
        arcs = "; ".join([o.get("title","") for o in s.outline[:3]]) if s.outline else ""
        parts.append(f"Mùa {s.season_index}: {arcs}")
    return "\n".join(parts)

def render_section_2(model):
    st.header("2) Lên dàn bài (Outline) theo số tập — theo Mùa đang chọn")

    proj: Project | None = st.session_state.project
    if not proj or not proj.chosen_storyline:
        st.info("Chưa chọn cốt truyện ở bước 1.")
        return

    # Season switch / ops
    colS1, colS2, colS3 = st.columns([1.4, 1, 1])
    with colS1:
        if proj.seasons:
            season_labels = [f"Mùa {s.season_index:02d} ({len(s.episodes)} tập)" for s in proj.seasons]
            pick_season = st.selectbox("Chọn Mùa", season_labels, index=st.session_state.current_season_idx, key="season_pick")
            st.session_state.current_season_idx = season_labels.index(pick_season)
        else:
            st.caption("Chưa có Mùa nào.")
    with colS2:
        if st.button("➕ Tạo Mùa mới"):
            next_idx = len(proj.seasons) + 1
            new_season = Season(season_index=next_idx, episode_count=10, outline=[], episodes=[])
            proj.seasons.append(new_season)
            st.session_state.current_season_idx = len(proj.seasons) - 1
            save_project(proj)
            st.success(f"Đã tạo Mùa {next_idx}.")
    with colS3:
        if len(proj.seasons) > 1:
            if st.button("🗑️ Xoá Mùa hiện tại"):
                idx = st.session_state.current_season_idx
                del proj.seasons[idx]
                for i, s in enumerate(proj.seasons, 1):
                    s.season_index = i
                st.session_state.current_season_idx = max(0, st.session_state.current_season_idx - 1)
                save_project(proj)
                st.success("Đã xoá Mùa.")

    sidx = st.session_state.current_season_idx
    cur_season = proj.seasons[sidx]

    ep_count = st.number_input("Số tập của Mùa này", min_value=4, max_value=30,
                               value=cur_season.episode_count, step=1, key=f"ep_count_s{sidx}")
    if st.button("🧭 Tạo dàn bài cho Mùa này", disabled=not bool(model), key=f"btn_outline_s{sidx}"):
        with st.spinner("Đang tạo dàn bài..."):
            recap = _season_recap_text(proj) if sidx > 0 else ""
            prompt = build_outline_prompt_season(proj.chosen_storyline, int(ep_count), recap)
            data = gemini_json(model, prompt)
            outline_list = []
            if isinstance(data, list):
                for item in data:
                    title = item.get("title") or "Tập"
                    beat = item.get("beat") or ""
                    outline_list.append({"title": title, "beat": beat})
            else:
                lines = str(data).splitlines()
                for i, ln in enumerate(lines, 1):
                    outline_list.append({"title": f"Tập {i}", "beat": ln})

            cur_season.episode_count = int(ep_count)
            cur_season.outline = outline_list
            cur_season.episodes = [
                Episode(index=i+1, title=o.get("title", f"Tập {i+1}"), summary=o.get("beat", ""))
                for i, o in enumerate(outline_list)
            ]
            proj.seasons[sidx] = cur_season
            save_project(proj)
            st.success(f"Đã tạo dàn bài cho Mùa {cur_season.season_index}.")

    if cur_season.outline:
        st.write(f"### Dàn bài đề xuất — Mùa {cur_season.season_index}:")
        for i, row in enumerate(cur_season.outline, 1):
            with st.expander(f"Tập {i}: {row['title']}"):
                st.write(row["beat"])
        if st.button("✅ Duyệt dàn bài mùa này", key=f"approve_outline_s{sidx}"):
            save_project(proj)
            st.success("Đã duyệt dàn bài cho Mùa hiện tại.")
