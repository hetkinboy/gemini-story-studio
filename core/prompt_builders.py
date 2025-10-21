# -*- coding: utf-8 -*-
from typing import Optional, List, Dict
from core.presets import PRESETS, preset_block

def build_storyline_prompt(idea: str, preset_name: str) -> str:
    """
    Gợi ý 5 phương án cốt truyện từ ý tưởng + preset.
    Kết quả yêu cầu JSON Array (không markdown, không lời dẫn).
    """
    preset_info = preset_block(preset_name)
    return f"""
Bạn là biên kịch audio-first. Dựa trên Ý Tưởng: "{idea}".
Preset: {preset_name}.

{preset_info}

Hãy đề xuất đúng 5 PHƯƠNG ÁN CỐT TRUYỆN. Mỗi phương án 120–180 từ, nêu:
- Bối cảnh & móc XUYÊN KHÔNG (nếu phù hợp thể loại)
- Mâu thuẫn chính & tuyến quan hệ nhân vật
- Cơ chế HỆ THỐNG / Quy tắc thế giới (nếu có)
- Hứa hẹn cao trào cuối mùa
Viết tiếng Việt.

Trả về JSON ARRAY gồm 5 object, mỗi object: {{"title":"<10–16 từ mô tả ngắn>","summary":"<120–180 từ>"}}
KHÔNG thêm lời dẫn, KHÔNG markdown, chỉ in JSON hợp lệ.
""".strip()


def build_outline_prompt_season(
    chosen: str,
    episode_count: int,
    recap: str = "",
    preset_name: Optional[str] = None
) -> str:
    """
    Sinh dàn ý mùa (episode_count tập) từ cốt truyện đã chọn + preset (nếu có).
    """
    preset_info = preset_block(preset_name) if preset_name else ""
    recap_part = f"\nRecap các mùa trước:\n{recap}\n" if recap else ""
    return f"""
Từ cốt truyện đã chọn:\n---\n{chosen}\n---{recap_part}
{preset_info}

Hãy tạo DÀN Ý MÙA gồm {episode_count} tập.
YÊU CẦU:
- Mỗi tập mô tả 1–2 câu: bối cảnh, mâu thuẫn, tiến độ xung đột, hook nối tập sau.
- Liên kết continuity (nhân vật, nợ cốt truyện, đồ vật/điểm mốc).
- Việt hoá hoàn toàn, mạch lạc, audio-first.

Trả về JSON list: [{{"title":"...", "beat":"..."}}].
KHÔNG thêm lời dẫn, KHÔNG markdown.
""".strip()


def build_episode_prompt(
    chosen: str,
    ep_title: str,
    ep_beat: str,
    preset_name: Optional[str] = None
) -> str:
    """
    Sinh kịch bản một tập theo format audio-first 3 cột.
    FULL_SCRIPT phải là Markdown table 3 cột đúng header, không có chữ thừa ngoài bảng.
    """
    preset_info = preset_block(preset_name) if preset_name else ""
    return f"""
Viết kịch bản AUDIO-FIRST cho tập: "{ep_title}" dựa trên dàn ý: "{ep_beat}" và tổng cốt truyện:
{chosen}

{preset_info}
YÊU CẦU CHI TIẾT CHO FULL_SCRIPT:
- Viết kịch bản **audio-first**, trong đó mỗi hành động, chuyển động hay phản ứng đều được diễn tả bằng **micro-actions** ngắn và có **âm thanh gợi tả** đi kèm.
- Khi nhân vật làm gì, hãy mô tả cả **cảm giác – tiếng động – không gian** (VD: tiếng gió, tiếng chân, tiếng áo lụa, hơi thở, tiếng va chạm…).
- Luôn có các dòng `Sound Effects`, `BGM`, `Transition` đan xen để người nghe cảm nhận được không khí.
- Lời thoại cần tự nhiên, có biểu cảm và cảm xúc giọng (VD: [khẽ run], [giọng thấp], [cười nhẹ], [ngập ngừng]…).
- Mỗi cảnh nên có tiết tấu rõ: mở cảnh → hành động → đối thoại → âm → kết cảnh.
- Không đưa ví dụ cụ thể nào vào kịch bản; chỉ áp dụng nguyên tắc trên khi viết.

ĐẦU RA PHẢI LÀ JSON GỒM 3 KHÓA:
- **FULL_SCRIPT**: Bảng Markdown 3 cột như hướng dẫn, với các dòng {"Narration", "Dialogue", "Sound Effects", "BGM", "Transition"} thể hiện diễn tiến từng hành động.
- **ASSETS**: Danh sách scene (cho phần hình và âm thanh) dạng:
  [
    {{
      "scene": "Tên cảnh ngắn gọn",
      "image_prompt": "Mô tả khung cảnh hoặc nhân vật để vẽ 1 keyframe",
      "sfx_prompt": "Gợi ý SFX / ambience chính của cảnh",
      "characters": ["Tên 1", "Tên 2"]
    }}
  ]
  * Lưu ý: image_prompt cần đồng bộ với Character Bible, nét Á Đông (donghua style), tránh siêu thực Tây phương.
- **TTS**: Phiên bản đọc liền mạch (không Markdown), ưu tiên dễ nghe, nhịp rõ, tự nhiên.

TRẢ VỀ JSON DUY NHẤT (định dạng chính xác):
{{
  "FULL_SCRIPT": "| Content Type | Detailed Content | Technical Notes |\\n|---|---|---|\\n…",
  "ASSETS": [{{"scene":"…","image_prompt":"…","sfx_prompt":"…","characters":["…"]}}],
  "TTS": "…"
}}
""".strip()


def build_character_bible_prompt(
    project_name: str,
    idea: str,
    chosen: str,
    outline: Optional[List[Dict[str, str]]],
    max_chars: int = 6,
    preset_name: Optional[str] = None
) -> str:
    """
    Sinh Character Bible (tối đa max_chars nhân vật).
    Hỗ trợ preset và tham chiếu dàn ý mùa nếu có.
    """
    preset_info = preset_block(preset_name) if preset_name else ""

    outline_text = ""
    if outline:
        try:
            items = [f"- {i+1}. {ep.get('title','')} — {ep.get('beat','')}" for i, ep in enumerate(outline)]
            outline_text = "\n".join(items)
        except Exception:
            outline_text = ""

    return f"""
Bạn là biên tập xây dựng 'Character Bible' cho dự án: "{project_name}".
Ý tưởng gốc: {idea}
Cốt truyện đã chọn: {chosen}

{preset_info}

Nhiệm vụ: Tạo danh sách tối đa {max_chars} nhân vật cốt lõi phục vụ dựng kịch bản audio-first.
YÊU CẦU mỗi nhân vật có các thuộc tính:
- name, role, age
- look (ưu tiên nét Á Đông; tránh siêu thực Tây phương), hair, outfit
- color_theme (2–3 màu chủ đạo), notes (đặc trưng khi render donghua/cel-shaded)

Nếu có dàn ý mùa, tham chiếu nhịp câu chuyện sau:
{outline_text}

Trả về JSON: {{"characters":[{{"name":"...","role":"...","age":"...","look":"...","hair":"...","outfit":"...","color_theme":"...","notes":"..."}}]}}.
KHÔNG kèm lời dẫn hay markdown, chỉ in JSON hợp lệ.
""".strip()
