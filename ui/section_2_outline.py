# -*- coding: utf-8 -*-
import streamlit as st
from core.data_models import Project, Season, Episode
from core.prompt_builders import build_outline_prompt_season
from core.gemini_helpers import gemini_json
from core.project_io import save_project

def _season_recap_text(p: Project) -> str:
    if not p or not p.seasons:
        return ""
    parts = []
    # recap các mùa trước (không gồm mùa hiện tại)
    for s in p.seasons[:-1]:
        arcs = "; ".join([o.get("title", "") for o in s.outline[:3]]) if s.outline else ""
        parts.append(f"Mùa {s.season_index}: {arcs}")
    return "\n".join(parts)

def _clean_ep_title(raw_title: str, ep_index: int) -> str:
    """
    Chuẩn hoá tiêu đề:
    - Gỡ mọi tiền tố numbering: 'Tập 1', 'tap 01', 'Ep 3', 'Episode 10'
      + chấp nhận dấu cách đặc biệt \u00A0, zero-width \u200b
      + chấp nhận colon ASCII ':' và fullwidth '：'
      + chấp nhận gạch nối/ascii & unicode: - – — · • .
    - Trả về phần tiêu đề tinh gọn. Nếu rỗng → 'Tập {ep_index}'.
    """
    import re
    t = (raw_title or "").strip()
    if not t:
        return f"Tập {ep_index}"

    # chuẩn hoá khoảng trắng: thay NO-BREAK SPACE/zero-width thành space thường
    t = t.replace("\u00A0", " ").replace("\u200b", "")

    # 1) Xoá các pattern có dấu câu sau số
    t = re.sub(
        r'^\s*(?:t[âa]p|tap|ep(?:isode)?)\s*\d+\s*[:：\-\–\—\.\·•]\s*',
        '', t, flags=re.IGNORECASE
    )
    # 2) Xoá nốt trường hợp chỉ có số mà không dấu câu (ex: "Tập 3  Tiêu đề")
    t = re.sub(r'^\s*(?:t[âa]p|tap|ep(?:isode)?)\s*\d+\s*', '', t, flags=re.IGNORECASE)

    # dọn đuôi kí tự thừa
    t = t.strip(" -:：·.•—–").strip()
    return t or f"Tập {ep_index}"

def render_section_2(model):
    st.header("2) Lên dàn bài (Outline) theo số tập — theo Mùa đang chọn")

    proj: Project = st.session_state.get("project")
    if not proj:
        st.info("Chưa có project. Hãy tạo project trước.")
        return

    # chọn/current season
    if "current_season_idx" not in st.session_state:
        st.session_state.current_season_idx = 0

    colS1, colS2, colS3 = st.columns([1, 1, 1])
    with colS1:
        if proj.seasons:
            season_labels = [f"Mùa {s.season_index:02d} ({len(s.episodes)} tập)" for s in proj.seasons]
            pick_season = st.selectbox("Mùa đang chọn", season_labels, index=st.session_state.current_season_idx)
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
                st.session_state.current_season_idx = max(0, idx - 1)
                save_project(proj)
                st.success("Đã xoá Mùa.")

    sidx = st.session_state.current_season_idx
    cur_season = proj.seasons[sidx]

    ep_count = st.number_input(
        "Số tập của Mùa này", min_value=4, max_value=30,
        value=cur_season.episode_count, step=1, key=f"ep_count_s{sidx}"
    )

    if st.button("🧭 Tạo dàn bài cho Mùa này", disabled=not bool(model), key=f"btn_outline_s{sidx}"):
        with st.spinner("Đang tạo dàn bài..."):
            recap = _season_recap_text(proj) if sidx > 0 else ""
            prompt = build_outline_prompt_season(proj.chosen_storyline, int(ep_count), recap, preset_name=proj.preset)
            data = gemini_json(model, prompt)

            outline_list = []
            if isinstance(data, list):
                for idx, item in enumerate(data, 1):
                    raw_title = item.get("title") or ""
                    title = _clean_ep_title(raw_title, idx)     # << dùng hàm mạnh
                    beat = item.get("beat") or ""
                    outline_list.append({"title": title, "beat": beat})
            else:
                lines = str(data).splitlines()
                for i, ln in enumerate(lines, 1):
                    outline_list.append({"title": f"Tập {i}", "beat": ln})

            cur_season.episode_count = int(ep_count)
            cur_season.outline = outline_list
            # tạo Episode list từ outline, title đã clean
            cur_season.episodes = [
            Episode(
                index=i+1,
                title=_clean_ep_title(o.get("title", f"Tập {i+1}"), i+1),
                summary=o.get("beat", "")
            )
            for i, o in enumerate(outline_list)
            ]
            proj.seasons[sidx] = cur_season
            save_project(proj)
            st.success(f"Đã tạo dàn bài cho Mùa {cur_season.season_index}.")

    if cur_season.outline:
        st.write(f"### Dàn bài đề xuất — Mùa {cur_season.season_index}:")
        for i, row in enumerate(cur_season.outline, 1):
            # hiển thị “Tập i: {title}” — title đã được clean nên không lặp
            title_show = _clean_ep_title(row.get("title",""), i)   # << thêm dòng này
            with st.expander(f"Tập {i}: {title_show}"):
                st.write(row["beat"])
        if st.button("✅ Duyệt dàn bài mùa này", key=f"approve_outline_s{sidx}"):
            save_project(proj)
            st.success("Đã duyệt dàn bài cho Mùa hiện tại.")
