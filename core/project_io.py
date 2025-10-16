import json, io, zipfile
from pathlib import Path
from typing import List
from core.data_models import Project, Season, Episode

from core.text_utils import _safe_name

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "projects"
DATA_DIR.mkdir(exist_ok=True)

def save_project(proj: Project) -> Path:
    f = DATA_DIR / f"{_safe_name(proj.name)}.json"
    with f.open("w", encoding="utf-8") as fp:
        json.dump(proj.model_dump(), fp, ensure_ascii=False, indent=2)
    return f

def load_project(path: Path) -> Project:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "seasons" not in data:  # migrate cũ
        eps = [Episode(**e) for e in data.get("episodes", [])]
        outline = data.get("outline", [])
        season = Season(season_index=1, episode_count=data.get("episode_count", 10), outline=outline, episodes=eps)
        data = {
            "name": data.get("name", "Project"),
            "idea": data.get("idea", ""),
            "preset": data.get("preset", ""),
            "storyline_choices": data.get("storyline_choices", []),
            "chosen_storyline": data.get("chosen_storyline", ""),
            "seasons": [season.model_dump()],
            "aspect_ratio": data.get("aspect_ratio", "16:9"),
            "donghua_style": data.get("donghua_style", True),
            "character_bible": data.get("character_bible", {"characters": []}),
        }
    seasons = []
    for s in data.get("seasons", []):
        eps = [Episode(**e) for e in s.get("episodes", [])]
        seasons.append(Season(
            season_index=s.get("season_index", len(seasons)+1),
            episode_count=s.get("episode_count", 10),
            outline=s.get("outline", []),
            episodes=eps
        ))
    data["seasons"] = seasons
    data.setdefault("aspect_ratio", "16:9")
    data.setdefault("donghua_style", True)
    data.setdefault("character_bible", {"characters": []})
    return Project(**data)

def export_zip(proj: Project) -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(proj.model_dump(), ensure_ascii=False, indent=2))
        z.writestr("character_bible.json", json.dumps(proj.character_bible, ensure_ascii=False, indent=2))
        for s in proj.seasons:
            season_root = f"season_{s.season_index:02d}/"
            z.writestr(season_root + "outline.json", json.dumps(s.outline, ensure_ascii=False, indent=2))
            for ep in s.episodes:
                base = f"{season_root}ep{ep.index:02d}_{_safe_name(ep.title)}"
                z.writestr(f"{base}/script.txt", ep.script_text or "")
                z.writestr(f"{base}/tts.txt", ep.tts_text or "")
                z.writestr(f"{base}/assets.json", json.dumps(ep.assets or {}, ensure_ascii=False, indent=2))
                # xuất veo31 segments (nếu có)
                try:
                    scs = ep.assets.get("scenes", [])
                    lines = []
                    for j, sc in enumerate(scs, 1):
                        v = sc.get("veo31", {})
                        segs = v.get("segments", [])
                        if not segs: continue
                        lines.append(f"## {sc.get('scene', f'Cảnh {j}')}")
                        for si, seg in enumerate(segs, 1):
                            lines.append(
                                f"\n# Clip {si} — {seg.get('duration_sec',8)}s: {seg.get('title','')}\n"
                                f"[Characters] {', '.join(seg.get('characters', []))}\n"
                                f"{seg.get('veo_prompt','')}\n"
                                f"[SFX] {seg.get('sfx','')}\n"
                            )
                    if lines:
                        z.writestr(f"{base}/veo31_segments.txt", "\n".join(lines))
                except Exception:
                    pass
    mem.seek(0)
    return mem.read()
