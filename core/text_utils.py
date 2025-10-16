import re, unicodedata
from typing import List, Dict

def _fold(s: str) -> str:
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.lower().strip()

def _safe_name(s: str) -> str:
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.U)
    return s.strip().replace(" ", "_")[:60]

def clean_tts_text(text: str) -> str:
    if not text: return ""
    s = re.sub(r"\*\*|\*|__|`+", "", text)
    s = re.sub(r"^\s*(SCN|Cảnh|Scene)\s*\d+\s*[:\-]?.*$", "", s, flags=re.MULTILINE|re.IGNORECASE)
    s = re.sub(r"\[(?:SFX|FX|Ambience|Âm nền|BGM|Nhạc nền|Transition|Chuyển cảnh)[^\]]*\]", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\((?:SFX|FX|Ambience|Âm nền|BGM|Nhạc nền|Transition|Chuyển cảnh)[^\)]*\)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*(ASSETS|TTS|FULL_SCRIPT)\s*:.*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

SPEAKER_PAT = re.compile(
    r"^(?:\s*[-–—]\s*)?(?:\*\s*)?(?P<name>[A-ZÀ-Ỵa-zà-ỹ0-9 _\[\]\(\)HỆ THỐNGSystem]+?)\s*[:：]\s*(?P<line>.+)$"
)

def parse_tts_lines(text: str):
    lines = []
    for raw in text.split('\n'):
        t = raw.strip()
        if not t: continue
        m = SPEAKER_PAT.match(t)
        if m:
            name = m.group('name').strip()
            name = re.sub(r'^[\[\(]\s*|\s*[\]\)]$', '', name).strip()
            if _fold(name) in {"he thong", "system", "voice system"}:
                name = "HỆ THỐNG"
            lines.append({"speaker": name, "text": m.group('line').strip()})
        else:
            lines.append({"speaker": "Người Dẫn Chuyện", "text": t})
    return lines

def extract_characters(parsed: List[Dict[str, str]]) -> List[str]:
    chars = []
    for it in parsed:
        sp = it["speaker"]
        if sp not in ("Người Dẫn Chuyện",) and sp not in chars:
            chars.append(sp)
    if any(it["speaker"] == "HỆ THỐNG" for it in parsed) and "HỆ THỐNG" not in chars:
        chars.append("HỆ THỐNG")
    return chars

def suggest_styles(char_names: List[str]) -> Dict[str, str]:
    out = {}
    for n in char_names:
        base = _fold(n)
        if n == "HỆ THỐNG":
            out[n] = "Trung tính, vang kim loại nhẹ, nhịp đều 0.9x"
        elif any(k in base for k in ["nu", "tieu", "co"]):
            out[n] = "Nữ dịu, ấm, hơi thì thầm khi nội tâm"
        elif any(k in base for k in ["nam", "ca", "anh"]):
            out[n] = "Nam trầm, chắc, dứt khoát khi đối đầu"
        else:
            out[n] = "Trung tính, giàu cảm xúc theo ngữ cảnh"
    return out

def seed_char_names_from_tts(tts_text: str) -> list[str]:
    parsed = parse_tts_lines(clean_tts_text(tts_text or ""))
    names = []
    for ln in parsed:
        sp = ln.get("speaker", "")
        if sp and sp not in ("Người Dẫn Chuyện", "HỆ THỐNG") and sp not in names:
            names.append(sp)
    return names[:10]
