from typing import Optional, List, Dict
from core.text_utils import seed_char_names_from_tts
from core.prompt_builders import build_character_bible_prompt
from core.gemini_helpers import gemini_json

def ai_generate_character_bible(model, project_name: str, idea: str, chosen_storyline: str,
                                outline: Optional[List[Dict[str, str]]], max_chars: int = 6) -> Dict:
    prompt_cb = build_character_bible_prompt(project_name, idea, chosen_storyline, outline, max_chars)
    data_cb = gemini_json(model, prompt_cb)
    if isinstance(data_cb, dict) and "characters" in data_cb:
        return data_cb
    return {"characters": []}

def seed_from_text(base_cb: Dict, tts_or_script: str) -> Dict:
    names = seed_char_names_from_tts(tts_or_script)
    cb = base_cb or {"characters": []}
    existing = {c.get("name") for c in cb.get("characters", [])}
    for n in names:
        if n and n not in existing:
            cb.setdefault("characters", []).append({
                "name": n, "role": "", "age": "",
                "look": "gương mặt Á Đông; tránh nét siêu thực Tây phương",
                "hair": "", "outfit": "", "color_theme": "", "notes": "donghua/cel-shaded"
            })
    return cb
