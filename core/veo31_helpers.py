from typing import Optional, List, Dict

def build_veo31_segments_prompt(
    ep_title: str,
    scene_name: str,
    scene_text: str,
    max_segments: int = 3,
    aspect_ratio: str = "16:9",
    donghua_style: bool = True,
    character_bible: Optional[Dict[str, any]] = None,
    characters_in_scene: Optional[List[str]] = None,
) -> str:
    style_hint = (
        "stylized animation, Chinese donghua look, cel-shaded, clean lineart, "
        "Asian facial features, natural black/dark hair unless specified, "
        "avoid photorealism, avoid western/European facial structure, "
        "soft skin rendering, rich fabric texture"
        if donghua_style else
        "cinematic stylized look, avoid hyper-realistic faces"
    )
    char_text = ""
    if character_bible and character_bible.get("characters"):
        chosen = character_bible["characters"]
        if characters_in_scene:
            chosen = [c for c in character_bible["characters"] if c.get("name") in characters_in_scene]
        lines = []
        for c in chosen:
            lines.append(
                f"- {c.get('name','?')}: role={c.get('role','')}, age={c.get('age','')}, "
                f"look={c.get('look','')}, hair={c.get('hair','')}, outfit={c.get('outfit','')}, "
                f"colors={c.get('color_theme','')}, notes={c.get('notes','')}"
            )
        if lines:
            char_text = "CHARACTER BIBLE (use consistently):\n" + "\n".join(lines)
    ar_text = f"target_aspect_ratio={aspect_ratio}"

    return f"""
Bạn là đạo diễn tiền-kỳ cho video AI Veo 3.1. Từ thông tin cảnh:

• TẬP: {ep_title}
• CẢNH: {scene_name}
• NỘI DUNG CẢNH:
---
{scene_text}
---

{char_text if char_text else "CHARACTER BIBLE: (none provided)"}

YÊU CẦU:
- Chia cảnh thành các đoạn video 8 GIÂY (duration_sec=8). Tổng số đoạn tối đa {max_segments}.
- Mỗi đoạn là MỘT SHOT liền mạch, ưu tiên hành động, cảm xúc, chuyển động camera.
- Mô tả rõ:
  • Hành động nhân vật
  • Camera: ống kính, khung hình (CU/MS/WS), chuyển động (dolly/pan/handheld/drone…), độ cao/góc nhìn
  • Bố cục & chuyển cảnh trong 8s (rack focus/whip pan…)
  • Ánh sáng/không khí (giờ, keylight, rimlight, volumetric…)
  • Môi trường/đạo cụ
  • Phong cách: {style_hint}
  • FPS & AR: 24fps, {ar_text}
  • Tông cảm xúc / nhịp điệu
- Mỗi segment phải nêu rõ "characters" xuất hiện trong shot.
- Gợi ý SFX/ambience.

TRẢ VỀ JSON DUY NHẤT:
{{
  "scene": "{scene_name}",
  "segments": [
    {{
      "title": "Ngắn gọn 3–7 từ",
      "duration_sec": 8,
      "characters": ["Tên A","Tên B"],
      "veo_prompt": "Character context -> mô tả shot chi tiết + 24fps + {aspect_ratio}; tránh siêu thực Tây phương.",
      "sfx": "ambience/SFX",
      "notes": "continuity"
    }}
  ]
}}
""".strip()
