import streamlit as st

from core.env_loader import load_env, init_model, quiet_logs
from core.data_models import Project
from core.project_io import DATA_DIR

from ui.sidebar import render_sidebar
from ui.section_1_idea import render_section_1
from ui.section_2_outline import render_section_2
from ui.section_3_episode import render_section_3

quiet_logs()
st.set_page_config(page_title="Gemini Story Studio", page_icon="🎧", layout="wide")

# Session init
if "project" not in st.session_state:
    st.session_state.project = None
if "current_season_idx" not in st.session_state:
    st.session_state.current_season_idx = 0
if "storyline_choices" not in st.session_state:
    st.session_state.storyline_choices = []

# Load .env and init model
api_key = load_env()
model_name, use_tts = render_sidebar()   # also handles load/save/export UI
model = init_model(api_key, model_name) if api_key else None

st.title("🎧 Gemini Story Studio — Xuyên Không / Ngôn Tình / Hệ Thống")

# Sections
render_section_1(model)
render_section_2(model)
render_section_3(model, use_tts)
