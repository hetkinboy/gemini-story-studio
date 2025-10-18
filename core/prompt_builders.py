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

YÊU CẦU:
- Format bảng 3 cột (Markdown table): hàng tiêu đề CHÍNH XÁC là
  `| Content Type | Detailed Content | Technical Notes |`
  và ngay dưới là hàng gạch `|---|---|---|`.
- Mỗi hàng là một bước thuộc một cảnh (SCN): Narration / Dialogue / Sound Effects / Voice System / BGM / Transition.
- Không chèn bất kỳ văn bản ngoài bảng trong FULL_SCRIPT (không title, không chú thích).
- Diễn đạt Việt hoá hoàn toàn các thuật ngữ hệ thống: Cấp độ, Lớp, Nhân tính, Tha hoá, Nhiệm vụ, Mục tiêu, Phần thưởng, Kích hoạt, Hoàn tất.
- Phong cách audio-first: ưu tiên âm thanh dẫn hướng, hành động vật lý, nhịp đối thoại, cắt cảnh mượt.

Xuất theo 3 phần (JSON):
(A) FULL_SCRIPT: ~900–1400 từ, **chỉ** là Markdown table 3 cột như yêu cầu.
(B) ASSETS: danh sách scene [{{
  "scene":"Tên cảnh",
  "image_prompt":"mô tả tranh minh hoạ (donghua/cel-shaded, nét Á Đông, màu chủ đạo)...",
  "sfx_prompt":"gợi ý ambience/Foley/BGM/transition...",
  "characters":["Tên 1","Tên 2", ...]
}}]
(C) TTS: bản rút gọn ~6–9 phút (chỉ thoại + narration, không SFX)

Trả về JSON: {{"FULL_SCRIPT":"...","ASSETS":[{{"scene":"...","image_prompt":"...","sfx_prompt":"...","characters":["..."]}}], "TTS":"..."}}
KHÔNG thêm lời dẫn, KHÔNG markdown ngoài giá trị FULL_SCRIPT (vốn là bảng Markdown).
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
