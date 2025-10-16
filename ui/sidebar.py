import streamlit as st
from pathlib import Path
from core.env_loader import load_env, get_key_info, validate_key_format, set_runtime_key, write_dotenv_key, reset_caches_and_rerun
from core.project_io import DATA_DIR, save_project, load_project, export_zip

def render_sidebar():
    st.sidebar.title("⚙️ Cấu hình")

    # ============ 🔐 API Key Manager ============
    with st.sidebar.expander("🔐 API Key (GEMINI_API_KEY)", expanded=True):
        current_key = load_env()
        st.caption(f"Hiện tại: {get_key_info(current_key)}")

        new_key = st.text_input(
            "Nhập key mới (không lưu nếu chưa bấm nút bên dưới)",
            type="password",
            placeholder="dán GEMINI_API_KEY vào đây…",
            key="api_key_entry_sidebar",
        )

        colK1, colK2 = st.columns(2)
        with colK1:
            if st.button("⚡ Dùng tạm thời (runtime)"):
                if not validate_key_format(new_key):
                    st.warning("Key trống hoặc không hợp lệ.")
                else:
                    set_runtime_key(new_key)
                    st.success("Đã ghi đè key tạm thời cho phiên hiện tại.")
                    reset_caches_and_rerun()
        with colK2:
            if st.button("💾 Ghi vào .env"):
                if not validate_key_format(new_key):
                    st.warning("Key trống hoặc không hợp lệ.")
                else:
                    ok = write_dotenv_key(new_key)
                    if ok:
                        st.success("Đã ghi key vào .env và áp dụng ngay.")
                        reset_caches_and_rerun()
                    else:
                        st.error("Không ghi được .env. Kiểm tra quyền ghi file.")

        colR1, colR2 = st.columns(2)
        with colR1:
            if st.button("🔄 Reload .env"):
                # chỉ reload .env và rerun
                reset_caches_and_rerun()
        with colR2:
            if st.button("🧽 Xoá override (dùng lại .env)"):
                # Xoá mọi override runtime để quay về .env: cách đơn giản là xóa biến env hiện tại
                # rồi reload .env ở vòng render kế tiếp.
                for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                    if var in st.session_state:
                        del st.session_state[var]
                try:
                    import os
                    if "GEMINI_API_KEY" in os.environ: del os.environ["GEMINI_API_KEY"]
                    if "GOOGLE_API_KEY" in os.environ: del os.environ["GOOGLE_API_KEY"]
                except Exception:
                    pass
                st.info("Đã xoá override. App sẽ tải lại key từ .env.")
                reset_caches_and_rerun()
    # ============ /API Key Manager ============

    model_name = st.sidebar.selectbox("Model", ["gemini-2.5-pro", "gemini-2.5-flash"])
    custom_model = st.sidebar.text_input("Model tuỳ chọn", value="", help="Ví dụ: gemini-2.5-flash")
    model_name = custom_model or model_name

    use_tts = st.sidebar.toggle("Bật TTS (gTTS)", value=False, help="Tạo file MP3 cho tab TTS")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 Dự án")
    proj_files = sorted(DATA_DIR.glob("*.json"))
    if proj_files:
        sel_file = st.sidebar.selectbox("Mở project", ["(Chọn)"] + [f.name for f in proj_files])
        if sel_file != "(Chọn)":
            st.session_state.project = load_project(DATA_DIR / sel_file)
            st.sidebar.success(f"Đã mở {sel_file}")

    if st.sidebar.button("💾 Lưu project", type="primary"):
        if st.session_state.project:
            f = save_project(st.session_state.project)
            st.sidebar.success(f"Đã lưu: {f.name}")
        else:
            st.sidebar.warning("Chưa có project")

    if st.sidebar.button("📦 Export ZIP"):
        if st.session_state.project:
            zbytes = export_zip(st.session_state.project)
            st.sidebar.download_button("Tải xuống project.zip", data=zbytes, file_name="project.zip")
        else:
            st.sidebar.warning("Chưa có project")

    # Debug (ẩn key)
    current_key2 = load_env()
    if current_key2:
        st.sidebar.caption(f"[DEBUG] {get_key_info(current_key2)}")
    else:
        st.sidebar.error("Chưa thấy GEMINI_API_KEY trong .env.")

    return model_name, use_tts
