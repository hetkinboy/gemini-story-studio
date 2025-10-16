from typing import Optional, List, Dict

def build_storyline_prompt(idea: str, preset_name: str) -> str:
    return f"""
Bạn là biên kịch audio-first. Dựa trên Ý Tưởng: "{idea}".
Preset: {preset_name}.

Hãy đề xuất đúng 5 PHƯƠNG ÁN CỐT TRUYỆN. Mỗi phương án 120–180 từ, nêu:
- Bối cảnh & móc XUYÊN KHÔNG
- Mâu thuẫn chính & cặp đôi
- Cơ chế HỆ THỐNG (chỉ số, nhiệm vụ)
- Hứa hẹn tuyến cao trào cuối mùa
Viết tiếng Việt.

Trả về JSON ARRAY gồm 5 object, mỗi object: {{"title":"<10–16 từ mô tả ngắn>","summary":"<120–180 từ>"}}
KHÔNG thêm lời dẫn, KHÔNG markdown, chỉ in JSON hợp lệ.
""".strip()

def build_outline_prompt_season(chosen: str, episode_count: int, recap: str = "") -> str:
    recap_part = f"\nRecap các mùa trước:\n{recap}\n" if recap else ""
    return f"""
Từ cốt truyện đã chọn:\n---\n{chosen}\n---{recap_part}
Hãy tạo DÀN BÀI {episode_count} tập cho MÙA MỚI. Mỗi hàng gồm:
- Tiêu đề tập (6–12 từ)
- Tóm tắt ngắn 2–3 câu, nhấn mạnh cao trào tập và móc nối tập sau.
- Nối continuity từ mùa trước (nhân vật, nợ cốt truyện, mối quan hệ).
Trả về JSON list: [{{"title":"..." ,"beat":"..." }}, ...]
""".strip()

def build_episode_prompt(chosen: str, ep_title: str, ep_beat: str) -> str:
    return f"""
Viết kịch bản AUDIO-FIRST cho tập: "{ep_title}" dựa trên dàn ý: "{ep_beat}" và tổng cốt truyện:\n{chosen}\n
YÊU CẦU:
- Chia 5–8 cảnh. Mỗi cảnh có Narration và Dialogue (kèm chỉ dẫn cảm xúc).
- Thêm Voice HỆ THỐNG ở các điểm: kích hoạt nhiệm vụ, cập nhật chỉ số, phần thưởng.
- Việt hóa thuật ngữ: Cấp độ, Lớp, Nhân tính, Tha hóa, Nhiệm vụ, Mục tiêu, Phần thưởng, Kích hoạt, Hoàn tất.
- Văn phong Trung Quốc audio, giàu nhịp cảnh & âm thanh.
- Xuất theo 3 phần:
  (A) FULL_SCRIPT: ~900–1400 từ.
  (B) ASSETS: danh sách scene với image_prompt & sfx_prompt cho mỗi cảnh.
  (C) TTS: rút gọn ~6–9 phút.
Trả về JSON: {{"FULL_SCRIPT":"...","ASSETS":[{{"scene":"...","image_prompt":"...","sfx_prompt":"..."}}], "TTS":"..."}}
""".strip()

def build_character_bible_prompt(project_name: str,
                                 idea: str,
                                 chosen_storyline: str,
                                 outline: Optional[List[Dict[str, str]]],
                                 max_chars: int = 6) -> str:
    outline_hint = ""
    if outline:
        tops = outline[:5]
        outline_hint = "\n".join([f"- {i+1}. {o.get('title','')} — {o.get('beat','')}" for i, o in enumerate(tops)])
    return f"""
Bạn là giám đốc hình ảnh cho dự án: {project_name}.

Dựa vào:
IDEA:
{idea}

STORYLINE CHỌN:
{chosen_storyline}

OUTLINE GỢI Ý (các tập đầu):
{outline_hint or '(không cung cấp)'}

Hãy đề xuất Character Bible cho tối đa {max_chars} nhân vật cốt lõi, ưu tiên phong cách Á Đông, phù hợp Xuyên Không · Ngôn Tình · Hệ Thống. 
TRẢ VỀ JSON:
{{
  "characters": [
    {{
      "name": "…",
      "role": "…",
      "age": "…",
      "look": "… (ưu tiên nét Á Đông), tránh siêu thực Tây phương",
      "hair": "…",
      "outfit": "…",
      "color_theme": "…",
      "notes": "… (đặc trưng khi render donghua)"
    }}
  ]
}}
""".strip()
