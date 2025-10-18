# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Any

def _character_bible_text(
    character_bible: Optional[Dict[str, Any]],
    characters_in_scene: Optional[List[str]] = None
) -> str:
    """
    Render block CHARACTER BIBLE gọn; nếu có danh sách nhân vật trong cảnh thì lọc theo.
    """
    if not character_bible or not character_bible.get("characters"):
        return "CHARACTER BIBLE: (none provided)"

    chosen = character_bible["characters"]
    if characters_in_scene:
        names = set(characters_in_scene)
        chosen = [c for c in chosen if (c.get("name") or "") in names]

    if not chosen:
        return "CHARACTER BIBLE: (none provided)"

    lines = ["CHARACTER BIBLE (use consistently):"]
    for c in chosen:
        lines.append(
            f"- {c.get('name','?')}: "
            f"role={c.get('role','')}, age={c.get('age','')}, "
            f"look={c.get('look','')}, hair={c.get('hair','')}, "
            f"outfit={c.get('outfit','')}, colors={c.get('color_theme','')}, "
            f"notes={c.get('notes','')}"
        )
    return "\n".join(lines)


def build_veo31_segments_prompt(
    ep_title: str,
    scene_name: str,
    scene_text: str,
    max_segments: int = 3,
    aspect_ratio: str = "16:9",
    donghua_style: bool = True,
    character_bible: Optional[Dict[str, Any]] = None,
    characters_in_scene: Optional[List[str]] = None,
) -> str:
    """
    Sinh prompt cho Veo 3.1 theo một cảnh.
    - Mỗi segment là một SHOT ~8s, tập trung HÀNH ĐỘNG NHÂN VẬT + CHUYỂN ĐỘNG CAMERA.
    - Trả về prompt (model sẽ trả JSON đúng schema yêu cầu ở dưới).
    """
    style_hint = (
        "stylized animation, Chinese donghua look, cel-shaded, clean lineart, "
        "Asian facial features, natural black/dark hair unless specified, "
        "avoid photorealism, avoid western/European facial structure, "
        "soft skin rendering, rich fabric texture"
        if donghua_style else
        "cinematic stylized look, avoid hyper-realistic faces"
    )
    cb_text = _character_bible_text(character_bible, characters_in_scene)
    ar_text = f"target_aspect_ratio={aspect_ratio}"
    chars_line = f"[Characters in scene] {', '.join(characters_in_scene or [])}".strip()

    return f"""
Bạn là đạo diễn tiền-kỳ cho video AI Veo 3.1. Từ thông tin cảnh:

• TẬP: {ep_title}
• CẢNH: {scene_name}
• NỘI DUNG CẢNH:
---
{scene_text}
---
{chars_line if chars_line else ""}

{cb_text}

YÊU CẦU:
- Chia cảnh thành các đoạn video 8 GIÂY (duration_sec=8). Tổng số đoạn tối đa {max_segments}.
- Mỗi đoạn là MỘT SHOT LIỀN MẠCH, ưu tiên **HÀNH ĐỘNG NHÂN VẬT** (tay/chân/ánh mắt/nhịp thở/tương tác đạo cụ) và **CHUYỂN ĐỘNG CAMERA**.
- Mô tả rõ cho TỪNG SHOT:
  • Hành động nhân vật (động tác theo thời gian trong 8s, tương tác với ai/đạo cụ gì)
  • Biểu cảm & hướng nhìn (góc mắt, thay đổi nét mặt, chuyển trọng tâm cơ thể)
  • Camera: ống kính, khung (CU/MS/WS), chuyển động (dolly/pan/tilt/handheld/drone), góc/độ cao
  • Bố cục & continuity trong 8s (rack focus/whip pan/match cut…)
  • Ánh sáng/không khí (giờ, keylight, rimlight, volumetric, mưa/sương/bụi…)
  • Môi trường/đạo cụ (texture bề mặt, chi tiết nền)
  • Phong cách: {style_hint}
  • FPS & AR: 24fps, {ar_text}
  • Tông cảm xúc / nhịp dựng
- Mỗi segment phải nêu rõ "characters".
- Gợi ý SFX/ambience (ngắn gọn, khớp hành động).

TRẢ VỀ JSON DUY NHẤT:
{{
  "scene": "{scene_name}",
  "segments": [
    {{
      "title": "Ngắn gọn 3–7 từ",
      "duration_sec": 8,
      "characters": ["Tên A","Tên B"],
      "veo_prompt": "Character action beats (tay/chân/ánh mắt/đạo cụ) -> camera (lens/khung/chuyển động) -> ánh sáng/không khí -> môi trường/đạo cụ -> 24fps + {aspect_ratio}; tránh siêu thực Tây phương.",
      "sfx": "ambience/SFX ngắn",
      "notes": "continuity (nếu cần)"
    }}
  ]
}}
KHÔNG thêm lời dẫn, KHÔNG markdown, chỉ in JSON hợp lệ.
""".strip()
