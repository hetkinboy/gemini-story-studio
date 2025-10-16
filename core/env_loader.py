import os
import streamlit as st

def quiet_logs():
    os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
    os.environ.setdefault("GRPC_CPP_ENABLE_STACKTRACE", "0")
    os.environ.setdefault("GRPC_ALTS_ENABLED", "0")
    try:
        import absl.logging as absl_logging
        absl_logging.set_verbosity(absl_logging.ERROR)
    except Exception:
        pass

def load_env() -> str:
    # Luôn reload .env để chắc chắn đọc key mới trên đĩa
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass
    # Ưu tiên GEMINI_API_KEY (hoặc GOOGLE_API_KEY nếu bạn dùng tên đó)
    return os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

def get_key_info(key: str) -> str:
    if not key:
        return "chưa có key"
    return f"key_len={len(key)} | key_hash={abs(hash(key)) % 100000}"

def validate_key_format(k: str) -> bool:
    # Không bắt buộc chuẩn regex quá gắt — chỉ đảm bảo không rỗng và không có khoảng trắng
    return bool(k and k.strip() and " " not in k)

def set_runtime_key(new_key: str):
    """
    Ghi đè key trong ENV của process hiện tại (không đụng file .env).
    Dùng khi bạn muốn thay ngay lập tức trong phiên đang chạy.
    """
    os.environ["GEMINI_API_KEY"] = new_key
    os.environ["GOOGLE_API_KEY"] = new_key  # phòng TH SDK đọc GOOGLE_API_KEY

def write_dotenv_key(new_key: str) -> bool:
    """
    Ghi key mới vào file .env (an toàn). Trả về True nếu thành công.
    """
    try:
        from dotenv import set_key, find_dotenv
        env_path = find_dotenv(usecwd=True)
        if not env_path:
            # nếu chưa có .env, tạo file mới trong cwd
            env_path = os.path.join(os.getcwd(), ".env")
            open(env_path, "a", encoding="utf-8").close()
        set_key(env_path, "GEMINI_API_KEY", new_key)
        # Đồng bộ runtime ngay sau khi ghi file
        set_runtime_key(new_key)
        return True
    except Exception:
        return False

def reset_caches_and_rerun():
    try:
        st.cache_resource.clear()
    except Exception:
        pass
    try:
        st.cache_data.clear()
    except Exception:
        pass
    # Streamlit >= 1.27 dùng st.rerun(); bản cũ vẫn còn experimental_rerun
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass  # cùng lắm không rerun, nhưng cache đã clear


@st.cache_resource(show_spinner=False)
def init_model(api_key: str, model_name: str):
    if not api_key:
        return None
    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError(f"Chưa cài google-generativeai: {e}")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)
